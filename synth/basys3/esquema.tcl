# Esquematico RTL de Vivado (diseno elaborado) en PDF. Necesita la interfaz:
#   cd results/basys3_esquema
#   vivado -mode gui -source ../../synth/basys3/esquema.tcl
# (LOCPATH y LD_LIBRARY_PATH como en build.tcl). Variante silenciosa.
set raiz [file normalize ../..]
read_vhdl -vhdl2008 [list \
    $raiz/rtl/trng/ring_osc.vhd $raiz/rtl/trng/reset_sync.vhd $raiz/rtl/trng/ero_core.vhd \
    $raiz/rtl/trng/trng_capture.vhd $raiz/rtl/trng/flujo_crudo.vhd $raiz/rtl/trng/health_tests.vhd \
    $raiz/rtl/trng/bit_cdc.vhd $raiz/rtl/io/i2c_slave.vhd $raiz/rtl/aes/aes_pkg.vhd \
    $raiz/rtl/aes/aes_enc.vhd $raiz/rtl/aes/aes_enc_32.vhd $raiz/rtl/aes/aes_cmac.vhd \
    $raiz/rtl/drbg/ctr_drbg.vhd $raiz/rtl/top/motor_top.vhd $raiz/rtl/fpga/medidor_frec.vhd \
    $raiz/rtl/fpga/siete_seg.vhd $raiz/rtl/fpga/basys3_top.vhd]
synth_design -rtl -top basys3_top -part xc7a35tcpg236-1 -generic G_QUIETO=true -generic G_MEDIDOR=false
set jer [get_cells -hier -filter {IS_PRIMITIVE == 0}]
puts "BLOQUES: $jer"
show_schematic -name top [get_cells]
write_schematic -force -format pdf -orientation landscape -name top [pwd]/esquema_basys3_top.pdf
show_schematic -name motor [get_cells -filter {IS_PRIMITIVE == 0} u_motor/*]
write_schematic -force -format pdf -orientation landscape -name motor [pwd]/esquema_motor_top.pdf
puts "ESQUEMAS ESCRITOS"
exit
