#!/bin/sh

#SBATCH --job-name=kripke-128n
#SBATCH --nodes=128
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 128 --map-by ppr:96:node -x UCX_POSIX_USE_PROC_LINK=n \
	            singularity exec --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
				/shared/containers/metric-kripke-cpu_azure-hpc.sif kripke \
			    --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 32,12,32
echo "End time:" $( date +%s )