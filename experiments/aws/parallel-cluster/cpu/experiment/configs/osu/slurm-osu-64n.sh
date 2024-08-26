#!/bin/sh

#SBATCH --job-name=osu-64n
#SBATCH --nodes=64
#SBATCH --time=0:20:00
#SBATCH --exclusive

echo "Start time:" $( date +%s )
nodes=64

# At most 28 combinations, 8 nodes 2 at a time
hosts=$( mpirun -N ${nodes} --map-by ppr:1:node hostname | shuf -n 8 | tr '\n' ' ' )
list=${hosts}

dequeue_from_list() {
  shift;
  list=$@
}

for i in $hosts; do
  dequeue_from_list $list
  for j in $list; do
    echo "Point-to-point pairwise experiments for nodes" ${i} ${j}
    time -p mpirun -N 2 --map-by ppr:1:node \
      --host ${i},${j} \
      /shared/bin/singularity exec /shared/containers/metric-osu-cpu_libfabric-zen4.sif \
        /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    time -p mpirun -N 2 --map-by ppr:1:node \
      --host ${i},${j} \
      /shared/bin/singularity exec /shared/containers/metric-osu-cpu_libfabric-zen4.sif \
        /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw
  done
done

iter=0
for i in {1..5}; do
  echo "Allreduce iteration" ${iter}
  time -p mpirun -N ${nodes} --map-by ppr:96:node \
      /shared/bin/singularity exec /shared/containers/metric-osu-cpu_libfabric-zen4.sif \
        /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  iter=$((iter+1))
done

echo "End time:" $( date +%s )