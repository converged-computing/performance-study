#!/bin/sh

#SBATCH --job-name=laghos-256n
#SBATCH --nodes=256
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 256 --map-by ppr:96:node \
        singularity exec /shared/containers/metric-laghos_libfabric-cpu-zen4.sif /opt/laghos/laghos \
        -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
echo "End time:" $( date +%s )