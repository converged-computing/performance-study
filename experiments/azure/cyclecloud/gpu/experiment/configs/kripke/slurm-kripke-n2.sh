#!/bin/sh

#SBATCH --job-name=kripke-2n
#SBATCH --nodes=2
#SBATCH --time=0:20:00
#SBATCH --exclusive
## #SBATCH --gpus-per-task=1  

. /etc/profile.d/modules.sh
ml mpi/hpcx-pmix-2.18
#ml cuda/11.8.0 #xl/2023.06.28-cuda-11.8.0-gcc-11.2.1

echo "Start time:" $( date +%s )
export CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7"
/usr/bin/time -p mpirun -N 2 -n 16 -x UCX_POSIX_USE_PROC_LINK=n  --map-by ppr:8:node \
     singularity exec --env CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7" \
     --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-kripke-gpu_azure-hpc-gpu-ubuntu2204.sif kripke \
    --arch CUDA --layout GDZ --dset 8 --zones 64,64,64 --gset 16 --groups 64 \
    --niter 50 --legendre 8 --quad 8 --procs 4,2,2
echo "End time:" $( date +%s )
