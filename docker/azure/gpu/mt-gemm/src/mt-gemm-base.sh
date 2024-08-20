#!/bin/bash

appbase="/g/g92/marathe1/variorum/gpu-benchmarking/benchmarks/lgc-cap-bm/mt-gemm-base"
execname=mt-dgemm.x
nnodes=2
ntasks=8
NTASKS_PER_NODE=`echo $ntasks/$nnodes | bc`

input_iters=200
input=8192

cd ${appbase}
# Required step to generate hostfile for mpirun
# You may skip this if you have a hostfile already set up.
srun -N ${nnodes} -n ${nnodes} hostname > hostfile
export CUDA_VISIBLE_DEVICES=0,1,2,3
mpirun -np $ntasks --hostfile hostfile -N $NTASKS_PER_NODE ./${execname} ${input} ${input_iters}
cd -
