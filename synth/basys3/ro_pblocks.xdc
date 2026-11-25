# Un pblock por anillo, lejos el uno del otro y de la logica: dos anillos
# iguales colocados juntos se acoplan (inyeccion por la alimentacion y el
# sustrato) y dejan de ser independientes; y si la herramienta los funde
# o los reparte por el chip, los retardos cambian. Cada bloque son seis
# slices (24 LUT): sobra para 13 etapas. Las coordenadas son del XC7A35T
# (SLICE_X0..X65, Y0..Y149); se eligen a la izquierda del chip, en filas
# distintas, y se revisan con la vista de dispositivo tras implementar.
# CONTAIN_ROUTING con 2 slices deja el lazo sin rutar (Vivado 2025.2, 17-11-2026):
# solo se fija la colocacion y se aparta el resto de la logica.

create_pblock pb_ro1
add_cells_to_pblock [get_pblocks pb_ro1] [get_cells {u_motor/u_ro1/u_nand u_motor/u_ro1/g_inv[*].u_inv}]
resize_pblock [get_pblocks pb_ro1] -add {SLICE_X0Y60:SLICE_X1Y62}
set_property EXCLUDE_PLACEMENT TRUE [get_pblocks pb_ro1]

create_pblock pb_ro2
add_cells_to_pblock [get_pblocks pb_ro2] [get_cells {u_motor/u_ro2/u_nand u_motor/u_ro2/g_inv[*].u_inv}]
resize_pblock [get_pblocks pb_ro2] -add {SLICE_X0Y90:SLICE_X1Y92}
set_property EXCLUDE_PLACEMENT TRUE [get_pblocks pb_ro2]
