#!/bin/sh

#SBATCH --job-name=mixbench-1n
#SBATCH --nodes=1
#SBATCH --time=0:20:00
#SBATCH --exclusive

export OMP_NUM_THREADS=96
echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 1 --map-by ppr:1:node \
	/shared/bin/singularity exec /shared/containers/metric-mixbench_libfabric-cpu.sif \
	mixbench-cpu 32
echo "End time:" $( date +%s )