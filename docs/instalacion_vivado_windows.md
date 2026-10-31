# Instalar Vivado en Windows 11 y grabar la Basys 3

Receta para el PC de Windows de Mario. El flujo de la placa ya está
escrito (`synth/basys3/build.tcl`, `basys3.xdc`, `ro_pblocks.xdc`); lo que
falta es la herramienta. Versiones, tamaños y fuentes en
`docs/plataforma_y_flujo.md` §3. **Nada de esto se ha ejecutado todavía:**
los pasos salen de la documentación de AMD y Digilent; lo marcado
[NO VERIFICADO] hay que confirmarlo al hacerlo y corregir este documento.

## 0. Por qué Windows y no el Ubuntu

AMD soporta Windows 11 (23H2, 24H2, 25H2) y en Linux solo Ubuntu 22.04 y
24.04 (UG973 2026.1). El PC de Linux lleva Ubuntu 26.04: probablemente
funcionaría, pero sin garantía. Generar el bitstream en Windows es lo
seguro; grabarlo se puede hacer desde cualquiera de los dos (§6).

## 1. Requisitos

- Windows 11, cuenta de administrador para los drivers del cable.
- **60 GB libres en SSD** (instalado, solo Artix-7: 30-45 GB [ESTIMADO]).
- 8 GB de RAM bastan para el XC7A35T; 16 GB, cómodo [ESTIMADO].
- Cuenta de AMD (gratuita): la pide el instalador. **La crea y la usa
  Mario**; las credenciales no van al repositorio.
- Licencia: ninguna. El Artix-7 entero está en el nivel gratuito
  ("Vivado ML Standard").
- Unos 45-90 min de instalación con el instalador web [ESTIMADO].

## 2. Descarga

1. <https://www.amd.com/en/support/downloads/adaptive-socs-and-fpgas/development-tools.html>,
   versión más reciente (2026.1 o su actualización 2026.1.1).
2. Bajar el **"Windows Self Extracting Web Installer"** (EXE, ~290 MB),
   no la imagen completa SFD (~98 GB).
3. Iniciar sesión con la cuenta de AMD cuando lo pida.

## 3. Instalación

Ejecutar el EXE y, en el asistente:

1. Producto: **Vivado** (no Vitis).
2. Edición: **Vivado ML Standard** (la gratuita; si el nombre ha cambiado,
   la que no pide licencia).
3. Componentes, desmarcar todo lo que no sea:
   - *Devices → 7 Series → **Artix-7*** (Spartan-7 opcional, no hace falta).
   - Dejar marcado **"Install Cable Drivers"** (son los del USB-JTAG de la
     Basys 3) [NO VERIFICADO: nombre exacto de la casilla en 2026.1].
   - Fuera: Vitis, DocNav, Model Composer, dispositivos Alveo/Kria/Versal,
     Zynq y UltraScale.
4. Ruta: **sin espacios ni tildes**; aceptar la que proponga
   (`C:\AMDDesignTools\2026.1` en las versiones recientes, `C:\Xilinx` en
   las antiguas) [NO VERIFICADO: ruta por defecto en 2026.1]. Abajo se
   llama `<VIVADO>` a `...\2026.1\Vivado`.
5. Aceptar el aviso de Windows para instalar los drivers.

Comprobación, en PowerShell:

```powershell
& "<VIVADO>\bin\vivado.bat" -version
```

Para no escribir la ruta entera en cada sesión de PowerShell:

```powershell
$env:Path += ";<VIVADO>\bin"
vivado -version
```

(o añadir `<VIVADO>\bin` al PATH de usuario en "Variables de entorno").

Si los drivers no se instalaron en el paso 3, como administrador
[NO VERIFICADO: ruta en 2026.1]:

```powershell
cd "<VIVADO>\data\xicom\cable_drivers\nt64"
.\install_drivers_wrapper.bat
```

## 4. Conectar la placa

