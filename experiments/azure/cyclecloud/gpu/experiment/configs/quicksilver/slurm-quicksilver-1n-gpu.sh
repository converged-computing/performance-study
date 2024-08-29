#!/bin/sh

#SBATCH --job-name=quicksilver-1n
#SBATCH --nodes=1
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
ml mpi/hpcx-pmix-2.18
module unload mpi
#xl/2023.06.28-cuda-11.8.0-gcc-11.2.1

echo "Start time:" $( date +%s )
export CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7"
/usr/bin/time -p mpirun -N 1 -x UCX_POSIX_USE_PROC_LINK=n --map-by ppr:4:node \
    singularity exec --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-quicksilver-gpu_azure-hpc-gpu-ubuntu2204.sif qs \
    --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp \
     -X 16  -Y 16  -Z 16  -x 16  -y 16  -z 16  -I 2  -J 2  -K 1  -n 163840
echo "End time:" $( date +%s )
