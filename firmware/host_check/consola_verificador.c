/* La consola del verificador en el PC, contra el modelo del motor: la
 * misma main.c que va al ESP32, por stdin/stdout. Sirve para probar los
 * programas del PC que hablan con el verificador (analysis/campana_motor.py)
 * sin placa. El tiempo es el del modelo: vTaskDelay avanza el tick sin
 * dormir, asi que una captura con kd alto "tarda" segundos de tick y
 * microsegundos de reloj. Termina al cerrarse stdin. Lo compila run_host.py.
 */
#include <stdio.h>
#include <stdlib.h>

static int consola_fgetc(FILE *f)
{
    int c = fgetc(f);
    if (c == EOF && feof(f)) exit(0);
    return c;
}
#define fgetc consola_fgetc
#include "main.c"
#undef fgetc

int main(void)
{
    setvbuf(stdout, NULL, _IOLBF, 0);
    app_main();
    return 0;
}
