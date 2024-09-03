#!/bin/sh

#SBATCH --job-name=magma-1n
#SBATCH --nodes=1
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
ml mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
export CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7"
OMP_NUM_THREADS=8 mpirun -n 8 -x UCX_POSIX_USE_PROC_LINK=n --map-by ppr:8:node \
	singularity exec --nv --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y \
	--env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
	/shared/containers/metric-magma_azure-hpc-gpu-ubuntu2204.sif /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1

echo "End time:" $( date +%s )
