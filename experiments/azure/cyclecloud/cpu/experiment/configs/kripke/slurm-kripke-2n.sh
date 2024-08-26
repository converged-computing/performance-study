#!/bin/sh

#SBATCH --job-name=kripke-2n
#SBATCH --nodes=2
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 2 --map-by ppr:96:node -x UCX_POSIX_USE_PROC_LINK=n \
	            singularity exec --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
				/shared/containers/metric-kripke-cpu_azure-hpc.sif kripke \
			    --layout GDZ --dset 8 --zones 96,96,96 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,6,8
echo "End time:" $( date +%s )