# Flujo non-project de Vivado para la Basys 3 (docs/plataforma_y_flujo.md 3.3).
# Instalacion en Windows y puesta en marcha: docs/instalacion_vivado_windows.md
#
#   cd synth/basys3
#   vivado -mode batch -source build.tcl -log build.log -journal build.jou
#
# Deja en build/: checkpoints, informes de utilizacion, temporizacion, DRC
# y metodologia, y el bitstream. Programar: build.tcl con "programar" como
# argumento (-tclargs programar) y la placa por USB.
# Probado en placa el 17-11-2026 (docs/basys3.md).

#
# Variantes: GENERICOS="G_QUIETO=true G_MEDIDOR=false" en el entorno pasa
# cada par a synth_design -generic y deja la salida en build/<variante>
# (booleanos de VHDL como true/false, comprobado). En Linux se graba con
# openFPGALoader -b basys3 (Vivado necesita los drivers de cable como root).
# Los relojes de los anillos del XDC estan en g_inv[N-1] de 11/13 etapas: si
# se cambian G_ETAPAS_RO1/RO2 hay que cambiar el XDC (se comprueba abajo).
# XDC_EXTRA="ro_bel.xdc" fija LOC y BEL de cada etapa (una LUT6 por etapa).

set part xc7a35tcpg236-1
set top  basys3_top
set raiz [file normalize ../..]
set gen_args {}
set variante ""
if {[info exists ::env(GENERICOS)] && [string trim $::env(GENERICOS)] ne ""} {
    foreach g [split [string trim $::env(GENERICOS)]] {
        if {$g eq ""} continue
        lappend gen_args -generic $g
        append variante "_[string map {= _} $g]"
    }
}
if {[info exists ::env(XDC_EXTRA)] && [string trim $::env(XDC_EXTRA)] ne ""} {
    foreach x [split [string trim $::env(XDC_EXTRA)]] { append variante "_[file rootname $x]" }
}
set out  ./build[expr {$variante eq "" ? "" : "/[string range $variante 1 end]"}]
file mkdir $out
puts "variante: [expr {$variante eq "" ? "por defecto" : $variante}] -> $out"

# 1) Fuentes (VHDL-2008), en orden de dependencia
read_vhdl -vhdl2008 [list \
    $raiz/rtl/trng/ring_osc.vhd \
    $raiz/rtl/trng/reset_sync.vhd \
    $raiz/rtl/trng/ero_core.vhd \
    $raiz/rtl/trng/trng_capture.vhd \
    $raiz/rtl/trng/flujo_crudo.vhd \
    $raiz/rtl/trng/health_tests.vhd \
    $raiz/rtl/trng/bit_cdc.vhd \
    $raiz/rtl/io/i2c_slave.vhd \
    $raiz/rtl/aes/aes_pkg.vhd \
    $raiz/rtl/aes/aes_enc.vhd \
    $raiz/rtl/aes/aes_enc_32.vhd \
    $raiz/rtl/aes/aes_cmac.vhd \
    $raiz/rtl/drbg/ctr_drbg.vhd \
    $raiz/rtl/top/motor_top.vhd \
    $raiz/rtl/fpga/medidor_frec.vhd \
    $raiz/rtl/fpga/siete_seg.vhd \
    $raiz/rtl/fpga/basys3_top.vhd]
read_xdc ./basys3.xdc
read_xdc ./ro_pblocks.xdc
# XDC_EXTRA="ro_bel.xdc": restricciones adicionales (colocacion fija de las
# etapas); la salida va a build/<variante>_<nombre del xdc>.
if {[info exists ::env(XDC_EXTRA)] && [string trim $::env(XDC_EXTRA)] ne ""} {
    foreach x [split [string trim $::env(XDC_EXTRA)]] { read_xdc ./$x }
}

# 2) Sintesis. -flatten_hierarchy rebuilt conserva los nombres jerarquicos
#    que usan los XDC (u_motor/u_ro1/...).
synth_design -top $top -part $part -flatten_hierarchy rebuilt {*}$gen_args
# Sin estos relojes el dominio del anillo queda sin restringir y Vivado sigue
# adelante: se para aqui.
foreach ck {ro1_clk ro2_clk} {
    if {[llength [get_clocks -quiet $ck]] == 0} {
        error "$ck sin definir: el pin de basys3.xdc no coincide con G_ETAPAS"
    }
}
write_checkpoint -force $out/post_synth.dcp
report_utilization -hierarchical -file $out/util_synth_hier.rpt

# 3) Implementacion
opt_design
place_design
route_design
write_checkpoint -force $out/post_route.dcp

# Los anillos en la netlist implementada: N LUT por anillo, colocadas y
# con el lazo rutado (en la Basys 2 la herramienta los colapso).
foreach r {u_ro1 u_ro2} {
    set c [lsort [get_cells -hier -filter "NAME =~ u_motor/$r/*"]]
    puts "ANILLO $r: [llength $c] celdas"
    foreach x $c { puts "  $x [get_property REF_NAME $x] [get_property LOC $x] [get_property BEL $x]" }
    foreach n [get_nets u_motor/$r/cadena*] { puts "  red $n [get_property ROUTE_STATUS $n]" }
}
report_route_status -file $out/route_status.rpt

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
