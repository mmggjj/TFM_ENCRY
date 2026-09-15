# De FPGA a ASIC: viabilidad de convertir el motor criptográfico en un elemento seguro dedicado

**Documento de apoyo al TFM** — Máster en Microelectrónica, Universidad de Sevilla / IMSE-CNM (CSIC).
**Pregunta que se responde:** el diseño actual (TRNG de osciladores de anillo + SHA-256 + DRBG + AES-128 + SPI) sobre Basys 3 / Artix-7, ¿podría convertirse en un circuito integrado dedicado tipo *elemento seguro* que sirva claves a un ESP32?

**Fecha de consulta de todas las fuentes: 12 de septiembre de 2026.**

**Convenio de marcado usado en todo el documento:**

- `[VERIFICADO]` — se abrió la página/fuente citada y el dato aparece literalmente en ella.
- `[NO VERIFICADO]` — el dato procede de una cita secundaria, de un resultado de buscador sin abrir la fuente primaria, o no se pudo acceder a la página (muro de pago, 403, requiere registro).

> **Advertencia sobre precios.** Los precios de fabricación de silicio están, en la mayoría de las fundiciones, tras registro o petición formal. Donde ha sido así se indica explícitamente. No se ha estimado ni interpolado ningún precio: las cifras que aparecen están copiadas de las tablas públicas citadas.

---

## 1. Seguridad hardware en el IMSE-CNM

### 1.1 Existe un área de investigación formal, no solo trabajos sueltos

