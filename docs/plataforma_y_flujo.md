# Plataforma y flujo de herramientas — Motor criptográfico ligero en FPGA (Basys 3 / Artix-7) validado frente al ESP32

Documento de investigación técnica (plataforma y herramientas; **no** cubre criptografía ni teoría del TRNG).
Fecha de consulta de todas las fuentes: 2026-09-11.

Convención de marcado:
- **[VERIFICADO]**: la página/PDF se abrió y confirma el dato (se indica versión del documento).
- **[VERIFICADO URL]**: la URL existe y pertenece al documento citado, pero el texto concreto no se pudo leer (docs.amd.com sirve el cuerpo por JavaScript) — el dato se toma de otra fuente o se marca aparte.
- **[NO VERIFICADO]**: dato de segunda mano (buscador, foros) no confirmado en fuente primaria.
- **[ESTIMADO]**: juicio propio/experiencia, no hay fuente.

Nota metodológica: digilent.com devuelve 403 a herramientas automáticas y docs.amd.com sirve el contenido por JS; los datos de Digilent se han tomado de los **PDF** oficiales del mismo dominio (manual y esquemático) y los de AMD de los PDF originales (DS180, DS181, UG470, UG480) o de páginas cuyo cuerpo sí se sirvió.

---

## 1. Digilent Basys 3

### 1.1 FPGA y recursos

| Dato | Valor | Fuente |
|---|---|---|
| FPGA | **XC7A35T-1CPG236C** (IC7 en el esquemático) | Esquemático Basys 3 C.0 hoja 4/5 [VERIFICADO]; RM §Overview [VERIFICADO] |
| Celdas lógicas | 33 280 | DS180 v2.6.1 (2020-09-08) Tabla Artix-7 [VERIFICADO] |
| Slices | 5 200 (cada slice: 4 LUT6 + 8 FF → 20 800 LUT6, 41 600 FF) | DS180 Tabla + nota 1 [VERIFICADO]; RM: "33,280 logic cells in 5200 slices (each slice contains four 6-input LUTs and 8 flip-flops)" [VERIFICADO] |
| RAM distribuida máx. | 400 Kb | DS180 [VERIFICADO] |
| Block RAM | 50 bloques de 36 Kb (100 de 18 Kb) = 1 800 Kb | DS180 [VERIFICADO]; RM "1,800 Kbits" [VERIFICADO] |
| DSP48E1 | 90 | DS180 [VERIFICADO] |
| CMT (1 MMCM + 1 PLL cada una) | 5 | DS180 [VERIFICADO]; RM "Five clock management tiles, each with a phase-locked loop" [VERIFICADO] |
| XADC | 1 | DS180 [VERIFICADO] |
| PCIe / GTP | 1 bloque PCIe, 4 GTP en el die; **2 GTP** disponibles en CPG236 | DS180 Tabla 5 [VERIFICADO] |
| E/S máx. | 250 en el die; **106 E/S de usuario** en CPG236 (10×10 mm, paso 0,5 mm) | DS180 Tabla 5 [VERIFICADO] |
| Longitud del bitstream | 17 536 096 bits (≈2,19 MB sin comprimir) | UG470 v1.10 Tabla 1-1 [VERIFICADO] |
| Grado de velocidad | -1 (VCCINT nominal 1,0 V) | DS181 v1.27.1 [VERIFICADO] |

URLs:
- DS180: https://docs.amd.com/v/u/en-US/ds180_7Series_Overview (PDF directo: https://docs.amd.com/api/khub/documents/2LByHkO~nSZXcei2D55fTg/content)
- DS181: https://docs.amd.com/v/u/en-US/ds181_Artix_7_Data_Sheet (PDF directo: https://docs.amd.com/api/khub/documents/iAkxxTOk96ANLJqYf2hgrQ/content)
- UG470: https://docs.amd.com/v/u/en-US/ug470_7Series_Config
- Manual (RM) Basys 3: https://digilent.com/reference/programmable-logic/basys-3/reference-manual ; PDF: https://digilent.com/reference/_media/basys3:basys3_rm.pdf ("Revised April 8, 2016 — This manual applies to the Basys 3 rev. C, DOC# 502-183") [VERIFICADO]
- Esquemático: https://digilent.com/reference/_media/basys3:basys3_sch.pdf ("Basys 3 C.0", Doc# 500-183, 5/21/2014, 7 hojas en el PDF) [VERIFICADO]

### 1.2 Oscilador de placa — dato crítico para el TRNG

- El RM dice: "The Basys 3 board includes a single 100 MHz oscillator connected to pin W5 (W5 is a MRCC input on bank 34)" [VERIFICADO, RM §4].
- El esquemático (hoja 5) identifica el componente: **IC9 = DSC1033CC1-100.0000T** (Micrel, hoy Microchip; oscilador MEMS "PureSilicon" 3,3 V, salida CMOS), red `CLK100MHZ` → pin W5 [VERIFICADO]. **No es un Abracon ASEM** (pista falsa frecuente en foros).
- Pin W5 = `IO_L12P_T1_MRCC_34` (fichero de encapsulado oficial `xc7a35tcpg236pkg.txt`, 10/25/2013) [VERIFICADO].
- Decodificación del código de pedido según el datasheet DSC1033 (Micrel MK-Q-B-P-D-031809-01-7, fecha de código 2009-03-18): `DSC1033 P T S – xxx.xxxx T` → **P=C: encapsulado plástico 3,2×2,5 mm; T=C: 0…+70 °C; S=1: ±50 ppm; 100.0000 MHz; T = tape & reel** [VERIFICADO].
- **Especificación de jitter del fabricante** (tabla "Specifications", datasheet DSC1033) [VERIFICADO]:
  - "Jitter, Cycle to Cycle, JCC, F = 100 MHz: **95 ps**" (único valor tabulado, en la columna Max; la nota 3 remite a la gráfica "typical cycle to cycle jitter" para la dependencia con la frecuencia; en la página 3 hay gráficas "Period Jitter (RMS, ps) vs frequency" con eje 0–40 ps y "Cycle to Cycle Jitter (ps)" con eje 0–200 ps a 25 °C — no se puede leer el valor puntual a 100 MHz del texto extraído).
  - Tolerancia de frecuencia global: ±25/±50 ppm según opción (la placa lleva ±50 ppm).
  - Tr/Tf: 1,3 ns típ. / 2 ns máx. (20–80 %, CL = 15 pF); ciclo de trabajo 45–55 %; VOH ≥ 0,8·VDD, VOL ≤ 0,2·VDD; arranque 1,5 ms típ./3 ms máx.
  - **No se especifica jitter de periodo RMS ni ruido de fase en tabla** — solo la gráfica. Consecuencia para el TFM: la referencia de 100 MHz tiene un jitter ciclo-a-ciclo acotado en ~95 ps (máx.), muy superior al jitter por periodo de un RO de pocos inversores; si el TRNG mide jitter del RO **contra** este reloj, la contribución del XO (y del MMCM si se usa) debe modelarse o medirse por separado (p. ej. midiendo el reloj de placa con un contador/TDC o comparando dos RO entre sí, que cancela el reloj de referencia). Esto es una recomendación [ESTIMADO] derivada del dato verificado.
  - Nota: los osciladores MEMS con PLL fraccional (arquitectura "Frac-N PLL" en el diagrama de bloques del datasheet [VERIFICADO]) presentan espurios/jitter no gaussiano — a tener en cuenta si se hace estadística fina del jitter.
- Datasheet: https://ww1.microchip.com/downloads/en/DeviceDoc/DSC1033%20Datasheet%20MKQBPD0318091-7.pdf [VERIFICADO]

### 1.3 Pmod JA/JB/JC/JXADC

- Todos los Pmod son 2×6, 100 mil, hembra; pines 6 y 12 = VCC 3,3 V, 5 y 11 = GND, 8 señales; "The VCC and Ground pins can deliver up to 1A of current. Pmod data signals are not matched pairs, and they are routed using best-available tracks without impedance control or delay matching" [VERIFICADO, RM §9].
- Protección: en el esquemático (hoja 1) **cada señal de JA, JB y JC lleva una resistencia serie de 200 Ω** (R1–R24) [VERIFICADO]. Las señales de JXADC **no** llevan resistencia serie; van en 4 pares acoplados con condensadores entre pares (C33–C36, hoja 5) y el RM las describe como "wired to the auxiliary analog input pins of the FPGA … routed closely coupled" [VERIFICADO parcialmente: valores de los condensadores no extraíbles del texto].
- IOSTANDARD: el XDC maestro pone `LVCMOS33` en todos los Pmod y, para JXADC, también `LVCMOS33` cuando se usan como digitales [VERIFICADO].
- **Pines con capacidad de reloj (MRCC/SRCC) en los Pmod** (fichero de encapsulado oficial [VERIFICADO] cruzado con el XDC maestro [VERIFICADO]):

