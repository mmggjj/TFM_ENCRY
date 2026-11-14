#!/usr/bin/env bash
# basys2_top (VHDL-2008) -> una netlist Verilog para XST, que no lee
# VHDL-2008. GHDL elabora con los genericos de basys2_top; las LUT1/LUT2
# de los anillos quedan como instancias de primitiva (cajas negras), que
# XST reconoce y conserva. Es lo mismo que hace synth/sintetiza.py --verilog
# para el integrado.
#   bash synth/basys2/a_verilog.sh       (desde la raiz del repo)
# Deja synth/basys2/build/basys2_top.v y el log de GHDL a su lado.
set -euo pipefail
GHDL=${GHDL:-ghdl}
OUT=synth/basys2/build
mkdir -p "$OUT"
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
cat > "$W/vcomponents.vhd" <<'VHD'
library ieee;
use ieee.std_logic_1164.all;
package vcomponents is
  component LUT1 generic (INIT : bit_vector(1 downto 0) := "00");
    port (O : out std_ulogic; I0 : in std_ulogic); end component;
  component LUT2 generic (INIT : bit_vector(3 downto 0) := "0000");
    port (O : out std_ulogic; I0, I1 : in std_ulogic); end component;
end package;
VHD
"$GHDL" -a --std=08 --work=unisim --workdir="$W" "$W/vcomponents.vhd"
FUENTES="rtl/trng/ring_osc.vhd rtl/trng/reset_sync.vhd rtl/trng/ero_core.vhd
  rtl/trng/trng_capture.vhd rtl/trng/flujo_crudo.vhd rtl/trng/health_tests.vhd
  rtl/trng/bit_cdc.vhd rtl/io/i2c_slave.vhd rtl/aes/aes_pkg.vhd
  rtl/aes/aes_enc.vhd rtl/aes/aes_enc_32.vhd rtl/aes/aes_cmac.vhd
  rtl/drbg/ctr_drbg.vhd rtl/top/motor_top.vhd rtl/fpga/medidor_frec.vhd
  rtl/fpga/siete_seg.vhd rtl/fpga/basys2_top.vhd"
"$GHDL" -a --std=08 --workdir="$W" -P"$W" $FUENTES
# GENERICOS: genericos de basys2_top para variantes (-gG_QUIETO=true).
# shellcheck disable=SC2086
"$GHDL" --synth --std=08 --workdir="$W" -P"$W" --out=verilog ${GENERICOS:-} basys2_top \
  > "$OUT/basys2_top.v" 2> "$OUT/ghdl_synth.log"
echo "netlist: $OUT/basys2_top.v ($(wc -l < "$OUT/basys2_top.v") lineas); log de GHDL: $OUT/ghdl_synth.log"
