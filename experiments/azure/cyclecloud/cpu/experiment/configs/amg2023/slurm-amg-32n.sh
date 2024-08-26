#!/bin/sh

#SBATCH --job-name=amg-32n
#SBATCH --nodes=32
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 32 --map-by ppr:32:node --cpus-per-proc 3 -x UCX_POSIX_USE_PROC_LINK=n \
                            singularity exec --env OMP_NUM_THREADS=3 --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
			                /shared/containers/metric-amg2023_azure-hpc-cpu-int64-zen3.sif \
                            /opt/spack-environment/.spack-env/view/bin/amg \
                            -n 256 256 128 -P 16 8 8 -problem 2
echo "End time:" $( date +%s )