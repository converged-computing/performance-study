#!/bin/sh

#SBATCH --job-name=amg-2n
#SBATCH --nodes=2
#SBATCH --time=0:20:00
#SBATCH --exclusive

export OMP_NUM_THREADS=3
echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 2 --map-by ppr:32:node --cpus-per-proc 3 \
                            singularity exec /shared/containers/metric-amg2023_spack-slim-cpu-int64-zen3.sif /bin/bash run-amg.sh amg \
                            -n 256 256 128 -P 4 4 4 -problem 2
echo "End time:" $( date +%s )