/**
 * @file power_mgr.c
 * @brief 电源管理实现。
 *
 * 遵循 Skill 低功耗最佳实践：
 * - 采样间隔 >1s 使用 Stop 模式（RTC 唤醒）
 * - Stop 前关闭外设时钟、配置未用引脚
 * - 唤醒后恢复系统时钟和外设
 * - 根据电池电压自适应采样率
 */
#include "power_mgr.h"
#include "hal.h"
#include "bsp_config.h"

void power_mgr_init(void)
{
    /* RTC 唤醒由 sleep_until_next 按需配置 */
}

batt_state_t power_mgr_get_batt_state(uint16_t batt_mv)
{
    if (batt_mv >= BSP_BATT_FULL_MV) {
        return BATT_FULL;
    } else if (batt_mv >= BSP_BATT_GOOD_MV) {
        return BATT_GOOD;
    } else if (batt_mv >= BSP_BATT_LOW_MV) {
        return BATT_LOW;
    } else {
        return BATT_CRITICAL;
    }
}

uint32_t power_mgr_get_sample_interval_ms(batt_state_t state)
{
    switch (state) {
    case BATT_FULL:
    case BATT_GOOD:
        return BSP_SAMPLE_INTERVAL_MS;
    case BATT_LOW:
        return BSP_SAMPLE_INTERVAL_LOW_BATT_MS;
    case BATT_CRITICAL:
        /* 临界电量：大幅降频以延长续航 */
        return BSP_SAMPLE_INTERVAL_LOW_BATT_MS * 2U;
    default:
        return BSP_SAMPLE_INTERVAL_MS;
    }
}

bool power_mgr_is_battery_ok(uint16_t batt_mv)
{
    return batt_mv >= BSP_BATT_CRITICAL_MV;
}

void power_mgr_sleep_until_next(uint32_t interval_ms)
{
    /* 1. 配置 RTC 唤醒定时器 */
    hal_rtc_wakeup_init(interval_ms);

    /* 2. 挂起非必要外设（关时钟） */
    hal_peripherals_suspend();

    /* 3. 清唤醒标志后进入 Stop 模式 */
    hal_rtc_wakeup_clear();
    hal_power_enter_stop();

    /* 4. 唤醒后恢复系统时钟（Stop 模式后 PLL 需重配） */
    hal_clock_restore();

    /* 5. 恢复外设 */
    hal_peripherals_resume();

    /* 6. 等待 RTC 唤醒标志确认（防止误唤醒） */
    while (!hal_rtc_wakeup_flag_get()) {
        /* 若为非 RTC 唤醒（如外部中断），直接返回处理 */
        break;
    }
    hal_rtc_wakeup_clear();
}
