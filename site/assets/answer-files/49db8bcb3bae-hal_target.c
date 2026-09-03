/**
 * @file hal_target.c
 * @brief STM32F4 目标 HAL 实现（寄存器级）。
 *
 * 本文件仅在 ARM 交叉编译时参与构建，主机测试不编译。
 * 寄存器位域用法参照 Skill 参考代码及 STM32F4 参考手册；
 * 移植到具体型号时需对照数据手册确认（Skill 工作流第 4 步）。
 *
 * 注意：本文件中的寄存器值为设计参考，上硬件前必须用逻辑分析仪/示波器验证时序。
 */
#ifdef STM32_TARGET

#include "hal.h"
#include "bsp_config.h"
#include "stm32f4xx.h"

/* ---- 临界区 ---- */
void hal_critical_enter(void) { __disable_irq(); }
void hal_critical_exit(void)  { __enable_irq(); }

/* ---- 系统时钟（168 MHz，PLL）---- */
void hal_clock_restore(void)
{
    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY)) { }

    FLASH->ACR = FLASH_ACR_PRFTEN | FLASH_ACR_ICEN |
                 FLASH_ACR_DCEN | FLASH_ACR_LATENCY_5WS;

    RCC->PLLCFGR = (8U << RCC_PLLCFGR_PLLM_Pos) |
                   (336U << RCC_PLLCFGR_PLLN_Pos) |
                   (0U << RCC_PLLCFGR_PLLP_Pos) |
                   RCC_PLLCFGR_PLLSRC_HSE |
                   (7U << RCC_PLLCFGR_PLLQ_Pos);

    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) { }

    RCC->CFGR = RCC_CFGR_HPRE_DIV1 | RCC_CFGR_PPRE1_DIV4 |
                RCC_CFGR_PPRE2_DIV2;
    RCC->CFGR |= RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) { }

    SystemCoreClock = BSP_SYSCLK_HZ;
}

/* ---- GPIO ---- */
void hal_gpio_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN |
                    RCC_AHB1ENR_GPIOCEN;

    /* PA5 LED 推挽输出 */
    GPIOA->MODER &= ~(3U << (5U * 2U));
    GPIOA->MODER |=  (1U << (5U * 2U));
    GPIOA->OTYPER &= ~(1U << 5U);

    /* PA2/PA3 UART2 复用 */
    GPIOA->MODER |= (2U << (2U * 2U)) | (2U << (3U * 2U));
    GPIOA->AFR[0] |= (7U << (2U * 4U)) | (7U << (3U * 4U));

    /* PB6/PB7 I2C1 复用开漏 */
    GPIOB->MODER |= (2U << (6U * 2U)) | (2U << (7U * 2U));
    GPIOB->OTYPER |= (1U << 6U) | (1U << 7U);
    GPIOB->PUPDR |= (1U << (6U * 2U)) | (1U << (7U * 2U));
    GPIOB->AFR[0] |= (4U << (6U * 4U)) | (4U << (7U * 4U));

    /* 未使用引脚设为模拟模式以降低漏电 */
    GPIOC->MODER = 0xFFFFFFFFU;
}

void hal_led_set(bool on)
{
    if (on) {
        GPIOA->BSRR = (1U << 5U);
    } else {
        GPIOA->BSRR = (1U << (5U + 16U));
    }
}

/* ---- I2C1 ---- */
hal_status_t hal_i2c_init(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_I2C1EN;

    I2C1->CR1 |= I2C_CR1_SWRST;
    I2C1->CR1 &= ~I2C_CR1_SWRST;

    I2C1->CR2 = BSP_APB1_HZ / 1000000U;  /* 42 MHz */
    I2C1->CCR = BSP_APB1_HZ / (2U * BSP_I2C_SPEED_HZ);
    I2C1->TRISE = (BSP_APB1_HZ / 1000000U) + 1U;

    I2C1->CR1 |= I2C_CR1_PE;
    return HAL_OK;
}

/* 带超时的 I2C 等待宏 */
#define I2C_WAIT(cond, timeout_ms)                                    \
    do {                                                              \
        uint32_t _t = (timeout_ms) * 100U;                            \
        while (!(cond) && --_t) { __NOP(); }                          \
        if (_t == 0) return HAL_ERR_TIMEOUT;                          \
    } while (0)

