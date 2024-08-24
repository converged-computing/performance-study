#!/bin/sh

#SBATCH --job-name=stream-1n
#SBATCH --nodes=1
#SBATCH --time=0:10:00
#SBATCH --exclusive

export OMP_NUM_THREADS=96
echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 1 --map-by ppr:1:node \
	/shared/bin/singularity exec /shared/containers/metric-stream_libfabric-cpu-zen4.sif \
	stream_c.exe
echo "End time:" $( date +%s )