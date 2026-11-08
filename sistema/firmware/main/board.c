#include <stdio.h>
#include "board.h"

typedef struct {
    const char *name;
    int gpio;
    bool output;
} pin_use_t;

static const pin_use_t PINS[] = {
    {"BOMBA (IN1)",        PIN_PUMP,      true},
    {"ELECTROVALVULA (IN2)", PIN_VALVE,   true},
    {"YF-S201",            PIN_FLOW,      false},
    {"PING SIG",           PIN_PING,      true},
    {"DHT22",              PIN_DHT22,     true},
    {"EC-5 EXCITACION",    PIN_EC5_POWER, true},
    {"EC-5 ADC1_CH6",      PIN_EC5_ADC,   false},
};

static bool is_forbidden(int gpio, bool output, const char **why)
{
    switch (gpio) {
    case 0: case 2: case 5: case 12: case 15:
        *why = "pin de arranque (strapping)";
        return true;
    case 6: case 7: case 8: case 9: case 10: case 11:
        *why = "flash SPI interna";
        return true;
    case 1: case 3:
        *why = "UART0 (consola y flasheo)";
        return true;
    default:
        break;
    }
    if (output && gpio >= 34) {
        *why = "GPIO34-39 son solo de entrada";
        return true;
    }
    return false;
}

bool board_check_pins(bool verbose)
{
    const int n = sizeof(PINS) / sizeof(PINS[0]);
    bool ok = true;
    for (int i = 0; i < n; i++) {
        const char *why = NULL;
        if (is_forbidden(PINS[i].gpio, PINS[i].output, &why)) {
            printf("PINES: CONFLICTO %s en GPIO%d: %s\n", PINS[i].name, PINS[i].gpio, why);
            ok = false;
        }
        for (int j = i + 1; j < n; j++) {
            if (PINS[i].gpio == PINS[j].gpio) {
                printf("PINES: CONFLICTO GPIO%d usado por %s y %s\n",
                       PINS[i].gpio, PINS[i].name, PINS[j].name);
                ok = false;
            }
        }
        if (verbose) {
            printf("PIN GPIO%-2d -> %s\n", PINS[i].gpio, PINS[i].name);
        }
    }
    if (verbose || !ok) {
        printf("PINES: %s\n", ok ? "SIN CONFLICTOS" : "HAY CONFLICTOS");
    }
    return ok;
}
