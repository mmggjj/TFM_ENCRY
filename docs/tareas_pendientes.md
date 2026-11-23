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

2. ~~**O5 y los KAT del DRBG en placa.**~~ Decidido el 23-11 (Mario, tras
   una revisión independiente): O5 **cumplido con salvedad**, sin tocar el
   enunciado. Las 40/40 cubren AES, CMAC, registro de clave, I2C y
   secuenciador, pero no el CTR_DRBG (la clave es un dato leído, no una
   predicción). Los 960 casos CAVP los pasa el modelo Python; el VHDL se
   compara con el modelo. Añadido en simulación: `tb_motor_top` vuelca la
   semilla y `verifica_top.py` recalcula clave1, aleatorio1 y clave2 con el
   modelo (cadena semilla → clave de extremo a extremo), y `tb_ctr_drbg`
   pasa de 2 a 52 semillas. La variante de FPGA con carga de semilla
   (6-10 h) queda descartada; la de simular la netlist de Vivado, también.
3. **Aislamiento de los anillos en el integrado** (tarea 10 de
   `docs/basys3.md`, "Tareas pendientes (18-11-2026)"): búfer a la salida,
   alimentación o anillo de guarda propios, `ro_mon` sin carga. Propuesta:
   recomendación de trazado y trabajo futuro en la memoria, sin cambio de
   diseño.

## Cierre (después de la memoria)

4. ~~**Revisión independiente de la memoria**~~: hecha el 23-11
   (`results/revision_memoria_20261123/informe.md`: 12 graves, 47 medios,
   46 menores; cifras y tablas principales rehechas desde los datos,
   coinciden). Aplicada el mismo día (fb02735-61791f0; EN 156 páginas, ES
   163). Quedan los puntos 13-15.
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

## Lo que dejó la revisión del 23-11 (apuntado el 23-11)

13. **Para Mario:** agradecimientos (nombran a la empresa) y "Tutores"
    vacío, sin tocar; cotejar con los PDF originales lo que el repositorio no
    sostiene (Petura 2016, ec. 1 y columna de viabilidad; Bayon 2012,
    potencia del campo; BER 3-8 % de las SRAM; fecha de Blanco-Romero;
    Kuon y Rose "27-49×"). El factor 2,35 se sustituyó por un rango de
    utilización de `docs/via_asic.md`; si aparece su fuente, se cita.
14. **Fuera de `memoria/`:** el comentario de `rtl/trng/health_tests.vhd`
    (15-17) dice que la norma permite el complemento del APT (es una
    adición propia); el autotest de `analysis/nist_sp800_22.py` aborta ~38 %
    de las veces (cuenta como fallos las excursiones no aplicables);
    `docs/modelo_ero_resultados.md` (157-161) arrastra el rango erróneo de la
    estimación previa del divisor.
15. **Solo se cierran midiendo o simulando** (la memoria ya no los afirma):
    la RF en A y B del ESP32; si la raya reproduce b ≈ 2; el espectro del
    bitstream de campaña (`espectro_fase.py --lista` sobre
    `basys3_jitter_kd02_quieto_bel`); los ciclos con el AES de 32 bits (hoy
    849 y 213 [ESTIMADO] en la memoria; punto 11); QEMU y placa del medidor
    con el firmware 0x04; por qué salen 2 o 3 bloques por clave; la
    diferencia entre tandas del Monte Carlo; el margen del primer biestable
    en la esquina rápida; los 774 grupos de `radio_sin_ruido`.
