/* Ejecuta en la PC los mismos escenarios del SELFTEST del ESP32 */
#include <stdio.h>
#include "logic_tests.h"

int main(void)
{
    int passed = 0;
    int failed = logic_tests_run(&passed);
    printf("HOST RESULTADO: %d PASS, %d FAIL\n", passed, failed);
    return failed ? 1 : 0;
}
