/**
 * @file test_app.c
 * @brief 主机端可重复验证测试。
 *
 * 编译：见 Makefile（make test）
 * 运行：./build/test_runner
 *
 * 覆盖：
 *   1. 正常采样周期：温度转换精度、帧格式、校验和
 *   2. I2C 瞬时故障：重试 + 总线恢复后成功
 *   3. I2C 持续故障：错误状态上报、错误计数、系统复位
 *   4. 温度越界检测
 *   5. 读数不稳定检测
 *   6. 低电量/临界电量：状态位、采样间隔自适应
 *   7. 看门狗喂狗
 *   8. 多周期循环
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "app.h"
#include "bsp_config.h"
#include "hal_mock.h"

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, msg) do {                                       \
    if (cond) { g_pass++; printf("  [PASS] %s\n", msg); }           \
    else { g_fail++; printf("  [FAIL] %s (line %d)\n", msg, __LINE__); } \
} while (0)

/* 从帧中解析温度（0.01 °C） */
static int16_t frame_temp(const uint8_t *f)
{
    return (int16_t)(((uint16_t)f[2] << 8) | f[3]);
}

/* 从帧中解析电池电压 */
static uint16_t frame_batt(const uint8_t *f)
{
    return (uint16_t)(((uint16_t)f[4] << 8) | f[5]);
}

/* 校验和验证 */
static int frame_checksum_ok(const uint8_t *f)
{
    uint8_t sum = 0;
    uint8_t i;
    for (i = 0; i < (uint8_t)(BSP_FRAME_LEN - 1U); i++) sum ^= f[i];
    return sum == f[BSP_FRAME_LEN - 1];
}

static void test_normal_cycle(void)
{
    const mock_stats_t *st;
    int rc;

    printf("\n[测试1] 正常采样周期\n");
    mock_stats_reset();
    mock_set_sensor_temp_centi(2525); /* 25.25 °C，TMP102 可精确表示 */
    mock_set_batt_mv(3700);

    rc = app_init();
    CHECK(rc == 0, "app_init 成功");

    rc = app_run_once();
    CHECK(rc == 0, "app_run_once 返回成功");

    st = mock_stats_get();
    CHECK(st->uart_frames_sent == 1, "发送了 1 帧");
    CHECK(st->last_frame[0] == BSP_FRAME_SYNC0, "同步字节 0 正确");
    CHECK(st->last_frame[1] == BSP_FRAME_SYNC1, "同步字节 1 正确");
    CHECK(frame_temp(st->last_frame) == 2525, "温度值 25.25°C 正确");
    CHECK(frame_batt(st->last_frame) == 3700, "电池电压 3700mV 正确");
    CHECK(st->last_frame[6] == APP_STATUS_OK, "状态字节为正常");
    CHECK(frame_checksum_ok(st->last_frame), "帧校验和正确");
    CHECK(st->wdg_refreshes >= 2, "看门狗至少喂了 2 次");
    CHECK(st->sleep_cycles == 1, "进入了 1 次低功耗");
    CHECK(st->last_sleep_ms == BSP_SAMPLE_INTERVAL_MS, "满电采样间隔 60s");
}

static void test_i2c_transient_fault(void)
{
    const mock_stats_t *st;
    int rc;

    printf("\n[测试2] I2C 瞬时故障后恢复\n");
    mock_stats_reset();
    mock_set_sensor_temp_centi(2000);
    (void)app_init();

    /* 前 2 次 I2C 操作失败，之后恢复 */
    mock_i2c_set_fail_next(2);

    rc = app_run_once();
    CHECK(rc == 0, "重试后采样成功");
    st = mock_stats_get();
    CHECK(st->i2c_bus_recoveries >= 1, "执行了总线恢复");
    CHECK(frame_temp(st->last_frame) == 2000, "恢复后温度正确");
    CHECK((st->last_frame[6] & APP_STATUS_SENSOR_ERR) == 0, "无传感器错误标志");
}

static void test_i2c_persistent_fault(void)
{
    const mock_stats_t *st;
    int rc;
    uint8_t i;

    printf("\n[测试3] I2C 持续故障导致系统复位\n");
    mock_stats_reset();
    (void)app_init();

    /* 让所有 I2C 操作都失败 */
    mock_i2c_set_fail_next(255);

    for (i = 0; i < APP_MAX_CONSECUTIVE_ERRORS; i++) {
        rc = app_run_once();
        if (rc == 0) break;
    }

    st = mock_stats_get();
    CHECK(st->resets_requested >= 1, "连续错误后请求系统复位");
    CHECK((st->last_frame[6] & APP_STATUS_SENSOR_ERR) != 0, "上报了传感器错误");
}

