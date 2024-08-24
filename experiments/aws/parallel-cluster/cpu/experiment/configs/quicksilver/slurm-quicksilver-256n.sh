#!/bin/sh

#SBATCH --job-name=quicksilver-256n
#SBATCH --nodes=256
#SBATCH --time=0:10:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
export OMP_NUM_THREADS=3
/usr/bin/time -p mpirun -N 256 -x OMP_NUM_THREADS=3 --map-by ppr:32:node \
    singularity exec /shared/containers/metric-quicksilver-cpu_libfabric-zen4.sif qs \
    --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp \
    -X 256 -Y 256 -Z 128 -x 256 -y 256 -z 128 -I 32 -J 16 -K 16 -n 2684354560
echo "End time:" $( date +%s )