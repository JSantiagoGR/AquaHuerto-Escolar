/*
 * Mapa de pines del ESP32-WROOM-32U (ESP32-D0WD-V3 rev 3.1).
 * GPIO26/27/19/18/4 son los mismos que funcionaron físicamente en las
 * Pruebas 01–03. GPIO25/34 son los del esquema de la Actividad 2.2 (EC-5).
 */
#pragma once

#include "driver/gpio.h"
#include "hal/adc_types.h"

/* Relevadores (módulo 2 canales SRD-05VDC-SL-C, activo en BAJO: CONFIRMADO) */
#define PIN_PUMP            GPIO_NUM_26     /* IN1 -> bomba (vía etapa de potencia)  */
#define PIN_VALVE           GPIO_NUM_27     /* IN2 -> electroválvula NC              */
#define RELAY_ACTIVE_LOW    1

/* Caudalímetro YF-S201: amarillo -> diodo (franja al sensor) -> GPIO19 + pull-up */
#define PIN_FLOW            GPIO_NUM_19

/* Ultrasónico Parallax PING))) #28015: SIG -> 1 kΩ -> GPIO18, 2 kΩ GPIO18-GND */
#define PIN_PING            GPIO_NUM_18

/* DHT22/AM2302 (temperatura y humedad relativa), alimentado a 3.3 V */
#define PIN_DHT22           GPIO_NUM_4

/* EC-5: excitación por pulso de 10 ms desde GPIO25 (3.3 V, ~10 mA, igual que
 * en la calibración de la Actividad 2.2) y salida analógica a GPIO34. */
#define PIN_EC5_POWER       GPIO_NUM_25
#define EC5_POWER_ACTIVE_HIGH 1             /* 0 si se usa un PNP/P-MOSFET en lado alto */
#define PIN_EC5_ADC         GPIO_NUM_34
#define EC5_ADC_UNIT        ADC_UNIT_1
#define EC5_ADC_CHANNEL     ADC_CHANNEL_6   /* GPIO34 = ADC1_CH6 (válido con Wi-Fi) */

/* Comprueba que no haya pines repetidos ni pines prohibidos (arranque, flash,
 * UART0). Imprime el resultado y devuelve false si hay conflicto. */
bool board_check_pins(bool verbose);
