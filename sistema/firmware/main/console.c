#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_system.h"

#include "actuators.h"
#include "app_types.h"
#include "board.h"
#include "commands.h"
#include "configuration.h"
#include "irrigation_controller.h"
#include "mqtt_manager.h"
#include "net_config.h"
#include "wifi_manager.h"
#include "selftest.h"
#include "simulation.h"
#include "console.h"
#include "soil_sensor.h"

#define UART_NUM  UART_NUM_0
#define CONSOLE_LINE_MAX  480

static void help(void)
{
    printf(
        "=================== COMANDOS (consola serial) ===================\n"
        " ESTADO | CONFIG | HISTORIAL | PINES | AYUDA\n"
        " START <litros> [FORCE]      Riego manual por volumen (ej. START 1)\n"
        " STOP                        Detiene todo de inmediato\n"
        " MODO MANUAL | MODO AUTO | MODO IA   Modo de operacion\n"
        " OBJETIVO [%%VWC]             Riega por dosis hasta la humedad optima o la indicada\n"
        " IA | IA BORRAR CONFIRMAR    Estado / reinicio del modelo predictivo\n"
        " CLIMA | CLIMA ACTUALIZAR    Pronostico Open-Meteo\n"
        " SET <parametro> <valor>     Cambia un parametro (ver CONFIG)\n"
        " HUMEDAD <min> <obj> <max>   Cambia los tres umbrales a la vez\n"
        " HORARIO <1|2> <ON|OFF> <HH:MM> <HH:MM>\n"
        " TINACO <vacio_cm> <lleno_cm>  Calibra el nivel del tinaco\n"
        " CALFLUJO <pulsos> <mL_medidos> Calibra pulsos/L con recipiente\n"
        " CLEAR [ALARMA|ALL]          Borra alarmas resueltas\n"
        " EC5 PRUEBA [s]              Excita el EC-5 s segundos y muestra mV de los pines ADC\n"
        " LOG ON | LOG OFF            Linea de telemetria periodica\n"
        " --- Red (solo consola; las contrasenas nunca se muestran) ---\n"
        " RED | RED DIAG | WIFI SCAN\n"
        " WIFI <casa|tec|huerto> <ssid> <contrasena>   (sin espacios)\n"
        " WIFIHEX <red> <ssid_hex> <contrasena_hex>    (cualquier caracter)\n"
        " WIFI OFF <red> | WIFI PREF <red>\n"
        " MQTT URI <mqtt://IP:1883> | MQTT USER <usuario> <contrasena>\n"
        " MQTTHEX <usuario_hex> <contrasena_hex> | MQTT TOPIC <base> | DEVICE <id> <casa|final>\n"
        " RED APLICAR                 Reconecta Wi-Fi y MQTT con lo guardado\n"
        " --- Solo consola (presencia fisica) ---\n"
        " POWER ON CONFIRMAR | POWER OFF   Habilita salidas de potencia\n"
        " PERFIL A | PERFIL B CONFIRMAR    Pruebas / instalacion final\n"
        " SIM ON | SIM OFF                 Simulacion (salidas inactivas)\n"
        " SIM SUELO <v>|FALLA  SIM TINACO <pct>|FALLA|NOCAL  SIM FLUJO <L/min>\n"
        " SIM AMB <t> <hr>|FALLA  SIM HORA <HH:MM>|INVALIDA|REAL  SIM VELOCIDAD <n>\n"
        " SIM SECADO <pp/h>  SIM LLUVIA <pp> (agua externa simulada)\n"
        " SELFTEST                         Pruebas automaticas de la logica\n"
        " JSON {..} | JSONRET {..}         Prueba local de un comando MQTT\n"
        " FABRICA CONFIRMAR | REINICIAR | REINICIAR DURO (prueba de corte)\n"
        "================================================================\n");
}

