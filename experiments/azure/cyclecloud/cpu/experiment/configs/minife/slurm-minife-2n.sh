#!/bin/sh

#SBATCH --job-name=minife-2n
#SBATCH --nodes=2
#SBATCH --time=0:10:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 2 --map-by ppr:96:node \
	/shared/bin/singularity exec /shared/containers/metric-minife_libfabric-cpu-zen4.sif \
	miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
echo "End time:" $( date +%s )