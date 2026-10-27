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
#define REG_CLAVE        0x10
#define REG_RETO         0x20
#define REG_ETIQUETA     0x30
#define REG_ALEATORIO    0x40
#define REG_CAPTURA      0x80

#define MOTOR_ID         0xA5
#define MOTOR_VERSION    0x03

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

#define DG_ARRANCADO     (1u << 0)
#define DG_RECHAZADA     (1u << 1)
#define DG_AGOTADO       (1u << 2)   /* contador de peticiones al tope: resembrar */

/* Tiempos de espera, en tiempo real. Con CFG_KD = 24 y el anillo a ~700 MHz
 * un bit tarda 24 ms: el test de arranque (1024 bits) ~25 s y una siembra
 * (384 bits mas, como mucho, una ventana de 1024 para validarlos) ~34 s. */
#define T_ARRANQUE_MS    30000u
#define T_SIEMBRA_MS     40000u
#define T_ORDEN_MS       500u

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

/* Sondea DIAG hasta que pase el test de arranque o venzan max_ms. diag:
 * ultimo DIAG leido. ESP_ERR_TIMEOUT si no arranca, ESP_FAIL si el bus. */
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
