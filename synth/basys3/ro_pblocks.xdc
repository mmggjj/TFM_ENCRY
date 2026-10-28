# Un pblock por anillo, lejos el uno del otro y de la logica: dos anillos
# iguales colocados juntos se acoplan (inyeccion por la alimentacion y el
# sustrato) y dejan de ser independientes; y si la herramienta los funde
# o los reparte por el chip, los retardos cambian. Cada bloque son dos
# slices (8 LUT): sobra para 7 etapas. Las coordenadas son del XC7A35T
# (SLICE_X0..X65, Y0..Y149); se eligen a la izquierda del chip, en filas
# distintas, y se revisan con la vista de dispositivo tras implementar.
# NO PROBADO EN PLACA.

create_pblock pb_ro1
add_cells_to_pblock [get_pblocks pb_ro1] [get_cells {u_motor/u_ro1/u_nand u_motor/u_ro1/g_inv[*].u_inv}]
resize_pblock [get_pblocks pb_ro1] -add {SLICE_X0Y60:SLICE_X1Y61}
set_property CONTAIN_ROUTING TRUE [get_pblocks pb_ro1]

create_pblock pb_ro2
add_cells_to_pblock [get_pblocks pb_ro2] [get_cells {u_motor/u_ro2/u_nand u_motor/u_ro2/g_inv[*].u_inv}]
resize_pblock [get_pblocks pb_ro2] -add {SLICE_X0Y90:SLICE_X1Y91}
set_property CONTAIN_ROUTING TRUE [get_pblocks pb_ro2]