1. Cable micro-USB al conector **PROG/UART** de la Basys 3 (alimenta la
   placa y lleva el JTAG por el FT2232 de la placa; no hace falta otro cable).
2. Jumper **JP1** (modo de arranque): para grabar por JTAG vale cualquier
   posición; para que arranque sola desde la flash, en **QSPI**.
3. Interruptor **POWER** a ON (LED de alimentación encendido).
4. En el Administrador de dispositivos deben aparecer dos interfaces del
   FT2232 ("USB Serial Converter A/B") y un puerto COM (la UART).
5. Comprobar que Vivado la ve:

```powershell
vivado -mode tcl
```
```tcl
open_hw_manager
connect_hw_server
get_hw_targets            ;# debe listar uno, .../Digilent/...
open_hw_target
get_hw_devices            ;# xc7a35t_0
close_hw_manager
exit
```

## 5. Generar el bitstream y grabar

Clonar el repositorio en una ruta corta y sin espacios (p. ej.
`C:\tfm\TFM_ENCRY`); Vivado lleva mal las rutas largas de Windows.

```powershell
cd C:\tfm\TFM_ENCRY\synth\basys3
vivado -mode batch -source build.tcl -log build.log -journal build.jou
```

Deja en `synth\basys3\build\` los checkpoints, los informes y
`basys3_top.bit`. Para generar **y** grabar en la misma pasada:

```powershell
vivado -mode batch -source build.tcl -log build.log -journal build.jou -tclargs programar
```

(`build.tcl` siempre sintetiza antes de grabar; el bitstream va a la
FPGA, no a la flash, y se pierde al apagar.)

Qué mirar, **leyendo los informes enteros** (nada de filtrar
`build.log`):

- `build.log`: errores y avisos de síntesis. Se esperan los avisos de lazo
  combinacional de los anillos (son intencionados: `ALLOW_COMBINATORIAL_LOOPS`
  en el XDC).
- `drc.rpt`: `LUTLP-1` debe salir como aviso, no como error.
- `method.rpt`: `TIMING-23` (lazo combinacional) por los anillos.
- `timing.rpt`: WNS/WHS de `sys_clk_pin` y de `ro2_clk`. El periodo de
  `ro2_clk` (1,4 ns) es una **estimación**: si no cierra, no es todavía un
  fallo; se mide la frecuencia real del anillo con el primer bitstream y
  se ajusta el XDC.
- `util_hier.rpt`: que existan los dos anillos (`u_motor/u_ro1`,
  `u_motor/u_ro2`) y no los haya eliminado la optimización.

Señal de vida tras grabar: **ld15** parpadea (latido); **ld0** es la
alarma de salud. Pines y Pmod en `synth/basys3/basys3.xdc`.

## 6. Grabar sin Vivado (opcional)

Con el `.bit` ya generado, `openFPGALoader` lo graba desde cualquier PC;
en el de Linux está en `~/eda/oss-cad-suite/bin` [NO PROBADO]:

```bash
openFPGALoader -b basys3 basys3_top.bit        # a la FPGA (volátil)
openFPGALoader -b basys3 -f basys3_top.bit     # a la flash SPI (con JP1 en QSPI, arranca sola)
```

En Linux hace falta acceso al FT2232 sin root (regla udev de
openFPGALoader, `99-openfpgaloader.rules`, y el usuario en `plugdev`).

## 7. Conectar el ESP32

Ver `docs/plataforma_y_flujo.md` §7 y `docs/mapa_registros.md`. Lo mínimo:
SCL a JA1, SDA a JA2, **pull-ups externos de 2,2-4,7 kΩ a 3,3 V**, cables
cortos y **solo GND común** entre placas (nunca unir 3,3 V ni 5 V).

## 8. Al hacerlo de verdad

Anotar aquí la versión exacta instalada, la ruta, el espacio que ocupó,
el tiempo de `build.tcl` y lo que salga en los informes; y quitar las
marcas [NO VERIFICADO] que se confirmen.
