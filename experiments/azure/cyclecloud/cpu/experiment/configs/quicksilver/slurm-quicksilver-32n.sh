#!/bin/sh

#SBATCH --job-name=quicksilver-32n
#SBATCH --nodes=32
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
ml mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
export OMP_NUM_THREADS=3
/usr/bin/time -p mpirun -N 32 --cpus-per-proc 3 -x UCX_POSIX_USE_PROC_LINK=n --map-by ppr:32:node \
    singularity exec --env OMP_NUM_THREADS=3 --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-quicksilver-cpu_azure-hpc.sif qs \
    --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp \
    -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320
echo "End time:" $( date +%s )
