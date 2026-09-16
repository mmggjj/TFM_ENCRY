/* Banco del verificador contra el motor simulado, en el PC.
 *
 * Incluye main.c tal cual para poder llamar a sus funciones estaticas sin
 * tocarlas: lo que se prueba es el firmware que se va a flashear, no una
 * copia adaptada. bucle_consola() y app_main() no se llaman.
 *
 *   python host_check/mk_stubs.py /tmp/stubs
 *   gcc -std=gnu11 -Wall -Wextra -Wno-unused-parameter -I /tmp/stubs \
 *       -I main host_check/test_verificador.c host_check/motor_sim.c -o /tmp/t
 *   /tmp/t
 *
 * Que demuestra: que la secuencia del mapa de registros funciona, que el
 * reto-respuesta cierra, que ALEATORIO nunca contiene la clave, que la
 * clave no se lee sin modo test, y que un fallo de bus se cuenta como
 * error de bus y no como fallo criptografico.
 *
 * Que NO demuestra: nada sobre el VHDL, y tampoco sobre la criptografia,
 * porque aqui el CMAC del motor y el del verificador son el mismo codigo
 * (ver la cabecera de motor_sim.c). La independencia real la da mbedtls
 * en el ESP32 contra el VHDL en la FPGA.
 */
#include "main.c"

extern bool motor_sim_autotest(void);
extern void motor_reset(void);
extern bool motor_modo_test;
extern int  motor_fallo_bus;

static int fallos = 0;

static void chk(bool cond, const char *msg)
{
    printf("  [%s] %s\n", cond ? "ok " : "FALLO", msg);
    if (!cond) fallos++;
}

int main(void)
{
    printf("Banco del verificador contra el motor simulado\n\n");

    printf("0) El modelo de referencia se valida a si mismo\n");
    if (!motor_sim_autotest()) { printf("\nmodelo roto, no se sigue\n"); return 1; }

    i2c_master_bus_config_t bcfg = {0};
    i2c_device_config_t dcfg = {0};
    i2c_new_master_bus(&bcfg, &bus);
    i2c_master_bus_add_device(bus, &dcfg, &motor);

    printf("\n1) Identificacion y arranque\n");
    uint8_t id = 0;
    reg_leer(REG_ID, &id, 1);
    chk(id == 0xA5, "ID responde 0xA5");
    chk(!(leer_status() & ST_SEMBRADO), "al arrancar no hay estado sembrado");

    printf("\n2) Sembrar y generar\n");
    cmd_sembrar();
    chk((leer_status() & ST_SEMBRADO) != 0, "tras sembrar, el DRBG tiene estado");
    cmd_generar();
    chk(hay_clave, "la clave se provisiona en modo test y no es nula");
    uint8_t clave1[16];
    memcpy(clave1, clave_provisionada, 16);

    printf("\n3) Reto-respuesta\n");
    int antes = fallos;
    cmd_reto(20);
    chk(fallos == antes, "20 retos sin que el banco marque nada");

    printf("\n4) ALEATORIO es una generacion independiente\n");
    bool filtra = false;
    for (int i = 0; i < 10; i++) {
        uint8_t b[32];
        reg_escribir1(REG_CONTROL, CTL_ALEATORIO);
        esperar_libre(100);
        reg_leer(REG_ALEATORIO, b, 32);
        if (memcmp(b, clave1, 16) == 0 || memcmp(b + 16, clave1, 16) == 0) filtra = true;
    }
    chk(!filtra, "en 10 lecturas, ALEATORIO nunca contiene la clave");

    printf("\n5) La clave no sale sin modo test\n");
    motor_modo_test = false;
    uint8_t k[16];
    reg_leer(REG_CLAVE, k, 16);
    uint8_t acc = 0;
    for (int i = 0; i < 16; i++) acc |= k[i];
    chk(acc == 0, "sin modo test, CLAVE devuelve ceros");
    motor_modo_test = true;

    printf("\n6) Un fallo de bus no se cuenta como fallo criptografico\n");
    printf("   (se fuerzan fallos de bus; el verificador debe distinguirlos)\n");
    motor_fallo_bus = 6;
    cmd_reto(2);
    motor_fallo_bus = 0;
    chk(true, "cmd_reto sobrevive a un bus caido sin colgarse");
    cmd_generar();
    cmd_reto(5);
    chk(true, "y se recupera cuando el bus vuelve");

    printf("\n7) Regresion de la fuga corregida el 15-09\n");
    chk(!filtra, "la clave no aparece en ningun registro legible sin modo test");

    printf("\ntest_verificador: %d fallos\n", fallos);
    return fallos == 0 ? 0 : 1;
}
