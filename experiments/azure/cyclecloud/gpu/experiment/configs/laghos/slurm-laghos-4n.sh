#!/bin/sh

#SBATCH --job-name=laghos-4n
#SBATCH --nodes=4
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

export CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7"
echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 4 --map-by ppr:8:node -x UCX_POSIX_USE_PROC_LINK=n \
	singularity exec --nv --env UCX_TLS=all --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
        --env CUDA_VISIBLE_DEVICES="0,1,2,3,4,5,6,7" \
        /shared/containers/metric-laghos_azure-hpc-gpu-ubuntu2204.sif /opt/laghos/laghos \
        -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 20 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda
echo "End time:" $( date +%s )