| Pmod | Pin FPGA | Nombre de pin | Banco | Capacidad reloj |
|---|---|---|---|---|
| JA1/JA2/JA3/JA4/JA7/JA8/JA9/JA10 | J1/L2/J2/G2/H1/K2/H2/G3 | IO_L3N_T0_DQS_AD5N_35, IO_L5N_T0_AD13N_35, IO_L2N_T0_AD12N_35, IO_L1N_T0_AD4N_35, IO_L3P_T0_DQS_AD5P_35, IO_L5P_T0_AD13P_35, IO_L2P_T0_AD12P_35, IO_L1P_T0_AD4P_35 | 35 | **ninguno** (son pares AD auxiliares del XADC) |
| JB1 (A14), JB7 (A15) | A14, A15 | IO_L6P_T0_16, IO_L6N_T0_VREF_16 | 16 | no |
| JB2 (A16), JB8 (A17) | A16, A17 | IO_L12P_T1_**MRCC**_16, IO_L12N_T1_**MRCC**_16 | 16 | **MRCC** |
| JB3 (B15), JB9 (C15) | B15, C15 | IO_L11N_T1_**SRCC**_16, IO_L11P_T1_**SRCC**_16 | 16 | SRCC |
| JB4 (B16), JB10 (C16) | B16, C16 | IO_L13N_T2_**MRCC**_16, IO_L13P_T2_**MRCC**_16 | 16 | **MRCC** |
| JC1 (K17), JC7 (L17) | K17, L17 | IO_L12N_T1_**MRCC**_14, IO_L12P_T1_**MRCC**_14 | 14 | **MRCC** |
| JC2 (M18), JC8 (M19) | M18, M19 | IO_L11P_T1_**SRCC**_14, IO_L11N_T1_**SRCC**_14 | 14 | SRCC |
| JC3 (N17), JC9 (P17) | N17, P17 | IO_L13P_T2_**MRCC**_14, IO_L13N_T2_**MRCC**_14 | 14 | **MRCC** |
| JC4 (P18), JC10 (R18) | P18, R18 | IO_L14P_T2_**SRCC**_14, IO_L14N_T2_**SRCC**_14 | 14 | SRCC |
| JXADC1..4 (P), 7..10 (N) | J3/L3/M2/N2, K3/M3/M1/N1 | IO_L7P_T1_AD6P_35, IO_L8P_T1_AD14P_35, IO_L9P_T1_DQS_AD7P_35, IO_L10P_T1_AD15P_35 y sus N | 35 | no |

  Implicación práctica: si el SCLK del ESP32 se quisiera usar como reloj real dentro de la FPGA (BUFG/MMCM), debe entrar por JB o JC en un pin MRCC (p. ej. **JB2/A16** o **JC1/K17**). Para un esclavo SPI síncrono muestreado con el reloj de 100 MHz (recomendado a ≤20 MHz de SCLK) no hace falta pin de reloj; JA sirve igual. Nota: la numeración del XDC (`JA[0..7]`) sigue el orden JA1,JA2,JA3,JA4,JA7,JA8,JA9,JA10 [VERIFICADO].

### 1.4 Alimentación

