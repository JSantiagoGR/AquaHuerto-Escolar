idf_component_register(
    SRCS
        "app_main.c"
        "app_types.c"
        "board.c"
        "configuration.c"
        "storage.c"
        "actuators.c"
        "safety.c"
        "flow_sensor.c"
        "soil_sensor.c"
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
    INCLUDE_DIRS "."
    PRIV_REQUIRES
        esp_driver_gpio esp_driver_uart esp_driver_pcnt esp_adc esp_timer
        nvs_flash esp_wifi esp_netif esp_event lwip mqtt esp_system
)
