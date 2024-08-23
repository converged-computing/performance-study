#!/bin/sh

#SBATCH --job-name=kripke-128n
#SBATCH --nodes=128
#SBATCH --time=0:10:00
#SBATCH --exclusive

export OMP_NUM_THREADS=1
echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 128 --map-by ppr:96:node \
	                    /shared/bin/singularity exec /shared/containers/metric-kripke-cpu_libfabric-zen4.sif kripke \
			    --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 32,12,32
echo "End time:" $( date +%s )