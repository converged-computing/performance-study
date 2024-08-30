#!/bin/sh

#SBATCH --job-name=lammps-32n
#SBATCH --nodes=32
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 32 --map-by ppr:96:node \
        /shared/bin/singularity exec --pwd /code \
        /shared/containers/metric-lammps-cpu_zen4-reax.sif \
        lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns
echo "End time:" $( date +%s )
