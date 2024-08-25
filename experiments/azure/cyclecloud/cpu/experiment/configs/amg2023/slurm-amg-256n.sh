#!/bin/sh

#SBATCH --job-name=amg-256n
#SBATCH --nodes=256
#SBATCH --time=0:10:00
#SBATCH --exclusive

export OMP_NUM_THREADS=3
echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 256 --map-by ppr:32:node --cpus-per-proc 3 \
                            singularity exec /shared/containers/metric-amg2023_spack-slim-cpu-int64-zen3.sif /bin/bash run-amg.sh amg \
                            -n 256 256 128 -P 32 16 16 -problem 2
echo "End time:" $( date +%s )