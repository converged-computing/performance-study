#!/bin/sh

#SBATCH --job-name=quicksilver-2n
#SBATCH --nodes=2
#SBATCH --time=0:10:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
export OMP_NUM_THREADS=3
/usr/bin/time -p mpirun -N 2 -x OMP_NUM_THREADS=3 --map-by ppr:32:node \
    singularity exec /shared/containers/metric-quicksilver-cpu_libfabric-zen4.sif qs \
    --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp \
    -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 10485760
echo "End time:" $( date +%s )