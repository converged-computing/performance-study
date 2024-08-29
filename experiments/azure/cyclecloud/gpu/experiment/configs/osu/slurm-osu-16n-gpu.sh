#!/bin/sh

#SBATCH --job-name=osu-16n
#SBATCH --nodes=16
#SBATCH --time=0:30:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
ml mpi/hpcx-pmix-2.18
#ml cuda/11.8.0 #xl/2023.06.28-cuda-11.8.0-gcc-11.2.1

echo "Start time:" $( date +%s )
mpirun --map-by ppr:1:node \
     /shared/bin/singularity exec --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
     /shared/containers/metric-osu-gpu_azure-hpc-gpu-ubuntu2204.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda D D    
     #/shared/containers/metric-osu-gpu_azure-hpc-gpu-ubuntu2204.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda D D    
echo "End time:" $( date +%s )