static void test_out_of_range(void)
{
    const mock_stats_t *st;
    int rc;

    printf("\n[测试4] 温度越界检测\n");
    mock_stats_reset();
    (void)app_init();

    mock_i2c_set_bad_range(true);
    rc = app_run_once();
    CHECK(rc != 0, "越界时返回错误");

    st = mock_stats_get();
    CHECK((st->last_frame[6] & APP_STATUS_RANGE_ERR) != 0, "上报了越界错误");
    CHECK(frame_temp(st->last_frame) == (int16_t)0x8000, "越界温度标记为无效值");
}

static void test_unstable_reading(void)
{
    const mock_stats_t *st;
    int rc;

    printf("\n[测试5] 读数不稳定检测\n");
    mock_stats_reset();
    (void)app_init();

    mock_i2c_set_unstable(true);
    rc = app_run_once();
    CHECK(rc != 0, "不稳定时返回错误");

    st = mock_stats_get();
    CHECK((st->last_frame[6] & APP_STATUS_SENSOR_ERR) != 0, "上报了传感器错误");
}

static void test_low_battery(void)
{
    const mock_stats_t *st;
    int rc;

    printf("\n[测试6] 低电量自适应\n");
    mock_stats_reset();
    mock_set_batt_mv(3300); /* 低电量 */
    (void)app_init();
    rc = app_run_once();
    CHECK(rc == 0, "低电量下仍正常采样");

    st = mock_stats_get();
    CHECK((st->last_frame[6] & APP_STATUS_BATT_LOW) != 0, "上报了低电量标志");
    CHECK(st->last_sleep_ms == BSP_SAMPLE_INTERVAL_LOW_BATT_MS, "低电量采样间隔延长到 5min");

    /* 临界电量 */
    mock_stats_reset();
    mock_set_batt_mv(2900);
    (void)app_init();
    (void)app_run_once();
    st = mock_stats_get();
    CHECK((st->last_frame[6] & APP_STATUS_BATT_CRIT) != 0, "上报了临界电量标志");
    CHECK(st->last_sleep_ms == BSP_SAMPLE_INTERVAL_LOW_BATT_MS * 2,
          "临界电量采样间隔延长到 10min");
}

static void test_multiple_cycles(void)
{
    const mock_stats_t *st;
    int i;

    printf("\n[测试7] 多周期循环稳定性\n");
    mock_stats_reset();
    mock_set_sensor_temp_centi(2200);
    (void)app_init();

    for (i = 0; i < 5; i++) {
        mock_set_sensor_temp_centi((int16_t)(2200 + i * 25));
        (void)app_run_once();
    }

    st = mock_stats_get();
    CHECK(st->uart_frames_sent == 5, "5 个周期发送了 5 帧");
    CHECK(st->sleep_cycles == 5, "5 个周期休眠 5 次");
    CHECK(st->resets_requested == 0, "无系统复位");
    CHECK(frame_temp(st->last_frame) == 2300, "最后一帧温度正确");
}

static void test_checksum_function(void)
{
    uint8_t frame[BSP_FRAME_LEN];
    uint8_t i;

    printf("\n[测试8] 校验和纯函数\n");
    app_build_frame(frame, -1234, 3650, APP_STATUS_OK);
    CHECK(frame[0] == 0xAA && frame[1] == 0x55, "同步头正确");
    CHECK(frame_temp(frame) == -1234, "负温度 -12.34°C 正确");
    CHECK(frame_batt(frame) == 3650, "电池电压正确");

    /* 手动验证校验和 */
    {
        uint8_t expected = 0;
        for (i = 0; i < BSP_FRAME_LEN - 1; i++) expected ^= frame[i];
        CHECK(frame[BSP_FRAME_LEN - 1] == expected, "校验和与手动计算一致");
    }
}

int main(void)
{
    printf("===== 温度采集固件主机验证 =====\n");

    test_normal_cycle();
    test_i2c_transient_fault();
    test_i2c_persistent_fault();
    test_out_of_range();
    test_unstable_reading();
    test_low_battery();
    test_multiple_cycles();
    test_checksum_function();

    printf("\n===== 结果：%d 通过，%d 失败 =====\n", g_pass, g_fail);
    return (g_fail == 0) ? 0 : 1;
}
