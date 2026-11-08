/*
 * Escenarios de prueba de la lógica PURA (máquina de estados, modos, IA y
 * configuración) con entradas y reloj VIRTUALES. Se ejecutan:
 *  - en el ESP32 con el comando SELFTEST (sin tocar GPIO ni el estado real)
 *  - en la PC con tests/host (mismo código fuente)
 * Es una prueba de software: no valida el hardware.
 */
#pragma once

/* Devuelve el número de pruebas fallidas; *passed recibe las exitosas */
int logic_tests_run(int *passed);
