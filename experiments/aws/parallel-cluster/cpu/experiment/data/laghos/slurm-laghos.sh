#!/bin/sh

#SBATCH --job-name=laghos-32n-test
#SBATCH --output=laghos-32n-out.log
#SBATCH --error=laghos-32n-err.log
#SBATCH --nodes=32
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
#/usr/bin/time -p mpirun -N 32 --map-by ppr:32:node singularity exec /shared/containers/metric-laghos-cpu_libfabric-zen4.sif qs --inputFile /opt/laghos/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp  -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320
/usr/bin/time -p mpirun -N 32 --map-by ppr:96:node singularity exec /shared/containers/metric-laghos_libfabric-cpu-zen4.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
echo "End time:" $( date +%s )
