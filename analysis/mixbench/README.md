# Mixbench Analysis

Mixbench can be run in a few ways:

- one sample per node
- across nodes
- wrapper or without wrappe

and we first need to catalog how each was done.

## Catalog

I'll group these based on similarity. Note that the setting of the attribute of the study id is removed for easier readability.

### 5x on 2 nodes, no wrapper mixbench-cpu 32

- aws eks CPU
- google compute-engine CPU

#### aws eks CPU

> run 5x on 2 nodes without wrapper, mixbench-cpu 32

```bash
# Size 32 was run 5x on 2 nodes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run -l -N2 mixbench-cpu 32
done

# Size 64-256 were run 5x on each node (nodes was the variable here)
for i in $(seq 1 5); do     
    for node in $(seq 0 $nodes); do
      flux submit --requires="hosts:flux-sample-$node" --env OMP_NUM_THREADS=96 -l -N1 -n 1 mixbench-cpu 32
  done
done

# Size 256, also had a run on all nodes
for i in $(seq 2 5); do     
    flux run --env OMP_NUM_THREADS=96 -l -N256 mixbench-cpu 32
done
```

#### google compute-engine CPU

```console
# 5x each of this for sizes 32,64,128,256
time flux run -l -N2 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-mixbench_cpu.sif mixbench-cpu 32
```

### mixbench-cuda (no wrapper) 32 across all nodes

- google compute-engine GPU

#### google compute-engine GPU

```console
time flux run -N4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-mixbench_google-gpu.sif mixbench-cuda 32
time flux run -o gpu-affinity=per-task -o cpu-affinity=per-task -N8 -n 64 -g 1 singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-mixbench_google-gpu.sif mixbench-cuda 32
time flux run -N16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-mixbench_google-gpu.sif mixbench-cuda 32
time flux run -N32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-mixbench_google-gpu.sif mixbench-cuda 32
```

### no wrapper (mixbench-cpu 32) each single node

- google gke CPU: run 5x on each single node with mixbench-cpu 32
- azure aks CPU: run 5x without wrapper, mixbench-cpu 32 each single node
- azure cyclecloud CPU: run once without wrapper mixbench-cpu 32 on each node

#### google gke CPU

```console
# 5x across each node for sizes 32,64,128,256
for i in $(seq 1 5); do     
    for node in $(seq 0 $nodes); do
      flux submit --requires="hosts:flux-sample-$node" --env OMP_NUM_THREADS=56 -l -N1 -n 1 mixbench-cpu 32
   done
done
```

#### azure aks CPU

This has a different pattern depending on the size

```console
# 5x across 2 nodes for size 32
time flux run -l -N2 -n 192 mixbench-cpu 32

# 5x across each node for size 64,128,256
for i in $(seq 1 5); do     
    for node in $(seq 0 $nodes); do
      flux submit --requires="hosts:flux-sample-$node" --env OMP_NUM_THREADS=96 -l -N1 -n 1 mixbench-cpu 32
   done
done
```

#### azure cyclecloud CPU

```console
/usr/bin/time -p mpirun -N 1 --map-by ppr:1:node --cpus-per-proc 96 -x UCX_POSIX_USE_PROC_LINK=n \
					/shared/bin/singularity exec --env OMP_NUM_THREADS=96 --env OMP_NUM_THREADS=3 --env UCX_TLS=ud,shm,rc --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
					/shared/containers/metric-mixbench_azure-hpc.sif \
					mixbench-cpu 32
```

### wrapper 32 across all nodes**

- azure aks GPU: run 5x across all nodes with wrapper 32 and GPU
- azure cyclecloud GPU: run across nodes with wrapper 32
- google gke GPU: run across all nodes with wrapper 32

#### azure aks GPU

```console
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N4 -n 32 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N8 -n 64 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N16 -n 128 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N32 -n 256 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
```

#### azure cyclecloud GPU

There are a [lot of configs here](https://github.com/converged-computing/performance-study/tree/main/experiments/azure/cyclecloud/gpu/experiment/configs/mixbench) and (I think) the size 1 and 2 were for testing, and the others were run?

```console
# size 4
/usr/bin/time -p mpirun -n 4 -x UCX_POSIX_USE_PROC_LINK=n --map-by ppr:1:node \
    singularity exec --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-mixbench_azure-hpc-gpu-ubuntu2204.sif /opt/mixbench/mixbench-cuda/wrapper 32
# size 8
/usr/bin/time -p mpirun -n 8 -x UCX_POSIX_USE_PROC_LINK=n --map-by ppr:1:node \
    singularity exec --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-mixbench_azure-hpc-gpu-ubuntu2204.sif /opt/mixbench/mixbench-cuda/wrapper 32    
# size 16
/usr/bin/time -p mpirun -n 16 -x UCX_POSIX_USE_PROC_LINK=n --map-by ppr:1:node \
    singularity exec --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-mixbench_azure-hpc-gpu-ubuntu2204.sif /opt/mixbench/mixbench-cuda/wrapper 32 
# size 32
/usr/bin/time -p mpirun -n 32 -x UCX_POSIX_USE_PROC_LINK=n --map-by ppr:1:node \
    singularity exec --env UCX_TLS=ud_x,rc_mlx5,cma --env UCX_UNIFIED_MODE=y --env UCX_NET_DEVICES=mlx5_ib0:1 --env OPAL_PREFIX= \
    /shared/containers/metric-mixbench_azure-hpc-gpu-ubuntu2204.sif /opt/mixbench/mixbench-cuda/wrapper 32
```

#### google gke GPU

```console
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N4 -n 32 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N8 -n 64 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N16 -n 128 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N32 -n 256 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
```

### wrapper 32 on each single node

- aws eks GPU: run once with wrapper 32 on each individual node
- aws parallel-cluster CPU: run once with wrapper 32 on each node

#### aws eks GPU

```console
# Size didn't matter here - run once on each of 16 nodes.
for i in $(seq 1 5); do     
    for node in $(seq 0 $nodes); do
      flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --requires="hosts:flux-sample-$node" -N1 -n 1 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
  done
done
```

#### aws parallel-cluster CPU

```console
# only this one script
/usr/bin/time -p mpirun -N 1 --map-by ppr:1:node \
	/shared/bin/singularity exec /shared/containers/metric-mixbench_libfabric-cpu.sif \
	mixbench-cpu 32
```

I don't know if it's possible to derive anything meaningful, comparison wise, from the above. I think the wrapper turned out to be problematic too because it wouldn't hit all GPU, which is why I used mixbench-cuda directly when I saw that on Google Compute Engine.
