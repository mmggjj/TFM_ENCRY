# Flujo non-project de Vivado para la Basys 3 (docs/plataforma_y_flujo.md 3.3).
#
#   cd synth/basys3
#   vivado -mode batch -source build.tcl -log build.log -journal build.jou
#
# Deja en build/: checkpoints, informes de utilizacion, temporizacion, DRC
# y metodologia, y el bitstream. Programar: build.tcl con "programar" como
# argumento (-tclargs programar) y la placa por USB.
# NO PROBADO EN PLACA.

set part xc7a35tcpg236-1
set top  basys3_top
set raiz [file normalize ../..]
set out  ./build
file mkdir $out

# 1) Fuentes (VHDL-2008), en orden de dependencia
read_vhdl -vhdl2008 [list \
    $raiz/rtl/trng/ring_osc.vhd \
    $raiz/rtl/trng/reset_sync.vhd \
    $raiz/rtl/trng/ero_core.vhd \
    $raiz/rtl/trng/trng_capture.vhd \
    $raiz/rtl/trng/health_tests.vhd \
    $raiz/rtl/trng/bit_cdc.vhd \
    $raiz/rtl/io/i2c_slave.vhd \
    $raiz/rtl/aes/aes_pkg.vhd \
    $raiz/rtl/aes/aes_enc.vhd \
    $raiz/rtl/aes/aes_cmac.vhd \
    $raiz/rtl/drbg/ctr_drbg.vhd \
    $raiz/rtl/top/motor_top.vhd \
    $raiz/rtl/fpga/basys3_top.vhd]
read_xdc ./basys3.xdc
read_xdc ./ro_pblocks.xdc

# 2) Sintesis. -flatten_hierarchy rebuilt conserva los nombres jerarquicos
#    que usan los XDC (u_motor/u_ro1/...).
synth_design -top $top -part $part -flatten_hierarchy rebuilt
write_checkpoint -force $out/post_synth.dcp
report_utilization -hierarchical -file $out/util_synth_hier.rpt

# 3) Implementacion
opt_design
place_design
route_design
write_checkpoint -force $out/post_route.dcp

# 4) Informes. El lazo combinacional de cada anillo sale como LUTLP-1:
#    se baja a aviso porque es intencionado (ALLOW_COMBINATORIAL_LOOPS).
set_property SEVERITY {Warning} [get_drc_checks LUTLP-1]
report_utilization -hierarchical -hierarchical_depth 3 -file $out/util_hier.rpt
report_timing_summary -delay_type min_max -max_paths 10 -file $out/timing.rpt
report_clock_interaction -file $out/clocks.rpt
report_drc -file $out/drc.rpt
report_methodology -file $out/method.rpt

# 5) Bitstream
write_bitstream -force -bin_file $out/$top.bit

# 6) Programacion por JTAG, solo si se pide
if {[lsearch $argv programar] >= 0} {
    open_hw_manager
    connect_hw_server
    open_hw_target
    current_hw_device [lindex [get_hw_devices xc7a35t*] 0]
    set_property PROGRAM.FILE $out/$top.bit [current_hw_device]
    program_hw_devices [current_hw_device]
    close_hw_manager
}
