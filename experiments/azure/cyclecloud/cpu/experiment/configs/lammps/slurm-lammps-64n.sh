#!/bin/sh

#SBATCH --job-name=lammps-64n
#SBATCH --nodes=64
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 64 --map-by ppr:96:node -x UCX_POSIX_USE_PROC_LINK=n \
	/shared/bin/singularity exec --pwd /code --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-lammps-cpu_azure-hpc-reax.sif \
	lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns
echo "End time:" $( date +%s )
