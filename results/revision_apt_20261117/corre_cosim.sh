#!/bin/bash
# uso: corre_cosim.sh W C RCT CICLOS SEMILLA
cd /tmp/claude-1000/revision_b3
ghdl -r --std=08 tb_cosim -gW=$1 -gC=$2 -gRCT=$3 -gCICLOS=$4 -gSEMILLA=$5 2>&1
