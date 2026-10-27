/* mbedtls falso para el banco del verificador cuando no hay mbedtls de
 * verdad en el PC: el CMAC lo calcula el propio modelo del motor, asi que
 * la verificacion cruzada NO es independiente (ver motor_sim.c). Con
 * mbedtls real (run_host.py --mbedtls) este fichero no se enlaza. */
#include <stddef.h>
#include <stdint.h>

void motor_sim_cmac16(const uint8_t clave[16], const uint8_t msg[16], uint8_t tag[16]);

static const int CIPHER_AES128 = 1;
const void *mbedtls_cipher_info_from_type(int t) { (void)t; return &CIPHER_AES128; }
int mbedtls_cipher_cmac(const void *ci, const unsigned char *key, size_t keybits,
                        const unsigned char *input, size_t ilen, unsigned char *out)
{
    (void)ci;
    if (keybits != 128 || ilen != 16) return -1;
    motor_sim_cmac16(key, input, out);
    return 0;
}
