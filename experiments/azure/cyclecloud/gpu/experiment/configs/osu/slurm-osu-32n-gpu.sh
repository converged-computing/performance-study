#!/bin/sh

#SBATCH --job-name=osu-32n
#SBATCH --nodes=32
#SBATCH --time=0:30:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
ml mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
nodes=32

# At most 28 combinations, 8 nodes 2 at a time
hosts=$( srun hostname | shuf -n 8 | tr '\n' ' ' )
list=${hosts}

dequeue_from_list() {
  shift;
  list=$@
}

for i in $hosts; do
  dequeue_from_list $list
  for j in $list; do
    echo "Point-to-point pairwise experiments for nodes" ${i} ${j}
    time -p mpirun -N 2 --map-by ppr:1:node -x UCX_POSIX_USE_PROC_LINK=n --host ${i},${j} \
      /shared/bin/singularity exec \
      --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
      /shared/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda D D
    time -p mpirun -N 2 --map-by ppr:1:node -x UCX_POSIX_USE_PROC_LINK=n --host ${i},${j} \
      /shared/bin/singularity exec \
      --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
      /shared/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw -d cuda D D
  done
done

for i in $( seq 1 5 ); do
  echo "Allreduce iteration" ${i}
  time -p mpirun -N ${nodes} --map-by ppr:96:node -x UCX_POSIX_USE_PROC_LINK=n \
      /shared/bin/singularity exec \
      --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
      /shared/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda D D
done

echo "End time:" $( date +%s )
