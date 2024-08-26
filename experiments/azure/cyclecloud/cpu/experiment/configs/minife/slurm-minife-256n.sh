#!/bin/sh

#SBATCH --job-name=minife-256n
#SBATCH --nodes=256
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 256 --map-by ppr:96:node -x UCX_POSIX_USE_PROC_LINK=n \
	/shared/bin/singularity exec --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \ 
	/shared/containers/metric-minife_azure-hpc.sif \
	miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
echo "End time:" $( date +%s )