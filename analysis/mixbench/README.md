# Mixbench Analysis

Mixbench can be run in a few ways:

- one sample per node
- across nodes
- wrapper or without wrapper

and we first needed to [catalog](#catalog) how each was done. It's still not clear how to parse CPU results.

## Results

These are easier to share as written content (I didn't know a good way to plot) so I'll do that.

### GPU

What I did in the parsing script is to:

1. parse the high level metrics for each GPU in each environment
2. Within an environment, calculate the percentage of GPUs that have some metric set to a value
3. Go through each, and print if either everything is the same or different.

Results are below.

#### Metrics that are the same

```console
gpu for cuda_driver_version are all the same, [12.4]
gpu for gpu_clock_rate_mhz are all the same, [1530]
gpu for memory_clock_rate_mhz are all the same, [438]
gpu for memory_bus_width_bits are all the same, [4096]
gpu for warpsize are all the same, [32]
gpu for l2_cache_size_kb are all the same, [6144]
gpu for compute_capability are all the same, [7.0]
gpu for total_sps are all the same, [5120.0]
gpu for compute_throughput_gflops are all the same, [15667.2]
gpu for memory_bandwidth_gb_per_sec are all the same, [898.05]
gpu for buffer_size_mb are all the same, [256]
gpu for trade-off_type are all the same, ['compute with global memory (block strided)']
gpu for elements_per_thread are all the same, [8]
gpu for thread_fusion_degree are all the same, [4]
```

#### Metrics that are different

##### total_memory

This was expected - we see that the Google GPUs have half the memory. We also see that the CycleCloud and AWS GPUs both have (roughly) the same, but they are slightly different.

```console
gpu for total_memory have differences,                     experiment env_type nodes        metric        value percentage
0               google/gke/gpu      gpu    32  total_memory  16928342016        1.0
18              google/gke/gpu      gpu     8  total_memory  16928342016        1.0
36              google/gke/gpu      gpu    16  total_memory  16928342016        1.0
54              google/gke/gpu      gpu     4  total_memory  16928342016        1.0
72   google/compute-engine/gpu      gpu    32  total_memory  16928342016        1.0
90   google/compute-engine/gpu      gpu     8  total_memory  16928342016        1.0
108  google/compute-engine/gpu      gpu    16  total_memory  16928342016        1.0
126  google/compute-engine/gpu      gpu     4  total_memory  16928342016        1.0
144                aws/eks/gpu      gpu     8  total_memory  34079899648        1.0
162                aws/eks/gpu      gpu    16  total_memory  34079899648        1.0
180                aws/eks/gpu      gpu     4  total_memory  34079899648        1.0
198       azure/cyclecloud/gpu      gpu    32  total_memory  34079899648        1.0
217       azure/cyclecloud/gpu      gpu     8  total_memory  34079899648        1.0
236       azure/cyclecloud/gpu      gpu    16  total_memory  34079899648        1.0
255       azure/cyclecloud/gpu      gpu     4  total_memory  34079899648        1.0
274              azure/aks/gpu      gpu    32  total_memory  34072559616        1.0
293              azure/aks/gpu      gpu     8  total_memory  34072559616        1.0
312              azure/aks/gpu      gpu    16  total_memory  34072559616        1.0
331              azure/aks/gpu      gpu     4  total_memory  34072559616        1.0
```

##### device

This corresponds with the above, and it's the same pattern but with respect to device name.
I'm surprise that the CycleCloud and AWS are reported as the same when they are not.

```console
gpu for device have differences,                     experiment env_type nodes  metric                 value percentage
1               google/gke/gpu      gpu    32  device  Tesla V100-SXM2-16GB        1.0
19              google/gke/gpu      gpu     8  device  Tesla V100-SXM2-16GB        1.0
37              google/gke/gpu      gpu    16  device  Tesla V100-SXM2-16GB        1.0
55              google/gke/gpu      gpu     4  device  Tesla V100-SXM2-16GB        1.0
73   google/compute-engine/gpu      gpu    32  device  Tesla V100-SXM2-16GB        1.0
91   google/compute-engine/gpu      gpu     8  device  Tesla V100-SXM2-16GB        1.0
109  google/compute-engine/gpu      gpu    16  device  Tesla V100-SXM2-16GB        1.0
127  google/compute-engine/gpu      gpu     4  device  Tesla V100-SXM2-16GB        1.0
145                aws/eks/gpu      gpu     8  device  Tesla V100-SXM2-32GB        1.0
163                aws/eks/gpu      gpu    16  device  Tesla V100-SXM2-32GB        1.0
181                aws/eks/gpu      gpu     4  device  Tesla V100-SXM2-32GB        1.0
199       azure/cyclecloud/gpu      gpu    32  device  Tesla V100-SXM2-32GB        1.0
218       azure/cyclecloud/gpu      gpu     8  device  Tesla V100-SXM2-32GB        1.0
237       azure/cyclecloud/gpu      gpu    16  device  Tesla V100-SXM2-32GB        1.0
256       azure/cyclecloud/gpu      gpu     4  device  Tesla V100-SXM2-32GB        1.0
275              azure/aks/gpu      gpu    32  device  Tesla V100-SXM2-32GB        1.0
294              azure/aks/gpu      gpu     8  device  Tesla V100-SXM2-32GB        1.0
313              azure/aks/gpu      gpu    16  device  Tesla V100-SXM2-32GB        1.0
332              azure/aks/gpu      gpu     4  device  Tesla V100-SXM2-32GB        1.0
```

##### total_global_mem_mb

This is another view of total memory.

```console
gpu for total_global_mem_mb have differences,                     experiment env_type nodes               metric  value percentage
8               google/gke/gpu      gpu    32  total_global_mem_mb  16144        1.0
26              google/gke/gpu      gpu     8  total_global_mem_mb  16144        1.0
44              google/gke/gpu      gpu    16  total_global_mem_mb  16144        1.0
62              google/gke/gpu      gpu     4  total_global_mem_mb  16144        1.0
80   google/compute-engine/gpu      gpu    32  total_global_mem_mb  16144        1.0
98   google/compute-engine/gpu      gpu     8  total_global_mem_mb  16144        1.0
116  google/compute-engine/gpu      gpu    16  total_global_mem_mb  16144        1.0
134  google/compute-engine/gpu      gpu     4  total_global_mem_mb  16144        1.0
152                aws/eks/gpu      gpu     8  total_global_mem_mb  32501        1.0
170                aws/eks/gpu      gpu    16  total_global_mem_mb  32501        1.0
188                aws/eks/gpu      gpu     4  total_global_mem_mb  32501        1.0
206       azure/cyclecloud/gpu      gpu    32  total_global_mem_mb  32501        1.0
225       azure/cyclecloud/gpu      gpu     8  total_global_mem_mb  32501        1.0
244       azure/cyclecloud/gpu      gpu    16  total_global_mem_mb  32501        1.0
263       azure/cyclecloud/gpu      gpu     4  total_global_mem_mb  32501        1.0
282              azure/aks/gpu      gpu    32  total_global_mem_mb  32494        1.0
301              azure/aks/gpu      gpu     8  total_global_mem_mb  32494        1.0
320              azure/aks/gpu      gpu    16  total_global_mem_mb  32494        1.0
339              azure/aks/gpu      gpu     4  total_global_mem_mb  32494        1.0
```

##### total_global_mem_mb

This was interesting, because there is a setting on the GPU for error correction. This was also detected as different in the original parsing:

```console
WARNING azure/aks/gpu/size32 has GPUs that are different for ECC enabled: {'Yes': 1472, 'No': 576}
```

I read about it [here](https://support.chaos.com/hc/en-us/articles/24886637113617-ECC-State-for-Nvidia-GPUs-Error-Correcting-Code) - ECC is "[Error Correcting Code](https://en.wikipedia.org/wiki/ECC_memory)" From the post:

> On GPUs it is a feature that uses extra memory bits to store error information, for certain use cases if an error of particular severity occurs it can either be detected and/or corrected. ECC is not useful for GPU rendering, we recommend turning it off for all your GPUs as it degrades performance. In our tests, turning on ECC reduced performance by 15% on the RTX 4090 and Tesla A40 GPUs while making no difference in GPU rendering.

We can see the breakdown here - Azure has a mixture (those are percentages) of nodes with enabled vs. disabled.

```console
gpu for ecc_enabled have differences,                     experiment env_type nodes       metric value percentage
9               google/gke/gpu      gpu    32  ecc_enabled   Yes        1.0
27              google/gke/gpu      gpu     8  ecc_enabled   Yes        1.0
45              google/gke/gpu      gpu    16  ecc_enabled   Yes        1.0
63              google/gke/gpu      gpu     4  ecc_enabled   Yes        1.0
81   google/compute-engine/gpu      gpu    32  ecc_enabled   Yes        1.0
99   google/compute-engine/gpu      gpu     8  ecc_enabled   Yes        1.0
117  google/compute-engine/gpu      gpu    16  ecc_enabled   Yes        1.0
135  google/compute-engine/gpu      gpu     4  ecc_enabled   Yes        1.0
153                aws/eks/gpu      gpu     8  ecc_enabled   Yes        1.0
171                aws/eks/gpu      gpu    16  ecc_enabled   Yes        1.0
189                aws/eks/gpu      gpu     4  ecc_enabled   Yes        1.0
207       azure/cyclecloud/gpu      gpu    32  ecc_enabled   Yes       0.75
208       azure/cyclecloud/gpu      gpu    32  ecc_enabled    No       0.25
226       azure/cyclecloud/gpu      gpu     8  ecc_enabled    No      0.425
227       azure/cyclecloud/gpu      gpu     8  ecc_enabled   Yes      0.575
245       azure/cyclecloud/gpu      gpu    16  ecc_enabled   Yes      0.625
246       azure/cyclecloud/gpu      gpu    16  ecc_enabled    No      0.375
264       azure/cyclecloud/gpu      gpu     4  ecc_enabled   Yes        0.5
265       azure/cyclecloud/gpu      gpu     4  ecc_enabled    No        0.5
283              azure/aks/gpu      gpu    32  ecc_enabled   Yes    0.71875
284              azure/aks/gpu      gpu    32  ecc_enabled    No    0.28125
302              azure/aks/gpu      gpu     8  ecc_enabled   Yes      0.875
303              azure/aks/gpu      gpu     8  ecc_enabled    No      0.125
321              azure/aks/gpu      gpu    16  ecc_enabled   Yes     0.6875
322              azure/aks/gpu      gpu    16  ecc_enabled    No     0.3125
340              azure/aks/gpu      gpu     4  ecc_enabled   Yes        1.0
```

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


