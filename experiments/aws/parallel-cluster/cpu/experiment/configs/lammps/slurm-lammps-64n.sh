#!/bin/sh

#SBATCH --job-name=lammps-64n
#SBATCH --nodes=64
#SBATCH --time=0:10:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 64 --map-by ppr:96:node \
	/shared/bin/singularity exec --pwd /code /shared/containers/metric-lammps-cpu_zen4.sif \
	lmp -k on -sf kk -pk kokkos newton on neigh half \
	-in in.snap.test -var snapdir 2J8_W.SNAP \ 
	-v x 128 -v y 128 -v z 128 -var nsteps 20000
echo "End time:" $( date +%s )