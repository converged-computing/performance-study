#!/bin/sh

#SBATCH --job-name=laghos-256n
#SBATCH --nodes=256
#SBATCH --time=0:20:00
#SBATCH --exclusive

. /etc/profile.d/modules.sh
module unload mpi
module load mpi/hpcx-pmix-2.18

echo "Start time:" $( date +%s )
/usr/bin/time -p mpirun -N 256 --map-by ppr:96:node -x UCX_POSIX_USE_PROC_LINK=n \
	singularity exec --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
        /shared/containers/metric-laghos_azure-hpc.sif /opt/laghos/laghos \
        -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
echo "End time:" $( date +%s )