/* Banco del medidor contra el motor simulado, en el PC, con mbedtls de
 * verdad. Incluye main.c del medidor tal cual (ver test_verificador.c).
 * Lo compila y lo lanza run_host.py, que ademas pasa la salida de este
 * programa, con sus tramas, por analysis/verifica_lecturas.py: la
 * comprobacion de las firmas en el PC la hace otra biblioteca
 * (cryptography), no mbedtls.
 *
 * Que demuestra: que sin aleatorio del motor (sin sembrar, alarma, bus
 * caido) no hay clave nueva y la anterior sigue valiendo; que la clave
 * consume bloques del motor; que las lecturas firmadas se verifican con
 * la publica y una lectura manipulada o repetida no; que la firma es
 * determinista (no depende de ningun generador al firmar); que la CSR
 * lleva la misma publica; que la privada no aparece en ninguna trama; y
 * que tras olvidar la clave no sale nada.
 *
 * Que NO demuestra: nada sobre el VHDL ni sobre la calidad de la
 * entropia del motor, que aqui es un modelo.
 */
#include "main.c"
#include "mbedtls/x509_csr.h"

extern bool motor_sim_autotest(void);
extern void motor_alarma(bool a);
extern uint32_t motor_ticks(void);
extern int  motor_fallo_bus;
extern int  motor_fallo_tras_aleatorio;
extern int  motor_n_tramas;
extern int  motor_n_aleatorio;
extern bool plataforma_nvs_rota;
extern bool plataforma_nvs_hay_blob(void);

static int fallos = 0;
/* Lo que el banco ha mandado al PC, para que run_host.py lo contraste con
 * lo que encuentre verifica_lecturas.py. */
static int esp_validas = 0, esp_manipuladas = 0, esp_repetidas = 0, esp_csr = 0, esp_cambios = 0;

static void chk(bool cond, const char *msg)
{
    printf("  [%s] %s\n", cond ? "ok " : "FALLO", msg);
    if (!cond) fallos++;
}

static size_t publica_actual(uint8_t der[PUBLICA_MAX])
{
    size_t n = 0;
    if (clave_publica(&clave, der, PUBLICA_MAX, &n) != 0) return 0;
    return n;
}

/* d de la clave privada: en el ECPrivateKey DER de P-256 (SEC1) va tras
 * la cabecera 30 77 02 01 01 04 20. */
static bool privada_actual(uint8_t d[32])
{
    uint8_t der[160];
    int n = mbedtls_pk_write_key_der(&clave.pk, der, sizeof der);
    if (n <= 0) return false;
    const uint8_t *p = der + sizeof der - n;
    if (n != 121 || p[0] != 0x30 || p[5] != 0x04 || p[6] != 0x20) return false;
    memcpy(d, p + 7, 32);
    return true;
}

static bool contiene(const uint8_t *pajar, size_t n, const uint8_t *aguja, size_t m)
{
    if (m > n) return false;
    for (size_t i = 0; i + m <= n; i++)
        if (memcmp(pajar + i, aguja, m) == 0) return true;
    return false;
}

