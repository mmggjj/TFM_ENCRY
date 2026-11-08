/* Banco del verificador contra el motor simulado, en el PC.
 *
 * Incluye main.c tal cual para poder llamar a sus funciones estaticas sin
 * tocarlas: lo que se prueba es el firmware que se va a flashear, no una
 * copia adaptada. bucle_consola() y app_main() no se llaman. Lo compila y
 * lo lanza run_host.py.
 *
 * Que demuestra: que la secuencia del mapa de registros funciona, que el
 * reto-respuesta cierra, que ALEATORIO nunca contiene la clave, que la
 * clave no se lee sin modo test, que un fallo de bus se cuenta como error
 * de bus y no como fallo criptografico, que una orden rechazada (alarma,
 * CFG_KD bajo, sin test de arranque) no se toma por buena ni deja salir
 * datos al PC, y que los plazos de espera son de tiempo real.
 *
 * Que NO demuestra: nada sobre el VHDL. Sobre la criptografia, solo si se
 * enlaza con mbedtls de verdad: con mbedtls_stub.c el CMAC del motor y el
 * del verificador son el mismo codigo (ver la cabecera de motor_sim.c).
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
extern uint32_t motor_pet_max;
extern bool motor_capturando;
extern bool motor_arranque_lento;

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

    motor_abrir(0, 0, 0);

    printf("\n1) Identificacion y arranque\n");
    uint8_t id = 0, diag = 0, st = 0;
    motor_reg_leer(REG_ID, &id, 1);
    chk(id == 0xA5, "ID responde 0xA5");
    chk(!(motor_status() & ST_SEMBRADO), "al arrancar no hay estado sembrado");
    motor_reg_leer(REG_DIAG, &diag, 1);
    chk(!(diag & DG_ARRANCADO), "al arrancar el test de arranque no ha pasado");

    printf("\n2) Sembrar y generar\n");
    motor_reg_escribir1(REG_CFG_KD, 2);
    uint32_t t0 = motor_ticks();
    cmd_sembrar();
    chk(motor_ticks() > t0, "sembrar espera al test de arranque");
    chk(!(motor_status() & ST_SEMBRADO), "con CFG_KD bajo el motor rechaza y no queda sembrado");
    chk(motor_orden(CTL_SEMBRAR, T_ORDEN_MS, &st) == ESP_ERR_INVALID_STATE,
        "motor_orden() distingue el rechazo de una orden que acaba enseguida");
    motor_reg_escribir1(REG_CFG_KD, 7);
    cmd_sembrar();
    chk((motor_status() & ST_SEMBRADO) != 0, "tras sembrar, el DRBG tiene estado");
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
        chk(motor_aleatorio(b) == ESP_OK, "aleatorio aceptado");
        if (memcmp(b, clave1, 16) == 0 || memcmp(b + 16, clave1, 16) == 0) filtra = true;
    }
    chk(!filtra, "en 10 lecturas, ALEATORIO nunca contiene la clave");

    printf("\n5) La clave no sale sin modo test\n");
    motor_modo_test = false;
    uint8_t k[16];
    motor_reg_leer(REG_CLAVE, k, 16);
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
    chk(motor_ticks() - t0 < 1000,
        "sembrar con alarma se rinde enseguida (con alarma el test de arranque no pasa)");
    cmd_borrar();
    cmd_aleatorio(3);
    chk(motor_n_tramas == tramas + 3, "tras borrar, aleatorio vuelve a enviar sus tramas");

    printf("\n9) Los plazos son de tiempo real\n");
    motor_colgado = true;
    t0 = motor_ticks();
    chk(motor_orden(CTL_ALEATORIO, T_ORDEN_MS, &st) == ESP_ERR_TIMEOUT, "un motor colgado da timeout");
    chk(motor_ticks() - t0 >= T_ORDEN_MS, "y el timeout dura lo que dice");
    motor_colgado = false;

    printf("\n10) Regresion de la fuga corregida el 15-09\n");
    motor_modo_test = false;
    uint8_t mapa[256 + 15] = {0};
    for (int d = 0; d < 256; d += 16) motor_reg_leer((uint8_t)d, mapa + d, 16);
    bool aparece = false;
    for (int d = 0; d < 256; d++)
        if (memcmp(mapa + d, motor_clave(), 16) == 0) aparece = true;
    chk(!aparece, "sin modo test la clave no aparece en ningun registro legible");
    motor_modo_test = true;

    printf("\n11) El contador de peticiones se agota y hay que resembrar\n");
    uint8_t pet[4];
    motor_reg_leer(REG_PETICIONES, pet, 4);
    uint32_t peticiones = pet[0] | (pet[1] << 8) | ((uint32_t)pet[2] << 16) | ((uint32_t)pet[3] << 24);
    motor_pet_max = peticiones + 2;
    cmd_aleatorio(5);                          /* solo 2 deben salir */
    int tramas_antes = motor_n_tramas;
    motor_reg_leer(REG_DIAG, &diag, 1);
    chk((diag & DG_AGOTADO) != 0, "DIAG.agotado tras llegar al tope");
    cmd_aleatorio(1);
    chk(motor_n_tramas == tramas_antes, "agotado: aleatorio rechazado y sin trama al PC");
    cmd_sembrar();
    motor_reg_leer(REG_DIAG, &diag, 1);
    chk((diag & DG_AGOTADO) == 0 && (motor_status() & ST_SEMBRADO), "resembrar baja DIAG.agotado");
    motor_pet_max = 0xFFFFFFFFu;

    printf("\n12) Zeroizacion del motor\n");
    cmd_generar();
    chk(hay_clave, "hay clave antes de borrar");
    cmd_cero();
    uint8_t cero16[16] = {0};
    chk(!hay_clave && memcmp(motor_clave(), cero16, 16) == 0, "tras 'cero' la clave del motor es nula y la provisionada no vale");
    chk(!(motor_status() & (ST_SEMBRADO | ST_CLAVE_VALIDA)), "ni sembrado ni clave valida");
    cmd_reto(1);
    chk(ult_reto.aciertos == 0 && ult_reto.fallos == 0, "reto sin clave no cuenta nada");
    cmd_sembrar();
    cmd_generar();
    cmd_reto(3);
    chk(ult_reto.aciertos == 3, "tras borrar, sembrar y generar, el reto-respuesta vuelve a cerrar");

    printf("\n13) Divisor y captura de bits crudos\n");
    cmd_kd(30);
    uint8_t kd = 0;
    motor_reg_leer(REG_CFG_KD, &kd, 1);
    chk(kd != 30, "kd fuera de rango no se escribe");
    cmd_kd(10);
    motor_reg_leer(REG_CFG_KD, &kd, 1);
    chk(kd == 10, "kd 10 queda escrito");
    tramas = motor_n_tramas;
    t0 = motor_ticks();
    cmd_crudo(3);
    chk(motor_n_tramas == tramas + 3, "crudo 3 envia 3 tramas");
    chk(motor_ticks() - t0 >= 3 * ((4096u << 10) / 300000u),
        "y espera a que cada captura se llene (4096 x 2^10 periodos de ro2)");
    cmd_kd(18);                                /* ~3,6 s por captura en el modelo */
    tramas = motor_n_tramas;
    t0 = motor_ticks();
    cmd_crudo(1);
    chk(motor_n_tramas == tramas + 1 && motor_ticks() - t0 >= 3000,
        "con kd 18 la captura tarda mas de los 2 s del plazo antiguo y llega");
    motor_capturando = true;
    tramas = motor_n_tramas;
    cmd_crudo(1);
    chk(motor_n_tramas == tramas, "con otra captura en curso no sale trama");
    motor_capturando = false;
    motor_modo_test = false;
    cmd_crudo(1);
    chk(motor_n_tramas == tramas, "sin modo test no sale trama");
    motor_modo_test = true;
    cmd_kd(6);
    cmd_crudo(1);
    cmd_sembrar();
    chk((motor_status() & ST_SEMBRADO) != 0, "tras capturar se vuelve a sembrar");

    printf("\n14) Plazos segun CFG_KD: anillo lento y CFG_KD = 24\n");
    cmd_kd(24);
    chk(motor_plazo_arranque_ms() == (uint32_t)(((uint64_t)2048 << 24) * 2000 / MOTOR_RO2_MIN_HZ),
        "plazo de arranque con kd 24 = 2 ventanas a 100 MHz, x2 (687 s)");
    cmd_kd(6);
    chk(motor_plazo_arranque_ms() == T_ARRANQUE_MS && motor_plazo_siembra_ms() == T_SIEMBRA_MS,
        "con kd 6 quedan los minimos de siempre");
    motor_arranque_lento = true;
    cmd_kd(24);
    cmd_borrar();                              /* reinicia la ventana: ~57 s a 300 MHz */
    t0 = motor_ticks();
    cmd_sembrar();
    uint32_t dt = motor_ticks() - t0;
    chk((motor_status() & ST_SEMBRADO) && dt > T_ARRANQUE_MS,
        "con kd 24 y ro2 a 300 MHz siembra, aunque el arranque dura mas que el plazo fijo de 30 s");
    printf("     (arranque y siembra: %u ms)\n", (unsigned)dt);
    motor_arranque_lento = false;
    cmd_kd(6);

    printf("\ntest_verificador: %d fallos\n", fallos);
    return fallos == 0 ? 0 : 1;
}
