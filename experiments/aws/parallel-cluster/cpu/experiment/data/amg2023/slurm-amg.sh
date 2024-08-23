#!/bin/sh

#SBATCH --job-name=amg-2n-test
#SBATCH --output=amg-2n-out.log
#SBATCH --error=amg-2n-err.log
#SBATCH --nodes=2
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $SLURM_JOB_START_TIME
time -p mpirun -N 2 --map-by ppr:96:node singularity exec /shared/containers/metric-amg2023_spack-slim-cpu.sif /bin/bash /shared/amg2023/run-amg.sh amg -n 256 256 128 -P 12 4 4 -problem 2
echo "End time:" $SLURM_JOB_END_TIME
