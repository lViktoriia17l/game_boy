#include "main.h"
#include "usart.h"
#include "gpio.h"


uint8_t rx_buf[5];
uint8_t tx_buf[6];
uint8_t matrix[9][9] = {0};
uint8_t packet[83];
uint8_t arr_y[9];
uint8_t arr_x[9];
/* Оголошення змінних */
 uint8_t rx_buffer[5]; // Буфер для 5 байт


// CMD
#define CMD_START     0x01
#define CMD_RESTART   0x02
#define CMD_GIVEUP    0x03
#define CMD_SET       0x04
#define CMD_CLEAR     0x05
#define CMD_CLEARALL  0x06
#define CMD_FIELD     0x07

// STATUS
#define STATUS_OK       0x10
#define STATUS_INVALID  0x11
#define STATUS_LOCKED   0x12
#define STATUS_CHKERR   0x13
#define STATUS_LOSE     0x14
#define STATUS_WIN      0x15
#define STATUS_FAIL     0x16

void SystemClock_Config(void);
void process_command(uint8_t cmd, uint8_t b1, uint8_t b2, uint8_t b3);
void send_response(uint8_t cmd, uint8_t status, uint8_t b1, uint8_t b2, uint8_t b3);


int main(void)
{
  HAL_Init();
  SystemClock_Config();
  MX_GPIO_Init();
  MX_USART2_UART_Init();

  /* ВИДАЛІТЬ АБО ЗАКОМЕНТУЙТЕ ЦЕЙ РЯДОК: */
  // HAL_UART_Receive_IT(&huart2, rx_buf, 5);

  while (1)
  {
      // Тепер функція реально чекатиме на прихід 5 байт
      if (HAL_UART_Receive(&huart2, rx_buffer, 5, HAL_MAX_DELAY) == HAL_OK)
      {
          // Як тільки 5 байт отримано — миттєво відправляємо їх назад
          HAL_UART_Transmit(&huart2, rx_buffer, 5, 100);
      }
  }
}


/*
    !           !           !
    !           !           !
    !           !           !
    !           !           !
  !!!!!       !!!!!       !!!!!
   !!!         !!!         !!!
    !           !           !
  все що з низу не рухати код по пизді іде
    !           !           !
   !!!         !!!         !!!
  !!!!!       !!!!!       !!!!!
    !           !           !
    !           !           !
    !           !           !
    !           !           !
  */


void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};


  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL12;
  RCC_OscInitStruct.PLL.PREDIV = RCC_PREDIV_DIV1;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }


  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    Error_Handler();
  }
}

void Error_Handler(void)
{
   __disable_irq();
  while (1)
  {
  }

}
#ifdef USE_FULL_ASSERT

void assert_failed(uint8_t *file, uint32_t line)
{

}
#endif
