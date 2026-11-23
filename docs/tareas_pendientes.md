# Tareas pendientes (apuntadas el 22-11-2026, para la semana del 23-11)

Estado al cierre del 22-11: H 0,60 cerrada en las cinco esquinas (Monte
Carlo del biestable, 24 chips por esquina, H declarable 0,757), caudal y
falsas alarmas del integrado (`results/caudal_integrado.md`), síntesis
repetida (`motor_top` 95,46 kGE), trece bancos en verde, placa cerrada con el
bitstream del 19-11. Fable está escribiendo la memoria (fases 2-4 de
`docs/plan_memoria_cierre.md`).

## En marcha

1. ~~**Memoria.**~~ Hecha el 22-11 (Fable, f0bce5a-ade2d66; revisada y
   corregida en b433571; EN 145 páginas, ES 150). Quedan tres notas no
   impresas: O5/KAT (punto 2), ciclos de siembra y generación con el AES de
   32 bits (M1, punto 11) y la foto del montaje (punto 12).

## Decisiones de Mario

2. **O5 y los KAT del DRBG en placa.** Opciones: (a) anotar que el DRBG se
   cubre en simulación (960 vectores CAVP) y AES/CMAC en placa contra mbedTLS
   (40/40 con la clave leída en modo test); (b) variante solo para la FPGA
   (genérico desactivado en el integrado) que en modo test deje cargar la
   semilla por I2C, comparar con `analysis/ctr_drbg_ref.py`, demostrar con
   `synth/equivalencia.sh` que el integrado queda igual, bitstream y prueba
   en placa: 4-6 h [ESTIMADO]; añade una vía de inyección de semilla que
   habría que defender. En la memoria hay una nota no impresa
   `% PENDIENTE DE MARIO: KAT en placa`.
3. **Aislamiento de los anillos en el integrado** (tarea 10 de
   `docs/basys3.md`, "Tareas pendientes (18-11-2026)"): búfer a la salida,
   alimentación o anillo de guarda propios, `ro_mon` sin carga. Propuesta:
   recomendación de trazado y trabajo futuro en la memoria, sin cambio de
   diseño.

## Cierre (después de la memoria)

4. **Revisión independiente de la memoria** (paso 22 del plan): agente sin
   las conclusiones de la sesión, con código y datos; aplicar correcciones.
5. ~~**Subir los commits locales** y comprobar la CI~~: subido el 22-11
   (b433571), CI en verde.
6. **PR de `feat/lecturas-firmadas` a `main`** con la CI en verde (paso 23).

## Opcionales (no cambian el diseño)

7. **Regrabar la placa** con un bitstream del RTL actual (el del 19-11 solo
   difiere ante escrituras de `CFG_KD` fuera de rango; `synth/basys3/build.tcl`).
8. **Origen de la raya de ~39,4 kHz** en la FPGA: descartado el sondeo I2C;
   hipótesis abierta, el regulador conmutado (portadora a ~480 kHz con bandas
   a ±39,5 kHz). Va a la memoria como hecho medido con origen abierto.
9. **Causa de la dispersión de Q con 11 etapas** (10,5 % frente al 5,6 % del
   blanco; `results/dispersion_q.md`): repetir 2-4 realizaciones guardando
   los cruces (`anillo_ihp.py`, ~2 h cada una) y mirar estacionariedad,
   arranque y var(M).
10. **Monte Carlo del peor chip con 11 etapas** (~11 h; regla ya fijada en
    `docs/decisiones_pendientes.md`). El revisor lo dio por recomendable, no
    necesario.

## Huecos de la memoria (apuntados el 23-11)

11. **Ciclos de siembra y generación con el AES de 32 bits (M1):** la memoria
    da 209 y 53 ciclos, que son del núcleo de una ronda; medirlos en
    simulación con el núcleo compacto (el que lleva `motor_top`) y llevarlos
    a `docs/` y al cap. 4.
12. **Foto del montaje** (Basys 3 + ESP32): la hace Mario; hueco comentado
    en el cap. 5.