hal_status_t hal_i2c_write_reg(uint8_t dev, uint8_t reg,
                               const uint8_t *data, uint16_t len)
{
    uint16_t i;

    I2C1->CR1 |= I2C_CR1_START;
    I2C_WAIT(I2C1->SR1 & I2C_SR1_SB, BSP_I2C_TIMEOUT_MS);

    I2C1->DR = (uint8_t)(dev << 1);
    I2C_WAIT(I2C1->SR1 & I2C_SR1_ADDR, BSP_I2C_TIMEOUT_MS);
    (void)I2C1->SR1; (void)I2C1->SR2;

    I2C1->DR = reg;
    I2C_WAIT(I2C1->SR1 & I2C_SR1_TXE, BSP_I2C_TIMEOUT_MS);

    for (i = 0; i < len; i++) {
        I2C1->DR = data[i];
        I2C_WAIT(I2C1->SR1 & I2C_SR1_TXE, BSP_I2C_TIMEOUT_MS);
    }

    I2C_WAIT(I2C1->SR1 & I2C_SR1_BTF, BSP_I2C_TIMEOUT_MS);
    I2C1->CR1 |= I2C_CR1_STOP;
    return HAL_OK;
}

hal_status_t hal_i2c_read_reg(uint8_t dev, uint8_t reg,
                              uint8_t *buf, uint16_t len)
{
    uint16_t i;

    /* 先写寄存器指针 */
    I2C1->CR1 |= I2C_CR1_START;
    I2C_WAIT(I2C1->SR1 & I2C_SR1_SB, BSP_I2C_TIMEOUT_MS);
    I2C1->DR = (uint8_t)(dev << 1);
    I2C_WAIT(I2C1->SR1 & I2C_SR1_ADDR, BSP_I2C_TIMEOUT_MS);
    (void)I2C1->SR1; (void)I2C1->SR2;
    I2C1->DR = reg;
    I2C_WAIT(I2C1->SR1 & I2C_SR1_BTF, BSP_I2C_TIMEOUT_MS);

    /* 重复起始读 */
    I2C1->CR1 |= I2C_CR1_START;
    I2C_WAIT(I2C1->SR1 & I2C_SR1_SB, BSP_I2C_TIMEOUT_MS);
    I2C1->DR = (uint8_t)((dev << 1) | 1U);
    I2C_WAIT(I2C1->SR1 & I2C_SR1_ADDR, BSP_I2C_TIMEOUT_MS);
    (void)I2C1->SR1; (void)I2C1->SR2;

    if (len == 1U) {
        I2C1->CR1 &= ~I2C_CR1_ACK;
        I2C1->CR1 |= I2C_CR1_STOP;
        I2C_WAIT(I2C1->SR1 & I2C_SR1_RXNE, BSP_I2C_TIMEOUT_MS);
        buf[0] = (uint8_t)I2C1->DR;
    } else {
        I2C1->CR1 |= I2C_CR1_ACK;
        for (i = 0; i < len; i++) {
            if (i == len - 1U) {
                I2C1->CR1 &= ~I2C_CR1_ACK;
                I2C1->CR1 |= I2C_CR1_STOP;
            }
            I2C_WAIT(I2C1->SR1 & I2C_SR1_RXNE, BSP_I2C_TIMEOUT_MS);
            buf[i] = (uint8_t)I2C1->DR;
        }
    }
    return HAL_OK;
}

void hal_i2c_bus_recover(void)
{
    /* 9 个 SCL 脉冲解锁卡死的从机 */
    uint8_t i;
    /* 简化实现：复位 I2C 外设 */
    I2C1->CR1 |= I2C_CR1_SWRST;
    for (i = 0; i < 9U; i++) { __NOP(); }
    I2C1->CR1 &= ~I2C_CR1_SWRST;
    I2C1->CR1 |= I2C_CR1_PE;
}

/* ---- UART2 ---- */
hal_status_t hal_uart_init(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;
    USART2->BRR = BSP_APB1_HZ / BSP_UART_BAUD;
    USART2->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
    return HAL_OK;
}

hal_status_t hal_uart_send(const uint8_t *data, uint16_t len)
{
    uint16_t i;
    uint32_t t;
    for (i = 0; i < len; i++) {
        t = BSP_UART_TIMEOUT_MS * 100U;
        while (!(USART2->SR & USART_SR_TXE) && --t) { }
        if (t == 0) return HAL_ERR_TIMEOUT;
        USART2->DR = data[i];
    }
    return HAL_OK;
}

