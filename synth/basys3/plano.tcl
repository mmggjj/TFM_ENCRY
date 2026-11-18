# Vuelca la colocacion de la implementacion para analysis/plano_basys3.py.
# cd results/basys3_plano; vivado -mode batch -source ../../synth/basys3/plano.tcl
# (con LOCPATH y LD_LIBRARY_PATH como en build.tcl; checkpoint de la silenciosa).
open_checkpoint [file normalize ../../synth/basys3/build]/G_QUIETO_true_G_MEDIDOR_false/post_route.dcp
set f [open [pwd]/celdas.csv w]
puts $f "celda,tipo,sitio,x,y"
foreach c [get_cells -hier -filter {IS_PRIMITIVE && LOC != ""}] {
  set s [get_sites -of_objects $c]
  puts $f "$c,[get_property REF_NAME $c],$s,[get_property RPM_X $s],[get_property RPM_Y $s]"
}
close $f
set f [open [pwd]/sitios.csv w]
puts $f "sitio,tipo,x,y"
foreach s [get_sites -filter {SITE_TYPE =~ SLICE* }] { puts $f "$s,[get_property SITE_TYPE $s],[get_property RPM_X $s],[get_property RPM_Y $s]" }
close $f
foreach p {pb_ro1 pb_ro2} { puts "PBLOCK $p [get_property GRID_RANGES [get_pblocks $p]]" }
