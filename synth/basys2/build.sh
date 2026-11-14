#!/usr/bin/env bash
# Flujo de ISE 14.7 por linea de ordenes para la Basys 2 (docs/basys2.md).
# XST no lee VHDL-2008: primero GHDL pasa basys2_top a Verilog
# (a_verilog.sh) y XST sintetiza esa netlist. Despues ngdbuild, map, par,
# trce y bitgen. Los logs y los informes quedan en synth/basys2/build/.
#
#   bash synth/basys2/build.sh              sintesis + implementacion + bitstream
#   bash synth/basys2/build.sh programar    ademas, graba la FPGA (Adept 2)
#
# ISE en ~/Xilinx/14.7 por defecto (ISE_DIR lo cambia). Grado de
# velocidad: el de la serigrafia del chip (VELOCIDAD, -4 por defecto).
# NO PROBADO: ni ISE ni la placa se han usado todavia.
set -euo pipefail
cd "$(dirname "$0")/../.."
ISE_DIR=${ISE_DIR:-$HOME/Xilinx/14.7/ISE_DS}
VELOCIDAD=${VELOCIDAD:-4}       # la serigrafia de la placa de Mario dice 4C
PARTE=xc3s100e-${VELOCIDAD}-cp132
B=synth/basys2/build
mkdir -p "$B"

# ISE 14.7 pide libncurses.so.5, que Ubuntu 24.04+ ya no trae: ISE_COMPAT
# es una carpeta con libncurses.so.5 -> libncurses.so.6 (y libtinfo), que
# solo ve ISE (docs/basys2.md).
ISE_COMPAT=${ISE_COMPAT:-$HOME/eda/ise_compat}
[ -d "$ISE_COMPAT" ] && export LD_LIBRARY_PATH="$ISE_COMPAT${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# settings64.sh de ISE no tolera set -u
set +u
# shellcheck disable=SC1091
source "$ISE_DIR/settings64.sh" > /dev/null
set -u

bash synth/basys2/a_verilog.sh

cd "$B"
echo 'verilog work "basys2_top.v"' > basys2_top.prj
cat > basys2_top.xst <<EOF
set -tmpdir xst_tmp
set -xsthdpdir xst
run
-ifn basys2_top.prj
-ifmt mixed
-top basys2_top
-ofn basys2_top.ngc
-ofmt NGC
-p $PARTE
-opt_mode Speed
-opt_level 1
-keep_hierarchy Soft
-iobuf YES
-iob auto
EOF
mkdir -p xst_tmp xst

paso() { echo "== $1"; shift; "$@"; }
paso xst      xst -ifn basys2_top.xst -ofn basys2_top.syr
# UCF: otro fichero para variantes en las que XST da otros nombres de red
# (sin medidor la salida del anillo es u_motor/ro_mon<i>, no u_motor_ro_mon<i>).
paso ngdbuild ngdbuild -dd _ngo -nt timestamp -uc "${UCF:-../basys2.ucf}" -p "$PARTE" \
                       basys2_top.ngc basys2_top.ngd
paso map      map -p "$PARTE" -o basys2_top_map.ncd basys2_top.ngd basys2_top.pcf
paso par      par -w -ol high basys2_top_map.ncd basys2_top.ncd basys2_top.pcf
paso trce     trce -v 10 -u 10 basys2_top.ncd basys2_top.pcf -o basys2_top.twr
# StartUpClk = JtagClk: se graba por JTAG (Adept). Para la Platform Flash
# haria falta CCLK y un .mcs con promgen.
paso bitgen   bitgen -w -g StartUpClk:JtagClk -g CRC:Enable \
                     basys2_top.ncd basys2_top.bit basys2_top.pcf
echo "bitstream: $B/basys2_top.bit"
echo "informes: $B/basys2_top.syr (XST), basys2_top_map.mrp (ocupacion),"
echo "          basys2_top.par (rutado), basys2_top.twr (tiempos)"

if [ "${1:-}" = "programar" ]; then
  # La placa se elige por numero de serie: el nombre de usuario guardado en
  # la de Mario esta corrupto y "-d Basys2" no la encuentra. ADEPT_DEV lo
  # cambia. Cadena JTAG: 0 = XC3S100E, 1 = XCF02S (Platform Flash).
  # Sin el LD_LIBRARY_PATH de ISE: su libstdc++ es mas vieja que la que
  # pide Adept y djtgcfg no arranca.
  ADEPT_DEV=${ADEPT_DEV:-$(env -u LD_LIBRARY_PATH djtgcfg enum | awk '/Serial Number/ {print "SN:" $3; exit}')}
  paso djtgcfg env -u LD_LIBRARY_PATH djtgcfg prog -d "$ADEPT_DEV" -i 0 -f basys2_top.bit
fi
