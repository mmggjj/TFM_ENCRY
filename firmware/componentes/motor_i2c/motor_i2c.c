/* Acceso al motor de claves por I2C. Ver motor_i2c.h. */
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "motor_i2c.h"

static const char *TAG = "motor_i2c";

static i2c_master_bus_handle_t bus;
static i2c_master_dev_handle_t motor;
static bool io_ok = true;
static uint32_t rng_bloques;

esp_err_t motor_abrir(int puerto, int sda, int scl)
{
    i2c_master_bus_config_t bcfg = {
        .i2c_port = puerto, .sda_io_num = sda, .scl_io_num = scl,
        .clk_source = I2C_CLK_SRC_DEFAULT, .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    esp_err_t e = i2c_new_master_bus(&bcfg, &bus);
    if (e != ESP_OK) return e;
    i2c_device_config_t dcfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7, .device_address = MOTOR_DIR,
        .scl_speed_hz = 400000,
    };
    return i2c_master_bus_add_device(bus, &dcfg, &motor);
}

esp_err_t motor_reg_escribir(uint8_t dir, const uint8_t *datos, size_t n)
{
    uint8_t buf[1 + 32];
    if (n > 32) return ESP_ERR_INVALID_SIZE;
    buf[0] = dir;
    memcpy(buf + 1, datos, n);
    esp_err_t e = i2c_master_transmit(motor, buf, 1 + n, 100);
    if (e != ESP_OK) io_ok = false;
    return e;
}

esp_err_t motor_reg_leer(uint8_t dir, uint8_t *datos, size_t n)
{
    esp_err_t e = i2c_master_transmit_receive(motor, &dir, 1, datos, n, 100);
    if (e != ESP_OK) {
        io_ok = false;
        memset(datos, 0, n);   /* nunca dejar el buffer del llamante sin tocar */
    }
    return e;
}

esp_err_t motor_reg_escribir1(uint8_t dir, uint8_t v)
{
    return motor_reg_escribir(dir, &v, 1);
}

uint8_t motor_status(void)
{
    uint8_t s = 0;
    /* Si la lectura falla se devuelve 0, no 0xFF: con 0xFF quedaban a uno
     * sembrado, clave_valida, etiqueta_lista y modo_test, o sea que un bus
     * caido se leia como "todo listo". Falla cerrado. */
    motor_reg_leer(REG_STATUS, &s, 1);
    return s;
}

/* Antes se contaban vueltas de 2 ms, pero a 100 Hz pdMS_TO_TICKS(2) es 0 y
 * el plazo duraba una fraccion de lo indicado. */
esp_err_t motor_esperar_libre(uint32_t max_ms, uint8_t *st)
{
    const TickType_t t0 = xTaskGetTickCount();
    const TickType_t paso = pdMS_TO_TICKS(2) ? pdMS_TO_TICKS(2) : 1;
    for (;;) {
        if (motor_reg_leer(REG_STATUS, st, 1) != ESP_OK) return ESP_FAIL;
        if (!(*st & ST_OCUPADO)) return ESP_OK;
        if (xTaskGetTickCount() - t0 >= pdMS_TO_TICKS(max_ms)) break;
        vTaskDelay(paso);
    }
    ESP_LOGE(TAG, "el motor no se libera en %" PRIu32 " ms", max_ms);
    return ESP_ERR_TIMEOUT;
}

esp_err_t motor_orden(uint8_t ctl, uint32_t max_ms, uint8_t *st)
{
    uint8_t diag = 0;
    *st = 0;
    /* "Ocupado: no mandar otra orden" es obligacion del maestro. Tras un
     * fallo de bus a mitad de una orden el motor puede seguir ocupado un
     * instante, y la siguiente orden se rechazaria sin motivo. */
    esp_err_t e = motor_esperar_libre(max_ms, st);
    if (e != ESP_OK) return e;
    if (motor_reg_escribir1(REG_CONTROL, ctl) != ESP_OK) return ESP_FAIL;
    e = motor_esperar_libre(max_ms, st);
    if (e != ESP_OK) return e;
    if (motor_reg_leer(REG_DIAG, &diag, 1) != ESP_OK) return ESP_FAIL;
    return (diag & DG_RECHAZADA) ? ESP_ERR_INVALID_STATE : ESP_OK;
}

esp_err_t motor_esperar_arranque(uint32_t max_ms, uint8_t *diag)
{
    const TickType_t t0 = xTaskGetTickCount();
    const TickType_t paso = pdMS_TO_TICKS(10) ? pdMS_TO_TICKS(10) : 1;
    for (;;) {
        if (motor_reg_leer(REG_DIAG, diag, 1) != ESP_OK) return ESP_FAIL;
        if (*diag & DG_ARRANCADO) return ESP_OK;
        if (xTaskGetTickCount() - t0 >= pdMS_TO_TICKS(max_ms)) return ESP_ERR_TIMEOUT;
        vTaskDelay(paso);
    }
}

esp_err_t motor_aleatorio(uint8_t bloque[32])
{
    uint8_t st;
    memset(bloque, 0, 32);
    /* Una orden rechazada deja en ALEATORIO el bloque anterior, y un fallo
     * de bus deja ceros: ninguno de los dos vale como aleatorio. */
    esp_err_t e = motor_orden(CTL_ALEATORIO, T_ORDEN_MS, &st);
    if (e != ESP_OK) return e;
    return motor_reg_leer(REG_ALEATORIO, bloque, 32);
}

/* Borrado que el compilador no puede quitar: un memset sobre una variable
 * que muere justo despues desaparece con -O2/-Os (comprobado en el
 * ensamblador), y el ultimo bloque del motor se quedaba en la pila. */
static void borrar(uint8_t *p, size_t n)
{
    volatile uint8_t *v = p;
    while (n--) *v++ = 0;
}

int motor_rng(void *ctx, unsigned char *salida, size_t n)
{
    (void)ctx;
    uint8_t b[32];
    unsigned char *p = salida;
    size_t resto = n;
    while (resto > 0) {
        if (motor_aleatorio(b) != ESP_OK) {
            memset(salida, 0, n);
            borrar(b, sizeof b);
            return MOTOR_ERR_RNG;
        }
        rng_bloques++;
        size_t k = resto < 32 ? resto : 32;
        memcpy(p, b, k);
        p += k;
        resto -= k;
    }
    borrar(b, sizeof b);
    return 0;
}

uint32_t motor_rng_bloques(void) { return rng_bloques; }
bool motor_io_ok(void) { return io_ok; }
void motor_io_reiniciar(void) { io_ok = true; }

const char *motor_texto_err(esp_err_t e)
{
    switch (e) {
    case ESP_OK:                return "ok";
    case ESP_ERR_INVALID_STATE: return "RECHAZADA por el motor";
    case ESP_ERR_TIMEOUT:       return "el motor no se libera";
    default:                    return "ERROR I2C";
    }
}

const char *motor_texto_alarmas(uint8_t st)
{
    if ((st & ST_ALM_RCT) && (st & ST_ALM_APT)) return " ALARMA_RCT ALARMA_APT";
    if (st & ST_ALM_RCT) return " ALARMA_RCT";
    if (st & ST_ALM_APT) return " ALARMA_APT";
    return "";
}
