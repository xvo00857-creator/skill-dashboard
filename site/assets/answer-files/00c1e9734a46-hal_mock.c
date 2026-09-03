/**
 * @file hal_mock.c
 * @brief 主机模拟 HAL 实现。
 *
 * 在主机上用 gcc/clang 编译时替代 hal_target.c，使驱动和应用逻辑
 * 无需真实硬件即可编译、运行和验证。不依赖任何外部库。
 */
#ifdef UNIT_TEST

#include "hal.h"
#include "hal_mock.h"
#include "bsp_config.h"
#include <string.h>

/* ---- 模拟状态 ---- */
static uint32_t g_tick = 0;
static uint16_t g_batt_mv = 3700;
static int16_t  g_sensor_temp_centi = 2500; /* 25.00 °C */
static uint8_t  g_i2c_fail_count = 0;
static bool     g_bad_range = false;
static bool     g_unstable = false;
static bool     g_rtc_wakeup = false;
static uint32_t g_rtc_period_ms = 0;

static mock_stats_t g_stats;

/* 模拟 TMP102 寄存器 */
static uint8_t  g_reg_pointer = 0;
static uint8_t  g_tmp102_config[2] = {0x60, 0xA0}; /* SD=1, 12bit */
static uint8_t  g_temp_read_count = 0;  /* 温度读取次数，用于模拟不稳定 */

/* 内部：根据当前模拟温度生成 TMP102 原始值 */
static uint16_t make_tmp102_raw(int16_t centi)
{
    /* centi (0.01°C) -> TMP102 raw: raw = centi / 0.0625 = centi * 16 */
    int32_t raw12 = ((int32_t)centi * 16) / 100;
    return (uint16_t)((raw12 & 0x0FFF) << 4);
}

void mock_stats_reset(void)
{
    memset(&g_stats, 0, sizeof(g_stats));
    g_tick = 0;
    g_batt_mv = 3700;
    g_sensor_temp_centi = 2500;
    g_i2c_fail_count = 0;
    g_bad_range = false;
    g_unstable = false;
    g_rtc_wakeup = false;
    g_rtc_period_ms = 0;
    g_temp_read_count = 0;
}

const mock_stats_t *mock_stats_get(void) { return &g_stats; }

void mock_i2c_set_fail_next(uint8_t times) { g_i2c_fail_count = times; }
void mock_i2c_set_bad_range(bool en) { g_bad_range = en; }
void mock_i2c_set_unstable(bool en) { g_unstable = en; }
void mock_set_batt_mv(uint16_t mv) { g_batt_mv = mv; }
void mock_set_sensor_temp_centi(int16_t c) { g_sensor_temp_centi = c; }
void mock_rtc_trigger_wakeup(void) { g_rtc_wakeup = true; }
void mock_advance_ms(uint32_t ms) { g_tick += ms; }

/* ---- HAL 接口实现 ---- */

void hal_critical_enter(void) { /* 主机单线程，无需关中断 */ }
void hal_critical_exit(void)  { }

hal_status_t hal_i2c_init(void) { return HAL_OK; }

hal_status_t hal_i2c_write_reg(uint8_t dev, uint8_t reg,
                               const uint8_t *data, uint16_t len)
{
    (void)dev;
    g_stats.i2c_ops++;

    if (g_i2c_fail_count > 0) {
        g_i2c_fail_count--;
        return HAL_ERR_TIMEOUT;
    }

    g_reg_pointer = reg;

    if (reg == BSP_TMP102_REG_CONFIG && len == 2) {
        g_tmp102_config[0] = data[0];
        g_tmp102_config[1] = data[1];
    }
    return HAL_OK;
}

hal_status_t hal_i2c_read_reg(uint8_t dev, uint8_t reg,
                              uint8_t *buf, uint16_t len)
{
    (void)dev;
    g_stats.i2c_ops++;

    if (g_i2c_fail_count > 0) {
        g_i2c_fail_count--;
        return HAL_ERR_TIMEOUT;
    }

    if (reg == BSP_TMP102_REG_TEMP && len == 2) {
        int16_t temp = g_sensor_temp_centi;
        uint16_t raw;

        if (g_bad_range) {
            temp = 20000; /* 200 °C，越界 */
        }
        raw = make_tmp102_raw(temp);

        /* 偶数次读取（第 2、4、... 次）偏移，模拟两次读数不一致 */
        if (g_unstable && (g_temp_read_count & 1U)) {
            raw = make_tmp102_raw((int16_t)(temp + 50)); /* 差 0.5 °C */
        }
        g_temp_read_count++;

        buf[0] = (uint8_t)(raw >> 8);
        buf[1] = (uint8_t)(raw & 0xFF);
    } else if (reg == BSP_TMP102_REG_CONFIG && len == 2) {
        buf[0] = g_tmp102_config[0];
        buf[1] = g_tmp102_config[1];
    } else {
        memset(buf, 0, len);
    }
    return HAL_OK;
}

void hal_i2c_bus_recover(void)
{
    g_stats.i2c_bus_recoveries++;
}

hal_status_t hal_uart_init(void) { return HAL_OK; }

hal_status_t hal_uart_send(const uint8_t *data, uint16_t len)
{
    if (len > sizeof(g_stats.last_frame)) {
        len = sizeof(g_stats.last_frame);
    }
    memcpy(g_stats.last_frame, data, len);
    g_stats.last_frame_len = (uint8_t)len;
    g_stats.uart_frames_sent++;
    return HAL_OK;
}

void hal_rtc_wakeup_init(uint32_t period_ms)
{
    g_rtc_period_ms = period_ms;
    g_rtc_wakeup = false;
}

void hal_rtc_wakeup_clear(void) { g_rtc_wakeup = false; }

bool hal_rtc_wakeup_flag_get(void) { return g_rtc_wakeup; }

void hal_power_enter_stop(void)
{
    /* 模拟 Stop：推进时间到唤醒时刻 */
    g_stats.sleep_cycles++;
    g_stats.last_sleep_ms = g_rtc_period_ms;
    g_tick += g_rtc_period_ms;
    /* 测试中由 mock_rtc_trigger_wakeup 或自动唤醒 */
    g_rtc_wakeup = true;
}

void hal_clock_restore(void) { /* 模拟：无需恢复 */ }

void hal_watchdog_init(void) { g_stats.wdg_refreshes = 0; }
void hal_watchdog_refresh(void) { g_stats.wdg_refreshes++; }

void hal_gpio_init(void) { }
void hal_led_set(bool on) { (void)on; }

void hal_adc_init(void) { }

uint16_t hal_adc_read_batt_mv(void) { return g_batt_mv; }

uint32_t hal_get_tick_ms(void) { return g_tick; }

void hal_delay_ms(uint32_t ms) { g_tick += ms; }

void hal_system_reset(void)
{
    g_stats.resets_requested++;
    /* 不真正退出，让测试可以断言 */
}

void hal_peripherals_suspend(void) { }
void hal_peripherals_resume(void) { }

#endif /* UNIT_TEST */
