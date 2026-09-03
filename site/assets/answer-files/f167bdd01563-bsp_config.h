/**
 * @file bsp_config.h
 * @brief 板级配置——所有硬件相关常量集中于此，禁止在驱动/应用中硬编码。
 *
 * 目标平台：STM32F4 系列（与 Skill 参考代码一致，寄存器位域需对照数据手册确认）。
 * 温度传感器：TMP102（I2C，12 位，0.0625 °C/LSB）。
 */
#ifndef BSP_CONFIG_H
#define BSP_CONFIG_H

#include <stdint.h>

/* ---- 时钟 ---- */
#define BSP_SYSCLK_HZ           168000000U
#define BSP_APB1_HZ             42000000U
#define BSP_LSI_HZ              32000U

/* ---- I2C1（PB6=SCL, PB7=SDA）---- */
#define BSP_I2C_SPEED_HZ        100000U
#define BSP_I2C_TIMEOUT_MS      50U

/* ---- TMP102 温度传感器 ---- */
#define BSP_TMP102_ADDR         0x48U   /* 7 位地址 */
#define BSP_TMP102_REG_TEMP     0x00U
#define BSP_TMP102_REG_CONFIG   0x01U
#define BSP_TMP102_REG_TLOW     0x02U
#define BSP_TMP102_REG_THIGH    0x03U
/* TMP102 12 位模式：1 LSB = 0.0625 °C，原始值为 16 位有符号左移 4 位 */
#define BSP_TMP102_RESOLUTION   625     /* 0.0625 °C 以 0.0001 °C 为单位 */
#define BSP_TEMP_MIN_CENTI      (-4000) /* -40.00 °C，单位 0.01 °C */
#define BSP_TEMP_MAX_CENTI      12500   /* 125.00 °C */
#define BSP_TEMP_STABLE_DIFF    10      /* 两次读数一致性阈值，0.01 °C */

/* ---- UART2（PA2=TX, PA3=RX）---- */
#define BSP_UART_BAUD           9600U
#define BSP_UART_TIMEOUT_MS     100U

/* ---- RTC 唤醒 ---- */
#define BSP_SAMPLE_INTERVAL_MS  60000U  /* 默认 60 秒采样一次 */
#define BSP_SAMPLE_INTERVAL_LOW_BATT_MS 300000U /* 低电量时 5 分钟 */

/* ---- 独立看门狗 IWDG（LSI 约 32 kHz）---- */
#define BSP_IWDG_TIMEOUT_MS     4000U
#define BSP_IWDG_PR             2U      /* /64 分频 */
#define BSP_IWDG_RLR            2000U   /* 32000/64/2000 = 4 s */

/* ---- 电池电压（ADC 通道 0，2:1 分压）---- */
#define BSP_BATT_DIVIDER        2U
#define BSP_BATT_FULL_MV        3700U
#define BSP_BATT_GOOD_MV        3400U
#define BSP_BATT_LOW_MV         3200U
#define BSP_BATT_CRITICAL_MV    3000U
#define BSP_ADC_VREF_MV         3300U
#define BSP_ADC_MAX             4095U   /* 12 位 */

/* ---- 采样重试 ---- */
#define BSP_SENSOR_MAX_RETRIES  3U

/* ---- 应用帧 ---- */
#define BSP_FRAME_SYNC0         0xAAU
#define BSP_FRAME_SYNC1         0x55U
#define BSP_FRAME_LEN           8U      /* 同步2+温度2+电池2+状态1+校验1 */

/* ---- LED（PA5）---- */
#define BSP_LED_ERROR_BLINKS    3U

#endif /* BSP_CONFIG_H */
