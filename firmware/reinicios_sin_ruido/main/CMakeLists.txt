# mismo programa que firmware/reinicios; solo cambia el bootloader
idf_component_register(SRCS "../../reinicios/main/reinicios.c")
target_compile_definitions(${COMPONENT_LIB} PRIVATE VARIANTE="sin_ruido")