/* ---- RTC 唤醒 ---- */
void hal_rtc_wakeup_init(uint32_t period_ms)
{
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    PWR->CR |= PWR_CR_DBP;

    RCC->CSR |= RCC_CSR_LSION;
    while (!(RCC->CSR & RCC_CSR_LSIRDY)) { }

    RCC->BDCR |= RCC_BDCR_RTCSEL_0;
    RCC->BDCR |= RCC_BDCR_RTCEN;

    RTC->WPR = 0xCA; RTC->WPR = 0x53;
    RTC->CR &= ~RTC_CR_WUTE;
    while (!(RTC->ISR & RTC_ISR_WUTWF)) { }

    /* LSI 约 32 kHz，唤醒重装值 = period_ms * 32 */
    RTC->WUTR = (period_ms * (BSP_LSI_HZ / 1000U)) - 1U;
    RTC->CR |= RTC_CR_WUTIE | RTC_CR_WUTE;

    EXTI->IMR |= EXTI_IMR_MR22;
    EXTI->RTSR |= EXTI_RTSR_TR22;
    NVIC_EnableIRQ(RTC_WKUP_IRQn);
}

void hal_rtc_wakeup_clear(void)
{
    RTC->ISR &= ~RTC_ISR_WUTF;
    EXTI->PR = EXTI_PR_PR22;
}

bool hal_rtc_wakeup_flag_get(void)
{
    return (RTC->ISR & RTC_ISR_WUTF) != 0U;
}

/* RTC 唤醒中断：仅清标志，不做处理（短 ISR） */
void RTC_WKUP_IRQHandler(void)
{
    if (RTC->ISR & RTC_ISR_WUTF) {
        RTC->ISR &= ~RTC_ISR_WUTF;
        EXTI->PR = EXTI_PR_PR22;
    }
}

/* ---- 低功耗 ---- */
void hal_power_enter_stop(void)
{
    PWR->CR |= PWR_CR_CWUF;
    PWR->CR |= PWR_CR_LPDS;
    PWR->CR &= ~PWR_CR_PDDS;
    SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
    __WFI();
}

/* ---- 看门狗 ---- */
void hal_watchdog_init(void)
{
    IWDG->KR = 0x5555U;
    IWDG->PR = BSP_IWDG_PR;
    IWDG->RLR = BSP_IWDG_RLR;
    IWDG->KR = 0xAAAAU;
    IWDG->KR = 0xCCCCU;
}

void hal_watchdog_refresh(void)
{
    IWDG->KR = 0xAAAAU;
}

/* ---- ADC（电池电压）---- */
void hal_adc_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    ADC1->CR1 = 0;
    ADC1->CR2 = 0;
}

uint16_t hal_adc_read_batt_mv(void)
{
    uint32_t t;
    uint16_t raw;

    ADC1->CR2 |= ADC_CR2_ADON;
    for (t = 0; t < 1000U; t++) { __NOP(); }

    ADC1->SQR3 = 0U; /* 通道 0 */
    ADC1->CR2 |= ADC_CR2_SWSTART;

    t = 100000U;
    while (!(ADC1->SR & ADC_SR_EOC) && --t) { }
    raw = (uint16_t)ADC1->DR;

    ADC1->CR2 &= ~ADC_CR2_ADON;

    return (uint16_t)(((uint32_t)BSP_ADC_VREF_MV * raw / BSP_ADC_MAX)
                      * BSP_BATT_DIVIDER);
}

/* ---- 外设门控 ---- */
void hal_peripherals_suspend(void)
{
    RCC->APB1ENR &= ~(RCC_APB1ENR_USART2EN | RCC_APB1ENR_I2C1EN);
    RCC->APB2ENR &= ~RCC_APB2ENR_ADC1EN;
}

void hal_peripherals_resume(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN | RCC_APB1ENR_I2C1EN;
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
}

/* ---- 系统 ---- */
static volatile uint32_t g_tick = 0;
uint32_t hal_get_tick_ms(void) { return g_tick; }
void hal_delay_ms(uint32_t ms) { g_tick += ms; }
void hal_system_reset(void) { NVIC_SystemReset(); }

#endif /* STM32_TARGET */
