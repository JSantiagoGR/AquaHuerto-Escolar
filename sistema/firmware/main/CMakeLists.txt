idf_component_register(
    SRCS
        "main.c"
        "app_types.c"
        "board.c"
        "configuration.c"
        "config_table.c"
        "net_config.c"
        "ia_model.c"
        "weather.c"
        "logic_tests.c"
        "storage.c"
        "actuators.c"
        "safety.c"
        "flow_sensor.c"
        "soil_sensor.c"
        "sensor_filter.c"
        "tank_level.c"
        "environment_sensor.c"
        "simulation.c"
        "sensors.c"
        "timekeeping.c"
        "irrigation_logic.c"
        "irrigation_controller.c"
        "commands.c"
        "wifi_manager.c"
        "mqtt_manager.c"
        "console.c"
        "selftest.c"
        "wdt_diag.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES
        esp_driver_gpio esp_driver_uart esp_driver_pcnt esp_adc esp_timer
        nvs_flash esp_wifi esp_netif esp_event lwip mqtt esp_system
        esp_http_client mbedtls esp_hw_support
)