int main(void)
{
    printf("Banco del medidor contra el motor simulado\n\n");

    printf("0) El modelo de referencia se valida a si mismo\n");
    if (!motor_sim_autotest()) { printf("\nmodelo roto, no se sigue\n"); return 1; }

    iniciar_medidor();
    motor_abrir(0, 0, 0);
    uint8_t cero8[8] = {0};
    chk(memcmp(actual.id, cero8, 8) != 0, "el id del equipo sale de la MAC del chip");

    printf("\n1) Sin sembrar no hay clave\n");
    cmd_clave();
    chk(!clave.valida, "clave rechazada: el motor no da aleatorio sin sembrar");
    chk(motor_n_aleatorio == 0 && motor_rng_bloques() == 0, "y no se consumio ningun bloque");
    int tramas = motor_n_tramas;
    cmd_lectura(2);
    chk(motor_n_tramas == tramas, "sin clave no sale ninguna lectura");
    cmd_csr();
    chk(motor_n_tramas == tramas, "ni CSR");

    printf("\n2) Clave del equipo con aleatorio del motor\n");
    cmd_sembrar();
    chk((motor_status() & ST_SEMBRADO) != 0, "el motor queda sembrado");
    tramas = motor_n_tramas;
    cmd_clave();
    chk(clave.valida, "hay clave");
    chk(motor_n_aleatorio >= 1 && (int)motor_rng_bloques() == motor_n_aleatorio,
        "cada bloque de la clave es una orden aleatorio aceptada por el motor");
    chk(motor_n_tramas == tramas + 1, "la publica sale en una trama P");
    uint8_t pub1[PUBLICA_MAX];
    size_t npub1 = publica_actual(pub1);
    chk(npub1 == 91 && pub1[0] == 0x30, "publica en SubjectPublicKeyInfo DER de P-256 (91 bytes)");

    printf("\n3) Lecturas firmadas\n");
    tramas = motor_n_tramas;
    uint32_t t0 = motor_ticks();
    cmd_lectura(5);
    esp_validas += 5;
    chk(motor_n_tramas == tramas + 5, "5 lecturas, 5 tramas L");
    /* Humo, no temporizacion: con los stubs vTaskDelay solo suma ticks. */
    chk(motor_ticks() - t0 >= 4 * INTERVALO_MS, "entre lecturas se cede la CPU el intervalo");
    chk(actual.secuencia == ((1u << 24) | 5) && actual.energia_wh > 0,
        "secuencia = arranque 1, lectura 5; la energia avanza");
    uint8_t reg[LECTURA_BYTES], f1[FIRMA_MAX], f2[FIRMA_MAX];
    size_t nf1 = 0, nf2 = 0;
    lectura_serializar(&actual, reg);
    chk(clave_firmar(&clave, reg, f1, sizeof f1, &nf1, rng_chip, NULL) == 0 &&
        clave_verificar(pub1, npub1, reg, f1, nf1) == 0, "la ultima lectura verifica con la publica");
    chk(clave_firmar(&clave, reg, f2, sizeof f2, &nf2, rng_chip, NULL) == 0 &&
        nf1 == nf2 && memcmp(f1, f2, nf1) == 0, "firma determinista: dos firmas iguales");
    reg[16] ^= 0x01;
    chk(clave_verificar(pub1, npub1, reg, f1, nf1) != 0, "un bit cambiado en la energia y no verifica");
    reg[16] ^= 0x01;
    lectura_t l2;
    lectura_deserializar(reg, &l2);
    chk(memcmp(&l2, &actual, sizeof l2) == 0, "serializar y deserializar es la identidad");

    printf("\n4) Lecturas que el PC debe rechazar\n");
    /* Manipulada: la energia cambia y la firma es la antigua, CRC bueno. */
    uint8_t trama[LECTURA_BYTES + FIRMA_MAX];
    memcpy(trama, reg, LECTURA_BYTES);
    memcpy(trama + LECTURA_BYTES, f1, nf1);
    trama[16] ^= 0x10;
    printf("# lectura manipulada\n");
    trama_pc('L', trama, LECTURA_BYTES + nf1);
    esp_manipuladas++;
    /* Repetida: la ultima lectura otra vez, intacta. */
    printf("# lectura repetida\n");
    memcpy(trama, reg, LECTURA_BYTES);
    trama_pc('L', trama, LECTURA_BYTES + nf1);
    esp_repetidas++;

    printf("\n5) Con el motor en alarma se sigue firmando, pero no hay clave nueva\n");
    motor_alarma(true);
    cmd_clave();
    uint8_t pub2[PUBLICA_MAX];
    chk(clave.valida && publica_actual(pub2) == npub1 && memcmp(pub1, pub2, npub1) == 0,
        "clave rechazada con alarma: sigue la anterior");
    tramas = motor_n_tramas;
    cmd_lectura(2);
    esp_validas += 2;
    chk(motor_n_tramas == tramas + 2, "las lecturas siguen saliendo con la clave que hay");
    cmd_borrar();
    cmd_sembrar();
    chk((motor_status() & ST_SEMBRADO) != 0, "tras borrar y repetir el arranque, sembrado");

    printf("\n6) Un fallo de bus a mitad de la clave no deja una clave a medias\n");
    /* El primer bloque sale bien y el bus cae antes de leer el segundo. */
    int antes_aleatorio = motor_n_aleatorio;
    motor_fallo_tras_aleatorio = motor_n_aleatorio + 1;
    cmd_clave();
    motor_fallo_tras_aleatorio = 0;
    motor_fallo_bus = 0;
    chk(motor_n_aleatorio == antes_aleatorio + 1, "el motor llego a aceptar el primer bloque");
    chk(clave.valida && publica_actual(pub2) == npub1 && memcmp(pub1, pub2, npub1) == 0,
        "con el bus caido a mitad no hay clave nueva y sigue la anterior");

    printf("\n7) Clave nueva y CSR\n");
    cmd_clave();
    esp_cambios++;
    size_t npub2 = publica_actual(pub2);
    chk(clave.valida && (npub2 != npub1 || memcmp(pub1, pub2, npub1) != 0),
        "la segunda clave es distinta de la primera");
    static char pem[CSR_MAX];
    cmd_csr();
    esp_csr++;
    chk(clave_csr(&clave, "CN=prueba", pem, sizeof pem, rng_chip, NULL) == 0, "la CSR se genera");
    mbedtls_x509_csr csr;
    mbedtls_x509_csr_init(&csr);
    int r = mbedtls_x509_csr_parse(&csr, (const unsigned char *)pem, strlen(pem) + 1);
    chk(r == 0, "la CSR se parsea (PKCS#10)");
    uint8_t pubcsr[PUBLICA_MAX];
    int npc = r == 0 ? mbedtls_pk_write_pubkey_der(&csr.pk, pubcsr, sizeof pubcsr) : -1;
    chk(npc == (int)npub2 && memcmp(pubcsr + sizeof pubcsr - npc, pub2, npub2) == 0,
        "la CSR lleva la publica del equipo");
    mbedtls_x509_csr_free(&csr);
    tramas = motor_n_tramas;
    cmd_lectura(1);
    esp_validas += 1;
    chk(motor_n_tramas == tramas + 1, "y se firma con la clave nueva");

    printf("\n8) La privada no aparece en lo que sale\n");
    uint8_t d[32];
    chk(privada_actual(d), "se extrae d de la clave para buscarla");
    lectura_serializar(&actual, reg);
    clave_firmar(&clave, reg, f1, sizeof f1, &nf1, rng_chip, NULL);
    chk(!contiene(pub2, npub2, d, 8) && !contiene(f1, nf1, d, 8) &&
        !contiene((const uint8_t *)pem, strlen(pem), d, 8),
        "ni la publica, ni una firma, ni la CSR contienen 8 bytes seguidos de d");

    printf("\n9) Olvidar la clave\n");
    cmd_olvidar();
    chk(!clave.valida, "la clave deja de valer");
    tramas = motor_n_tramas;
    cmd_lectura(1);
    cmd_publica();
    chk(motor_n_tramas == tramas, "sin clave no sale ni lectura ni publica");

    printf("\n10) Tras un reinicio la secuencia sigue creciendo\n");
    uint32_t seq_antes = actual.secuencia;
    iniciar_medidor();                         /* el "reinicio": RAM a cero, NVS no */
    chk(!clave.valida, "al reiniciar no hay clave en RAM");
    cmd_clave();                               /* el motor sigue sembrado */
    esp_cambios++;
    chk(clave.valida, "clave nueva tras el reinicio");
    cmd_lectura(1);
    esp_validas += 1;
    chk((actual.secuencia >> 24) == 2 && actual.secuencia > seq_antes,
        "arranque 2: la primera lectura supera a la ultima de antes del reinicio");
    plataforma_nvs_rota = true;
    iniciar_medidor();
    plataforma_nvs_rota = false;
    chk(arranques == 0, "sin NVS el contador de arranques es 0 y se avisa");
    chk(!clave.valida, "y sin NVS tampoco se recupera la clave");

    printf("\n11) La clave guardada en NVS sobrevive al reinicio\n");
    chk(plataforma_nvs_hay_blob(), "'clave' la dejo guardada en la NVS");
    iniciar_medidor();                         /* reinicio con NVS sana */
    chk(clave.valida, "al arrancar se recupera la clave de la NVS");
    uint8_t pub3[PUBLICA_MAX];
    size_t npub3 = publica_actual(pub3);
    cmd_lectura(1);
    esp_validas += 1;
    chk(npub3 > 0 && (actual.secuencia >> 24) == 3, "firma con la misma identidad en el arranque 3");
    uint8_t der[PRIVADA_MAX];
    size_t nder = 0;
    chk(clave_exportar(&clave, der, sizeof der, &nder) == 0 && nder == 121 && der[0] == 0x30,
        "la privada exportada es un ECPrivateKey DER de 121 bytes");
    cmd_olvidar();
    chk(!plataforma_nvs_hay_blob(), "'olvidar' la borra tambien de la NVS");
    iniciar_medidor();
    chk(!clave.valida, "y tras ese reinicio no hay clave");
    cmd_lectura(1);                            /* no debe salir nada */

    printf("\nesperado: validas=%d firma_invalida=%d repetidas=%d csr=%d clave_cambiada=%d\n",
           esp_validas, esp_manipuladas, esp_repetidas, esp_csr, esp_cambios);
    printf("test_medidor: %d fallos\n", fallos);
    return fallos == 0 ? 0 : 1;
}
