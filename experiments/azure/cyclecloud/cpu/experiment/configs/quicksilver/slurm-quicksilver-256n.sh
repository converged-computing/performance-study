#!/bin/sh

#SBATCH --job-name=quicksilver-256n
#SBATCH --nodes=256
#SBATCH --output=qs-output-N256n8192t3-slurm.txt
#SBATCH --error=qs-error--N256n8192t3-slurm.txt
#SBATCH --time=0:10:00
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
    -X 256 -Y 256 -Z 128 -x 256 -y 256 -z 128 -I 32 -J 16 -K 16 -n 2684354560
echo "End time:" $( date +%s )
