/*
 * Autodiagnóstico de la lógica de riego. Ejecuta escenarios sobre una copia
 * independiente de la máquina de estados con entradas y reloj VIRTUALES:
 * nunca toca los GPIO ni el estado real del sistema. Es una prueba de
 * software; no valida el hardware.
 */
#pragma once

/* Devuelve el número de pruebas fallidas */
int selftest_run(void);
