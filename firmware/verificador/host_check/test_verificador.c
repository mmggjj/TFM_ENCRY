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
 * clave no se lee sin modo test, que un fallo de bus se cuenta como error
 * de bus y no como fallo criptografico, que una orden rechazada (alarma,
 * CFG_KD bajo, sin test de arranque) no se toma por buena ni deja salir
 * datos al PC, y que los plazos de espera son de tiempo real.
 *
 * Que NO demuestra: nada sobre el VHDL, y tampoco sobre la criptografia,
 * porque aqui el CMAC del motor y el del verificador son el mismo codigo
 * (ver la cabecera de motor_sim.c). La independencia real la da mbedtls
 * en el ESP32 contra el VHDL en la FPGA.
 */
#include "main.c"

extern bool motor_sim_autotest(void);
extern void motor_reset(void);
extern void motor_alarma(bool a);
extern const uint8_t *motor_clave(void);
extern uint32_t motor_ticks(void);
extern bool motor_modo_test;
extern int  motor_fallo_bus;
extern bool motor_colgado;
extern int  motor_n_tramas;

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
    uint8_t id = 0, diag = 0, st = 0;
    reg_leer(REG_ID, &id, 1);
    chk(id == 0xA5, "ID responde 0xA5");
    chk(!(leer_status() & ST_SEMBRADO), "al arrancar no hay estado sembrado");
    reg_leer(REG_DIAG, &diag, 1);
    chk(!(diag & DG_ARRANCADO), "al arrancar el test de arranque no ha pasado");

    printf("\n2) Sembrar y generar\n");
    reg_escribir1(REG_CFG_KD, 2);
    uint32_t t0 = motor_ticks();
    cmd_sembrar();
    chk(motor_ticks() > t0, "sembrar espera al test de arranque");
    chk(!(leer_status() & ST_SEMBRADO), "con CFG_KD bajo el motor rechaza y no queda sembrado");
    chk(orden(CTL_SEMBRAR, T_ORDEN_MS, &st) == ESP_ERR_INVALID_STATE,
        "orden() distingue el rechazo de una orden que acaba enseguida");
    reg_escribir1(REG_CFG_KD, 7);
    cmd_sembrar();
    chk((leer_status() & ST_SEMBRADO) != 0, "tras sembrar, el DRBG tiene estado");
    cmd_generar();
    chk(hay_clave, "la clave se provisiona en modo test y no es nula");
    uint8_t clave1[16];
    memcpy(clave1, clave_provisionada, 16);

    printf("\n3) Reto-respuesta\n");
    cmd_reto(20);
    chk(ult_reto.aciertos == 20 && ult_reto.fallos == 0 && ult_reto.errores == 0,
        "20 retos, 20 aciertos");

    printf("\n4) ALEATORIO es una generacion independiente\n");
    bool filtra = false;
    for (int i = 0; i < 10; i++) {
        uint8_t b[32];
        chk(orden(CTL_ALEATORIO, T_ORDEN_MS, &st) == ESP_OK, "aleatorio aceptado");
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

    printf("\n6) Sin modo test, generar invalida la clave provisionada\n");
    cmd_generar();
    chk(!hay_clave, "la provisionada deja de valer: el motor cambio de clave");
    motor_modo_test = true;
    cmd_generar();
    chk(hay_clave, "en modo test se vuelve a provisionar");

    printf("\n7) Un fallo de bus no se cuenta como fallo criptografico\n");
    printf("   (se fuerzan fallos de bus; el verificador debe distinguirlos)\n");
    motor_fallo_bus = 6;
    cmd_reto(2);
    motor_fallo_bus = 0;
    chk(ult_reto.errores == 2 && ult_reto.fallos == 0,
        "con el bus caido, 2 errores de bus y 0 fallos criptograficos");
    cmd_reto(5);
    chk(ult_reto.aciertos == 5, "y se recupera cuando el bus vuelve");

    printf("\n8) Con alarma no sale nada hacia el PC\n");
    uint8_t clave_antes[16];
    memcpy(clave_antes, motor_clave(), 16);
    motor_alarma(true);
    int tramas = motor_n_tramas;
    cmd_aleatorio(3);
    chk(motor_n_tramas == tramas, "aleatorio con alarma no envia ninguna trama");
    cmd_generar();
    chk(memcmp(motor_clave(), clave_antes, 16) == 0 && hay_clave,
        "generar rechazado: la clave del motor y la provisionada siguen valiendo");
    t0 = motor_ticks();
    cmd_sembrar();
    chk(motor_ticks() - t0 >= T_ARRANQUE_MS, "sembrar con alarma se rinde tras el plazo");
    cmd_borrar();
    cmd_aleatorio(3);
    chk(motor_n_tramas == tramas + 3, "tras borrar, aleatorio vuelve a enviar sus tramas");

    printf("\n9) Los plazos son de tiempo real\n");
    motor_colgado = true;
    t0 = motor_ticks();
    chk(orden(CTL_ALEATORIO, T_ORDEN_MS, &st) == ESP_ERR_TIMEOUT, "un motor colgado da timeout");
    chk(motor_ticks() - t0 >= T_ORDEN_MS, "y el timeout dura lo que dice");
    motor_colgado = false;

    printf("\n10) Regresion de la fuga corregida el 15-09\n");
    motor_modo_test = false;
    uint8_t mapa[256 + 15] = {0};
    for (int d = 0; d < 256; d += 16) reg_leer((uint8_t)d, mapa + d, 16);
    bool aparece = false;
    for (int d = 0; d < 256; d++)
        if (memcmp(mapa + d, motor_clave(), 16) == 0) aparece = true;
    chk(!aparece, "sin modo test la clave no aparece en ningun registro legible");
    motor_modo_test = true;

    printf("\ntest_verificador: %d fallos\n", fallos);
    return fallos == 0 ? 0 : 1;
}