El IMSE-CNM organiza su actividad en **Áreas** que agrupan **Líneas**. Una de las ocho áreas se llama literalmente **"Hardware Security"** `[VERIFICADO]` (http://www.imse-cnm.csic.es/es/areas/hardware-sec.php). Dentro de ella hay **dos líneas**:

| Línea | Contenido declarado | Contactos según ficha oficial |
|---|---|---|
| **Cybersecurity** | Criptografía, biometría y cripto-biometría en hardware; ataques de canal lateral (DPA, DEMA) e inyección de fallos; **"Design of modules based on PUFs (within programmable devices and/or integrated circuits) to implement security primitives particularly related to key generation, identifiers, and random numbers"** | Iluminada Baturone Castillo; Carlos J. Jiménez Fernández |
| **Security and Reliability in CMOS and Emerging Technologies** | PUFs robustas explotando variabilidad; criptografía ligera; fiabilidad, variabilidad y envejecimiento; diseño en tecnologías beyond-CMOS | Francisco V. Fernández Fernández |

`[VERIFICADO]` — http://www.imse-cnm.csic.es/es/lineas/tic180-sec.php y http://www.imse-cnm.csic.es/es/lineas/tic026-sre.php

La frase citada de la línea *Cybersecurity* describe, casi palabra por palabra, el objeto del TFM: módulos basados en PUF **en dispositivos programables y/o circuitos integrados** para **generación de claves, identificadores y números aleatorios**. El encaje no es aproximado: es literal.

Existe además un **grupo de investigación** con nombre propio, *"Security and Reliability in CMOS and Emerging Technologies"*, en la lista oficial de grupos del instituto `[VERIFICADO]` (http://www.imse-cnm.csic.es/es/grupos-investigacion.php).

### 1.2 Infraestructura: hay laboratorio de ataques

El IMSE tiene un **Laboratorio de Ciberseguridad del Hardware** `[VERIFICADO]` (http://www.imse-cnm.csic.es/es/laboratorios/ciberseguridad.php), descrito como equipado *"para evaluar la inmunidad frente a diferentes tipos de ataques de canal lateral"* (consumo, tiempo de ejecución, fallos inducidos, emisión electromagnética). Equipamiento listado en la ficha, entre otros: analizador de forma de onda de corriente **Keysight CX3324A**, base motorizada XY **Zaber ASR100B120B-T3A** (para sondeo EM), amplificador de RF **Lambda RLNA00G20GA**, generador arbitrario **Keysight M9336A**, fuente **Keysight E36312A**, sistema de adquisición **Keysight DAQ970A**. Responsable del laboratorio según la ficha: **Antonio Ragel Morales** (Unidad Técnica de Laboratorios e Infraestructuras) `[VERIFICADO]`.

Esto importa para el TFM: la validación de un TRNG no termina en los tests NIST. La parte que distingue un TFM de máster de un ejercicio es la caracterización frente a ataques, y el instituto tiene el banco montado.

### 1.3 El precedente directo: el IMSE ya hizo FPGA → ASIC con un RO-PUF

Este es el hallazgo más relevante de todo el documento. El grupo de **Piedad Brox** y **Macarena C. Martínez-Rodríguez** ha recorrido exactamente el camino que plantea el TFM, y lo ha publicado:

**Etapa FPGA (Xilinx Serie 7, la misma familia que la Artix-7 de la Basys 3):**

- *"True Random Number Generation Capability of a Ring Oscillator PUF for Reconfigurable Devices"*, Electronics 11(23):4028, 2022. DOI `10.3390/electronics11234028`. Del resumen `[VERIFICADO]` (vía Semantic Scholar API): TRNG basado en RO-PUF para FPGA que aprovecha *"the different noise sources that affect the electronic implementation of the RO-PUF to extract the entropy"*, **sin más que cambios mínimos al diseño original de PUF**; validado con **NIST SP 800-22** y como fuente de entropía conforme a **NIST SP 800-90B**; integrado en sistema HW/SW híbrido sobre **Xilinx Zynq-7000**.
- *"Hardware-Efficient Configurable Ring-Oscillator-Based Physical Unclonable Function/True Random Number Generator Module for Secure Key Management"*, Sensors 24(17):5674, 2024. DOI `10.3390/s24175674`. Del resumen `[VERIFICADO]`: módulo **configurable PUF/TRNG** basado en ROs que *"takes full advantage of the structure of modern programmable devices offered by Xilinx 7 Series families"*.
- *"On-Line Evaluation and Monitoring of Security Features of an RO-Based PUF/TRNG for IoT Devices"*, Sensors 23(8):4070, 2023. DOI `10.3390/s23084070` `[VERIFICADO]` (metadatos; resumen no abierto).
- *"Efficient RO-PUF for Generation of Identifiers and Keys in Resource-Constrained Embedded Systems"*, Cryptography 6(4):51, 2022. DOI `10.3390/cryptography6040051` `[VERIFICADO]` (metadatos).

**Etapa ASIC:**

- *"VLSI integration of a RO-based PUF into a 65 nm technology"*, IEEE NorCAS 2024. DOI `10.1109/NorCAS64408.2024.10752474`. Del resumen `[VERIFICADO]`: RO-PUF con **metodología de diseño semi-custom en tecnología TSMC 65 nm**, *"validated through the entire design process, manufactured and experimentally characterized"*, con robustez frente a variaciones de temperatura y tensión. Nótese la frase del propio resumen: *"Its structure makes it suitable for, both, FPGA and ASIC applications."*
- *"Robust and Scalable Cell-Based 65-nm CMOS RO-PUF Implementation"*, **IEEE Open Journal of the Solid-State Circuits Society**, 2026 (Early Access). DOI `10.1109/OJSSCS.2026.3689804`. Autores confirmados vía Crossref `[VERIFICADO]`: P. Ortega-Castro, E. Camacho-Ruiz, J. M. Mora-Gutiérrez, P. Brox, M. C. Martínez-Rodríguez. **El texto completo no se pudo abrir** (IEEE Xplore devolvió 403), por lo que el área, el número de ROs y las métricas concretas quedan `[NO VERIFICADO]`.
- *"VLSI Integration of a Physical Unclonable Function as identifier and key generator"*, demo en el University Fair de **DATE 2025** `[VERIFICADO]` (metadatos de la ficha del IMSE; sin DOI).

La palabra clave del título de 2026 es **"Cell-Based"**: es precisamente el problema del apartado 5 de este documento (rediseñar el oscilador de anillo con celdas estándar en vez de LUTs).

### 1.4 Otras líneas cercanas con ASIC fabricado

El IMSE **ya ha fabricado ASICs criptográficos**, no solo FPGAs:

- *"ASIC design and power characterization of standard and low power multi-radix Trivium"*, IEEE TCAS-II 67(11):2682-2686, 2020. DOI `10.1109/TCSII.2020.2969242` `[VERIFICADO]` (metadatos).
- *"Breaking Trivium Stream Cipher Implemented in ASIC using Experimental Attacks and DFA"*, Sensors 20(23):6909, 2020. DOI `10.3390/s20236909` `[VERIFICADO]` (metadatos).
- *"Design and Evaluation of Countermeasures Against Fault Injection Attacks and Power Side-Channel Leakage Exploration for AES Block Cipher"*, IEEE Access 10:65548-65561, 2022. DOI `10.1109/ACCESS.2022.3183764` `[VERIFICADO]` (metadatos).

En el **catálogo de chips** del IMSE aparecen entradas etiquetadas `cnn_puf`, `criptobio`, `trivium` y la categoría `Criptography` / `Hardware Security` `[VERIFICADO]` (http://www.imse-cnm.csic.es/es/catalogo-chips.php).

### 1.5 Raíz de confianza y calibración de RO: los dos temas exactos del TFM

- *"Cryptographic Security Through a Hardware Root of Trust"*, ARC 2024, DOI `10.1007/978-3-031-55673-9_8` `[VERIFICADO]` (metadatos). Firmado por catorce autores del IMSE (Rojas-Muñoz, Sánchez-Solano, Martínez-Rodríguez, Camacho-Ruiz, Navarro-Torrero, Karmakar, Fernández-García, Tena-Sánchez, Potestad-Ordóñez, Casado-Galán, Ortega-Castro, Acosta-Jiménez, Jiménez-Fernández, Brox). Es, en esencia, el mismo objeto que el TFM: una raíz de confianza hardware.
- *"Auto-Calibrated Ring Oscillator TRNG Based on Jitter Accumulation"*, IEEE ISCAS 2020 (M. A. Prada-Delgado, C. Martínez-Gómez, I. Baturone) `[VERIFICADO]` (metadatos; sin DOI en la ficha).
- *"Calibration of Ring Oscillator PUF and TRNG"*, ECCTD 2020 (C. Martínez-Gómez, I. Baturone) `[VERIFICADO]` (metadatos; sin DOI en la ficha).
- *"A complete SHA-3 hardware library based on a high efficiency Keccak design"*, IEEE NorCAS 2023 `[VERIFICADO]` (metadatos; sin DOI en la ficha).
- *"Root of Trust Components to Increase Security of RISC-V Based Systems on Chips"*, RISC-V Summit Europe 2023 `[VERIFICADO]` (metadatos).

La **auto-calibración del RO-TRNG por acumulación de jitter** (ISCAS 2020) es la respuesta del propio instituto al problema de variabilidad entre ejemplares que se discute en el apartado 5.

### 1.6 Proyectos vivos en los que encajaría el trabajo

De la página de proyectos del IMSE `[VERIFICADO]` (http://www.imse-cnm.csic.es/es/proyectos.php), títulos literales relacionados:

- **TIRELESS** — *"Fiabilidad, seguridad y eficiencia energética en dispositivos y circuitos electrónicos para IoT edge"*
- **GREENCRYPT** — *"Diseño basado en inteligencia artificial de circuitos criptográficos seguros y sostenibles"*
- **CRYPTOHARDWEAR** — *"Soluciones hardware para afrontar los nuevos retos criptográficos de dispositivos wearables"*
- **RTN SECURE** — *"Explotación del RTN para seguridad hardware resistente al envejecimiento"*
- *"Diseño, implementación y validación de raíces de confianza hardware resistentes a ataques para sistemas empotrados seguros"*
- *"Secure Platform for ICT Systems Rooted at the Silicon Manufacturing Process"* (proyecto europeo, con participación en RISC-V Summit)
- **RESEQUA** — *"Design of REsilient SEcurity primitives against QUantum Attacks"*
- *"Primitivas criptográficas seguras en circuitos fotónicos integrados"*

### 1.7 Conclusión del apartado 1

El IMSE no solo tiene línea de seguridad hardware: tiene un **área** con dos líneas, laboratorio de ataques propio, ASICs criptográficos ya fabricados y un grupo que **ha publicado el paso FPGA(Serie 7) → ASIC(65 nm) de un RO-PUF en 2024 y 2026**. El TFM no abre camino: se incorpora a uno ya trazado. Las personas cuyo nombre aparece en las fichas oficiales como contacto de las líneas son las citadas en 1.1; el historial de publicación en RO-PUF/TRNG apunta al grupo de **P. Brox / M. C. Martínez-Rodríguez** como continuación natural del trabajo. *(No se afirma aquí ninguna disponibilidad ni compromiso de estas personas: son datos públicos de la web del instituto.)*

---

## 2. Acceso académico a fabricación (MPW)

### 2.1 Europractice: la vía institucional, y el IMSE ya está dentro

**EUROPRACTICE IC Service** revende bloques de obleas multiproyecto a instituciones académicas europeas. Dos hechos decisivos para este TFM:

**(a) Las cuotas de socio son públicas** `[VERIFICADO]` (https://www.europractice.stfc.ac.uk/membership/membership.html):

| Tipo de membresía | Cuota anual |
|---|---|
| Full-IC | **1.100 €** |
| Software-only | 600 € |
| MPW-only | 600 € |
| FPGA-only | 200 € |

**(b) El IMSE-CNM y la Universidad de Sevilla ya son socios Full-IC.** En la lista pública de miembros activos aparecen literalmente *"Instituto de Microelectrónica de Sevilla (IMSE-CNM) CSIC"* — Full-IC — y *"Universidad de Sevilla"* — Full-IC y FPGA-Only `[VERIFICADO]` (https://www.europractice.stfc.ac.uk/membership/membership_list.cfml). También aparecen *"IMB-CNM Barcelona"* y *"Barcelona Supercomputing Center"*, ambos Full-IC.

Es decir: **no hay que negociar ningún acuerdo marco**. España es país elegible por ser estado miembro de la UE, y las dos instituciones que firman el TFM ya tienen acceso y derecho a precio descontado `[VERIFICADO]`.

Condiciones del precio descontado: institución académica o laboratorio de investigación de financiación pública de los 27 estados de la UE más Albania, Armenia, Azerbaiyán, Bosnia-Herzegovina, Georgia, Islandia, Israel, Liechtenstein, Macedonia del Norte, Moldavia, Montenegro, Noruega, Suiza, Turquía, Serbia, Reino Unido y Ucrania; ser socio con la cuota anual pagada; y que el diseño sea **para fines educativos o investigación financiada públicamente** `[VERIFICADO]`.

### 2.2 Precios MPW y mini@sic 2026 — son públicos

Contra lo que suele suponerse, **Europractice publica los precios en abierto** para casi todas las fundiciones. Tabla extraída de https://europractice-ic.com/schedules-prices-2026/ `[VERIFICADO]`:

| Fundición / tecnología | Modalidad | Precio estándar | Precio descontado | Unidad / mínimo |
|---|---|---|---|---|
| **UMC L180** (180 nm) | mini@sic | 4.110 € | **3.430 €** | bloque de 1525 × 1525 µm (≈ 2,33 mm²) |
| UMC L180 | MPW completo | 16.750 € | 15.920 € | por bloque |
| UMC 40N | MPW completo | 70.500 € | 66.980 € | por bloque |
| **TSMC 65 nm LP** | mini@sic | 4.491 € | **3.691 €** | mínimo 1 mm² |
| TSMC 130 nm BCD+ | mini@sic | 14.054 € | 12.554 € | mínimo 6 mm² |
| TSMC 28 nm HPC+ | mini@sic | 10.609 € | 8.509 € | mínimo 1 mm² |
| **IHP SG13G2** (130 nm BiCMOS) | mini@sic | 6.205 €/mm² | **5.110 €/mm²** | coste mínimo equivalente a 0,8 mm² |
| IHP SG13G2 | MPW completo | 7.300 €/mm² | 6.205 €/mm² | por mm² |
| IHP SG13CMOS | MPW completo | 4.500 €/mm² | 3.825 €/mm² | por mm² |
| IHP Open Source SG13CMOS | MPW | 1.500 € | — | para > 100 mm² |
| **X-FAB XH018** (180 nm) | mini@sic | 5.700 € | **5.300 €** | bloque de 1520 × 1520 µm (≈ 2,31 mm²) |
| X-FAB XH018 4M | MPW completo | 1.126 €/mm² | 1.080 €/mm² | por mm² |
| ams OSRAM 0,18 µm | MPW | 1.650 €/mm² | 1.500 €/mm² | mínimo 5,5 mm² |
| ams OSRAM 0,35 µm | MPW | 640 €/mm² | 580 €/mm² | mínimo 10 mm² |
| GlobalFoundries 22FDX | MPW | 17.820 €/mm² | 16.200 €/mm² | por mm² |
| GlobalFoundries 28SLPe | MPW | 12.430 €/mm² | 11.300 €/mm² | por mm² |
| GlobalFoundries 12LP+ | MPW | 27.500 €/mm² | 25.000 €/mm² | por mm² |

**Excepción importante:** los precios de los **MPW generales de TSMC** (no mini@sic) **no son públicos**: la página exige rellenar un formulario *"Request TSMC Prices"* `[VERIFICADO]`. Lo mismo ocurre con las tarifas estándar de STMicroelectronics, que figuran como *"on request"*. Para esas dos, este documento **no puede dar precio**.

Los precios de IHP coinciden con los publicados directamente por la fundición (SG13G2 a 7.300 €/mm², SG13S 6.300 €/mm², SG13G3 9.000 €/mm²) `[VERIFICADO]` (https://www.ihp-microelectronics.com/services/research-and-prototyping-service/mpw-prototyping-service/schedule-price-list), lo que da confianza cruzada a la tabla.

### 2.3 Qué recibes por ese dinero, y qué no

`[VERIFICADO]` (europractice-ic.com/schedules-prices-2026/):

- **IHP**: *"As default 40 diced samples will be delivered"* (25 para diseños TSV/fotónicos).
- **X-FAB**: *"Delivery of 50 dies is included"*, tanto en MPW como en mini@sic.
- **UMS**: 16 dados en gel-pack.
- **TSMC mini@sic**: *"Subdicing is not supported"*.

**El encapsulado NO está incluido en el precio base.** Se entregan dados sueltos. Los servicios de *bumping* (IHP) tienen *"extra charge"* y el *backgrinding* necesario para encapsular en X-FAB *"is not always possible, and additional cost might apply"* `[VERIFICADO]`. Para un elemento seguro que debe soldarse junto a un ESP32, el encapsulado y la PCB de prueba son coste adicional **no cuantificado en este documento** — no he podido verificar tarifas de encapsulado.

### 2.4 Plazos

Esta es la parte peor documentada públicamente. Lo que sí está verificado:

- **IHP**: el GDSII final debe entregarse **dentro de los 14 días naturales** posteriores al registro del diseño `[VERIFICADO]`.
- **GlobalFoundries**: GDSII final **hasta 6 semanas** tras la fecha de registro `[VERIFICADO]`.
- La tabla de Europractice publica **fechas de cierre de envío de GDSII**, pero **no fechas de entrega de muestras** `[VERIFICADO]`. El plazo tapeout → muestras **no es público en esa página**.
- En el calendario propio de IHP, las fechas de *tapeout* y de *shipment* sugieren del orden de **2-3 meses** `[NO VERIFICADO]` — dedujo del emparejamiento de columnas del calendario, no de una afirmación explícita de plazo.

Como contraste empírico fiable, el calendario público de Tiny Tapeout sobre IHP SG13G2 (apartado 2.6) da **~11-14 meses** desde el cierre de la lanzadera hasta recibir los chips. Para planificación de un TFM, **el plazo realista es de meses a más de un año**, no de semanas.

### 2.5 Efabless ha cerrado — dato crítico y frecuentemente desactualizado

**Efabless cerró operaciones en marzo de 2025.** El aviso publicado decía literalmente: *"Due to funding challenges, Efabless has shut down operations until further notice. We regret any inconvenience and will provide updates as available."* `[VERIFICADO]` (https://semiwiki.com/forum/threads/efabless-just-shut-down.22217/, fecha del cierre situada el **4-5 de marzo de 2025**). La causa fue no cerrar la ronda de financiación Serie B.

**Consecuencia directa: el programa chipIgnite ya no existe.** Cualquier bibliografía o guía que recomiende chipIgnite como vía de tapeout barato está obsoleta. Si el TFM cita esa vía, debe citarla **en pasado**.

Cifras de alcance de chipIgnite antes del cierre (50 instituciones académicas, 80 diseños comerciales) `[NO VERIFICADO]` — aparecen en resúmenes de prensa cuyo original (eenewseurope, Tom's Hardware, Hackster) devolvió 403 al intentar abrirlo.

### 2.6 Tiny Tapeout: sigue vivo, y ahora sobre IHP

Tiny Tapeout **sobrevivió al cierre de Efabless migrando de fundición**. Estado actual `[VERIFICADO]` (https://tinytapeout.com/ y https://tinytapeout.com/faq/):

- Tecnologías ofrecidas ahora: **IHP SG13G2**, **SkyWater SKY130** y **GF180** (lanzaderas TTIHP, TTSky, TTGF).
- **Tamaño de baldosa (tile): 160 × 100 µm, que alberga del orden de 1.000 puertas lógicas digitales.** Se pueden comprar baldosas adicionales.
- Plazo: **6-9 meses de fabricación**, más PCBA, test y envío; **≈ 1 año de espera total**.
- Lanzadera abierta en el momento de la consulta: **IHP26b**.

Calendario concreto de la lanzadera **ttihp26a** `[VERIFICADO]` (https://tinytapeout.com/chips/ttihp26a/): lanzada el **25 de noviembre de 2025**, cierre de envíos el **23 de marzo de 2026**, entrega de chips prevista para **febrero de 2027**; *"Submitted to IHP using sg13g2 130nm open source PDK"*; 181 proyectos en el mapa del chip (una fuente secundaria menciona 283 diseños `[NO VERIFICADO]`).

**Precios de Tiny Tapeout:** la web remite a una calculadora en `app.tinytapeout.com/calculator`, que **no se pudo leer** (aplicación JavaScript; devolvió contenido vacío) `[NO VERIFICADO]`. Las cifras que circulan en prensa técnica para rondas anteriores son **150 $** (tarifa *early bird*, primeras 100 plazas, solo particulares), **300 $** (universidades, empresas y particulares fuera de esa cuota) por 1 baldosa + ASIC + placa de demostración, y **50 $** por baldosa adicional `[NO VERIFICADO]` — proceden de resultados de buscador referidos a la ronda 6 y **no** de la tarifa vigente. **No puedo verificar el precio actual de Tiny Tapeout.** El orden de magnitud documentable es **centenares de dólares**, frente a los **miles de euros** de un mini@sic de Europractice.

> **Cuánto ocupa el motor en baldosas.** Si una baldosa son ~1.000 puertas `[VERIFICADO]`, el motor completo estimado en el apartado 4 **no cabe en una baldosa ni en diez**. Tiny Tapeout sirve para un bloque suelto (por ejemplo, solo el RO-TRNG con su acondicionador), no para el sistema entero.

### 2.7 IHP SG13G2 open source: la vía más barata, con letra pequeña

IHP publica un **PDK de código abierto** para SG13G2 (https://github.com/IHP-GmbH/IHP-Open-PDK). Características verificadas `[VERIFICADO]` (https://www.ihp-microelectronics.com/services/research-and-prototyping-service/fast-design-enablement/open-source-pdk):

- SG13G2 es un proceso **CMOS de 0,13 µm** con HBT SiGe:C (fT hasta 350 GHz), doble óxido de puerta (1,2 V y 3,3 V), cinco metales finos más dos gruesos y condensadores MIM.
- Incluye un *"Limited Base cell set of standard logic cells"* con vistas **CDL, GDSII, LEF y Verilog** — es decir, **suficiente para síntesis lógica y estimación de área**.
- Flujos digitales soportados: **OpenROAD** ya soportado; OpenLane anunciado.
- La propia página califica el PDK de *"early access version"* y *"not yet scheduled for production purpose at this time, but in development"*.

Sobre el **área gratuita en MPW**: IHP declara apoyar diseños para *"non-economic activities, such as university education, research projects"*, y existe un repositorio `IHP-Open-DesignLib` como punto central para fabricación bajo el concepto de *IHP Free MPW runs*. **Sin embargo, la página no publica el proceso de solicitud, los límites de área ni las condiciones**, y lo formula más como objetivo que como oferta cerrada `[VERIFICADO]` (que no hay condiciones publicadas). Una fuente secundaria indica que hay *"un concepto para provisión sostenible de área MPW gratuita o de bajo coste para la comunidad open source desde 2026 en desarrollo"* `[NO VERIFICADO]`. **Conclusión honesta: la vía existe y es real, pero su coste y sus condiciones no están documentados públicamente y hay que preguntar a IHP.**

### 2.8 Qué nodo tiene sentido para este diseño

Para un motor criptográfico digital con un TRNG analógico-sensible, y con presupuesto académico:

- **180 nm (UMC L180 mini@sic, 3.430 € descontado, ≈ 2,33 mm²)** — el punto dulce. Nodo maduro, bien caracterizado, jitter alto (bueno para un RO-TRNG), y un bloque mini@sic de 2,33 mm² es holgado para el motor completo según la estimación del apartado 4. Es la opción más defendible en una memoria.
- **130 nm (IHP SG13G2, 5.110 €/mm² descontado, mínimo equivalente 0,8 mm²)** — atractivo por el PDK abierto y por OpenROAD; permite desarrollar todo el flujo sin licencias comerciales. Un die de 1 mm² costaría del orden de **5.110 €** `[VERIFICADO]` (cálculo directo sobre precio unitario publicado).
- **65 nm (TSMC mini@sic, 3.691 € descontado, mínimo 1 mm²)** — es el nodo que **ya usó el IMSE** para su RO-PUF (NorCAS 2024). Precio comparable al de 180 nm, pero el diseño del RO es más delicado y el PDK no es abierto.
- **28 nm y por debajo** — fuera de discusión para un TFM: 8.509 € el mini@sic más barato, complejidad de flujo muy superior y ninguna ventaja para este circuito.

---

## 3. Contra qué compite: elementos seguros comerciales

### 3.1 El hallazgo que más importa al TFM

Se contaron las menciones literales de "SP 800-90" en los datasheets oficiales de los cuatro candidatos `[VERIFICADO]`:

| Datasheet | Menciones de "800-90" |
|---|---|
| Microchip ATECC608B (DS40002239B) | 3 |
| NXP SE050 (Rev. 3.8) | 5 |
| Infineon OPTIGA Trust M (Rev. 3.70) | **0** |
| ST STSAFE-A110 (DS13039 Rev 1) | **0** |

**Solo dos de los cuatro reclaman conformidad con SP 800-90 en su hoja de datos. Y de esos dos, solo uno tiene un certificado NIST de la fuente de entropía física.**

- **ATECC608B**: certificado **ESV NIST #E46**, *"ECC608 NRBG Entropy Source"*, fuente física de osciladores de anillo, **SP 800-90B**, entropía/muestra = 0,5071, laboratorio AEGISOLVE, validado el 28-09-2023; cubre 608A, 608B y 608C `[VERIFICADO]`. Pero conviene leer la redacción del propio datasheet: *"The random number generator is designed to meet the requirements documented in the NIST 800-90A, 800-90B and 800-90C documents"* — **"is designed to meet"**, es decir, declaración de intención de diseño. Solo la parte **90B (fuente de entropía)** tiene certificado; el **90A (DRBG)** y el **90C** no.
- **SE050**: DRBG con certificado **CAVP #C886**; la fuente de ruido figura en el certificado únicamente como *"NDRNG — Allowed Algorithm"*, sin certificado ESV SP 800-90B propio `[VERIFICADO]`.

> **Consecuencia para la memoria del TFM.** El trabajo puede afirmar con honestidad que **caracterizar una fuente de entropía con modelo estocástico y validación SP 800-90B / AIS 20/31 es algo que dos de los cuatro elementos seguros líderes del mercado ni siquiera declaran hacer**, y que ninguno publica su modelo estocástico. Ese es el hueco real que ocupa el TFM: no compite en coste ni en certificación, compite en **transparencia y trazabilidad de la entropía**.

### 3.2 Comparativa técnica

| | **ATECC608B** | **SE050** | **OPTIGA Trust M V3** | **STSAFE-A110** |
|---|---|---|---|---|
| Reclamo SP 800-90 en datasheet | Sí ("designed to meet" 90A/B/C) | Sí (TRNG 90B, DRBG 90A) | **No** | **No** |
| Certificado real del RNG | **ESV NIST #E46** (90B, físico, RO) | DRBG CAVP #C886; ruido solo "NDRNG Allowed" | ninguno publicado | ninguno publicado |
| AES | **AES-128 solo** + GF multiply para GCM | 128/192/256: CBC, ECB, CTR (+CCM/GCM en SE050E) | 128/192/256: ECB, CBC, CBC-MAC, CMAC | no especificado; envelope AES-128/256 |
| SHA | SHA-256, HMAC | SHA-1/224/256/384/512, HMAC/CMAC/GMAC | SHA-256; HMAC-256/384/512 | SHA-256, SHA-384 |
| ECC | **solo P-256** | P-192…P-521, Brainpool, Ed25519, X25519, X448 | P-256/384/521, Brainpool r1 | P-256/P-384 |
| RSA | no | hasta 4096 | 1024/2048 | no |
| Almacenamiento de claves | 16 slots, 1.208 B de data zone | 50 kB, objetos dinámicos | 10 kB: 4 ECC + 2 RSA + 1 AES + 4 X.509 + 4,5 kB | 6 kB EEPROM; 2 slots privados + 1 efímero |
| Interfaz | I2C 1 Mbps + SWI | I2C 3,4 MHz (HS), dir. 0x48; + ISO7816/14443 | I2C 1 MHz (FM+), dir. 0x30, Shielded Connection | I2C 400 kbps, 7 bits, sin clock stretching |
| **SPI** | **no** | **no** | **no** | **no** |
| Certificación | **JIL High, sin CC/EAL** + ESV #E46 | **CC EAL6+ hasta nivel SO** + FIPS 140-2 L3/L4 (#3840, **HISTORICAL**) | **CC EAL6+ solo HW** (BSI-DSZ-CC-0961) + PSA L3 | **CC EAL5+ AVA_VAN.5** |
| VCC | 2,0 – 5,5 V | 1,62 – 3,6 V | 1,62 – 5,5 V | 1,62 – 5,5 V |
| Corriente activa | 2 mA típ / 14 mA (ECC) | 4,4 mA típ / 14,4 mA (PKC) / 19 mA máx | 14,0 mA típ | 14/18/21 mA |
| Corriente en reposo | **30 nA típ (sleep)** | 3 µA típ (deep power-down) | 70 µA sleep / < 2,5 µA hibernate | 0,2–3 µA hibernate |
| Encapsulados | SOIC-8, UDFN-8 2×3, 3-lead | HX2QFN20 3×3 | PG-USON-10 3×3 | SO8N 4×5, UFDFPN8 2×3 |

Todo `[VERIFICADO]` sobre los datasheets oficiales citados en `refs_asic.bib`, salvo lo indicado en 3.4.

> **Dato que conviene subrayar: ninguno de los cuatro ofrece SPI.** Todos son I2C (el ATECC608B añade una interfaz propietaria de un solo hilo). El motor del TFM, que expone SPI, no es un sustituto *drop-in* de ninguno de ellos: es una arquitectura distinta.

### 3.3 Precios públicos de distribuidor

Consultados el 12-09-2026. Digi-Key en USD; Mouser redirige a `eu.mouser.com`, luego sus precios son **EUR de Mouser Europa**, presumiblemente sin IVA.

| Referencia | Encapsulado | @1 | @1000 | Fuente | Estado |
|---|---|---|---|---|---|
| **ATECC608B-MAHDA-T** | UDFN-8 2×3 | **0,87 $** | no ofrecido (25 = 0,8568 $; 15.000 = 0,70 $) | Digi-Key | `[VERIFICADO]` |
| ATECC608B-MAHDA-T | idem | 0,748 € | **0,736 €** | Mouser EU | `[VERIFICADO]` |
| **ATECC608B-SSHDA-T** | SOIC-8 | **0,90 $** | no ofrecido (25 = 0,8872 $; 4.000 = 0,725 $) | Digi-Key | `[VERIFICADO]` |
| ATECC608B-SSHDA-T | idem | 0,774 € | **0,667 €** | Mouser EU | `[VERIFICADO]` |
| **SE050C2HQ1/Z01SDZ** | HX2QFN-20 | **5,10 $** | no ofrecido (250 = 3,1004 $; 3.000 = 2,8708 $) | Digi-Key | `[VERIFICADO]` |
| SE050C2HQ1/Z01SDZ | idem | 4,27 € | **2,47 €** | Mouser EU | `[VERIFICADO]` |
| **SLS32AIA010MKUSON10XTMB1** | PG-USON-10 | **1,73 €** | **0,903 €** | Mouser EU | `[VERIFICADO]` |
| SLS32AIA010MKUSON10XTMA2 | idem | sin precio @1 | solo carrete 4.000 = 0,75572 $ | Digi-Key (**descatalogado**) | `[VERIFICADO]` |
| **STSAFA110S8SPL02** | SO8N | **2,49 $** | no ofrecido (500 = 1,39352 $; 2.500 = 1,2945 $) | Digi-Key | `[VERIFICADO]` |
| STSAFA110S8SPL03 | SO8N | 2,50 $ (1–9) | *"Contact sales"* > 500 (500 = 1,41 $) | ST eStore | `[VERIFICADO]` |
| STSAFA110DFSPL02 | UFDFPN8 | 2,14 € | no ofrecido (100 = 1,31 €) | Mouser EU | `[VERIFICADO]` |

**Advertencias de método, importantes para no citar mal estas cifras:**

1. **El tramo de 1.000 unidades a menudo no existe.** Digi-Key salta de 250/500 directamente al carrete completo. Donde la tabla dice "no ofrecido" es un hecho de la página, no una omisión.
2. **Las variantes preaprovisionadas del ATECC608B no tienen precio público.** `ATECC608B-TFLXTLSU`, `-TNGTLSU-G` y `-TNGTLSS-G` muestran en Digi-Key *"This product is no longer available at DigiKey"*; buscar `TNGTLS` en Mouser devuelve 0 resultados `[VERIFICADO]`.
3. **Digi-Key no ofrece precio a cantidad 1 para ningún OPTIGA Trust M**: todas sus referencias están descatalogadas o son solo-carrete sin stock `[VERIFICADO]`.

### 3.4 Lo que no se ha podido verificar

- **Protection Profile** de la certificación Common Criteria: **ninguno de los cuatro datasheets lo nombra**. Todos quedan `[NO VERIFICADO]`.
- **Número de certificado CC del STSAFE-A110** (esquema ANSSI/BSI): no localizado; `st.com` dio *timeout* reiterado y el datasheet se obtuvo del espejo oficial de Farnell `[NO VERIFICADO]`.
- **Dirección I2C por defecto del ATECC608B genérico**: el datasheet público es un *resumen*; el completo está bajo NDA. Solo la variante TNGTLS publica la suya (0x35) `[VERIFICADO que no se publica]`.
- La afirmación **JIL High** de Microchip procede de resultados de búsqueda sobre `microchip.com`, que devuelve HTTP 403 a acceso programático `[NO VERIFICADO por apertura directa]`.

### 3.5 Y lo que el ESP32 ya trae puesto

Antes de justificar un chip externo hay que decir qué falta de verdad. Documentación oficial de Espressif `[VERIFICADO]`:

- El **RNG hardware del ESP32** solo entrega aleatoriedad verdadera si el subsistema de RF (Wi-Fi/Bluetooth) está activo o si se ha llamado a `bootloader_random_enable()`. Cita literal: *"If none of the above conditions are true, the output of the RNG should be considered as pseudo-random only."* Y además: *"the internal hardware RNG state is not large enough to provide a continuous stream of true random numbers."*
- El **ESP32-S3** incorpora un periférico **RSA_DS** que produce firmas RSA *"without the RSA private key being accessible by software"*, periférico HMAC, cifrado de flash y arranque seguro.

Es decir: el ESP32 ya tiene almacenamiento de clave protegido y aceleradores. **Lo que no tiene es una fuente de entropía caracterizada y siempre disponible.** Ese es el argumento honesto —y el único sólido— para añadir hardware externo.

---

## 4. Cuánto silicio ocuparía el motor

### 4.1 TRNG en ASIC: implementaciones publicadas

| Referencia | Nodo | Área | Throughput | Energía | Fuente de entropía | Estado |
|---|---|---|---|---|---|---|
| **Yang, Blaauw y Sylvester, JSSC 2016** | **180 nm** | **7.250 µm²** (core) | 0,18 – 1,08 Mb/s | 28,9 – 101,7 pJ/b | **RO de etapas pares, colapso de dos flancos (jitter)** | `[VERIFICADO]` (PDF abierto) |
| Yang, Blaauw y Sylvester, JSSC 2016 | 40 nm | **836 µm²** | 2 Mb/s | 23 pJ/b @0,9 V; 11 pJ/b @0,6 V | idem | `[VERIFICADO]` |
| Cartagena, NORCAS 2016 | **130 nm** | **0,0098 mm²** total (post-proceso 0,0023 mm²) | n.e. | n.e. | RO de 3 flancos + autómata celular | `[VERIFICADO]` |
| Peetermans y Verbauwhede, TCHES 2022 | 28 nm | **750,7 µm²** | 298 Mb/s | **1,46 pJ/bit** @0,8 V | Jitter de flanco en RO, *jitter pipelining* | `[VERIFICADO]` |
| Cao, TCAS-I 2022 | 65 nm | **366 µm²** | 52 Mb/s | 5 pJ/bit | RO *current-starved* en inversión débil | `[VERIFICADO]` |
| Kim, ISSCC 2017 | 65 nm | ≈ 921 µm² (218 kF²) | 8 Mb/s | ≈ 35,7 pJ/bit | RO diferencial con resistencias de realimentación | Área `[VERIFICADO]` en fuente secundaria |
| Coustans, S3S 2017 | **180 nm** flash | n.e. | n.e. | **30 pJ/bit** (subumbral) | Self-Timed Ring + RO de inversores | `[VERIFICADO]` |
| Acar y Ergün, TCAS-II 2020 | **TSMC 180 nm** | 0,7225 mm² (incluye autotest FIPS 140-2) | n.e. | 11,8 mW (estimada) | **TERO** | `[VERIFICADO]` |
| Zhang y Shinohara, JSSC 2022 | 130 nm | core 661 µm²; 5.561 µm² con von Neumann | n.e. | 0,186 pJ/bit @0,3 V | Latch / metaestabilidad | `[VERIFICADO]` |
| Mathew, JSSC 2012 | 45 nm HKMG | 4.004 µm² | 2,4 Gb/s | 2,9 pJ/bit; 7 mW | **Metaestabilidad**, no RO | `[VERIFICADO]` |
| Mathew (µRNG), JSSC 2016 | 14 nm FinFET | 1.008 µm² | 162,5 Mb/s de entropía plena | 3 pJ/bit | 3 fuentes all-digital + extractor | `[VERIFICADO]` |
| Tokunaga, JSSC 2008 | 0,13 µm | 0,145 mm² (chip) | n.e. | n.e. | Metaestabilidad + control de calidad | `[VERIFICADO]` |

**La referencia de anclaje es Yang, Blaauw y Sylvester (JSSC 2016)**: es el único RO-TRNG con cifras completas medidas **en 180 nm**, justo el nodo que recomienda el apartado 2.8. Y trae una lección de calibración de expectativas: el mismo diseño pasa de **836 µm² a 40 nm** a **7.250 µm² a 180 nm** (×8,7), y de 23 pJ/b a 29–102 pJ/b. El TFM debe fijar sus expectativas con la cifra de 180 nm, no con la de nodos avanzados.

Como arquitectura de referencia del sistema completo conviene citar el **DRNG de Intel** (informe de Hamburg, Kocher y Marson, Cryptography Research, 12-03-2012) `[VERIFICADO]`: fuente de entropía a ≈ 3 GHz (un *dual differential jamb latch with feedback*, **no** un oscilador de anillo), acondicionamiento con **AES-CBC-MAC** y **CTR_DRBG con AES-128 según SP 800-90A**. Es exactamente el esqueleto que propone el TFM, lo que respalda la elección arquitectónica.

### 4.2 Área de los núcleos criptográficos en kGE

Definición usada en toda esta literatura: **1 GE = área de una NAND de 2 entradas con la mínima capacidad de carga** de la tecnología. Las cifras en GE solo son comparables entre sí dentro del mismo proceso y librería.

**AES-128:**

| Implementación | Nodo / librería | Área | Throughput | Funcionalidad | Estado |
|---|---|---|---|---|---|
| **Satoh et al., ASIACRYPT 2001 (compacto)** | 0,11 µm CMOS | **5,4 kGE = 0,052 mm²** | 311 Mb/s | **cifrado + descifrado combinados** | `[VERIFICADO]` |
| Satoh et al., ASIACRYPT 2001 (alta velocidad) | 0,11 µm CMOS | **21,3 kGE** | 2,6 Gb/s | idem | `[VERIFICADO]` |
| **Moradi et al., EUROCRYPT 2011** | UMC 180 nm | **2,4 kGE** | serie, muy lento | **solo cifrado** | `[VERIFICADO]` |
| Feldhofer et al., IEE Proc. Inf. Secur. 2005 | 0,35 µm | ≈ **3,4 kGE = 0,25 mm²** | 9,9 Mb/s @80 MHz | cifrado + descifrado + *key setup*, **chip fabricado** | `[VERIFICADO]` |

> **Corrección a un malentendido extendido que conviene no arrastrar a la memoria.** La cifra de 5,4 kGE de Satoh 2001 **no es de 180 nm sino de 0,11 µm**, y corresponde a un *datapath* **combinado de cifrado y descifrado**. La de Feldhofer es a **0,35 µm**. La de Moradi (2,4 kGE, 180 nm) es **solo cifrado** — que es justamente lo que necesita un CTR_DRBG.

**SHA-256:**

| Implementación | Nodo | Área | Throughput | Estado |
|---|---|---|---|---|
| **Satoh e Inoue, ITCC 2005** | **0,13 µm** | **11,5 – 15,3 kGE** | 1,1 – 2,4 Gb/s | `[VERIFICADO]` |
| Feldhofer y Rechberger, IS 2006 (bajo consumo, RFID) | 0,35 µm | **10.868 GE** | 454 kb/s @1 MHz | `[VERIFICADO]` en fuente secundaria |
| Kim, Ryou y Jun, Inscrypt 2008 | 0,25 µm | **8.588 GE** | 1.044 kb/s @1 MHz | `[VERIFICADO]` en fuente secundaria |
| Franck et al., Computers 2024 (**flujo abierto**) | **SKY130 130 nm** | **104.585 µm²** | 97,9 MHz máx | `[VERIFICADO]` |

El rango "10–25 kGE" que se cita habitualmente se confirma, con matices: **8,6 kGE** (ultracompacto, 0,25 µm), **10,9 kGE** (bajo consumo, 0,35 µm), **11,5–15,3 kGE** (0,13 µm orientado a rendimiento).

**DRBG:** no se ha encontrado **ninguna publicación revisada por pares con área en kGE de un CTR_DRBG o HMAC_DRBG hardware autónomo**. No se inventa la cifra. Una estimación constructiva sobre áreas de celda verificadas de la librería UMCL18G212T3 (registros Key y V de 128 b, incrementador de 128 b, contador de *reseed*, FSM y XOR de 256 b) da **≈ 3,2 kGE de envoltorio sobre un AES-128 existente** `[ESTIMADO, no verificado]`.

### 4.3 Conversión kGE → mm²

**180 nm `[VERIFICADO]`:** librería Virtual Silicon **UMCL18G212T3** (UMC L180 0,18 µm 1P6M), celda **HDNAN2D1 (NAND2, drive mínimo) = 9,677 µm²**, según Poschmann, *Lightweight Cryptography*, tesis doctoral, Ruhr-Universität Bochum, 2009, Tabla 2.1 (IACR ePrint 2009/516). Es la misma librería que usan Moradi et al. 2011 y Bogdanov et al. CHES 2008, de modo que sus cifras en GE son directamente convertibles.

> **1 GE = 9,677 µm² a 180 nm ⇒ 1 kGE = 0,009677 mm²**

**130 nm:** no se ha localizado en fuente abierta el área de la NAND2 de una librería comercial de 130 nm. Sí está publicada la de la librería abierta **SKY130** (`sky130_fd_sc_hd`): densidad **bruta de 266 kGates/mm²** y **densidad enrutada de 160 kGates/mm² o mejor** `[VERIFICADO]`, en la documentación oficial del PDK. Eso da **3,76 µm²/GE en bruto** y **6,25 µm²/GE tras enrutado**. Un escalado cuadrático desde los 180 nm verificados daría 5,05 µm²/GE `[ESTIMADO]`. **Recomendación: usar los valores de SKY130, que son medidos y publicados, y declarar el escalado como estimación.**

**Factor de utilización:** el área de celdas no es el área de die. La propia relación de SKY130 entre densidad bruta (266) y enrutada (160 kGates/mm²) marca un factor de **0,60** `[VERIFICADO]` — es el dato duro que responde a la pregunta del apartado 6 sobre cuánto subestima la síntesis lógica.

### 4.4 Presupuesto de área del motor completo

**Configuración A — compacta:**

| Bloque | kGE | Origen |
|---|---|---|
| Fuente de entropía RO + digitalización + post-proceso ligero | 2,0 | Cartagena NORCAS 2016 `[VERIFICADO + derivado]` |
| Health tests SP 800-90B (RCT + APT) + registros | 1,5 | `[ESTIMADO]` |
| AES-128 solo cifrado (*datapath* serie) | 2,4 | Moradi 2011 `[VERIFICADO]` |
| Envoltorio CTR_DRBG | 3,2 | `[ESTIMADO]` |
| SHA-256 compacto | 11,5 | Satoh e Inoue 2005 `[VERIFICADO]` |
| Interfaz SPI *slave* con sincronizadores CDC | 1,5 | `[ESTIMADO]` |
| FIFO, mapa de registros, *glue* | 2,5 | `[ESTIMADO]` |
| **TOTAL A** | **≈ 24,6 kGE** | |

**Configuración B — orientada a rendimiento:** 4 fuentes RO + XOR (6,0), health tests + extractor (3,0), AES-128 *round-based* (21,3 `[VERIFICADO]`), envoltorio CTR_DRBG (3,5), SHA-256 rápido (15,3 `[VERIFICADO]`), SPI (1,5), FIFO/BIST/*glue* (4,0) ⇒ **≈ 54,6 kGE**.

**Área resultante:**

| Configuración | kGE | 180 nm, celdas | 180 nm, core (util. 0,70) | 130 nm, celdas | 130 nm, core (util. 0,70) |
|---|---|---|---|---|---|
| A (compacta) | 24,6 | 0,238 mm² | **0,340 mm²** | 0,123 mm² | **0,176 mm²** |
| B (rendimiento) | 54,6 | 0,528 mm² | **0,755 mm²** | 0,273 mm² | **0,390 mm²** |

### 4.5 La conclusión que cambia el planteamiento: el diseño está limitado por los pads

En 180 nm, un anillo de pads para 28–40 pines fija un die mínimo del orden de **1,5 × 1,5 mm²**. Con 0,34–0,76 mm² de núcleo digital, **el chip no está limitado por la lógica sino por los pads**, en ambas configuraciones y en ambos nodos `[ESTIMADO: el tamaño del anillo de pads es una regla de diseño general, no una cifra tomada de un PDK concreto]`.

Traducido a dinero: un bloque **mini@sic de UMC L180 mide 1525 × 1525 µm = 2,33 mm² y cuesta 3.430 € con descuento académico** (apartado 2.2). **Cabe el motor completo, incluso la configuración B, con margen de sobra** para el TRNG, los condensadores de desacoplo y las estructuras de test. El obstáculo de este proyecto no es el área de silicio ni el precio de la oblea.

### 4.6 Dónde está realmente el área

Configuración A: SHA-256 **47 %**, CTR_DRBG + AES 23 %, TRNG + health tests 14 %, SPI y *glue* 16 %.

**El RO-TRNG es el bloque más barato del sistema (≈ 2–6 kGE). Quien manda en el área es el SHA-256.** Y si el CTR_DRBG proporciona ya el acondicionamiento —como hace el DRNG de Intel, que usa AES-CBC-MAC en lugar de un hash—, **el SHA-256 podría eliminarse por completo**, dejando la configuración A en ≈ 13 kGE (0,18 mm² a 180 nm). Probablemente sea la decisión arquitectónica más rentable de todo el trabajo.


---

## 5. Qué cambia en el TRNG al pasar de FPGA a ASIC

Este es el apartado con el que hay que tener más cuidado, porque es donde más se subestima el trabajo. El RTL del AES o del SHA-256 se lleva de FPGA a ASIC prácticamente sin tocarlo. **El oscilador de anillo no.** Es un circuito analógico disfrazado de digital, y cambia de naturaleza al cambiar de sustrato.

### 5.1 El oscilador hay que rediseñarlo, no re-sintetizarlo

**En FPGA**, el anillo se construye encadenando **LUTs** configuradas como inversores. El retardo por etapa lo domina la LUT y la interconexión programable, ambos fijados por la arquitectura del dispositivo. El diseñador controla la posición con restricciones `LOC`/`BEL`, pero no puede alterar el retardo de la celda: elige entre lo que la FPGA ofrece.

**En ASIC** el anillo se construye con **celdas estándar** (o a medida), y ahí aparece un grado de libertad que en FPGA no existe: el retardo depende de la geometría real. Esto está cuantificado en la literatura:

- **SCALLER** (Aljafar, Ul Abideen, Peetermans, Gierlichs y Pagliarini, arXiv:2406.01258, 2024) `[VERIFICADO]`: osciladores de anillo montados con celdas estándar en **CMOS 65 nm comercial**, explotando deliberadamente los **efectos locales de layout** (*local layout effects*), en concreto el **efecto de proximidad de pozo** (*Well Proximity Effect*): un transistor cerca del borde del pozo tiene tensión umbral y corriente de drenador distintas de otro alejado. Manipulando la geometría del pozo PMOS obtuvieron inversores con velocidades medibles distintas: la variante *extended* resultó **≈ 2 % más rápida** y la *shortened* **≈ 2,86 % más lenta**. Frecuencias de oscilación medidas tras fabricación: **80–900 MHz** según configuración; paso de sintonía ≈ **90 kHz**; margen de sintonía dentro de un mismo chip: **3,7–11 MHz** según variabilidad de proceso.

La lección: **en ASIC, el entorno físico de cada inversor cambia su retardo en el rango del 2–3 %**, lo cual es enorme comparado con el jitter que se quiere aprovechar. Esto es a la vez un problema (dos ejemplares nominalmente idénticos oscilan distinto) y una herramienta (permite sintonía fina que en FPGA no se puede hacer).

Es exactamente el problema que aborda la publicación del IMSE de 2026 cuyo título empieza por **"Robust and Scalable Cell-Based…"** y el de NorCAS 2024, que describe su enfoque como **"a semi-custom design methodology"** `[VERIFICADO]` — ni síntesis automática pura, ni *full-custom*: un punto intermedio en el que el anillo se compone a mano con celdas y se fija su emplazamiento.

**El problema del lazo combinacional.** Un anillo de inversores es un lazo combinacional, y las herramientas de síntesis y de análisis temporal estático lo tratan como un error o lo optimizan hasta eliminarlo (un número par de inversores en cascada se colapsa en un *buffer*, y uno impar en un inversor). En la práctica hay que blindar el anillo con atributos de preservación (`dont_touch` / `keep` / `size_only` según herramienta) y sacarlo del análisis temporal declarando un *false path* o rompiendo el lazo. **No he localizado una fuente académica que cuantifique o documente formalmente este punto**, por lo que queda `[NO VERIFICADO]` como cita: es práctica de ingeniería conocida, y la formulación "semi-custom" de los trabajos del IMSE es la evidencia indirecta de que el camino automático no sirve.

### 5.2 Jitter publicado: lo que no he podido verificar

La pregunta "¿cuánto jitter por periodo se publica en ASIC frente a FPGA?" **no tiene una respuesta que yo pueda dar con una cifra verificada**, y conviene decirlo antes que rellenarlo.

- La referencia canónica sobre caracterización de las fuentes de aleatoriedad en RO sobre FPGA es **Valtchanov, Fischer, Aubert y Bernard, "Characterization of randomness sources in ring oscillator-based true random number generators in FPGAs", DDECS 2010** `[VERIFICADO]` que existe y trata ese tema. Su hallazgo cualitativo, confirmado en el resumen: **la proporción de jitter procedente de fuentes de ruido correlacionadas frente a no correlacionadas depende del número de elementos de retardo (inversores)** del anillo. Esto importa porque **solo el jitter no correlacionado (térmico) cuenta como entropía** a efectos de SP 800-90B y AIS 20/31; el correlacionado (ruido de alimentación, acoplos globales) es manipulable por un atacante.
- **La desviación típica del jitter por periodo en ps, tanto en FPGA como en ASIC, no la he podido verificar**: los textos completos están tras el muro de pago de IEEE. `[NO VERIFICADO]`.
- Este vacío **coincide con el hueco de literatura que el propio plan del TFM ya había identificado** ("no hay cifra publicada de jitter por periodo para Artix-7"). Es coherente: si la cifra fuera pública y fácil, el hueco no existiría. Medirla en el banco es, precisamente, la aportación.

Lo que sí está medido y publicado es el **efecto** del jitter en silicio: el TRNG de Yang, Blaauw y Sylvester (JSSC 2016) entrega **0,18–1,08 Mb/s en 180 nm** y **2 Mb/s en 40 nm** `[VERIFICADO]`, es decir, en el nodo antiguo hay que acumular jitter durante más tiempo para obtener un bit.

### 5.3 Los tres problemas nuevos que aparecen en ASIC

**(a) Variabilidad entre ejemplares y necesidad de calibración por chip.** En FPGA se compra un dispositivo caracterizado por el fabricante y se reprograma hasta que funciona. En ASIC se reciben **40 dados** (IHP) o **50 dados** (X-FAB) `[VERIFICADO]` que salen todos distintos, y no hay segunda oportunidad. SCALLER lo mide: el margen de sintonía varía **3,7–11 MHz entre instancias del mismo chip** `[VERIFICADO]`. La consecuencia de diseño es ineludible: **hay que llevar la calibración dentro del chip**.

Las dos respuestas publicadas a este problema son:
- **Lazo de sintonía automático** — Yang, Blaauw y Sylvester, JSSC 2016: *"A configurable ring and tuning loop provides robustness across a wide range of temperature (−40 °C to 120 °C), voltage (0.6 to 0.9 V), process variation, and external attack"* `[VERIFICADO]`. El lazo ajusta dinámicamente el anillo para mantener un tiempo de colapso suficiente y así maximizar la entropía.
- **Auto-calibración por acumulación de jitter** — el trabajo del propio IMSE: *"Auto-Calibrated Ring Oscillator TRNG Based on Jitter Accumulation"* (Prada-Delgado, Martínez-Gómez y Baturone, ISCAS 2020) y *"Calibration of Ring Oscillator PUF and TRNG"* (ECCTD 2020) `[VERIFICADO]` (metadatos).

**(b) Envejecimiento.** La frecuencia de un RO se degrada con el tiempo por NBTI y HCI, y eso desplaza el punto de operación calibrado en fábrica. No es una preocupación teórica: el IMSE tiene una línea entera dedicada a ello, con el proyecto **RTN SECURE — "Explotación del RTN para seguridad hardware resistente al envejecimiento"** `[VERIFICADO]`, y publicaciones sobre fiabilidad de PUFs bajo degradación por envejecimiento (Saraza-Canflanca et al., *Microelectronics Reliability* 118:114049, 2021 `[VERIFICADO]` metadatos). En FPGA este problema simplemente no se ve en la escala de tiempo de un TFM.

**(c) Ataques de inyección por la alimentación.** Este es el más grave, y está documentado con números demoledores.

**Markettos y Moore, "The Frequency Injection Attack on Ring-Oscillator-Based True Random Number Generators", CHES 2009** `[VERIFICADO]` — resumen extraído literalmente del PDF del autor en la Universidad de Cambridge:

> *"We have devised a frequency injection attack which is able to destroy the source of entropy in ring-oscillator-based true random number generators (TRNGs). A TRNG will lock to frequencies injected into the power supply, eliminating the source of random jitter on which it relies. We are able to reduce the keyspace of a secure microcontroller based on a TRNG from 2^64 to 3300, and successfully attack a 2004 EMV ('Chip and PIN') payment card. We outline a realistic covert attack on the EMV payment system that requires only 13 attempts at guessing a random number that should require 2^32."*

Parámetros experimentales verificados en el mismo PDF:
- Señal inyectada: **onda senoidal de 900 mV pico a pico sobre el raíl de alimentación de 5 V**; barriendo frecuencia se observó **enganche (*injection locking*) a 24 MHz**.
- En la tarjeta EMV se encontraron cuatro frecuencias de enganche en el rango 0–500 MHz; se eligió **f_inject = 24,04 MHz**, la única por debajo de 100 MHz.
- El texto señala que en los anillos se establecen resonancias que **elevan la amplitud por encima de los raíles, de 5 V a 10 V pico a pico**.
- El mecanismo es *injection locking* clásico (condición de Adler), pero acoplado de forma indirecta: *"by co-ordinated biasing of the gates it passes through"*.
- Los autores apuntan además a variantes sin contacto: bucles magnéticos, o usar el propio chip como demodulador de una portadora de GHz modulada en amplitud.

**Y hay contramedida publicada, lo cual es la buena noticia.** El mismo trabajo de Yang, Blaauw y Sylvester (JSSC 2016) probó su TRNG contra este ataque acoplando una senoidal a la alimentación continua `[VERIFICADO]`:

- *"When directly applying such a supply noise injection attack to a single configuration of the TRNG, it fails to pass NIST tests."*
- Pero, como el enganche desplaza la media del contador de colapso fuera del rango especificado, **el lazo de control lo detecta y reconfigura**: *"while operating the control loop, all NIST tests are passed with injection peak-to-peak amplitudes up to 500 mV at the worst case injection frequency of 3×f_RO."*
- Y la advertencia honesta de los propios autores: *"If more sophisticated attacks are used, it is possible that the tuning loop cannot restore normal operation of the TRNG but the attack can still be detected to minimize damage to the secure system."*

> **Traducción para la memoria.** El lazo de calibración no es un lujo de diseño ni un adorno de robustez: es simultáneamente **el mecanismo que compensa la variabilidad de proceso** y **la única defensa publicada contra el ataque de inyección de frecuencia**. Un RO-TRNG en ASIC sin lazo de control y sin health tests en línea es un generador roto esperando a que alguien le acerque un generador de funciones. Esto conecta directamente con el equipamiento del Laboratorio de Ciberseguridad del Hardware del IMSE (apartado 1.2), que tiene exactamente las fuentes y el generador arbitrario necesarios para montar este ensayo.

### 5.4 Lo que no cambia

Conviene decirlo también, porque acota el trabajo: **el AES-128, el SHA-256, el DRBG, los health tests y la interfaz SPI son RTL síncrono ordinario.** Pasan de FPGA a ASIC por el flujo de síntesis estándar sin rediseño conceptual, y sus vectores de prueba (KAT de FIPS 197, CAVP, RFC 4493) siguen valiendo sin cambios. Todo el riesgo técnico del salto está concentrado en la capa 0.

---

## 6. Flujo de diseño digital a ASIC con herramientas de universidad

### 6.1 Herramientas comerciales: disponibles, sin precio público

EUROPRACTICE distribuye a universidades miembro *"a comprehensive range of leading design tools"* que incluye **Cadence y Synopsys**, con la condición explícita de uso *"for academic teaching and non-commercial research purposes only"* `[VERIFICADO]` (https://www.europractice.stfc.ac.uk/). Las notas de versión listadas mencionan paquetes Synopsys 2025-2026 (FEV, ASM, IMP, TCAD, 3D-IC, SLM) y Cadence 2025-2026 (Virtuoso ADE Artist, Spectre FX, Certus Closure Platform, **Joules**, Spectre X GPU).

**El precio de los paquetes de herramientas no es público**: la página no lo publica y no detalla qué contiene cada *bundle* `[VERIFICADO que no se publica]`. Tampoco confirma si Genus o Design Compiler están en un paquete concreto — hay que preguntar a EUROPRACTICE. Lo que sí es seguro es que **la Universidad de Sevilla y el IMSE-CNM son socios Full-IC** (apartado 2.1), luego el acceso a herramientas ya existe institucionalmente.

### 6.2 Librerías de celdas estándar abiertas

Cuatro opciones reales, todas utilizables para estimar área sin firmar un NDA:

| Librería / PDK | Nodo | Licencia y estado | Qué incluye |
|---|---|---|---|
| **SkyWater SKY130** | 130 nm | Abierta (Apache 2.0) | Varias librerías (`sky130_fd_sc_hd`, `hs`, `ls`, `ms`, `hdll`, `hvl`) con densidades publicadas. **Es la mejor documentada de las cuatro** `[VERIFICADO]` |
| **IHP SG13G2** | 130 nm BiCMOS | Abierta, *"early access version"* | *"Limited Base cell set of standard logic cells"* con vistas **CDL, GDSII, LEF y Verilog**; flujo **OpenROAD** soportado `[VERIFICADO]` |
| **GF180MCU** | **180 nm** | Abierta (Apache 2.0), iniciativa Google + GlobalFoundries | Librerías de celdas de **7 y 9 pistas** (`gf180mcu_fd_sc_mcu7t5v0`, `..._mcu9t5v0`) más un juego de celdas de Oklahoma State University `[VERIFICADO]` |
| **Nangate / Silvaco 45 nm Open Cell Library** | 45 nm | Disponible bajo **Apache 2.0 a través de Si2**; Silvaco (que adquirió Nangate) la ofrece junto con una de 15 nm, gratis para universidades y miembros de Si2 | Librería genérica de celdas estándar **para investigación y pruebas de flujos EDA**, no ligada a una fundición real `[VERIFICADO]` |

**Recomendación para este TFM: GF180MCU o SKY130.** GF180MCU porque es **180 nm**, el nodo que recomienda el apartado 2.8 y el que corresponde al mini@sic más barato (UMC L180). SKY130 porque es la mejor documentada y la que trae las cifras de densidad que permiten convertir kGE en mm² sin inventar nada. La Nangate 45 nm sirve para comparar con la literatura de EDA, pero **no corresponde a ninguna fundición accesible**, así que su área no se puede llevar a un presupuesto de fabricación.

### 6.3 Flujo abierto: Yosys, OpenROAD, OpenLane

El flujo abierto (**Yosys** para síntesis, **OpenROAD**/**OpenLane** para implementación física) está soportado sobre SKY130, GF180MCU e IHP SG13G2 `[VERIFICADO]` para este último en la página oficial de IHP.

**Y hay una prueba publicada de que un trabajo de este tamaño se puede hacer así.** Franck, Ginja, Carmo, Afonso y Luppe, *"Custom ASIC Design for SHA-256 Using Open-Source Tools"*, **Computers** 13(1):9, 2024. Del resumen `[VERIFICADO]`:

> Acelerador hardware a medida para SHA-256 *"entirely created using open-source electronic design automation tools"*, sintetizado en **SkyWater SKY130 130 nm mediante el flujo automatizado OpenLANE**. Diseño final **compatible con microcontroladores de 32 bits**, **área total de 104.585 µm²** y **frecuencia máxima de reloj de 97,9 MHz**. Se probaron y analizaron varias configuraciones de optimización durante la fase de síntesis.

Es casi exactamente el capítulo final que cabría en este TFM, pero con un solo bloque en lugar del motor completo. Sirve de plantilla metodológica y de referencia de comparación.

### 6.4 La pregunta clave: ¿basta con síntesis lógica, sin llegar a layout?

**Para el área: sí, con una corrección conocida y cuantificable.**

La documentación oficial del PDK SKY130 publica, para la librería `sky130_fd_sc_hd`, una **densidad bruta de 266 kGates/mm²** y, textualmente, *"Routed Gate Density is 160 kGates/mm^2 or better"* `[VERIFICADO]`. Esa pareja de cifras **es la respuesta cuantitativa a la pregunta**:

> **160 / 266 = 0,60.** El área que devuelve la síntesis lógica (suma de áreas de celda) hay que **dividirla por ~0,6**, o equivalentemente multiplicarla por ~1,66, para estimar el área de núcleo tras *place & route*.

Es un dato publicado por la fundición para su propia librería, no una regla general inventada. Con él, la conversión honesta del apartado 4.3 queda cerrada: se declara el área de celdas, se declara el factor y se declara el área de núcleo estimada, cada una con su etiqueta.

Las tres advertencias que hay que poner en la memoria, todas ellas razones por las que la síntesis **subestima**:

1. **La síntesis no conoce la interconexión real.** Usa modelos de carga de hilo (*wire load models*) estadísticos o ninguno. En nodos con interconexión dominante eso falsea tanto el retardo como la potencia.
2. **Faltan las estructuras que no son lógica**: anillo de pads, condensadores de desacoplo, celdas de relleno, *tap cells*, red de reloj real, estructuras de test. El apartado 4.5 ya mostró que en 180 nm **los pads dominan el tamaño del die**, así que la estimación por síntesis no solo es imprecisa: es que no responde a la pregunta del tamaño del chip.
3. **El oscilador de anillo no se puede estimar por síntesis en absoluto.** Su frecuencia depende del layout concreto (SCALLER: 2–2,86 % de diferencia solo por la geometría del pozo). Para el TRNG hay que ir a simulación eléctrica con parásitos extraídos, no a síntesis.

**Para la potencia: mucho más flojo, y hay que decirlo.** Una estimación de potencia en síntesis sin actividad de conmutación real (fichero SAIF o VCD procedente de simulación con vectores representativos) es poco más que una cota de referencia. Con SAIF mejora bastante en potencia dinámica, pero la potencia de interconexión sigue sin conocerse hasta después del enrutado. **Recomendación honesta: presentar potencia como comparación relativa entre variantes arquitectónicas del mismo diseño, no como cifra absoluta.**

### 6.5 Lo que cabe de verdad en el TFM

Ordenado de lo seguro a lo imposible:

| Alcance | ¿Cabe en el TFM? | Comentario |
|---|---|---|
| RTL completo verificado en Basys 3 con KAT y validación cruzada contra el ESP32 | **Sí — y todavía no está hecho** | El repositorio contiene hoy `ring_osc.vhd` y `ero_core.vhd`. Es el grueso del trabajo |
| Caracterización del jitter y modelo estocástico con SP 800-90B / AIS 20/31 | **Sí, y es la aportación original** | El vacío de literatura del apartado 5.2 lo confirma |
| **Síntesis lógica sobre celdas estándar abiertas (GF180MCU o SKY130) para dar área en kGE y mm², con el factor 0,60 declarado** | **Sí — este es el capítulo final realista** | Sin licencias, sin NDA, sin dinero, reproducible por el tribunal |
| Comparación de área/potencia entre variantes arquitectónicas (con y sin SHA-256, AES serie vs *round-based*) | **Sí, y es lo que da valor al capítulo** | Convierte la estimación en una decisión de diseño argumentada |
| Place & route completo con OpenLane y GDSII con DRC/LVS limpios | **Solo si sobra tiempo** | Duplica el esfuerzo del capítulo y aporta poco al argumento |
| Tapeout real en mini@sic | **No** | No por dinero (3.430 €) ni por área (cabe de sobra), sino por **plazo**: meses o más de un año hasta recibir dados, más encapsulado no presupuestado, más un banco de test que no existe |


---

## 7. Respuesta corta a la pregunta del autor

**¿Podría este diseño convertirse en un circuito integrado dedicado tipo elemento seguro que sirva claves a un ESP32?**

**Técnicamente sí, y con menos obstáculos de los que cabría esperar.** El motor completo ocupa **24,6–54,6 kGE**, es decir **0,18–0,76 mm² de núcleo**, y cabe con holgura en un bloque mini@sic de **1525 × 1525 µm que cuesta 3.430 €** con el descuento académico al que la Universidad de Sevilla y el IMSE-CNM **ya tienen derecho como socios Full-IC de EUROPRACTICE**. El chip estaría limitado por los pads, no por la lógica. Existe además el precedente interno: el IMSE ya llevó un RO-PUF de Xilinx Serie 7 a TSMC 65 nm, lo fabricó y lo caracterizó.

**Pero no cabe en un TFM, y las razones no son las que uno supondría.** No es el dinero (3.430 €) ni el área (sobra). Es la combinación de:

1. **El plazo.** Entre meses y más de un año desde el *tapeout* hasta recibir los dados. El calendario público de Tiny Tapeout sobre IHP es el ejemplo medible: lanzadera cerrada en marzo de 2026, chips en febrero de 2027.
2. **El encapsulado no está incluido** en ningún precio de MPW consultado, y no he podido verificar su coste.
3. **El punto de partida.** El repositorio contiene hoy dos ficheros VHDL. Antes de pensar en silicio hay que terminar y validar el diseño en FPGA.
4. **El rediseño del oscilador**, que es el único bloque que no se traslada con el flujo estándar (apartado 5).

**Lo que sí cabe, y cierra la memoria con honestidad, es el apartado 6.5:** síntesis lógica sobre una librería de celdas estándar abierta (GF180MCU a 180 nm o SKY130 a 130 nm), presentando el área en kGE y en mm² con el factor de utilización de 0,60 declarado explícitamente, y comparando variantes arquitectónicas. Eso convierte "esto podría ser un chip" de una frase de buenos deseos en un capítulo con números, sin licencias, sin NDA, sin dinero y reproducible por el tribunal.

**Y sobre contra qué compite:** no contra el precio. Un ATECC608B cuesta **0,87 $ a una unidad** y trae certificado NIST ESV #E46 de su fuente de entropía. Ningún TFM compite con eso. Compite en lo que esos chips **no** ofrecen: **dos de los cuatro elementos seguros líderes ni siquiera mencionan SP 800-90 en su hoja de datos**, ninguno publica su modelo estocástico, y todos son cajas negras. Un motor con modelo físico de la entropía, cota inferior demostrada y validación cruzada independiente es una aportación **metodológica**, no comercial. Ese es el argumento que se sostiene.

---

## 8. Tabla final de referencias y estado

| # | Fuente | Dato que aporta | Estado |
|---|---|---|---|
| 1 | IMSE-CNM, área "Hardware Security" | Existe área formal con dos líneas | `[VERIFICADO]` |
| 2 | IMSE-CNM, línea *Cybersecurity* | Módulos PUF en FPGA y/o ASIC para claves y números aleatorios; contactos oficiales | `[VERIFICADO]` |
| 3 | IMSE-CNM, línea *Security and Reliability* | PUF, criptografía ligera, variabilidad; contacto oficial | `[VERIFICADO]` |
| 4 | IMSE-CNM, Lab. Ciberseguridad del Hardware | Banco de ataques de canal lateral y su equipamiento | `[VERIFICADO]` |
| 5 | IMSE-CNM, proyectos | TIRELESS, GREENCRYPT, CRYPTOHARDWEAR, RTN SECURE, RESEQUA | `[VERIFICADO]` |
| 6 | Ortega-Castro et al., IEEE OJ-SSCS 2026 | RO-PUF *cell-based* en 65 nm CMOS (metadatos vía Crossref) | Metadatos `[VERIFICADO]`; contenido `[NO VERIFICADO]` (403) |
| 7 | Ortega-Castro et al., NorCAS 2024 | RO-PUF semi-custom en TSMC 65 nm, fabricado y caracterizado | `[VERIFICADO]` (resumen) |
| 8 | Sánchez-Solano et al., Sensors 2024 | Módulo PUF/TRNG configurable sobre Xilinx Serie 7 | `[VERIFICADO]` (resumen) |
| 9 | Rojas-Muñoz et al., Electronics 2022 | RO-PUF como TRNG; NIST SP 800-22 y SP 800-90B sobre Zynq-7000 | `[VERIFICADO]` (resumen) |
| 10 | Prada-Delgado et al., ISCAS 2020 | RO-TRNG auto-calibrado por acumulación de jitter | `[VERIFICADO]` (metadatos) |
| 11 | Mora-Gutiérrez et al., TCAS-II 2020 | El IMSE fabrica ASICs criptográficos (Trivium) | `[VERIFICADO]` (metadatos) |
| 12 | EUROPRACTICE, precios 2026 | Tabla completa de precios MPW y mini@sic | `[VERIFICADO]`; **TSMC MPW general y ST: NO públicos** |
| 13 | EUROPRACTICE, cuotas | Full-IC 1.100 €/año; Software 600 €; MPW 600 €; FPGA 200 € | `[VERIFICADO]` |
| 14 | EUROPRACTICE, lista de miembros | **IMSE-CNM CSIC y Universidad de Sevilla son Full-IC** | `[VERIFICADO]` |
| 15 | EUROPRACTICE, acceso a fundición | Se requieren NDA y DKLA por fundición | `[VERIFICADO]` |
| 16 | EUROPRACTICE, herramientas | Cadence y Synopsys para docencia e investigación no comercial | `[VERIFICADO]`; **precios NO públicos** |
| 17 | IHP, lista de precios | SG13G2 7.300 €/mm²; 40 muestras troqueladas | `[VERIFICADO]` |
| 18 | IHP, PDK abierto | SG13G2 130 nm; celdas con CDL/GDSII/LEF/Verilog; OpenROAD | `[VERIFICADO]`; **condiciones del MPW gratuito NO publicadas** |
| 19 | SemiWiki / aviso de Efabless | **Efabless cerró en marzo de 2025; chipIgnite no existe** | `[VERIFICADO]` |
| 20 | Tiny Tapeout (web y FAQ) | Baldosa 160×100 µm ≈ 1.000 puertas; 6–9 meses de fabricación, ≈1 año total | `[VERIFICADO]`; **precio actual NO verificable** (calculadora JS) |
| 21 | Tiny Tapeout, lanzadera ttihp26a | IHP SG13G2; cierre 23-03-2026, entrega prevista feb-2027 | `[VERIFICADO]` |
| 22 | Microchip, datasheet ATECC608B | *"designed to meet"* SP 800-90A/B/C; AES-128; solo P-256; 16 slots | `[VERIFICADO]` |
| 23 | NIST, certificado ESV #E46 | Fuente de entropía del ECC608 validada SP 800-90B | `[VERIFICADO]` |
| 24 | NXP, datasheet SE050 | TRNG SP 800-90B, DRBG SP 800-90A; CC EAL6+ hasta nivel SO | `[VERIFICADO]` |
| 25 | NIST, certificado CMVP #3840 | FIPS 140-2 del SE050, **estado actual: Historical** | `[VERIFICADO]` |
| 26 | Infineon, datasheet OPTIGA Trust M | **0 menciones de SP 800-90**; CC EAL6+ solo hardware | `[VERIFICADO]` |
| 27 | ST, datasheet STSAFE-A110 | **0 menciones de SP 800-90**; CC EAL5+ AVA_VAN.5 | `[VERIFICADO]`; nº de certificado `[NO VERIFICADO]` |
| 28 | Digi-Key / Mouser | Precios unitarios de los cuatro elementos seguros | `[VERIFICADO]`; **el tramo de 1.000 a menudo no existe** |
| 29 | Espressif, docs ESP-IDF | El RNG del ESP32 es pseudoaleatorio sin RF ni SAR ADC activos | `[VERIFICADO]` |
| 30 | Yang, Blaauw y Sylvester, JSSC 2016 | RO-TRNG en 40 y **180 nm**: 836 / **7.250 µm²**; lazo de sintonía; resistencia a inyección hasta 500 mV | `[VERIFICADO]` (PDF abierto) |
| 31 | Markettos y Moore, CHES 2009 | Ataque de inyección: 2^64 → 3300; EMV en 13 intentos; 900 mV a 24 MHz | `[VERIFICADO]` (PDF abierto) |
| 32 | Aljafar et al., arXiv:2406.01258 (SCALLER) | RO de celdas estándar en 65 nm; efecto de proximidad de pozo; 2–2,86 %; 80–900 MHz | `[VERIFICADO]` |
| 33 | Valtchanov et al., DDECS 2010 | Proporción de jitter correlacionado/no correlacionado según nº de inversores | `[VERIFICADO]` (existencia y hallazgo cualitativo); **cifras en ps `[NO VERIFICADO]`** |
| 34 | Satoh et al., ASIACRYPT 2001 | AES-128 en **5,4 kGE a 0,11 µm** (cifrado + descifrado), 0,052 mm², 311 Mb/s; 21,3 kGE a 2,6 Gb/s | `[VERIFICADO]` |
| 35 | Moradi et al., EUROCRYPT 2011 | AES-128 solo cifrado en **2,4 kGE** (UMC 180 nm) | `[VERIFICADO]` |
| 36 | Feldhofer et al., IEE Proc. 2005 | AES-128 ≈ 3,4 kGE a 0,35 µm, chip fabricado | `[VERIFICADO]` |
| 37 | Satoh e Inoue, ITCC 2005 | SHA-256 en **11,5–15,3 kGE a 0,13 µm**, 1,1–2,4 Gb/s | `[VERIFICADO]` |
| 38 | Poschmann, tesis 2009 (ePrint 2009/516) | **NAND2 = 9,677 µm² en UMC L180** ⇒ conversión kGE→mm² | `[VERIFICADO]` |
| 39 | SkyWater SKY130, docs del PDK | Densidad bruta **266 kGates/mm²**, enrutada **160 kGates/mm²** ⇒ factor **0,60** | `[VERIFICADO]` |
| 40 | Franck et al., Computers 2024 | SHA-256 completo con OpenLANE sobre SKY130: **104.585 µm²**, 97,9 MHz | `[VERIFICADO]` |
| 41 | Hamburg, Kocher y Marson, CRI 2012 | Arquitectura del DRNG de Intel: ES + AES-CBC-MAC + CTR_DRBG(AES-128) | `[VERIFICADO]` |
| 42 | GF180MCU / Nangate-Silvaco / Si2 | Librerías abiertas de 180 nm (7T y 9T) y de 45 nm bajo Apache 2.0 | `[VERIFICADO]` |
| 43 | Cartagena et al., NORCAS 2016 | TRNG completo en **130 nm: 0,0098 mm²** | `[VERIFICADO]` |
| 44 | Peetermans y Verbauwhede, TCHES 2022 | RO-TRNG 28 nm: 750,7 µm², 298 Mb/s, 1,46 pJ/bit, SP 800-90B IID | `[VERIFICADO]` |

### Resumen de lo que NO se ha podido verificar

1. **Precio actual de Tiny Tapeout** — la calculadora es una aplicación JavaScript que no devolvió contenido. Las cifras de 150 $/300 $/50 $ que circulan corresponden a rondas anteriores.
2. **Precios de los MPW generales de TSMC y de STMicroelectronics** — requieren formulario o figuran "on request".
3. **Condiciones del área MPW gratuita de IHP** — la vía existe, pero ni el proceso de solicitud ni los límites están publicados.
4. **Plazo tapeout → muestras en EUROPRACTICE** — la tabla publica cierres de GDSII, no fechas de entrega.
5. **Coste de encapsulado** — no incluido en ningún precio y no verificado.
6. **Jitter por periodo en ps, en FPGA y en ASIC** — textos completos tras muro de pago.
7. **Contenido técnico del artículo del IMSE en IEEE OJ-SSCS 2026** — IEEE Xplore devolvió HTTP 403.
8. **Protection Profile de las certificaciones Common Criteria** — ninguno de los cuatro datasheets lo nombra.
9. **Área en kGE de un CTR_DRBG o HMAC_DRBG publicado** — no existe en la literatura consultada; la cifra de ≈3,2 kGE es estimación constructiva propia.
10. **Precios de los paquetes EDA de EUROPRACTICE** — no publicados.
