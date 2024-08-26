#!/bin/sh

#SBATCH --job-name=nekrs-128n
#SBATCH --nodes=128
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
cd /shared/nekrs/turbPipe
/usr/bin/time -p mpirun -N 128 --map-by ppr:96:node \
	/shared/bin/singularity exec --pwd /shared/nekrs/turbPipe/ \
	/shared/containers/metric-nek5000_libfabric-cpu.sif \
	nekrs --setup /shared/nekrs/turbPipe/turbPipe.par
echo "End time:" $( date +%s )