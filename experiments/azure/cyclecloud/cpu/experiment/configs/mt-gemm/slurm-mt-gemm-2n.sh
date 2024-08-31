#!/bin/sh

#SBATCH --job-name=mt-gemm-2n
#SBATCH --nodes=2
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 2 --map-by ppr:96:node -x UCX_POSIX_USE_PROC_LINK=n \
	/shared/bin/singularity exec --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
	/shared/bin/singularity /shared/containers/mt-gemm_azure-hpc-1k.sif \
	/opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
echo "End time:" $( date +%s )