- Entrada: micro-USB J4 (USB-JTAG/UART) o fuente externa 5 V en J6; selección por puente (el RM lo llama "JP3 (near the power switch)" en el texto y "JP2" en la figura 2; el esquemático nombra **JP2** con redes VBUS/VEXT) [VERIFICADO, discrepancia interna del RM]. Interruptor SW16; LED "power good" LD20 alimentado por el PGOOD del LTC3633 [VERIFICADO].
- Fuente externa: "must deliver 4.5VDC to 5.5VDC and at least 1A of current (i.e., at least 5W of power)" [VERIFICADO RM §1].
- Reguladores (esquemático hoja 7 + RM fig. 2): **IC10 = LTC3633EUFD#PBF** (buck doble → **VCC1V0** y **VCC1V8**) e **IC11 = LTC3621EMS8E#PBF** (→ **VCC3V3**) [VERIFICADO]. La figura del RM etiqueta corrientes "1A", "2A" y "300 mA" pero el texto extraído no permite asignarlas inequívocamente a cada rama [VERIFICADO parcialmente].
- Reparto de rieles en la FPGA (hoja 6): VCC1V0 → **VCCINT (G10,H10,J10,L10,M10,N10) y VCCBRAM (M11,N11)** — es decir, **VCCINT y VCCBRAM comparten riel**; VCC1V8 → VCCAUX (J13,H13) a través de una **perla de ferrita "600 Ω/100 MHz"**; VCCO_14/34/35 → 3,3 V [VERIFICADO].
- **¿Punto de medida de corriente de VCCINT?** En el esquemático **no hay resistencia shunt ni puente serie** en VCC1V0. Existen tres componentes de un solo pin **W1, W2, W3** conectados a VCC3V3, VCC1V8 y VCC1V0 respectivamente (hoja 7) [VERIFICADO en la netlist]: por su naturaleza (un pin) son **puntos de prueba/lazos de tensión**, no puntos de corte para un amperímetro. Digilent confirma en su foro que "there is no integrated current measurement on the Basys3" [NO VERIFICADO: cita de buscador del hilo https://forum.digilent.com/topic/25279-basys3-power-consumption-measurement/]. Conclusión: la única medida no invasiva es en la **entrada de 5 V** (USB o J6); medir VCCINT aislado exigiría levantar la bobina de salida del LTC3633 o intercalar un shunt en la pista — fuera del alcance razonable. Sin embargo, W2/W3 permiten **medir la tensión** de los rieles 1,0/1,8 V con un multímetro para el análisis del XADC (comparar lectura interna vs externa).

### 1.5 E/S útiles para depuración (XDC maestro, [VERIFICADO])

Fichero: https://raw.githubusercontent.com/Digilent/digilent-xdc/master/Basys-3-Master.xdc ("general .xdc for the Basys3 rev B board"; todas las líneas van comentadas y se descomentan las usadas).

```tcl
## Reloj 100 MHz
set_property -dict { PACKAGE_PIN W5 IOSTANDARD LVCMOS33 } [get_ports clk]
create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports clk]
## Interruptores sw[15:0]: V17 V16 W16 W17 W15 V15 W14 W13 V2 T3 T2 R3 W2 U1 T1 R2
## LEDs led[15:0]:       U16 E19 U19 V19 W18 U15 U14 V14 V13 V3 W3 U3 P3 N3 P1 L1
## 7 segmentos seg[6:0]: W7 W6 U8 V8 U5 V5 U7 ; dp V7 ; ánodos an[3:0]: U2 U4 V4 W4
## Botones: btnC U18, btnU T18, btnL W19, btnR T17, btnD U17
## Pmod JA[0..7]: J1 L2 J2 G2 H1 K2 H2 G3   (JA1..JA4, JA7..JA10)
## Pmod JB[0..7]: A14 A16 B15 B16 A15 A17 C15 C16
## Pmod JC[0..7]: K17 M18 N17 P18 L17 M19 P17 R18
## JXADC[0..7]:  J3 L3 M2 N2 K3 M3 M1 N1  (XA1_P..XA4_P, XA1_N..XA4_N)
## UART: RsRx B18, RsTx A18
## Opciones de configuración (activas en el fichero):
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE 33 [current_design]
set_property CONFIG_MODE SPIx4 [current_design]
```

Detalles eléctricos (esquemático hoja 1–2, [VERIFICADO]): pulsadores PTA-142 con pull-down de 10 kΩ (activos a nivel alto; el RM: "generate a low output when they are at rest, and a high output only when they are pressed"); interruptores con 10 kΩ; LEDs con 330 Ω en serie; 7 segmentos con 100 Ω por cátodo y transistores por ánodo (2,2 kΩ); "The pushbuttons and slide switches are connected to the FPGA via series resistors to prevent damage from inadvertent short circuits" [VERIFICADO RM §8]. Para el TFM: 16 LEDs como bus de estado del DRBG/AES, 7 segmentos para mostrar bytes/frecuencia del RO, btnC como reset, switches para seleccionar modo de test.

### 1.6 USB-UART y JTAG (FT2232HQ)

- "The Basys 3 includes an FTDI FT2232HQ USB-UART bridge (attached to connector J4) … Serial port data is exchanged with the FPGA using a two-wire serial port (TXD/RXD) … on the **B18 and A18** FPGA pins" [VERIFICADO RM §5]. LEDs LD18 (TX) y LD17 (RX).
- **Simultaneidad**: "The FT2232HQ is also used as the controller for the Digilent USB-JTAG circuitry, but the USB-UART and USB-JTAG functions behave entirely independent of one another. Programmers interested in using the UART functionality of the FT2232 within their design do not need to worry about the JTAG circuitry interfering with the UART data transfers, and vice-versa" [VERIFICADO RM §5]. Es decir, **sí**: se puede tener el Hardware Manager (ILA/programación) y un terminal serie abiertos a la vez por el mismo micro-USB.
- Consecuencia para el banco de pruebas: la FPGA puede volcar bits del TRNG por UART al PC mientras el ESP32 habla por SPI; el ESP32 por su parte usa su propio USB-UART. Dos puertos COM independientes.
- Configuración: JTAG, QSPI flash (S25FL032P, hoja 4) o USB (pendrive) seleccionable con JP1 [VERIFICADO esquemático; RM §2].

---

## 2. Contingencia: Digilent Basys 2 (Spartan-3E XC3S100E, ISE 14.7)

- FPGA: Spartan-3E **XC3S100E**, encapsulado **CP132** [VERIFICADO RM Basys 2 rev. C, DOC# 502-155, "Revised April 8, 2016": https://digilent.com/reference/_media/basys2:basys2_rm.pdf]. Recursos (DS312-1 v3.7, 2008-04-18, Tabla 1: https://docs.amd.com/v/u/en-US/ds312): **2 160 celdas lógicas, 240 CLB, 960 slices (LUT4), 15 Kb RAM distribuida, 72 Kb BRAM (4 bloques de 18 Kb), 4 multiplicadores 18×18, 2 DCM, 108 E/S máx.** [VERIFICADO en espejo del PDF]. Frente al XC7A35T: ~22× menos LUT (y LUT4 en vez de LUT6), 25× menos BRAM, sin DSP48. AES-128 iterativo + SHA-256 + DRBG cabrían apretados; una versión desplegada no.
- Reloj: "User-settable clock (25/50/100 MHz), plus socket for 2nd clock" [VERIFICADO RM]. Oscilador de silicio configurable por puente — jitter típicamente mucho peor que un XO fijo (Digilent no publica cifra) [ESTIMADO].
- E/S: 4 Pmod de **6 pines** (JA–JD, 4 señales cada uno), "ESD and short-circuit protection on all I/O signals"; 8 LEDs, 4 dígitos 7-seg, 4 botones, 8 switches; USB vía **Atmel AT90USB2** con software **Adept** (no JTAG estándar de Xilinx: se programa con Adept o con iMPACT vía cable JTAG externo); consumo de referencia "about 100mA … from the 1.2V supply, 50mA from the 2.5V supply, and 50mA from the 3.3V" [VERIFICADO RM].
- Herramientas: **ISE Design Suite 14.7 (WebPACK)**, última versión (2013); para Windows 10/11 AMD distribuye "ISE 14.7 Windows 10 and Windows 11" como **máquina virtual Oracle VirtualBox con Oracle Linux** preinstalada, paquete ≈ **15,52 GB** [NO VERIFICADO: la página https://www.amd.com/en/support/downloads/adaptive-socs-and-fpgas/development-tools/archive-ise.html no cargó; cifra de terceros]. Sin XADC, sin ILA moderno (ChipScope), sin Tcl non-project comparable: flujo `xst → ngdbuild → map → par → bitgen` por Makefile.
- Equivalentes de atributos para el RO: `KEEP` (UCF/VHDL) mantiene la red; **`SAVE NET FLAG`** (S) en UCF evita que se elimine lógica sin carga; el lazo combinacional se acepta con la opción de PAR/TRCE `-loop` o vía constraint `NET "..." TIG` (timing ignore) en UCF; la LUT inversora se instancia como `LUT1` (INIT => "01") de la librería UNISIM de ISE, y `LOC`/`BEL` funcionan igual (formato `SLICE_XnYm`, `BEL = "F"|"G"`). [ESTIMADO/experiencia; documentación ISE no consultada en esta pasada].
- Impacto en el plan: cambiaría la memoria/área del diseño (probablemente eliminar SHA-256 en hardware o serializarlo), el flujo de scripts (Makefile ISE en VM Linux), la medida interna (no hay XADC ni sensor de temperatura → solo medida externa) y la comunicación (UART por AT90USB2 no es un COM directo: haría falta Pmod USB-UART externo). El esclavo SPI y el RO se portan sin cambios conceptuales.

---

## 3. Vivado ML Standard (gratuito) — versión, instalación, flujo Tcl

### 3.1 Versión vigente y requisitos

- Versión actual: **Vivado 2026.1** (UG973 2026.1 English, "Release Date 2026-06-23") con actualización **2026.1.1** ya publicada en la página de descargas [VERIFICADO: https://www.amd.com/en/support/downloads/adaptive-socs-and-fpgas/development-tools/2026-1.html y https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/Release-Notes].
- **Tamaños de descarga oficiales (2026.1)** [VERIFICADO en la página de descargas]:

| Fichero | Tipo | Tamaño |
|---|---|---|
| AMD Unified Installer for FPGAs & Adaptive SoCs 2026.1: **Windows Self Extracting Web Installer** | EXE | **286,37 MB** |
| Linux Self Extracting Web Installer | BIN | 394,17 MB |
| Unified Installer 2026.1 **SFD** (imagen completa, todos los SO) | TAR/GZIP | **98,28 GB** |
| Unified Installer 2026.1.1 SFD | EXE | 96,36 GB |
| Vivado 2026.1 **Lab Edition** – Windows | TAR/GZIP | 834,72 MB |
| Vivado 2026.1 Lab Edition – SFD (todos los SO) | TAR/GZIP | 3,77 GB |

  El web installer descarga solo lo seleccionado; UG973 muestra como ejemplo de un Vivado ML Enterprise "5.38 GB / 58.43 GB" en curso [VERIFICADO: https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/Web-Installer-Download-and-Install]. UG973 2026.1 advierte: "AMD does not support updates to existing installer via Web Installer" [VERIFICADO].
- **Espacio en disco para "solo Artix-7"**: AMD no publica una tabla por familia en las páginas de UG973 2026.1 accesibles (System Requirements/Memory Recommendations se sirven por JS y no se pudieron leer) [VERIFICADO URL]. Terceros citan ~60 GB para una sola familia [NO VERIFICADO: pcbsync.com]. Estimación propia a partir de instalaciones 2023–2025 con solo 7 series (Artix-7) y sin Vitis: **≈ 30–45 GB instalados, 12–20 GB descargados** [ESTIMADO]. Reservar 60 GB en SSD.
- **Tiempo de instalación**: no hay cifra oficial; terceros "1–2 horas" [NO VERIFICADO]; con web installer y ~100 Mb/s de red, 45–90 min [ESTIMADO].
- **RAM**: la tabla oficial "Memory Recommendations" (https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vivado/memory-recommendations.html) no se pudo leer (JS) [VERIFICADO URL]. Para XC7A35T, 8 GB funcionan y 16 GB son cómodos [ESTIMADO].
- **SO soportados (UG973 2026.1)** [VERIFICADO: https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/Supported-Operating-Systems]: "Microsoft Windows Professional/Enterprise 10.0 22H2 Update", "Microsoft Windows 11.0 23H2, 24H2, and 25H2 Update"; Linux: RHEL 8.10/9.4–9.7/10.0–10.1, SLES 15 SP4/SP6/SP7, Ubuntu 22.04.3–22.04.5 y 24.04–24.04.3, AlmaLinux, Rocky, Amazon Linux 2023. El Windows 11 Home de Mario **no** figura literalmente (solo Pro/Enterprise en el texto de Win10; para Win11 no se especifica edición) — en la práctica funciona [ESTIMADO].
- **Licencia**: UG973 2026.1, tabla "Device Availability by Subscription Tier": "Artix 7 FPGA Devices | All | All | All | All" — Artix-7 completo (incluido XC7A35T) está disponible en **todos** los niveles, incluido el gratuito (histórico "Vivado ML Standard"/WebPACK) [VERIFICADO: https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/Device-Availability-by-Subscription-Tier]. No hace falta fichero de licencia; el instalador pide cuenta AMD. La página de compra de Vivado no se pudo leer (timeout) para confirmar la denominación comercial actual ("Vivado ML Standard" vs nuevos "tiers") [VERIFICADO URL].
- **Instalar solo Artix-7**: en el web installer, en "Devices" desmarcar todo salvo "7 Series → Artix-7" (y opcionalmente Spartan-7); desmarcar Vitis, DocNav, Model Composer, "Install Devices for Alveo/Kria". Paso descrito en UG973 "Installer Download Options"/"Web Installer Download and Install" sin cifras [VERIFICADO URL]. Los ficheros de placa Digilent (board files) se instalan según https://github.com/Digilent/vivado-boards (README: "Installation instructions for the `new` files can be found in Section 3 of the Installing Vivado, Vitis, and Digilent Board Files guide" → https://digilent.com/reference/programmable-logic/guides/installing-vivado-and-vitis) [VERIFICADO README; guía Digilent 403]. Para un flujo non-project con XDC propio **no son necesarios**.

### 3.2 VHDL-2008 en Vivado

- Síntesis (UG901 2026.1, 2026-07-08): sección "VHDL-2008 Language Support"; activación en proyecto `set_property FILE_TYPE {VHDL 2008} [get_files <f>]`, en non-project `read_vhdl -vhdl2008 <f>`. Soporta: operadores relacionales "matching", `maximum/minimum`, desplazamientos, reducción lógica unaria, `if/else generate`, `case generate`, `case?`, `select?`, tipos con elementos no restringidos, `boolean_vector`/`integer_vector`, lectura de puertos `out`, expresiones en port map, `process(all)`, genéricos mejorados. Restricción: no mezclar 93/2008 en la misma compilación de forma inconsistente (los paquetes deben compilarse con el mismo estándar) [VERIFICADO: https://docs.amd.com/r/en-US/ug901-vivado-synthesis/VHDL-2008-Language-Support y .../Setting-up-Vivado-to-use-VHDL-2008].
- Simulación (xsim): `xvhdl -2008`; UG900 2026.1 documenta la librería UNISIM y su ubicación `<Vivado_Install_Dir>/data/vhdl/src/unisims/` con `unisim_VCOMP.vhd` y `unisim_VPKG.vhd`; cláusulas `library UNISIM; use UNISIM.VCOMPONENTS.all;` [VERIFICADO: https://docs.amd.com/r/en-US/ug900-vivado-logic-simulation/UNISIM-Library]. Página "VHDL-2008 Support" de UG900 no localizada por slug [NO VERIFICADO].

### 3.3 Esqueleto de flujo non-project reproducible (Tcl)

Comandos y URL de UG835 (Tcl Command Reference, 2026.1, 2026-06-23). Todas las URL siguientes existen y corresponden al comando [VERIFICADO URL]; la sintaxis mostrada es la estándar de UG835 (contenido detallado no legible por JS salvo donde se indica).

```tcl
# build.tcl — vivado -mode batch -source build.tcl -log build.log -journal build.jou
set part xc7a35tcpg236-1
set top  crypto_top
set out  ./build
file mkdir $out

# 1) Fuentes (VHDL-2008)                 https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/read_vhdl
read_vhdl -vhdl2008 [glob ./rtl/*.vhd]
read_xdc ./constr/basys3.xdc          ;# https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/read_xdc
read_xdc ./constr/ro_pblocks.xdc

# 2) Síntesis                            https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/synth_design
synth_design -top $top -part $part -flatten_hierarchy rebuilt
write_checkpoint -force $out/post_synth.dcp
report_utilization -hierarchical -file $out/util_synth_hier.rpt   ;# https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/report_utilization

# 3) Implementación                      https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/opt_design | place_design | route_design
opt_design
place_design
phys_opt_design                         ;# opcional
route_design
write_checkpoint -force $out/post_route.dcp

# 4) Informes
report_utilization  -hierarchical -hierarchical_depth 3 -file $out/util_hier.rpt
report_timing_summary -delay_type min_max -max_paths 10 -file $out/timing.rpt  ;# https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/report_timing_summary
report_power -file $out/power.rpt      ;# ESTIMACIÓN, ver §5  https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/report_power
report_drc  -file $out/drc.rpt
report_methodology -file $out/method.rpt

# 5) DRC del lazo combinacional (alternativa a ALLOW_COMBINATORIAL_LOOPS, ver §4)
set_property SEVERITY {Warning} [get_drc_checks LUTLP-1]   ;# https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/get_drc_checks

# 6) Bitstream                           https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/write_bitstream
write_bitstream -force -bin_file $out/$top.bit

# 7) Programación por JTAG (FT2232HQ)    https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/program_hw_devices
open_hw_manager
connect_hw_server
open_hw_target
current_hw_device [lindex [get_hw_devices xc7a35t*] 0]
set_property PROGRAM.FILE $out/$top.bit [current_hw_device]
program_hw_devices [current_hw_device]
close_hw_manager
```

Notas: `-flatten_hierarchy rebuilt` conserva nombres jerárquicos para `report_utilization -hierarchical` y para los `get_cells` de los pblocks; UG835 confirma `report_utilization -hierarchical -hierarchical_depth -hierarchical_percentages -file` [VERIFICADO resumen de la página]. Para medir fmax real de un núcleo, sobre-restringir el reloj (`create_clock -period 5.0` para 200 MHz) y leer el WNS: fmax ≈ 1/(T − WNS).

---

## 4. Osciladores de anillo en Vivado — flujo concreto

### 4.1 Instanciación de LUT1 inversora desde VHDL (UNISIM)

UG953 2026.1 (7 Series Libraries Guide): LUT1 "provides a look-up table version of a buffer or inverter"; atributo `INIT` tipo HEX, valores `2'h0`–`2'h3`, por defecto `2'h0`; INIT[0] es la salida para I0=0 e INIT[1] para I0=1 → **inversor = INIT "01"** (O=1 cuando I0=0). Plantilla VHDL oficial [VERIFICADO: https://docs.amd.com/r/en-US/ug953-vivado-7series-libraries/LUT1]:

```vhdl
library IEEE; use IEEE.std_logic_1164.all;
library UNISIM; use UNISIM.vcomponents.all;

entity ring_osc is
  generic (N : positive := 3);            -- impar
  port (en : in std_logic; osc : out std_logic);
end entity;

architecture rtl of ring_osc is
  signal ring : std_logic_vector(N downto 0);
  -- Atributos de síntesis (UG901 2026.1): DONT_TOUCH es la que sobrevive a place/route
  attribute DONT_TOUCH : string;
  attribute DONT_TOUCH of ring : signal is "TRUE";
  attribute KEEP : string;
  attribute KEEP of ring : signal is "TRUE";
  -- ALLOW_COMBINATORIAL_LOOPS también se admite como atributo RTL (mejor en XDC, ver 4.3)
  attribute ALLOW_COMBINATORIAL_LOOPS : string;
  attribute ALLOW_COMBINATORIAL_LOOPS of ring : signal is "TRUE";
begin
  -- Habilitación: NAND de entrada realizada con LUT2 (INIT "0111" = NAND) para arrancar/parar el anillo
  g_nand : LUT2 generic map (INIT => "0111")
           port map (O => ring(0), I0 => en, I1 => ring(N));
  g_inv : for i in 1 to N generate
    attribute DONT_TOUCH of inv : label is "TRUE";
  begin
    inv : LUT1 generic map (INIT => "01")
          port map (O => ring(i), I0 => ring(i-1));
  end generate;
  osc <= ring(N);
end architecture;
```

(La plantilla de UG953 usa `INIT => "00"` como valor por defecto y `LUT1_inst : LUT1 generic map (INIT => "00") port map (O => O, I0 => I0);` [VERIFICADO]; la sintaxis del atributo sobre `label` dentro de un `generate` es VHDL estándar.)

### 4.2 KEEP vs DONT_TOUCH

- UG901 2026.1 (2026-07-08): "KEEP is not forward-annotated to place/route" → para conservar la red en implementación usar **DONT_TOUCH**; DONT_TOUCH "prevents synthesis optimizations from modifying or removing specified design elements"; sintaxis VHDL `attribute DONT_TOUCH : string; attribute DONT_TOUCH of <signal> : signal is "TRUE";` [VERIFICADO: https://docs.amd.com/r/en-US/ug901-vivado-synthesis/DONT_TOUCH y https://docs.amd.com/r/en-US/ug901-vivado-synthesis/KEEP].
- UG903 2026.1: "Set DONT_TOUCH on a leaf cell, hierarchical cell, or net object to preserve it during netlist optimizations"; "A net with DONT_TOUCH cannot be absorbed by synthesis or implementation"; consejo: "Avoid using DONT_TOUCH on hierarchical cells for implementation … Use KEEP_HIERARCHY in synthesis"; "Use reset_property to reset DONT_TOUCH. Setting DONT_TOUCH to 0 does not reset the property" [VERIFICADO: https://docs.amd.com/r/en-US/ug903-vivado-using-constraints/DONT_TOUCH].
- Regla práctica para el RO: DONT_TOUCH en **cada celda LUT1** (label) **y** en las redes del anillo; sin ello `opt_design` colapsa la cadena de inversores en una sola LUT (o la elimina como constante).

### 4.3 Lazo combinacional: DRC LUTLP-1 y ALLOW_COMBINATORIAL_LOOPS

- Mensaje típico de `write_bitstream`/`report_drc` (reconstruido a partir de hilos de soporte de AMD y AWS re:Post; **no** se pudo leer el texto oficial en docs.amd.com) [NO VERIFICADO literal]:
  > `ERROR: [DRC LUTLP-1] Combinatorial Loop Alert: N LUT cells form a combinatorial loop. This can create a race condition. Timing analysis may not be accurate. The preferred resolution is to modify the design to remove combinatorial logic loops. If the loop is known and understood, this DRC can be bypassed by acknowledging the condition and setting the following XDC constraint on any one of the nets in the loop: 'set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets <myHier/myNet>]'. One net in the loop is <net>. Please evaluate your design. The cells in the loop are: <cells>.`
  Fuentes: https://adaptivesupport.amd.com/s/question/0D52E00006txrDLSAY/drc-lutlp1-combinatorial-loop-alert ; https://repost.aws/questions/QUg7tZgBpDSrS-XjbUxIZIHA/
- En síntesis aparece además la advertencia `[Synth 8-295] found timing loop` [VERIFICADO título de hilo: https://adaptivesupport.amd.com/s/question/0D52E00006iHiuFSAS/synth-8295-found-timing-loop].
- Dos formas de pasar el DRC:
  1. **Recomendada** (por red, documenta la intención): en XDC
     ```tcl
     set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets -hierarchical -filter {NAME =~ *ring_osc*/ring*}]
     ```
     Propiedad documentada en UG912 (Properties Reference); la página individual no se localizó por slug (404 en `/ALLOW_COMBINATORIAL_LOOPS`) — índice del documento: https://docs.amd.com/r/en-US/ug912-vivado-properties [VERIFICADO URL índice; página NO VERIFICADA].
  2. **Global** (rebaja la severidad del DRC a warning; permite generar bitstream con cualquier lazo — no recomendada por AMD):
     ```tcl
     set_property SEVERITY {Warning} [get_drc_checks LUTLP-1]
     ```
     UG912 "SEVERITY": "lets you change the severity assigned to individual design rule checks (DRC) … recognized levels: Advisory, Warning, Critical Warning, Error, Fatal" [VERIFICADO resumen: https://docs.amd.com/r/2023.2-English/ug912-vivado-properties/SEVERITY]. En modo proyecto debe ir en un `tcl.pre` del paso write_bitstream; en non-project basta antes de `write_bitstream`.
- **Análisis temporal**: UG906 2026.1 tiene la comprobación de metodología **TIMING-23 "Combinational Loop Found"**: Vivado rompe el lazo desactivando un arco temporal de una celda del lazo; para hacerlo explícito y reproducible:
  ```tcl
  set_disable_timing -from I0 -to O [get_cells -hierarchical -filter {NAME =~ *ring_osc*/g_inv[0].inv}]
  set_false_path -through [get_pins -hierarchical -filter {NAME =~ *ring_osc*/osc_reg/D}]   ;# para el cruce RO→dominio 100 MHz
  ```
  UG835: `set_disable_timing [-from <pin>] [-to <pin>] <cells>`; `set_false_path [-setup] [-hold] [-from] [-to] [-through]` [VERIFICADO URL: https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/set_disable_timing ; .../set_false_path ; UG906 https://docs.amd.com/r/en-US/ug906-vivado-design-analysis/TIMING-23-Combinational-Loop-Found].

### 4.4 Colocación: pblocks, LOC y BEL

- UG835 (2026.1): `create_pblock [-name] <name>`; `add_cells_to_pblock [-add_primitives] [-clear_locs] <pblock> <cells>`; `resize_pblock [-add <ranges>] [-remove <ranges>] [-from <locs>] [-to <locs>] [-locs <policy>] <pblock>` con rangos `SLICE_XnYm:SLICE_XpYq` [VERIFICADO URL/resumen: https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/create_pblock ; .../add_cells_to_pblock ; .../resize_pblock].
- UG912 2026.1 **BEL**: "BEL specifies the placement of a leaf-level Cell within a SLICE/CLB"; "The BEL property or constraint must be defined prior to the LOC property or constraint, or a placement error is returned"; aplica a LUT1–LUT6, FD*, SRL*, LUTRAM; valores p. ej. `A6LUT`, `B6LUT`, `C6LUT`, `D6LUT`, `A5FF`; XDC `set_property BEL A5FF [get_cells placed_reg]` [VERIFICADO: https://docs.amd.com/r/en-US/ug912-vivado-properties/BEL]. `IS_LOC_FIXED`/`IS_BEL_FIXED` (booleanos que fijan la colocación existente) — página no localizada [NO VERIFICADO].
- Ejemplo XDC para dos RO idénticos en slices contiguas (evita que el placer los mezcle y permite comparar):
  ```tcl
  create_pblock pb_ro0
  add_cells_to_pblock pb_ro0 [get_cells -hierarchical -filter {NAME =~ *ro_inst[0]*}]
  resize_pblock pb_ro0 -add {SLICE_X10Y50:SLICE_X11Y51}
  set_property CONTAIN_ROUTING TRUE [get_pblocks pb_ro0]   ;# opcional: encierra también el rutado
  # Colocación exacta LUT a LUT (BEL antes que LOC):
  set_property BEL A6LUT      [get_cells {ro_inst[0].u_ro/g_inv[1].inv}]
  set_property LOC SLICE_X10Y50 [get_cells {ro_inst[0].u_ro/g_inv[1].inv}]
  set_property BEL B6LUT      [get_cells {ro_inst[0].u_ro/g_inv[2].inv}]
  set_property LOC SLICE_X10Y50 [get_cells {ro_inst[0].u_ro/g_inv[2].inv}]
  ```
  Las coordenadas válidas del XC7A35T se consultan en la vista Device de Vivado o con `get_sites -filter {NAME =~ SLICE_X*}`. Fijar también el flip-flop de muestreo con `LOC`/`BEL` (`A5FF`) para que la métrica de frecuencia no dependa del rutado.
- Verificación tras `route_design`: `report_timing -loops` / `get_timing_arcs -filter {IS_DISABLED}`; y `report_utilization -cells [get_cells *ro*]` para confirmar N+1 LUT por anillo.

---

## 5. Medidas dentro del chip y potencia

### 5.1 XADC del Artix-7

- Especificaciones DS181 v1.27.1 (2024-07-03), Tabla 65 "XADC Specifications" (VCCADC = 1,8 V ±5 %, VREFP = 1,25 V, ADCCLK = 26 MHz, valores típicos a Tj = +40 °C) [VERIFICADO]:
  - Resolución **12 bits**; sample rate **1 MS/s**; INL ±2 LSB (−40…100 °C), DNL ±1 LSB, offset unipolar ±8 LSB, ganancia ±0,5 %.
  - **"Temperature Sensor Error: −40 °C ≤ Tj ≤ 100 °C: ±4 °C (Max)"**; ±6 °C fuera de ese rango. (No hay valor "típico" tabulado; el ±4 °C es máximo.)
  - **"Supply Sensor Error: −40 °C ≤ Tj ≤ 100 °C: ±1 % (Max)"**; ±2 % fuera.
  - Nota 5: la exactitud de los sensores internos depende de la referencia (interna o externa 1,25 V); en la Basys 3 no hay VREFP externo → referencia interna.
- Fórmulas de conversión (UG480 v1.9, 2016-09-27, cap. 2 "Sensors"; también en docs.amd.com/r/en-US/ug480_7Series_XADC) [VERIFICADO en PDF]:
  - **Temperatura**: `T(°C) = (ADC_code × 503.975 / 4096) − 273.15` (código de 12 bits = 12 MSB del registro de 16 bits); "1 LSB ≈ 0.123 °C" (Fig. 2-9).
  - **Tensión de alimentación**: fondo de escala 3 V → `V = ADC_code / 4096 × 3 V`; "VCCINT = 1V generates an output code of 1/3 x 4096 = 1365 = 555h". "The XADC monitors VCCINT, VCCAUX, and VCCBRAM. The measurement results are stored in status registers 01h, 02h, and 06h, respectively"; temperatura en 00h [00h NO VERIFICADO en esta pasada; 01h/02h/06h VERIFICADO].
  - LSB de canales analógicos externos: 1 V/4096 = 244 µV (modo unipolar).
- Instanciación (UG953 2026.1, primitiva **XADC**): puertos DRP `DADDR[6:0]`, `DCLK`, `DEN`, `DWE`, `DI[15:0]`, `DO[15:0]`, `DRDY`; analógicos `VP/VN`, `VAUXP/VAUXN[15:0]`; control `CONVST`, `CONVSTCLK`, `RESET`; estado `BUSY`, `EOC`, `EOS`, `CHANNEL[4:0]`, `ALM[7:0]`, `OT`, `JTAGBUSY/LOCKED/MODIFIED`; atributos `INIT_40..INIT_5F` (registros de control/secuencia/alarmas; `INIT_42` por defecto `16'h0800`, resto `16'h0000`); "Instantiation recommended via IP catalog; inference not supported" [VERIFICADO: https://docs.amd.com/r/en-US/ug953-vivado-7series-libraries/XADC]. Alternativa: IP "XADC Wizard" (genera el wrapper con la misma primitiva). Lectura por DRP: poner `DADDR=0x00`, `DEN=1` un ciclo, esperar `DRDY`, leer `DO[15:4]`. Modo secuenciador continuo sobre canales 0 (temp), 1 (VCCINT), 2 (VCCAUX), 6 (VCCBRAM) con `INIT_41 = 0x2xxx`/`INIT_48/49` (máscaras de canal) según UG480 cap. 3 [ESTIMADO detalle de bits; consultar UG480].
- Uso en el TFM: correlacionar frecuencia del RO con temperatura del die y con VCCINT (la Basys 3 no tiene VREF externo ni sensor externo; cotejar con W2/W3 y un termómetro IR si se dispone) — recordar ±4 °C máx. y ±1 % (≈ ±10 mV en 1,0 V).

### 5.2 `report_power` es una ESTIMACIÓN

- UG835: `report_power [-file] [-xpe] …`; los valores son **estimados** a partir de la actividad de conmutación (por defecto vectorless; mejor con SAIF de simulación post-route) [VERIFICADO URL/resumen: https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/report_power]. UG907 2026.1 documenta el "Confidence Level" (Low/Medium/High) como medida de la completitud de los datos de entrada y la sección "Achieving an Accurate Power Analysis Using Vivado Report Power" [VERIFICADO URL: https://docs.amd.com/r/en-US/ug907-vivado-power-analysis-optimization/Achieving-an-Accurate-Power-Analysis-Using-Vivado-Report-Power; cifras de exactitud NO VERIFICADAS]. Para el RO, report_power es especialmente poco fiable: el lazo no tiene reloj definido y la herramienta no conoce su frecuencia real (definir `set_switching_activity -toggle_rate` sobre las redes del anillo con la frecuencia medida mejora la estimación, pero sigue siendo **[ESTIMADO]** y así debe rotularse en la memoria).

### 5.3 Medida real de potencia de la placa (barata)

- **Medidor USB en línea RD UM25C**: exactitud declarada por el fabricante según la revisión de lygte-info.dk: tensión "±0.5% +2 digits", corriente "±1% +4 digits"; resolución 1 mV / 0,1 mA (0,0001 A); "The internal resistance is about 0.065ohm (This includes both connectors)" [VERIFICADO: https://lygte-info.dk/review/USBmeter%20RD%20Tech%20USB%20Meter%20UM25C%20UK.html]. Otras fuentes (manuales comerciales) escriben ±(0,5‰+2 dígitos) y ±(1‰+4 dígitos) — hay **ambigüedad %/‰** entre fuentes [NO VERIFICADO cuál es la oficial]; el manual FCC del UM34/UM34C (hermano de 4 A) declara "Voltage measurement accuracy: ±(0.2%+1digit)" con resolución 0,01 V / 0,001 A [VERIFICADO: https://fccid.io/2A5Y7-UM34C/User-Manual/User-manual-5807006.pdf]. Con la Basys 3 consumiendo del orden de 0,2–0,5 A a 5 V [ESTIMADO], un error de 1 % + 0,4 mA es ≈ 3–5 mA (≈ 15–25 mW): suficiente para deltas de decenas de mW entre diseños si se promedia (el UM25C refresca a ~2 Hz y registra por Bluetooth).
- **Shunt propio**: 0,1 Ω 1 % en el positivo de un cable USB abierto + multímetro en mV (o ADC del ESP32 con amplificador) — más barato, sin registro automático.
- **Qué se puede atribuir y qué no**: la medida en la entrada de 5 V incluye FT2232HQ, PIC24FJ128 (host HID), LEDs, reguladores (eficiencia del LTC3633/3621 ≈ 85–92 % [ESTIMADO]) y la propia FPGA en todos sus rieles. **Solo son atribuibles a la lógica del núcleo las DIFERENCIAS** entre configuraciones (p. ej. bitstream con RO parado vs RO activo, con AES en reposo vs cifrando), medidas en la misma sesión térmica, con LEDs apagados y sin tráfico UART/JTAG; el valor absoluto de VCCINT no es medible sin modificar la placa (§1.4). Reportar siempre `P_total(5 V)` y `ΔP` con incertidumbre, y el `report_power` aparte como [ESTIMADO].

---

## 6. Simulación sin Vivado (Windows 11, hoy)

### 6.1 GHDL

- Última versión: **GHDL v6.0.0 (2026-03-07)**; binarios Windows standalone `ghdl-mcode-6.0.0-mingw64.zip` (22,9 MB) y `ghdl-mcode-6.0.0-ucrt64.zip` (22,6 MB), más paquetes MSYS2 [VERIFICADO: https://github.com/ghdl/ghdl/releases]. Documentación de desarrollo: "7.0.0-dev" [VERIFICADO: https://ghdl.github.io/ghdl/getting.html].
- Backends: **mcode** ("the fastest for analysis … recommended pick if available on your platform (x86/amd64)", compila en memoria; sin soporte de código externo/cobertura), **LLVM** y **GCC** (necesarios para VHPI/cocotb, cosimulación y cobertura) [VERIFICADO getting.html].
- MSYS2 (packages.msys2.org, versión **6.0.0-3**): `mingw-w64-ucrt-x86_64-ghdl-mcode`, `mingw-w64-ucrt-x86_64-ghdl-llvm`, `mingw-w64-x86_64-ghdl-mcode`, `mingw-w64-x86_64-ghdl-llvm` [VERIFICADO: https://packages.msys2.org/base/mingw-w64-ghdl].
- VHDL-2008: `--std=08` (por defecto `93c`); `-fsynopsys` para `std_logic_arith/unsigned`; `--work=<lib>`; comandos `-a` (analizar), `-e` (elaborar), `-r` (ejecutar) [VERIFICADO: https://ghdl.github.io/ghdl/using/InvokingGHDL.html]. Ondas: `--wave=f.ghw` ("any VHDL type can be dumped into a GHW file"), `--vcd=f.vcd`, `--fst=f.fst` ("much smaller than VCD or GHW"), `--stop-time=10ns`; "All the waveform formats supported by GHDL are also supported by GTKWave" [VERIFICADO: https://ghdl.github.io/ghdl/using/Simulation.html].
- **UNISIM**: los fuentes VHDL de UNISIM se distribuyen **solo con Vivado** (`<Vivado>/data/vhdl/src/unisims/`, UG900 [VERIFICADO]). GHDL incluye scripts de precompilación de librerías de fabricante: Linux `compile-xilinx-vivado.sh`, Windows `<GHDL>\libraries\vendors\compile-xilinx-vivado.ps1`, opciones `--all/-All`, `--unisim/-Unisim`, `--vhdl93` (por defecto) / `--vhdl2008/-VHDL2008`, `--source/-Source <ruta Vivado data/vhdl/src>`, `--output/-Output`; las librerías resultantes se usan con `-P<dir>` [VERIFICADO: https://ghdl-rad.readthedocs.io/en/latest/getting/PrecompileVendorPrimitives.html]. Advertencia de la comunidad: no todas las primitivas UNISIM compilan en modo 2008 [NO VERIFICADO: PoC-Library docs].
  - **Sin Vivado instalado**: escribir un modelo funcional propio `LUT1`/`LUT2` (entidad con genérico `INIT : bit_vector(1 downto 0)` y `O <= INIT(to_integer(I0))` con retardo `after 1 ns` opcional) en una librería local llamada `unisim` (`ghdl -a --std=08 --work=unisim lut_models.vhd`) y el paquete `vcomponents` mínimo con las declaraciones de componente; el RTL no cambia y en Vivado se usa la UNISIM real. El RO **no se simula significativamente** en ningún caso (el jitter es físico); en simulación se sustituye por un modelo con periodo aleatorio (`uniform` de `ieee.math_real`).
- Receta mínima Windows 11 (sin Vivado) [VERIFICADO componentes; pasos = síntesis propia]:
  1. Instalar MSYS2 (msys2.org) y en la shell UCRT64: `pacman -S mingw-w64-ucrt-x86_64-ghdl-mcode mingw-w64-ucrt-x86_64-gtkwave` (GTKWave 3.3.127-1 en MSYS2 [VERIFICADO: https://packages.msys2.org/base/mingw-w64-gtkwave]; upstream LTS 3.3.128 [VERIFICADO: https://gtkwave.sourceforge.net/]). Alternativa sin MSYS2: descomprimir `ghdl-mcode-6.0.0-ucrt64.zip` y añadir `bin` al PATH.
  2. `ghdl -a --std=08 --work=unisim sim/unisim_lite/*.vhd` (modelos LUT1/LUT2/XADC-stub propios).
  3. `ghdl -a --std=08 -P. rtl/*.vhd tb/*.vhd && ghdl -e --std=08 -P. tb_crypto_top && ghdl -r --std=08 tb_crypto_top --wave=tb.ghw --stop-time=2ms`
  4. `gtkwave tb.ghw`.
  Con mcode el paso `-e` es instantáneo (no genera ejecutable). Para AES/SHA con vectores de test NIST, leer ficheros con `std.textio` (VHDL-2008 permite `read` de `std_logic_vector` hex vía `hread`).

### 6.2 NVC (alternativa)

- "NVC supports almost all of VHDL-2008 with the exception of PSL"; por defecto `--std=2008`; usa LLVM; **no** sintetiza; instalador Windows en releases e instalación por **`winget install NickGasson.NVC`**; en MSYS2 solo el entorno "Clang x64" está soportado para compilar; `nvc -a d.vhd tb.vhd -e tb -r`; librerías de fabricante: **`nvc --install vivado`** (requiere Vivado instalado; se guardan en `~/.nvc/lib`); GTKWave ≥ 3.3.79 o Surfer para FST [VERIFICADO: README https://github.com/nickg/nvc]. Última versión **1.22.1** ("released on August 1st, 2026" según https://www.nickg.me.uk/nvc/ [VERIFICADO]; el listado de GitHub mostraba la misma versión con otra fecha — comprobar). Ventaja frente a GHDL-mcode: VHPI completo para cocotb y mucho más rápido en diseños grandes; desventaja: sin paquete MSYS2 oficial (https://packages.msys2.org/base/mingw-w64-nvc → 404 [VERIFICADO]).

### 6.3 cocotb (testbench en Python)

- cocotb **2.1**; Python ≥ 3.9; `pip install "cocotb~=2.1"`; en Windows recomienda Miniconda + `conda install -c msys2 m2-base m2-make` o WSL [VERIFICADO: https://docs.cocotb.org/en/stable/install.html]. Simuladores: GHDL ≥ 2.0 (vía VPI, "prevents cocotb from accessing some VHDL-specific constructs, like 9-value signals"; **requiere backend LLVM/GCC**, no mcode), NVC ≥ 1.19.1 (FST por defecto, `--cover`) [VERIFICADO: https://docs.cocotb.org/en/stable/simulator_support.html]. Útil para comparar el AES/SHA de la FPGA con `pycryptodome`/`hashlib` en el mismo test — y reutilizar ese Python después con el ESP32 real.

---

## 7. ESP32 ↔ FPGA en la mesa

### 7.1 Pines SPI del ESP32 (ESP32-D0WD)

- ESP-IDF `spi_master` (ESP32, rama stable): "IO_MUX pins … up to 80 MHz"; "GPIO matrix … only up to 40 MHz" y "increases the input delay of the MISO signal, which makes MISO setup time violations more likely". Pines IO_MUX [VERIFICADO: https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/spi_master.html]:

| Señal | SPI2 (HSPI) | SPI3 (VSPI) |
|---|---|---|
| CS0 | GPIO15 | GPIO5 |
| SCLK | GPIO14 | GPIO18 |
| MISO | GPIO12 | GPIO19 |
| MOSI | GPIO13 | GPIO23 |
| QUADWP | GPIO2 | GPIO22 |
| QUADHD | GPIO4 | GPIO21 |

  Confirmado en el datasheet ESP32 Series v5.3, Tabla 2-1 (MTMS/GPIO14 = HSPICLK, MTDI/GPIO12 = HSPIQ, MTCK/GPIO13 = HSPID, MTDO/GPIO15 = HSPICS0; GPIO18 = VSPICLK, GPIO19 = VSPIQ, GPIO23 = VSPID, GPIO5 = VSPICS0) [VERIFICADO: https://documentation.espressif.com/esp32_datasheet_en.pdf].
- **Recomendación**: usar **VSPI (GPIO18/19/23/5)** — HSPI comparte GPIO12/15 que son **pines de strapping** (GPIO0, GPIO2, GPIO5, GPIO12/MTDI, GPIO15/MTDO) [VERIFICADO: datasheet §3 y guía GPIO de ESP-IDF]; GPIO5 (CS de VSPI) también es strapping pero solo afecta al timing de SDIO en arranque — mantenerlo alto/flotante en el reset o usar otro GPIO como CS por GPIO matrix (CS no es crítico en velocidad).
- Límite de frecuencia con retardo de MISO (spi_master): `Freq limit [MHz] = 80 / (floor(MISO_delay[ns]/12.5) + 1)`; "non-optimal wiring and/or a load capacitor on the bus will most likely lead to input delay values exceeding the values given in the Device specification"; si solo se escribe, `SPI_DEVICE_NO_DUMMY` permite 80 MHz incluso por GPIO matrix; "Full-duplex transactions are not compatible with the dummy bit workaround, hence the frequency is limited" [VERIFICADO]. Parámetro a ajustar: `spi_device_interface_config_t::input_delay_ns` (medir el retardo FPGA+cables y ponerlo aquí).
- Niveles: VDD3P3_CPU 1,8–3,6 V (dominio de GPIO18/19/23/5), VDD3P3_RTC 2,3–3,6 V; drive máximo IOH 40 mA @ VOH ≥ 2,64 V con "output drive strength set to the maximum", IOL 28 mA @ 0,495 V [VERIFICADO datasheet v5.3, Tabla DC]. Drive configurable `gpio_set_drive_capability(GPIO_DRIVE_CAP_0..3)`, por defecto CAP_2 [VERIFICADO: https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/gpio.html]. La FPGA a LVCMOS33 (VCCO = 3,3 V) es compatible directamente; ajustar en XDC `set_property DRIVE 8` y `SLEW SLOW` en MISO de la FPGA para reducir ringing en cables largos [ESTIMADO/buena práctica].

### 7.2 Cables Dupont y velocidad realista

- Sin fuente normativa para Dupont; referencias de terceros: 20 cm de Dupont ya degradan a 8 MHz en protoboard; "I2C and SPI communications should remain under 20cm for reliability above 100kHz"; capacidad parásita ≈ 15–30 pF por cable [NO VERIFICADO: pcbsync.com, electricalflux.com]; un proyecto ESP32→Basys 3 (esclavo SPI en Artix-7 con CDC) reporta transferencia fiable hasta **20 MHz** y corrimiento de bits a 25 MHz [NO VERIFICADO: https://github.com/gou-th/esp32-fpga-spi-interface].
- Recomendación de trabajo [ESTIMADO/experiencia]: cables de **10–15 cm**, un GND **por cada** línea de señal trenzado con ella (mínimo GND junto a SCLK y junto a MOSI), **SCLK = 8–10 MHz** como punto de operación fiable; 20 MHz factible con cables cortos y `input_delay_ns` bien medido; >26 MHz no tiene sentido con Dupont (y en full-duplex el propio driver lo limita). Para la validación del TFM la velocidad SPI es irrelevante frente al throughput del AES (a 10 MHz SPI: 1,25 MB/s ≫ tasa del TRNG).
- Esclavo SPI en la FPGA: muestrear SCLK/MOSI/CS con el reloj de 100 MHz (registros de 2 etapas), detectar flancos; a ≤20 MHz de SCLK hay ≥5 muestras por medio periodo. No usar SCLK como reloj de un dominio salvo por pin MRCC (§1.3). Modo SPI 0 (CPOL=0, CPHA=0) por simplicidad; MISO registrado en el flanco opuesto al de muestreo del maestro.

### 7.3 Masa común, alimentación separada y bucles de masa

- Cada placa alimentada por **su propio USB** (Basys 3 desde el PC vía FT2232; ESP32 desde el PC o un cargador). **Nunca** unir las líneas de 3,3 V/5 V entre placas — solo **GND** (referencia común obligatoria para SPI). Si ambos USB cuelgan del mismo PC, el GND ya está unido por los blindajes USB; el cable GND Dupont adicional crea un pequeño **bucle de masa** — inofensivo a estas frecuencias si los cables son cortos, pero conviene que el GND Dupont sea corto y vaya pegado a las señales para que el retorno de corriente de alta frecuencia no circule por el chasis del PC [ESTIMADO/experiencia; el proyecto citado en 7.2 recomienda igualmente "disconnect the positive power supply between devices, leaving only GND" cuando ambos están conectados al PC — NO VERIFICADO literal].
- Si el ESP32 se alimenta de un cargador de pared aislado y la Basys 3 del PC, no hay bucle; pero un cargador barato inyecta ruido de conmutación en el GND → peor para medir jitter/entropía del RO. Preferible: ambos del mismo PC/hub con alimentación propia.
- Para las medidas de potencia con UM25C (§5.3) intercalar el medidor **solo** en el USB de la Basys 3 y asegurarse de que el ESP32 **no** alimenta nada de la Basys 3 a través del Pmod (los 3,3 V del Pmod, con hasta 1 A, no deben conectarse al ESP32).
- Los pines Pmod tienen 200 Ω en serie (§1.3): limitan la corriente a ~16 mA si el ESP32 y la FPGA condujesen a la vez (error de dirección) — protección útil en el prototipo; añaden con 30 pF de cable una constante RC ≈ 6 ns — otra razón para no pasar de ~20 MHz [ESTIMADO].

---

## 8. Herramientas de análisis y métricas para la memoria

### 8.1 Área

- `report_utilization -hierarchical [-hierarchical_depth N] [-hierarchical_percentages] -file f` (UG835 2026.1) [VERIFICADO URL/resumen] da por módulo: Slice LUTs (lógica / memoria), Slice Registers, F7/F8 Muxes, Slices ocupadas (solo tras place), Block RAM Tiles (36 Kb y 18 Kb), DSPs, BUFG, MMCM/PLL. Reportar **LUT6, FF, slices, BRAM36 (o Kb), DSP** por bloque (RO+acondicionado, SHA-256, DRBG, AES-128, SPI, XADC/control). Ejecutar tras `route_design` (los slices solo son reales tras placement; la síntesis puede empaquetar dos LUT5 en una LUT6 y `opt_design` retocar).
- Para el TRNG añadir el nº de LUT1 y FF fijados por LOC/BEL y la ocupación del pblock.

### 8.2 Frecuencia máxima

- `report_timing_summary` (UG835 2026.1) → **WNS** (Worst Negative Slack), TNS, WHS (hold), y por reloj [VERIFICADO URL/resumen; UG906 "Report Timing Summary": https://docs.amd.com/r/en-US/ug906-vivado-design-analysis/Report-Timing-Summary]. `fmax = 1 / (T_clk − WNS)` solo es válido si WNS ≥ 0 y el diseño está rutado; para "fmax alcanzable" sobre-restringir hasta WNS ≈ 0 (bisección de `create_clock -period`). Indicar siempre el grado -1, la temperatura/proceso del análisis (por defecto esquinas slow/fast) y la versión de Vivado (2026.1).
- Frecuencia del RO: no sale de report_timing (arco desactivado); se mide en hardware con un contador de ciclos del RO por ventana del reloj de 100 MHz (con la incertidumbre del XO §1.2).

### 8.3 Métricas de la literatura para núcleos cripto en FPGA

- **Throughput** `TP = (bits por bloque × f_max) / ciclos por bloque` (para AES-128 iterativo: 128 × f / 10–11; para SHA-256: 512 × f / 64–68).
- **Eficiencia área**: la literatura de LWC/CAESAR sobre Artix-7 usa **throughput-to-area (TPA) en Mbps/LUT**, con el área en LUTs (sin contar BRAM/DSP, o indicándolos aparte) — p. ej. Kaps et al. (NIST LWC Workshop 2019): "Artix-7 FPGA implementations were compared according to maximum frequency, area (look-up tables (LUTs)), TP (Mbps), and throughput-to-area (TPA) ratios"; resultados en xc7a100tcsg324-3 con Vivado 2018.3: GIFT-COFB 415,4 Mbps, 2695 LUT, 0,154 Mbps/LUT; SpoC 152,8 Mbps, 1344 LUT, 0,114 Mbps/LUT [VERIFICADO: https://csrc.nist.gov/CSRC/media/Events/lightweight-cryptography-workshop-2019/documents/papers/hardware-implementations-of-nist-lwc-candidates-lwc2019.pdf]. Otros trabajos usan **Mbps/slice** (throughput per slice, TPS) — p. ej. AES-32GF "3.37 Mbps/slice" en Artix-7 [NO VERIFICADO: PMC10709070].
- Recomendación para la memoria: dar **ambas** (Mbps/LUT y Mbps/slice), fijar la unidad de área declarando si se incluyen BRAM/DSP (convención: "LUT-only, BRAM=0, DSP=0" para que el AES compacto sea comparable), citar dispositivo y grado (xc7a35t-1), versión de herramienta, y separar "post-synthesis" de "post-route". Para el TRNG las métricas son bits/s de salida, bits/s por LUT y min-entropía por bit (esto último lo aporta la parte de teoría).

### 8.4 Estimadores de min-entropía SP 800-90B: herramienta oficial del NIST, sin root, en WSL

- Fuente: `usnistgov/SP800-90B_EntropyAssessment` (C++, licencia NIST; v1.1.8, commit 87c104d de 2026-05-26) [VERIFICADO: https://github.com/usnistgov/SP800-90B_EntropyAssessment]. Da `ea_non_iid` (los diez estimadores de §6.3), `ea_iid` (pruebas de permutación + χ² de §5 y MCV), `ea_restart` (§3.1.4), `ea_conditioning` (§3.1.5) y `ea_transpose`.
- Dependencias del Makefile: bzip2, jsoncpp, OpenSSL, MPFR, GMP y **libdivsufsort** (32 y 64 bits). Sin `sudo` (la WSL de este equipo pide contraseña) se resuelve todo en espacio de usuario:
  1. Toolchain y librerías por micromamba: `micromamba create -p ~/eda90b -c conda-forge "gxx_linux-64>=12" make cmake bzip2 jsoncpp openssl mpfr gmp`. **libdivsufsort no está en conda-forge**: se compila de fuente (`git clone https://github.com/y-256/libdivsufsort`, `cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_DIVSUFSORT64=ON -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=~/eda90b ..`; sin la opción de política CMake ≥ 4 rechaza su `cmake_minimum_required` antiguo).
  2. Compilar la herramienta apuntando al prefijo: `make CXX=~/eda90b/bin/x86_64-conda-linux-gnu-g++ CXXFLAGS="-std=c++11 -fopenmp -O2 -ffloat-store -march=native -I$HOME/eda90b/include" INC="-L$HOME/eda90b/lib -Wl,-rpath,$HOME/eda90b/lib"` en `cpp/` (el Makefile fija `CXXFLAGS` con `=`, así que hay que pasarlo entero; `INC` es el único gancho para `-L`). Binarios en `~/SP800-90B_EntropyAssessment/cpp/ea_*`.
- **Formato de entrada**: un símbolo por byte, con el símbolo en los `bits_per_symbol` bits bajos. Con bytes crudos y `bits_per_symbol = 1` la herramienta aborta ("Data (8) does not fit within described bit width: 1"): para el modo binario hay que desempaquetar antes a bytes 0/1 (MSB primero). Mínimo recomendado 1 000 000 símbolos (avisa por debajo, pero calcula). Con `bits_per_symbol = 8` calcula `H_original` sobre bytes y `H_bitstring` sobre los bits desempaquetados, y devuelve `min(H_original, 8·H_bitstring)`.
- Envoltorio del proyecto: `analysis/entropia_90b.py` (desempaqueta, lanza no-IID e IID en ambos modos por `wsl.exe`, guarda log y JSON íntegros en `results/entropia90b/` y el resumen `results/entropia_90b.csv`). Coste medido en este equipo: 12 s para 125 000 bytes en modo 8 bits (`ea_non_iid`). Interpretación de las cifras (sesgo conservador de Collision/Compression, tope de resolución del MCV por tamaño de muestra) en `docs/esp32_linea_base_90b.md`.

---

## 9. Tabla de referencias y estado de verificación

| # | Referencia | URL | Estado |
|---|---|---|---|
| 1 | Digilent, Basys 3 FPGA Board Reference Manual, rev. C, 2016-04-08, DOC 502-183 | https://digilent.com/reference/_media/basys3:basys3_rm.pdf | [VERIFICADO] PDF completo |
| 2 | Digilent, Basys 3 Schematic C.0, 500-183, 2014-05-21 | https://digilent.com/reference/_media/basys3:basys3_sch.pdf | [VERIFICADO] texto extraído de las 7 hojas |
| 3 | Digilent, Basys-3-Master.xdc (digilent-xdc) | https://raw.githubusercontent.com/Digilent/digilent-xdc/master/Basys-3-Master.xdc | [VERIFICADO] completo |
| 4 | AMD, fichero de encapsulado xc7a35tcpg236pkg.txt (2013-10-25) | https://www.xilinx.com/support/packagefiles/a7packages/xc7a35tcpg236pkg.txt | [VERIFICADO] |
| 5 | AMD DS180 v2.6.1 (2020-09-08), 7 Series Overview | https://docs.amd.com/v/u/en-US/ds180_7Series_Overview | [VERIFICADO] Tablas Artix-7 y 5 |
| 6 | AMD DS181 v1.27.1 (2024-07-03), Artix-7 DC/AC | https://docs.amd.com/v/u/en-US/ds181_Artix_7_Data_Sheet | [VERIFICADO] Tabla 65 XADC |
| 7 | AMD UG480 v1.9 (2016-09-27), XADC User Guide | https://docs.amd.com/r/en-US/ug480_7Series_XADC | [VERIFICADO] fórmulas (PDF espejo); páginas HTML no legibles |
| 8 | AMD UG470 v1.10 (2015-06-24), 7 Series Configuration | https://docs.amd.com/v/u/en-US/ug470_7Series_Config | [VERIFICADO] Tabla 1-1 (PDF espejo) |
| 9 | Micrel/Microchip DSC1033 datasheet MK-Q-B-P-D-031809-01-7 | https://ww1.microchip.com/downloads/en/DeviceDoc/DSC1033%20Datasheet%20MKQBPD0318091-7.pdf | [VERIFICADO] jitter 95 ps, códigos |
| 10 | AMD Downloads 2026.1 | https://www.amd.com/en/support/downloads/adaptive-socs-and-fpgas/development-tools/2026-1.html | [VERIFICADO] tamaños |
| 11 | AMD UG973 2026.1 (2026-06-23): Supported OS; Device Availability by Subscription Tier; Web Installer; Installer Download Options | https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/ | [VERIFICADO] esas 4 páginas; System Requirements / Memory NO legibles |
| 12 | AMD UG835 2026.1 Tcl Command Reference (read_vhdl, synth_design, create_pblock, add_cells_to_pblock, resize_pblock, set_disable_timing, set_false_path, report_utilization, report_timing_summary, report_power, write_bitstream, program_hw_devices, get_drc_checks) | https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/ | [VERIFICADO URL] contenido parcial |
| 13 | AMD UG901 2026.1 (2026-07-08) Synthesis: DONT_TOUCH, KEEP, VHDL-2008 | https://docs.amd.com/r/en-US/ug901-vivado-synthesis/ | [VERIFICADO] |
| 14 | AMD UG903 2026.1 Using Constraints: DONT_TOUCH | https://docs.amd.com/r/en-US/ug903-vivado-using-constraints/DONT_TOUCH | [VERIFICADO] |
| 15 | AMD UG912 Properties: BEL (2026.1); SEVERITY (2023.2); ALLOW_COMBINATORIAL_LOOPS | https://docs.amd.com/r/en-US/ug912-vivado-properties/ | BEL/SEVERITY [VERIFICADO]; ALLOW_COMBINATORIAL_LOOPS [NO VERIFICADO] |
| 16 | AMD UG953 2026.1 Libraries Guide: LUT1, XADC | https://docs.amd.com/r/en-US/ug953-vivado-7series-libraries/ | [VERIFICADO] |
| 17 | AMD UG900 2026.1 Logic Simulation: UNISIM Library | https://docs.amd.com/r/en-US/ug900-vivado-logic-simulation/UNISIM-Library | [VERIFICADO] |
| 18 | AMD UG906 2026.1 Design Analysis: TIMING-23; Report Timing Summary | https://docs.amd.com/r/en-US/ug906-vivado-design-analysis/ | [VERIFICADO URL] |
| 19 | AMD UG907 2026.1 Power Analysis | https://docs.amd.com/r/en-US/ug907-vivado-power-analysis-optimization/ | [VERIFICADO URL] |
| 20 | Hilos de soporte AMD/AWS sobre DRC LUTLP-1 | https://adaptivesupport.amd.com/s/question/0D52E00006txrDLSAY/ ; https://repost.aws/questions/QUg7tZgBpDSrS-XjbUxIZIHA/ | [NO VERIFICADO] texto literal del mensaje |
| 21 | Espressif, ESP-IDF SPI Master Driver (ESP32, stable) | https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/spi_master.html | [VERIFICADO] |
| 22 | Espressif, ESP-IDF GPIO (ESP32, stable) | https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/gpio.html | [VERIFICADO] |
| 23 | Espressif, ESP32 Series Datasheet v5.3 | https://documentation.espressif.com/esp32_datasheet_en.pdf | [VERIFICADO] |
| 24 | GHDL releases v6.0.0; docs Invoking/Simulation/Getting | https://github.com/ghdl/ghdl/releases ; https://ghdl.github.io/ghdl/ | [VERIFICADO] |
| 25 | GHDL vendor scripts (Precompile Vendor Primitives) | https://ghdl-rad.readthedocs.io/en/latest/getting/PrecompileVendorPrimitives.html | [VERIFICADO] |
| 26 | MSYS2 paquetes ghdl 6.0.0-3, gtkwave 3.3.127-1 | https://packages.msys2.org/base/mingw-w64-ghdl ; .../mingw-w64-gtkwave | [VERIFICADO] |
| 27 | NVC README y web (1.22.1) | https://github.com/nickg/nvc ; https://www.nickg.me.uk/nvc/ | [VERIFICADO]; fecha de release ambigua |
| 28 | GTKWave LTS 3.3.128 | https://gtkwave.sourceforge.net/ | [VERIFICADO] |
| 29 | cocotb 2.1 install / simulator support | https://docs.cocotb.org/en/stable/install.html ; .../simulator_support.html | [VERIFICADO] |
| 30 | lygte-info, review UM25C | https://lygte-info.dk/review/USBmeter%20RD%20Tech%20USB%20Meter%20UM25C%20UK.html | [VERIFICADO] |
| 31 | RD UM25/UM34 user manual (FCC ID 2A5Y7-UM34C) | https://fccid.io/2A5Y7-UM34C/User-Manual/User-manual-5807006.pdf | [VERIFICADO] parcial |
| 32 | Kaps et al., "Hardware Implementations of NIST LWC Candidates", NIST LWC Workshop 2019 | https://csrc.nist.gov/CSRC/media/Events/lightweight-cryptography-workshop-2019/documents/papers/hardware-implementations-of-nist-lwc-candidates-lwc2019.pdf | [VERIFICADO] |
| 33 | Digilent Basys 2 Reference Manual rev. C, 2016-04-08, DOC 502-155 | https://digilent.com/reference/_media/basys2:basys2_rm.pdf | [VERIFICADO] |
| 34 | AMD DS312 v3.7 (2008-04-18) Spartan-3E | https://docs.amd.com/v/u/en-US/ds312 | [VERIFICADO] Tabla 1 (PDF espejo) |
| 35 | AMD ISE 14.7 archive (VM Windows 10/11) | https://www.amd.com/en/support/downloads/adaptive-socs-and-fpgas/development-tools/archive-ise.html | [NO VERIFICADO] tamaño 15,52 GB |
| 36 | Digilent forum, "Basys3 Power Consumption Measurement" | https://forum.digilent.com/topic/25279-basys3-power-consumption-measurement/ | [NO VERIFICADO] (403) |
| 37 | Digilent vivado-boards README | https://github.com/Digilent/vivado-boards | [VERIFICADO] |
| 38 | gou-th, esp32-fpga-spi-interface (Basys 3 esclavo SPI) | https://github.com/gou-th/esp32-fpga-spi-interface | [NO VERIFICADO] |
| 39 | AMD Memory Recommendations (Vivado) | https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vivado/memory-recommendations.html | [VERIFICADO URL] contenido no legible |
| 40 | NIST, SP800-90B_EntropyAssessment v1.1.8 (README, Makefile, usos de ea_non_iid/ea_iid) | https://github.com/usnistgov/SP800-90B_EntropyAssessment | [VERIFICADO] compilado y ejecutado en WSL (2026-09-19) |
| 41 | Y. Mori, libdivsufsort 2.0.1 | https://github.com/y-256/libdivsufsort | [VERIFICADO] compilado de fuente |
