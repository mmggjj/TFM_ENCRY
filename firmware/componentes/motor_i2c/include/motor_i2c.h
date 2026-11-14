/* Capa de acceso al motor de claves por I2C, comun a los programas del
 * ESP32 (verificador y medidor). Es docs/mapa_registros.md en C: si cambia
 * el mapa, cambia esto.
 *
 * Reglas que impone: ninguna orden se da por buena sin mirar
 * DIAG.rechazada, los plazos son de tiempo real y un fallo del bus se
 * distingue de un rechazo del motor. motor_rng() falla cerrado: si el
 * motor no da aleatorio (alarma, sin sembrar, bus caido) no se rellena con
 * otra fuente, se devuelve error y mbedtls aborta la operacion.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

/* ---- mapa de registros (docs/mapa_registros.md) ---------------------- */
#define MOTOR_DIR        0x30
#define REG_ID           0x00
#define REG_VERSION      0x01
#define REG_STATUS       0x02
#define REG_CONTROL      0x03
#define REG_CFG_KD       0x04
#define REG_CFG_PAG      0x05
#define REG_PETICIONES   0x0A
#define REG_DIAG         0x0E
#define REG_FLUJO        0x0F
#define REG_CLAVE        0x10
#define REG_RETO         0x20
#define REG_ETIQUETA     0x30
#define REG_ALEATORIO    0x40
#define REG_FLUJO_N      0x60   /* y 31 bytes de FLUJO_DATO detras */
#define REG_CAPTURA      0x80

#define MOTOR_ID         0xA5
#define MOTOR_VERSION    0x04   /* 0x04: captura continua (FLUJO) */
#define MOTOR_VERSION_MIN 0x03  /* lo que necesitan el verificador y el medidor */

#define ST_SEMBRADO      (1u << 0)
#define ST_OCUPADO       (1u << 1)
#define ST_ALM_RCT       (1u << 2)
#define ST_ALM_APT       (1u << 3)
#define ST_CLAVE_VALIDA  (1u << 4)
#define ST_CAPTURA_LLENA (1u << 5)
#define ST_ETIQ_LISTA    (1u << 6)
#define ST_MODO_TEST     (1u << 7)

#define CTL_SEMBRAR      (1u << 0)
#define CTL_GENERAR      (1u << 1)
#define CTL_AUTENTICAR   (1u << 2)
#define CTL_BORRAR_ALM   (1u << 3)
#define CTL_CAPTURAR     (1u << 4)
#define CTL_RESEMBRAR    (1u << 5)
#define CTL_ALEATORIO    (1u << 6)
#define CTL_BORRAR_TODO  (1u << 7)   /* zeroizacion: clave, DRBG, RETO, ALEATORIO */

#define FL_ACTIVO        (1u << 0)
#define FL_DESBORDADO    (1u << 1)
#define MOTOR_FLUJO_MAX  31u     /* bytes de flujo por transaccion */

#define DG_ARRANCADO     (1u << 0)
#define DG_RECHAZADA     (1u << 1)
#define DG_AGOTADO       (1u << 2)   /* contador de peticiones al tope: resembrar */
#define DG_SOLO_FUENTE   (1u << 3)   /* motor sin criptografia (Basys 2): solo bits crudos */

/* Tiempos de espera, en tiempo real. Los que dependen de los bits del anillo
 * (arranque, siembra, captura) se calculan con el CFG_KD del motor y ro2 a
 * MOTOR_RO2_MIN_HZ: con plazos fijos pensados para ~700 MHz, el anillo de
 * la FPGA (estimado 170-330 MHz) con CFG_KD = 24 no pasaba el test de
 * arranque a tiempo. T_ARRANQUE_MS y T_SIEMBRA_MS quedan como minimo. */
#define T_ARRANQUE_MS    30000u
#define T_SIEMBRA_MS     40000u
#define T_ORDEN_MS       500u
#define MOTOR_RO2_MIN_HZ 100000000ull     /* suelo de ro2 para los plazos */
#define MOTOR_BITS_APT   1024u            /* ventana del test de arranque */
#define MOTOR_BITS_SEMILLA 384u

