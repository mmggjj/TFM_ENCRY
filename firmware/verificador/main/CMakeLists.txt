set(fuentes "main.c")
# idf.py -DMOTOR_SIMULADO=1 build: el motor simulado del banco en host va
# dentro del firmware y suplanta al driver I2C con --wrap, para correr el
# verificador en QEMU (esp32) sin motor. Nunca para una placa.
if(MOTOR_SIMULADO)
    list(APPEND fuentes "../../host_check/motor_sim.c")
endif()
idf_component_register(SRCS ${fuentes}
                       INCLUDE_DIRS "."
                       REQUIRES motor_i2c mbedtls esp_rom)
if(MOTOR_SIMULADO)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE MOTOR_SIM_EN_CHIP=1)
    # -u: motor_sim.o esta en libmain.a y nadie lo llama directamente; sin
    # esto el enlazador no lo saca del archivo y los __wrap_ quedan sin definir.
    target_link_libraries(${COMPONENT_LIB} INTERFACE
        "-Wl,--wrap=i2c_master_transmit,--wrap=i2c_master_transmit_receive"
        "-Wl,-u,__wrap_i2c_master_transmit,-u,__wrap_i2c_master_transmit_receive")
endif()
