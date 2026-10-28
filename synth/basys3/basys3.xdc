# Restricciones de la Basys 3 para rtl/fpga/basys3_top.vhd.
# Pines del XDC maestro de Digilent (docs/plataforma_y_flujo.md 1.5).
# NO PROBADO EN PLACA.

## Reloj de placa, 100 MHz
set_property -dict { PACKAGE_PIN W5 IOSTANDARD LVCMOS33 } [get_ports clk]
create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports clk]

## Reset: btnC, activo a nivel alto (pull-down en placa)
set_property -dict { PACKAGE_PIN U18 IOSTANDARD LVCMOS33 } [get_ports btn_rst]

## modo_test: sw0
set_property -dict { PACKAGE_PIN V17 IOSTANDARD LVCMOS33 } [get_ports sw_test]

## I2C por Pmod JA: JA1 = SCL, JA2 = SDA. La Basys 3 no lleva pull-ups en
## los Pmod: se activan los del pin (debiles, ~10 k); para 400 kHz con
## cable, mejor 2,2-4,7 k externos a 3,3 V. Masa comun con el ESP32.
set_property -dict { PACKAGE_PIN J1 IOSTANDARD LVCMOS33 PULLUP TRUE } [get_ports scl]
set_property -dict { PACKAGE_PIN L2 IOSTANDARD LVCMOS33 PULLUP TRUE } [get_ports sda]

## LEDs: ld0 alarma de salud, ld15 latido
set_property -dict { PACKAGE_PIN U16 IOSTANDARD LVCMOS33 } [get_ports led_alarma]
set_property -dict { PACKAGE_PIN L1  IOSTANDARD LVCMOS33 } [get_ports led_vivo]

## Entradas asincronas (boton, interruptor, I2C muestreado a 100 MHz)
set_false_path -from [get_ports {btn_rst sw_test scl sda}]
set_false_path -to [get_ports {led_alarma led_vivo sda}]

## Anillo de muestreo (ro2, 5 etapas): es un reloj. Periodo ESTIMADO para
## LUT1 + rutado en Artix-7; el primer bitstream lee la frecuencia real y
## se ajusta. Sus registros (ero_core, trng_capture, bit_cdc origen,
## reset_sync del anillo) se temporizan contra este reloj.
create_clock -name ro2_clk -period 1.4 [get_pins {u_motor/u_ro2/g_inv[4].u_inv/O}]
set_clock_groups -asynchronous -group [get_clocks sys_clk_pin] -group [get_clocks ro2_clk]

## Anillo muestreado (ro1, 7 etapas): es dato, no reloj; se muestrea en
## ero_core y la metaestabilidad forma parte de la fuente.
set_false_path -through [get_pins {u_motor/u_ro1/g_inv[6].u_inv/O}]

## Los lazos de los anillos (ro_pblocks.xdc los coloca)
set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets {u_motor/u_ro1/cadena[*]}]
set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets {u_motor/u_ro2/cadena[*]}]
set_property DONT_TOUCH TRUE [get_cells {u_motor/u_ro1/u_nand u_motor/u_ro1/g_inv[*].u_inv}]
set_property DONT_TOUCH TRUE [get_cells {u_motor/u_ro2/u_nand u_motor/u_ro2/g_inv[*].u_inv}]
set_disable_timing -from I0 -to O [get_cells {u_motor/u_ro1/g_inv[*].u_inv u_motor/u_ro2/g_inv[*].u_inv}]
set_disable_timing -from I1 -to O [get_cells {u_motor/u_ro1/u_nand u_motor/u_ro2/u_nand}]

## Configuracion
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
