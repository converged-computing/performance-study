#!/bin/sh

#SBATCH --job-name=quicksilver-2n
#SBATCH --nodes=2
#SBATCH --time=0:10:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
ml mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
export OMP_NUM_THREADS=3
/usr/bin/time -p mpirun -N 2 --cpus-per-proc 3 -x UCX_POSIX_USE_PROC_LINK=n --map-by ppr:32:node \
    singularity exec --env OMP_NUM_THREADS=3 --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-quicksilver-cpu_azure-hpc.sif qs \
    --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp \
    -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 10485760
echo "End time:" $( date +%s )
