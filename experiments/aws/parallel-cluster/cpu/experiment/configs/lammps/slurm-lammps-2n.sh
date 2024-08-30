#!/bin/sh

#SBATCH --job-name=lammps-2n
#SBATCH --nodes=2
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 2 --map-by ppr:96:node \
        /shared/bin/singularity exec --pwd /code \
        /shared/containers/metric-lammps-cpu_zen4-reax.sif \
        lmp -v x 32 -v y 32 -v z 16 -in in.reaxff.hns
echo "End time:" $( date +%s )