/* Lo que devuelve motor_rng() cuando el motor no da aleatorio. Es el valor
 * de MBEDTLS_ERR_ENTROPY_SOURCE_FAILED, para que quien reciba el error de
 * mbedtls sepa de donde viene sin que esta capa dependa de mbedtls. */
#define MOTOR_ERR_RNG    (-0x003C)

/* Abre el bus y da de alta el motor. puerto es el numero de I2C del chip. */
esp_err_t motor_abrir(int puerto, int sda, int scl);

/* Acceso a registros. n <= 32 en las escrituras. Una lectura fallida deja
 * ceros en el buffer, nunca basura. Cualquier fallo baja motor_io_ok(). */
esp_err_t motor_reg_escribir(uint8_t dir, const uint8_t *datos, size_t n);
esp_err_t motor_reg_leer(uint8_t dir, uint8_t *datos, size_t n);
esp_err_t motor_reg_escribir1(uint8_t dir, uint8_t v);

/* STATUS, o 0 si el bus falla: un bus caido se lee como "nada listo". */
uint8_t motor_status(void);

/* Sondea hasta que baje "ocupado" o venzan max_ms. st: STATUS final.
 *   ESP_ERR_TIMEOUT  no se libera a tiempo
 *   ESP_FAIL         fallo del bus */
esp_err_t motor_esperar_libre(uint32_t max_ms, uint8_t *st);

/* Lanza una orden y espera a que acabe. El motor ignora las ordenes que no
 * puede atender (alarma, sin arrancar, sin sembrar, CFG_KD bajo, ocupado) o
 * aborta la siembra si la fuente falla, y lo dice en DIAG.rechazada; sin
 * mirarlo, una orden ignorada parece una que acabo enseguida.
 *   ESP_ERR_INVALID_STATE  rechazada o abortada por el motor
 *   ESP_ERR_TIMEOUT        no se libera a tiempo
 *   ESP_FAIL               fallo del bus */
esp_err_t motor_orden(uint8_t ctl, uint32_t max_ms, uint8_t *st);

/* Plazo para que el ERO entregue `bits` bits con el CFG_KD actual (se lee
 * del motor; si el bus falla se toma 24): bits * 2^CFG_KD periodos de ro2 a
 * MOTOR_RO2_MIN_HZ, por dos, y nunca menos de minimo_ms. */
uint32_t motor_plazo_bits_ms(uint32_t bits, uint32_t minimo_ms);

/* Plazos del test de arranque (hasta dos ventanas: la que este a medias y
 * una entera) y de la siembra (semilla mas esas dos ventanas). */
uint32_t motor_plazo_arranque_ms(void);
uint32_t motor_plazo_siembra_ms(void);

/* Sondea DIAG hasta que pase el test de arranque o venzan max_ms. diag:
 * ultimo DIAG leido. ESP_ERR_TIMEOUT si no arranca, ESP_FAIL si el bus,
 * ESP_ERR_INVALID_STATE en cuanto STATUS tenga una alarma: con alarma el
 * test no pasa hasta borrar_alarmas, y esperar el plazo entero no sirve. */
esp_err_t motor_esperar_arranque(uint32_t max_ms, uint8_t *diag);

/* Una orden "aleatorio" y la lectura de sus 32 bytes. Errores como
 * motor_orden(); con error el bloque queda a ceros. */
esp_err_t motor_aleatorio(uint8_t bloque[32]);

/* f_rng para mbedtls: rellena n bytes con bloques del DRBG del motor. Si
 * una orden falla devuelve MOTOR_ERR_RNG y deja la salida a ceros: no hay
 * fuente de reserva. Cada llamada consume bloques enteros. */
int motor_rng(void *ctx, unsigned char *salida, size_t n);

/* Bloques de 32 bytes que motor_rng() ha sacado del motor desde el inicio. */
uint32_t motor_rng_bloques(void);

/* Un fallo del bus no es un fallo criptografico. Cualquier acceso que falle
 * baja motor_io_ok(); quien cuente resultados lo reinicia antes y lo mira
 * despues para separar los dos casos en vez de sumarlos. */
bool motor_io_ok(void);
void motor_io_reiniciar(void);

const char *motor_texto_err(esp_err_t e);
const char *motor_texto_alarmas(uint8_t st);
