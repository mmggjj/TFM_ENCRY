#!/usr/bin/env bash
# Comprobacion sin Vivado: basys3_top entero con Yosys (synth_xilinx, xc7).
# Las LUT1/LUT2 de los anillos van como cajas negras. Es una estimacion de
# recursos de otra herramienta, no la de Vivado. Log integro en
# results/basys3_yosys_xc7.log.
#   bash synth/basys3/yosys_xc7.sh       (desde la raiz del repo)
set -euo pipefail
OSS=${OSS:-$HOME/eda/oss-cad-suite}
export PATH=$OSS/bin:$PATH
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
ghdl -a --std=08 --work=unisim --workdir="$W" "$W/vcomponents.vhd"
ghdl -a --std=08 --workdir="$W" -P"$W" \
  rtl/trng/ring_osc.vhd rtl/trng/reset_sync.vhd rtl/trng/ero_core.vhd \
  rtl/trng/trng_capture.vhd rtl/trng/flujo_crudo.vhd rtl/trng/health_tests.vhd rtl/trng/bit_cdc.vhd \
  rtl/io/i2c_slave.vhd rtl/aes/aes_pkg.vhd rtl/aes/aes_enc.vhd \
  rtl/aes/aes_enc_32.vhd rtl/aes/aes_cmac.vhd rtl/drbg/ctr_drbg.vhd \
  rtl/top/motor_top.vhd rtl/fpga/medidor_frec.vhd rtl/fpga/siete_seg.vhd \
  rtl/fpga/basys3_top.vhd
yosys -m ghdl -l results/basys3_yosys_xc7.log -p "
ghdl --std=08 --workdir=$W -P$W basys3_top
synth_xilinx -family xc7 -top basys3_top -flatten
stat" > /dev/null
echo "log: results/basys3_yosys_xc7.log"
