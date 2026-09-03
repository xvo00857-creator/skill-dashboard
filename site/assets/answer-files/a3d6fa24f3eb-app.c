/**
 * @file app.c
 * @brief 温度采集应用层。
 *
 * 架构：裸机超级循环 + RTC 唤醒 + Stop 模式。
 * 不使用 FreeRTOS——本设备只有一个周期任务，RTOS 会徒增 flash/RAM 开销。
 *
 * 状态机：INIT -> SAMPLE -> VALIDATE -> TRANSMIT -> SLEEP -> (RTC 唤醒) -> SAMPLE
 * 异常：任意步骤失败 -> 错误计数 -> 总线恢复/降频 -> 继续运行（不阻塞）
 */
#include "app.h"
#include "hal.h"
#include "bsp_config.h"
#include "temp_sensor.h"
#include "power_mgr.h"

static volatile uint8_t  g_error_count = 0;
static volatile uint8_t  g_app_status  = APP_STATUS_OK;

/* 上电原因检测（实际目标读取 RCC_CSR，模拟层可注入） */
static bool was_watchdog_reset(void)
{
    /* 目标实现：return (RCC->CSR & RCC_CSR_IWDGRSTF) != 0; */
    return false;
}

uint8_t app_calc_checksum(const uint8_t *frame, uint8_t len)
{
    uint8_t sum = 0;
    uint8_t i;
    for (i = 0; i < len; i++) {
        sum ^= frame[i];
    }
    return sum;
}

void app_build_frame(uint8_t *frame, int16_t temp_centi,
                     uint16_t batt_mv, uint8_t status)
{
    frame[0] = BSP_FRAME_SYNC0;
    frame[1] = BSP_FRAME_SYNC1;
    frame[2] = (uint8_t)((uint16_t)temp_centi >> 8);
    frame[3] = (uint8_t)((uint16_t)temp_centi & 0xFF);
    frame[4] = (uint8_t)(batt_mv >> 8);
    frame[5] = (uint8_t)(batt_mv & 0xFF);
    frame[6] = status;
    frame[7] = app_calc_checksum(frame, BSP_FRAME_LEN - 1U);
}

int app_init(void)
{
    hal_status_t st;

    /* 1. 时钟和 GPIO（目标实现中先配时钟树） */
    hal_clock_restore();
    hal_gpio_init();

    /* 2. UART */
    st = hal_uart_init();
    if (st != HAL_OK) {
        return (int)st;
    }

    /* 3. ADC（电池检测） */
    hal_adc_init();

    /* 4. 温度传感器 */
    st = temp_sensor_init();
    if (st != HAL_OK) {
        return (int)st;
    }

    /* 5. 电源管理 */
    power_mgr_init();

    /* 6. 看门狗（最后启动，避免初始化期间超时） */
    hal_watchdog_init();

    /* 7. 标记看门狗复位 */
    if (was_watchdog_reset()) {
        g_app_status |= APP_STATUS_WDG_RESET;
    }

    return 0;
}

int app_run_once(void)
{
    temp_reading_t reading;
    temp_status_t tstat;
    uint8_t frame[BSP_FRAME_LEN];
    batt_state_t batt;
    uint32_t interval;
    uint8_t status;
    hal_status_t uart_st;

    /* 喂狗，表明本周期开始 */
    hal_watchdog_refresh();

    /* 读电池电压（即使传感器失败也上报电池状态） */
    reading.batt_mv = hal_adc_read_batt_mv();
    batt = power_mgr_get_batt_state(reading.batt_mv);

    /* 采样 */
    tstat = temp_sensor_read(&reading);

    if (tstat != TEMP_OK) {
        g_error_count++;

        if (tstat == TEMP_ERR_RANGE) {
            g_app_status |= APP_STATUS_RANGE_ERR;
        } else {
            g_app_status |= APP_STATUS_SENSOR_ERR;
        }

        /* 错误时填充无效温度（0x8000 表示无效） */
        reading.temp_centi = (int16_t)0x8000;

        /* I2C 总线恢复 */
        if (tstat == TEMP_ERR_I2C) {
            hal_i2c_bus_recover();
        }

        /* 连续错误过多：请求系统复位 */
        if (g_error_count >= APP_MAX_CONSECUTIVE_ERRORS) {
            hal_system_reset();
            /* 不会返回 */
        }
    } else {
        g_error_count = 0;
        g_app_status &= (uint8_t)~(APP_STATUS_SENSOR_ERR |
                                   APP_STATUS_RANGE_ERR |
                                   APP_STATUS_CRC_ERR);
    }

    /* 合并电池状态到当前状态字 */
    status = g_app_status;
    if (batt == BATT_LOW) {
        status |= APP_STATUS_BATT_LOW;
        g_app_status |= APP_STATUS_BATT_LOW;
    } else if (batt == BATT_CRITICAL) {
        status |= APP_STATUS_BATT_CRIT;
        g_app_status |= APP_STATUS_BATT_CRIT;
    } else {
        /* 电池恢复后清除低电标志 */
        g_app_status &= (uint8_t)~(APP_STATUS_BATT_LOW |
                                   APP_STATUS_BATT_CRIT);
    }

    /* 组帧并发送 */
    app_build_frame(frame, reading.temp_centi, reading.batt_mv, status);
    uart_st = hal_uart_send(frame, BSP_FRAME_LEN);
    if (uart_st != HAL_OK) {
        /* UART 失败不致命，下一周期重试 */
        g_error_count++;
    }

    /* LED 指示：有错误时快闪 */
    if (status & (APP_STATUS_SENSOR_ERR | APP_STATUS_RANGE_ERR)) {
        uint8_t i;
        for (i = 0; i < BSP_LED_ERROR_BLINKS; i++) {
            hal_led_set(true);
            hal_delay_ms(50);
            hal_led_set(false);
            hal_delay_ms(50);
        }
    }

    /* 喂狗，表明本周期正常完成 */
    hal_watchdog_refresh();

    /* 根据电池状态选择采样间隔，进入低功耗 */
    interval = power_mgr_get_sample_interval_ms(batt);
    power_mgr_sleep_until_next(interval);

    return (tstat == TEMP_OK) ? 0 : (int)tstat;
}

void app_main_loop(void)
{
    if (app_init() != 0) {
        /* 初始化失败：闪 LED 并等待看门狗复位 */
        for (;;) {
            hal_led_set(true);
            hal_delay_ms(100);
            hal_led_set(false);
            hal_delay_ms(100);
            hal_watchdog_refresh();
        }
    }

    for (;;) {
        (void)app_run_once();
    }
}