static void post(command_t *c, cmd_type_t t, const char *name)
{
    c->type = t;
    c->src = SRC_SERIAL;
    strlcpy(c->name, name, sizeof(c->name));
    if (t == C_STOP) {
        controller_emergency_stop(c);
    } else if (!controller_post(c)) {
        printf("ERROR: cola de comandos llena\n");
    }
}

static bool hhmm(const char *s, int *minute)
{
    float m;
    if (!config_parse_time(s, &m)) {
        return false;
    }
    *minute = (int)m;
    return true;
}

static void handle_sim(char **tok, int n)
{
    sim_state_t *s = sim();
    if (n < 2) {
        printf("Uso: SIM ON|OFF|SUELO|TINACO|FLUJO|AMB|HORA|VELOCIDAD\n");
        return;
    }
    command_t c = {0};
    if (!strcasecmp(tok[1], "ON") || !strcasecmp(tok[1], "OFF")) {
        c.b1 = !strcasecmp(tok[1], "ON");
        post(&c, C_SIM, "SIM");
        return;
    }
    if (!s->active) {
        printf("Primero active la simulacion: SIM ON\n");
        return;
    }
    const char *v = (n >= 3) ? tok[2] : "";
    if (!strcasecmp(tok[1], "SUELO")) {
        if (!strcasecmp(v, "FALLA")) {
            s->soil_valid = false;
        } else {
            s->soil_valid = true;
            s->soil_vwc = strtof(v, NULL);
        }
    } else if (!strcasecmp(tok[1], "TINACO")) {
        if (!strcasecmp(v, "FALLA")) {
            s->tank_mode = SIM_TANK_FAIL;
        } else if (!strcasecmp(v, "NOCAL")) {
            s->tank_mode = SIM_TANK_UNCAL;
        } else {
            s->tank_mode = SIM_TANK_OK;
            s->tank_pct = strtof(v, NULL);
        }
    } else if (!strcasecmp(tok[1], "FLUJO")) {
        s->flow_lpm = strtof(v, NULL);
    } else if (!strcasecmp(tok[1], "AMB")) {
        if (!strcasecmp(v, "FALLA")) {
            s->env_valid = false;
        } else if (n >= 4) {
            s->env_valid = true;
            s->temp_c = strtof(tok[2], NULL);
            s->rh = strtof(tok[3], NULL);
        }
    } else if (!strcasecmp(tok[1], "HORA")) {
        int m;
        if (!strcasecmp(v, "INVALIDA")) {
            s->time_override = true;
            s->time_valid = false;
        } else if (!strcasecmp(v, "REAL")) {
            s->time_override = false;
        } else if (hhmm(v, &m)) {
            s->time_override = true;
            s->time_valid = true;
            s->minute = m;
        } else {
            printf("Hora invalida\n");
            return;
        }
    } else if (!strcasecmp(tok[1], "SECADO")) {
        s->dry_pph = strtof(v, NULL);
    } else if (!strcasecmp(tok[1], "LLUVIA")) {
        s->soil_vwc += strtof(v, NULL);         /* Agua que NO pasa por la bomba */
    } else if (!strcasecmp(tok[1], "VELOCIDAD")) {
        int sp = atoi(v);
        s->speed = (sp < 1) ? 1 : (sp > 120 ? 120 : sp);
    } else {
        printf("Parametro de simulacion desconocido\n");
        return;
    }
    printf("SIM: suelo %s %.1f%% | tinaco %s %.0f%% | flujo %.2f L/min | amb %s %.1fC %.0f%% | hora %s %02d:%02d | x%lu\n",
           s->soil_valid ? "OK" : "FALLA", s->soil_vwc,
           s->tank_mode == SIM_TANK_OK ? "OK" : (s->tank_mode == SIM_TANK_FAIL ? "FALLA" : "NOCAL"), s->tank_pct,
           s->flow_lpm, s->env_valid ? "OK" : "FALLA", s->temp_c, s->rh,
           !s->time_override ? "REAL" : (s->time_valid ? "SIM" : "INVALIDA"), s->minute / 60, s->minute % 60,
           (unsigned long)s->speed);
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Decodifica hexadecimal (permite espacios y cualquier carácter en SSID/contraseñas) */
static bool unhex(const char *in, char *out, size_t cap)
{
    size_t n = strlen(in);
    if (n % 2 || n / 2 >= cap) {
        return false;
    }
    for (size_t i = 0; i < n / 2; i++) {
        int a = hexval(in[2 * i]), b = hexval(in[2 * i + 1]);
        if (a < 0 || b < 0) {
            return false;
        }
        out[i] = (char)(a * 16 + b);
    }
    out[n / 2] = '\0';
    return true;
}

static void save_net(net_config_t *c, const char *what)
{
    if (net_config_save(c)) {
        printf("OK: %s guardado en NVS. Escriba RED APLICAR para reconectar.\n", what);
    } else {
        printf("ERROR: datos de red invalidos (contrasena Wi-Fi 8-63 caracteres, URI mqtt://..., topic sin # + ni espacios)\n");
    }
}

static void set_wifi(const char *slot, const char *ssid, const char *pass)
{
    net_config_t c;
    net_config_get(&c);
    int i = net_config_slot_find(&c, slot);
    if (i < 0) {
        printf("Red desconocida: use casa, tec o huerto\n");
        return;
    }
    if (strlen(ssid) == 0 || strlen(ssid) >= NET_SSID_MAX || strlen(pass) >= NET_PASS_MAX) {
        printf("SSID o contrasena demasiado largos\n");
        return;
    }
    strlcpy(c.slot[i].ssid, ssid, sizeof(c.slot[i].ssid));
    strlcpy(c.slot[i].pass, pass, sizeof(c.slot[i].pass));
    c.slot[i].enabled = 1;
    save_net(&c, "Red Wi-Fi");   /* La contraseña no se imprime */
}

static bool handle_net(char **tok, int n)
{
    const char *k = tok[0];
    net_config_t c;
    net_config_get(&c);
    if (!strcmp(k, "RED")) {
        if (n >= 2 && !strcasecmp(tok[1], "APLICAR")) {
            wifi_manager_reconfigure();
            mqtt_manager_reconfigure();
            printf("OK: reconectando con la configuracion guardada\n");
        } else if (n >= 2 && !strcasecmp(tok[1], "DIAG")) {
            command_t cmd = { .type = C_NET_DIAG, .src = SRC_SERIAL };
            strlcpy(cmd.name, "RED DIAG", sizeof(cmd.name));
            controller_post(&cmd);
        } else {
            net_config_print();
            wifi_diag_t d;
            wifi_manager_diag(&d);
            printf("Estado: Wi-Fi %s (%s %s, %d dBm, ultimo motivo %d: %s) | MQTT %s\n",
                   d.connected ? "CONECTADO" : "DESCONECTADO", d.ssid, d.ip, d.rssi, d.last_reason,
                   wifi_reason_text(d.last_reason), mqtt_manager_connected() ? "CONECTADO" : "DESCONECTADO");
        }
        return true;
    }
    if (!strcmp(k, "WIFI")) {
        if (n >= 2 && !strcasecmp(tok[1], "SCAN")) {
            wifi_manager_scan_print();
        } else if (n >= 3 && !strcasecmp(tok[1], "OFF")) {
            int i = net_config_slot_find(&c, tok[2]);
            if (i >= 0) {
                c.slot[i].enabled = 0;
                save_net(&c, "Red deshabilitada");
            }
        } else if (n >= 3 && !strcasecmp(tok[1], "PREF")) {
            int i = net_config_slot_find(&c, tok[2]);
            if (i >= 0) {
                c.preferred = (uint8_t)i;
                save_net(&c, "Red preferida");
            }
        } else if (n >= 4) {
            set_wifi(tok[1], tok[2], tok[3]);
        } else if (n == 3) {
            set_wifi(tok[1], tok[2], "");          /* Red abierta */
        } else {
            printf("Uso: WIFI <casa|tec|huerto> <ssid> <contrasena> | WIFI SCAN | WIFI OFF <red> | WIFI PREF <red>\n");
        }
        return true;
    }
    if (!strcmp(k, "WIFIHEX") && n >= 3) {
        char ssid[NET_SSID_MAX], pass[NET_PASS_MAX] = "";
        if (!unhex(tok[2], ssid, sizeof(ssid)) || (n >= 4 && !unhex(tok[3], pass, sizeof(pass)))) {
            printf("Hexadecimal invalido\n");
            return true;
        }
        set_wifi(tok[1], ssid, pass);
        return true;
    }
    if (!strcmp(k, "MQTT") && n >= 3) {
        if (!strcasecmp(tok[1], "URI")) {
            strlcpy(c.mqtt_uri, tok[2], sizeof(c.mqtt_uri));
            save_net(&c, "Broker");
        } else if (!strcasecmp(tok[1], "USER") && n >= 4) {
            strlcpy(c.mqtt_user, tok[2], sizeof(c.mqtt_user));
            strlcpy(c.mqtt_pass, tok[3], sizeof(c.mqtt_pass));
            save_net(&c, "Usuario MQTT");
        } else if (!strcasecmp(tok[1], "TOPIC")) {
            strlcpy(c.base_topic, tok[2], sizeof(c.base_topic));
            save_net(&c, "Topic base");
        } else {
            printf("Uso: MQTT URI <uri> | MQTT USER <u> <p> | MQTT TOPIC <base>\n");
        }
        return true;
    }
    if (!strcmp(k, "MQTTHEX") && n >= 3) {
        if (!unhex(tok[1], c.mqtt_user, sizeof(c.mqtt_user)) || !unhex(tok[2], c.mqtt_pass, sizeof(c.mqtt_pass))) {
            printf("Hexadecimal invalido\n");
            return true;
        }
        save_net(&c, "Usuario MQTT");
        return true;
    }
    if (!strcmp(k, "DEVICE") && n >= 2) {
        strlcpy(c.device_id, tok[1], sizeof(c.device_id));
        if (n >= 3) {
            strlcpy(c.env_name, tok[2], sizeof(c.env_name));
        }
        save_net(&c, "Identificador del dispositivo");
        return true;
    }
    return false;
}

static void process(char *line)
{
    char *tok[8];
    int n = 0;
    /* JSON <mensaje>: prueba local del procesador de comandos MQTT (mismo código
     * que un mensaje del broker; las respuestas se imprimen como "MQTT ...").
     * JSONRET <mensaje>: igual, pero marcado como mensaje retenido. */
    if (!strncasecmp(line, "JSON ", 5) || !strncasecmp(line, "JSONRET ", 8)) {
        bool ret = !strncasecmp(line, "JSONRET ", 8);
        const char *js = line + (ret ? 8 : 5);
        printf("> JSON%s %s\n", ret ? " (retenido)" : "", js);
        commands_handle_mqtt(js, (int)strlen(js), ret);
        return;
    }
    for (char *t = strtok(line, " \t"); t && n < 8; t = strtok(NULL, " \t")) {
        tok[n++] = t;
    }
    if (n == 0) {
        return;
    }
    for (char *p = tok[0]; *p; p++) {
        *p = (char)toupper((unsigned char)*p);
    }
    printf("> %s\n", tok[0]);
    command_t c = { .i1 = -1 };
    const char *k = tok[0];
    if (handle_net(tok, n)) {
        return;
    }

    if (!strcmp(k, "AYUDA") || !strcmp(k, "HELP")) {
        help();
    } else if (!strcmp(k, "ESTADO") || !strcmp(k, "STATUS")) {
        post(&c, C_GET_STATUS, "ESTADO");
    } else if (!strcmp(k, "CONFIG")) {
        post(&c, C_GET_CONFIG, "CONFIG");
    } else if (!strcmp(k, "HISTORIAL")) {
        post(&c, C_GET_HISTORY, "HISTORIAL");
    } else if (!strcmp(k, "PINES")) {
        board_check_pins(true);
    } else if (!strcmp(k, "EC5") && n >= 2 && !strcasecmp(tok[1], "PRUEBA")) {
        soil_sensor_diag(n >= 3 ? atoi(tok[2]) : 5);
    } else if (!strcmp(k, "START") && n >= 2) {
        c.f1 = strtof(tok[1], NULL);
        c.b1 = (n >= 3 && !strcasecmp(tok[2], "FORCE"));
        post(&c, C_START_MANUAL, "START");
    } else if (!strcmp(k, "STOP")) {
        post(&c, C_STOP, "STOP");
    } else if (!strcmp(k, "AUTO") && n >= 2) {
        post(&c, !strcasecmp(tok[1], "ON") ? C_ENABLE_AUTO : C_DISABLE_AUTO, "AUTO");
    } else if (!strcmp(k, "MODO") && n >= 2 && (!strcasecmp(tok[1], "MANUAL") || !strcasecmp(tok[1], "AUTO") ||
                                                 !strcasecmp(tok[1], "AUTOMATICO") || !strcasecmp(tok[1], "IA"))) {
        c.i1 = !strcasecmp(tok[1], "MANUAL") ? CM_MANUAL : (!strcasecmp(tok[1], "IA") ? CM_IA : CM_AUTO);
        post(&c, C_SET_MODE, "MODO");
    } else if (!strcmp(k, "OBJETIVO")) {
        c.f1 = (n >= 2) ? strtof(tok[1], NULL) : 0.0f;
        post(&c, C_START_TO_TARGET, "OBJETIVO");
    } else if (!strcmp(k, "IA")) {
        if (n >= 3 && !strcasecmp(tok[1], "BORRAR") && !strcasecmp(tok[2], "CONFIRMAR")) {
            post(&c, C_IA_RESET, "IA BORRAR");
        } else {
            post(&c, C_GET_IA, "IA");
        }
    } else if (!strcmp(k, "CLIMA")) {
        if (n >= 2 && !strcasecmp(tok[1], "ACTUALIZAR")) {
            post(&c, C_WEATHER_REFRESH, "CLIMA");
        } else {
            post(&c, C_NET_DIAG, "CLIMA");
        }
    } else if (!strcmp(k, "SET") && n >= 3) {
        strlcpy(c.key, tok[1], sizeof(c.key));
        strlcpy(c.sval, tok[2], sizeof(c.sval));
        post(&c, C_SET_PARAM, "SET");
    } else if (!strcmp(k, "HUMEDAD") && n >= 4) {
        c.f1 = strtof(tok[1], NULL);
        c.f2 = strtof(tok[2], NULL);
        c.f3 = strtof(tok[3], NULL);
        post(&c, C_SET_HUM_RANGE, "HUMEDAD");
    } else if (!strcmp(k, "HORARIO") && n >= 5) {
        c.i1 = atoi(tok[1]);
        c.b1 = !strcasecmp(tok[2], "ON");
        strlcpy(c.key, tok[3], sizeof(c.key));
        strlcpy(c.sval, tok[4], sizeof(c.sval));
        if (c.i1 != 1 && c.i1 != 2) {
            printf("Ventana 1 o 2\n");
            return;
        }
        post(&c, C_SET_SCHEDULE, "HORARIO");
    } else if (!strcmp(k, "TINACO") && n >= 3) {
        c.f1 = strtof(tok[1], NULL);
        c.f2 = strtof(tok[2], NULL);
        post(&c, C_SET_TANK_CAL, "TINACO");
    } else if (!strcmp(k, "CALFLUJO") && n >= 3) {
        c.f1 = __builtin_nanf("");
        c.f2 = strtof(tok[1], NULL);
        c.f3 = strtof(tok[2], NULL);
        if (c.f2 <= 0 || c.f3 <= 0) {
            printf("Uso: CALFLUJO <pulsos_contados> <mL_medidos_en_recipiente>\n");
            return;
        }
        post(&c, C_SET_FLOW_CAL, "CALFLUJO");
    } else if (!strcmp(k, "CLEAR")) {
        c.i1 = (n >= 2 && strcasecmp(tok[1], "ALL")) ? alarm_from_name(tok[1]) : -1;
        if (n >= 2 && strcasecmp(tok[1], "ALL") && c.i1 < 0) {
            printf("Alarma desconocida\n");
            return;
        }
        post(&c, C_CLEAR_ALARM, "CLEAR");
    } else if (!strcmp(k, "LOG") && n >= 2) {
        controller_set_console_log(!strcasecmp(tok[1], "ON"));
    } else if (!strcmp(k, "POWER") && n >= 2) {
        if (!strcasecmp(tok[1], "ON")) {
            if (n < 3 || strcasecmp(tok[2], "CONFIRMAR")) {
                printf("Para habilitar la potencia escriba: POWER ON CONFIRMAR\n"
                       "Verifique antes la etapa de potencia (ver SEGURIDAD.md)\n");
                return;
            }
            c.b1 = true;
        }
        post(&c, C_POWER, "POWER");
    } else if ((!strcmp(k, "PERFIL") || !strcmp(k, "MODO")) && n >= 2) {
        if (!strcasecmp(tok[1], "B")) {
            if (n < 3 || strcasecmp(tok[2], "CONFIRMAR")) {
                printf("Para pasar a instalacion final escriba: PERFIL B CONFIRMAR (ver docs/MIGRACION_RASPBERRY_PI.md)\n");
                return;
            }
            c.i1 = MODE_B_FINAL;
        } else {
            c.i1 = MODE_A_TEST;
        }
        post(&c, C_MODE, "PERFIL");
    } else if (!strcmp(k, "SIM")) {
        handle_sim(tok, n);
    } else if (!strcmp(k, "SELFTEST")) {
        selftest_run();
    } else if (!strcmp(k, "FABRICA")) {
        if (n < 2 || strcasecmp(tok[1], "CONFIRMAR")) {
            printf("Escriba: FABRICA CONFIRMAR\n");
            return;
        }
        post(&c, C_FACTORY, "FABRICA");
    } else if (!strcmp(k, "REINICIAR") && n >= 2 && !strcasecmp(tok[1], "DURO")) {
        /* Prueba de recuperación: equivale a un corte de energía (no cierra el
         * registro del riego en curso). Las salidas se apagan antes. */
        printf("REINICIO DURO (simula corte de energia)\n");
        actuators_emergency_off();
        vTaskDelay(pdMS_TO_TICKS(100));
        esp_restart();
    } else if (!strcmp(k, "REINICIAR")) {
        post(&c, C_REBOOT, "REINICIAR");
    } else {
        printf("Comando desconocido o incompleto. Escriba AYUDA\n");
    }
}

static void console_task(void *arg)
{
    char line[CONSOLE_LINE_MAX + 1];
    size_t len = 0;
    uint8_t buf[32];
    while (true) {
        int n = uart_read_bytes(UART_NUM, buf, sizeof(buf), pdMS_TO_TICKS(20));
        for (int i = 0; i < n; i++) {
            char ch = (char)buf[i];
            if (ch == '\r' || ch == '\n') {
                if (len > 0) {
                    line[len] = '\0';
                    process(line);
                    len = 0;
                }
            } else if (len < CONSOLE_LINE_MAX) {
                line[len++] = ch;
            } else {
                len = 0;
                printf("Linea demasiado larga\n");
            }
        }
    }
}

void console_start(void)
{
    uart_driver_install(UART_NUM, 512, 0, 0, NULL, 0);
    xTaskCreatePinnedToCore(console_task, "console", 6144, NULL, 3, NULL, 0);
}
