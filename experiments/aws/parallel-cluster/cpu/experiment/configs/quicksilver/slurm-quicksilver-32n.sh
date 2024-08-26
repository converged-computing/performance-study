#!/bin/sh

#SBATCH --job-name=quicksilver-32n
#SBATCH --nodes=32
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
export OMP_NUM_THREADS=3
/usr/bin/time -p mpirun -N 32 -x OMP_NUM_THREADS=3 --map-by ppr:32:node \
    singularity exec /shared/containers/metric-quicksilver-cpu_libfabric-zen4.sif qs \
    --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp \
    -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320
echo "End time:" $( date +%s )