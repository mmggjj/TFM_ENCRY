#!/usr/bin/env bash
# Comprobacion sin ISE: la netlist Verilog que leera XST (a_verilog.sh),
# sintetizada con Yosys synth_xilinx -family xc3se. Es una estimacion de
# otra herramienta, con soporte experimental de Spartan-3E (sin SRL16);
# ISE dara otra cifra. Log integro en results/basys2_yosys_xc3se.log.
#   bash synth/basys2/yosys_xc3se.sh       (desde la raiz del repo)
set -euo pipefail
OSS=${OSS:-$HOME/eda/oss-cad-suite}
export PATH=$OSS/bin:$PATH
bash synth/basys2/a_verilog.sh
yosys -l results/basys2_yosys_xc3se.log -p "
read_verilog -lib +/xilinx/cells_sim.v
read_verilog synth/basys2/build/basys2_top.v
synth_xilinx -family xc3se -top basys2_top -flatten
stat" > /dev/null
echo "log: results/basys2_yosys_xc3se.log"
