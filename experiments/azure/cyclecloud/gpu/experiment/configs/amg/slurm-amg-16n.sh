#!/bin/sh

#SBATCH --job-name=amg-16n
#SBATCH --nodes=16
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
export CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7"
/usr/bin/time -p mpirun -n 128 --map-by ppr:8:node -x UCX_POSIX_USE_PROC_LINK=n \
                 singularity exec --env UCX_TLS=ud,shm,rc \
		 --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
		/shared/containers/metric-amg2023_azure-hpc-gpu-ubuntu2204.sif \
                /opt/spack-environment/.spack-env/view/bin/amg \
		-n 256 256 128 -P 8 4 4 -problem 2
echo "End time:" $( date +%s )
