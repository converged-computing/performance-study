#!/bin/sh

#SBATCH --job-name=quicksilver-64n
#SBATCH --nodes=64
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
export OMP_NUM_THREADS=3
/usr/bin/time -p mpirun -N 64 -x OMP_NUM_THREADS=3 --map-by ppr:32:node \
    singularity exec /shared/containers/metric-quicksilver-cpu_libfabric-zen4.sif qs \
    --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp \
    -X 128 -Y 128 -Z 128 -x 128 -y 128 -z 128 -I 16 -J 16 -K 8 -n 671088640
echo "End time:" $( date +%s )