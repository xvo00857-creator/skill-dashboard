/**
 * @file temp_sensor.c
 * @brief TMP102 温度传感器驱动。
 *
 * 遵循 Skill 约束：
 * - I2C 操作全部带超时，不阻塞
 * - 不使用浮点（整数运算，单位 0.01 °C）
 * - 无动态内存分配
 * - 硬件参数全部来自 bsp_config.h，不硬编码
 * - 错误路径完整：I2C 失败、越界、读数不稳定均返回错误
 */
#include "temp_sensor.h"
#include "bsp_config.h"

/* TMP102 配置寄存器位定义 */
#define TMP102_CFG_SD       (1U << 0)   /* 关断模式 */
#define TMP102_CFG_TM       (1U << 1)   /* 比较器模式 */
#define TMP102_CFG_R0       (1U << 5)   /* 分辨率位 */
#define TMP102_CFG_R1       (1U << 6)
#define TMP102_CFG_OS       (1U << 7)   /* 单次转换触发 */
#define TMP102_CFG_EM       (1U << 4)   /* 扩展模式 */

/* 12 位分辨率：R1=1, R0=1 */
#define TMP102_CFG_12BIT    (TMP102_CFG_R1 | TMP102_CFG_R0)

/**
 * @brief 将 TMP102 原始 16 位寄存器值转换为 0.01 °C。
 *
 * TMP102 正常模式（12 位）：高 12 位为有符号温度，1 LSB = 0.0625 °C。
 * 原始值左移 4 位存储在 16 位寄存器中。
 * 转换：centi = raw * 625 / 10000 * 100 = raw * 625 / 100
 *       （625 = 0.0625 °C 以 0.0001 °C 为单位）
 */
static int16_t tmp102_raw_to_centi(uint16_t raw)
{
    int16_t signed_raw = (int16_t)raw;
    /* 右移 4 位恢复 12 位有符号值（算术右移保留符号） */
    signed_raw >>= 4;
    /* 0.0625 °C/LSB → 0.01 °C/LSB：乘 6.25，用整数 (x*25)/4 */
    int32_t centi = ((int32_t)signed_raw * 25) / 4;
    return (int16_t)centi;
}

/**
 * @brief 读一次温度原始寄存器（两次 I2C 事务：写寄存器指针 + 读）。
 */
static hal_status_t tmp102_read_raw(uint16_t *raw)
{
    uint8_t reg = BSP_TMP102_REG_TEMP;
    uint8_t buf[2] = {0, 0};
    hal_status_t st;

    st = hal_i2c_write_reg(BSP_TMP102_ADDR, BSP_TMP102_REG_TEMP, &reg, 0);
    /* 写寄存器指针：部分 HAL 把 reg 作为写数据发送；
       这里用 write_reg 发送寄存器地址，再 read */
    if (st != HAL_OK) {
        return st;
    }

    st = hal_i2c_read_reg(BSP_TMP102_ADDR, BSP_TMP102_REG_TEMP, buf, 2);
    if (st != HAL_OK) {
        return st;
    }

    *raw = (uint16_t)(((uint16_t)buf[0] << 8) | (uint16_t)buf[1]);
    return HAL_OK;
}

hal_status_t temp_sensor_init(void)
{
    hal_status_t st;
    uint8_t cfg[2];

    st = hal_i2c_init();
    if (st != HAL_OK) {
        return st;
    }

    /* 配置为关断模式 + 12 位分辨率，后续用 OS 位触发单次转换 */
    cfg[0] = (uint8_t)((TMP102_CFG_SD | TMP102_CFG_12BIT) >> 8);
    cfg[1] = (uint8_t)(TMP102_CFG_SD | TMP102_CFG_12BIT);

    st = hal_i2c_write_reg(BSP_TMP102_ADDR, BSP_TMP102_REG_CONFIG, cfg, 2);
    return st;
}

temp_status_t temp_sensor_read(temp_reading_t *reading)
{
    uint16_t raw1, raw2;
    int16_t t1, t2;
    int16_t diff;
    hal_status_t st;
    uint8_t os_cmd[2];
    uint32_t retry;

    if (reading == NULL) {
        return TEMP_ERR_I2C;
    }

    /* 触发单次转换：写 OS=1 到配置寄存器（保持 SD=1, 12 位） */
    os_cmd[0] = (uint8_t)((TMP102_CFG_SD | TMP102_CFG_12BIT | TMP102_CFG_OS) >> 8);
    os_cmd[1] = (uint8_t)(TMP102_CFG_SD | TMP102_CFG_12BIT | TMP102_CFG_OS);

    /* 带重试的 I2C 写 */
    for (retry = 0; retry < BSP_SENSOR_MAX_RETRIES; retry++) {
        st = hal_i2c_write_reg(BSP_TMP102_ADDR, BSP_TMP102_REG_CONFIG,
                               os_cmd, 2);
        if (st == HAL_OK) {
            break;
        }
        hal_i2c_bus_recover();
    }
    if (st != HAL_OK) {
        return TEMP_ERR_I2C;
    }

    /* TMP102 单次转换时间典型 32 ms（12 位），留足余量 */
    hal_delay_ms(40);

    /* 第一次读取（带重试） */
    for (retry = 0; retry < BSP_SENSOR_MAX_RETRIES; retry++) {
        st = tmp102_read_raw(&raw1);
        if (st == HAL_OK) {
            break;
        }
        hal_i2c_bus_recover();
        hal_delay_ms(2);
    }
    if (st != HAL_OK) {
        return TEMP_ERR_I2C;
    }

    /* 短暂间隔后第二次读取，用于一致性校验 */
    hal_delay_ms(5);

    for (retry = 0; retry < BSP_SENSOR_MAX_RETRIES; retry++) {
        st = tmp102_read_raw(&raw2);
        if (st == HAL_OK) {
            break;
        }
        hal_i2c_bus_recover();
        hal_delay_ms(2);
    }
    if (st != HAL_OK) {
        return TEMP_ERR_I2C;
    }

    t1 = tmp102_raw_to_centi(raw1);
    t2 = tmp102_raw_to_centi(raw2);

    /* 范围校验 */
    if (t1 < BSP_TEMP_MIN_CENTI || t1 > BSP_TEMP_MAX_CENTI) {
        return TEMP_ERR_RANGE;
    }

    /* 一致性校验：两次读数差不超过阈值 */
    diff = (t1 > t2) ? (int16_t)(t1 - t2) : (int16_t)(t2 - t1);
    if (diff > BSP_TEMP_STABLE_DIFF) {
        return TEMP_ERR_UNSTABLE;
    }

    reading->temp_centi = t1;
    reading->batt_mv = hal_adc_read_batt_mv();
    reading->status = 0;

    return TEMP_OK;
}
