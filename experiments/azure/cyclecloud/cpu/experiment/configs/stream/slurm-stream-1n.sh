#!/bin/sh

#SBATCH --job-name=stream-1n
#SBATCH --nodes=1
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 1 --map-by ppr:1:node -x UCX_POSIX_USE_PROC_LINK=n \
	/shared/bin/singularity exec --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= --env OMP_NUM_THREADS=96 \
	/shared/containers/metric-stream_azure-hpc.sif \
	stream_c.exe
echo "End time:" $( date +%s )