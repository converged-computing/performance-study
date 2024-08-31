#!/bin/sh

#SBATCH --job-name=lammps-4n
#SBATCH --nodes=4
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

export CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7"
echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 4 --map-by ppr:8:node -x UCX_POSIX_USE_PROC_LINK=n \
	singularity exec --nv --env UCX_TLS=all --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    --env CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7" \
    /shared/containers/metric-lammps-gpu_azure-hpc-reax.sif \
	lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
echo "End time:" $( date +%s )

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 4 --map-by ppr:8:node -x UCX_POSIX_USE_PROC_LINK=n \
	singularity exec --nv --env UCX_TLS=all --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    --env CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7" \
    /shared/containers/metric-lammps-gpu_azure-hpc-reax.sif \
	lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite
echo "End time:" $( date +%s )