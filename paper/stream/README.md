# Stream Paper Analysis

We are wanting to group data in the following way. Let's sanity check commands to validate that.
Note that I'm removing extra submit flags to just show resources and primary stuff. These are medians,
and they were printed in a different order and I organized them.

```
CPU for Copy size 64 experiment google/gke/cpu: 7652.2: std 2650.5119017203856
CPU for Copy size 64 experiment google/compute-engine/cpu: 4235.7: std 2022.5997565734058
CPU for Copy size 64 experiment aws/eks/cpu: 3840.0: std 421.83444927017104
CPU for Copy size 64 experiment azure/aks/cpu: 4010.6499999999996: std 570.8951663998799
CPU for Copy size 32 experiment aws/parallel-cluster/cpu: 38082.45: std 480.16554855745824
CPU for Copy size 32 experiment azure/cyclecloud/cpu: 48513.6: std 366.9498240430622

CPU for Scale size 64 experiment google/gke/cpu: 4815.4: std 1862.2623529244706
CPU for Scale size 64 experiment google/compute-engine/cpu: 4626.45: std 1912.485849686873
CPU for Scale size 64 experiment aws/eks/cpu: 2668.1: std 459.90621362490066
CPU for Scale size 64 experiment azure/aks/cpu: 2264.1: std 399.0602222397505
CPU for Scale size 32 experiment aws/parallel-cluster/cpu: 26240.050000000003: std 614.650544488683
CPU for Scale size 32 experiment azure/cyclecloud/cpu: 38049.0: std 918.7562970906649

CPU for Add size 64 experiment google/gke/cpu: 5626.799999999999: std 2282.6288006857276
CPU for Add size 64 experiment google/compute-engine/cpu: 5265.4: std 2250.778995919312
CPU for Add size 64 experiment aws/eks/cpu: 2822.4: std 549.9957806314385
CPU for Add size 64 experiment azure/aks/cpu: 2448.2: std 476.11369413747786
CPU for Add size 32 experiment aws/parallel-cluster/cpu: 30017.4: std 834.1587939428016
CPU for Add size 32 experiment azure/cyclecloud/cpu: 41537.2: std 302.48844264853756

CPU for Triad size 64 experiment google/gke/cpu: 6800.9: std 2402.2923925913333
CPU for Triad size 64 experiment google/compute-engine/cpu: 6239.35: std 2326.0915394353747
CPU for Triad size 64 experiment aws/eks/cpu: 3013.25: std 880.3020352757017
CPU for Triad size 64 experiment azure/aks/cpu: 2579.5: std 907.5778246577137

# These were run differently
CPU for Triad size 32 experiment aws/parallel-cluster/cpu: 30399.0: std 1094.7181338676867
CPU for Triad size 32 experiment azure/cyclecloud/cpu: 44102.2: std 473.60566782884825
```

```console
GPU for Triad size 32 for gpu and google/gke/gpu has median 782.9089 std 0.7215141688047312
GPU for Triad size 32 for gpu and google/compute-engine/gpu has median 783.2988 std 0.7281968467033578
GPU for Triad size 32 for gpu and on-premises/lassen/gpu has median 782.5194 std 0.9604636951745984
GPU for Triad size 32 for gpu and azure/cyclecloud/gpu has median 331.7054 std 221.8607557368494
GPU for Triad size 32 for gpu and azure/aks/gpu has median 748.5373 std 4.628462181451039
```

For the GPU Triad we report results from the largest size cluster, 32 nodes, for GB/s. We found comparable results across sizes for \gls*{gke} (Mdn 782.91, SD 0.72), Compute Engine (Mdn 783.3 SD 0.73), \gls*{aks} (Mdn 748.54 SD 4.63), and on-premises \emph{B} (Mdn 782.52 SD 0.96), and Azure CycleCloud presented with a large range of variation (Mdn 748.54 SD 4.63).


## 1.a Runs across all nodes (GPU)

```bash
# Lassen cuda-stream
time -p srun -N ${nnodes} -n ${nnodes} /p/vast1/convcomp/crosspform/benchmarks/GPU/cuda-stream/stream

# Azure CycleCloud GPU
mpirun -n 128 --map-by ppr:8:node singularity exec --nv metric-stream_azure-hpc-ubuntu2204.sif usr/local/bin/stream

# Azure AKS
flux run -N32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task stream

# Google Compute Engine GPU
# My notes confirm I saw using all GPU, and results were almost instant
flux run -N32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-stream_google-gpu.sif stream 

# GKE GPU
flux run -N4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task stream
```

## 1.b Runs across all nodes (CPU)

```bash
# Dane stream
time -p srun -N ${nnodes} -n ${nnodes} /p/vast1/convcomp/crosspform/benchmarks/CPU/STREAM/stream.omp.AVX2.80M.20x.icx

# EKS CPU (we also have for single nodes)
flux run -N256 -o cpu-affinity=per-task stream_c.exe
```

## 2.a Runs on single nodes (GPU)

EKS is the only GPU run on a single node - I suspect we ran it this way and changed out mind later (and could not redo it). I don't think we can use this data anywhere.

```bash   
# AWS EKS GPU
# submit to just one node, confirmed this binary is from cuda-stream
flux submit -N1 -n 8 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task stream 
```

## 2.b Runs on single nodes (CPU)

Note that I don't see stream for [most sizes for aws parallel cluster](https://github.com/converged-computing/performance-study/tree/main/experiments/aws/parallel-cluster/cpu/size256/results). I only see size 32. I checked artifacts (not every untagged, but those around the similar date).

I also see that some of these used `-n 96` and others `OMP_NUM_THREADS=96`. These use OMP_NUM_THREADS:

```bash   
# Azure CycleCloud CPU
mpirun -N 1 --map-by ppr:1:node /shared/bin/singularity exec --env OMP_NUM_THREADS=96 /shared/containers/metric-stream_azure-hpc.sif stream_c.exe

# AWS Parallel Cluster CPU
# We only have data for size 32 (that I can find)
mpirun -N 1 --map-by ppr:1:node /shared/bin/singularity exec --env OMP_NUM_THREADS=96 /shared/containers/metric-stream_azure-hpc.sif stream_c.exe
```

These do not:

```bash
# AWS EKS CPU (we also have for across nodes) but it doesn't use OMP_NUM_THREADS.
flux submit -N1 -n 96 -o cpu-affinity=per-task stream_c.exe

# Azure AKS CPU
flux submit -N1 -n 96 -o cpu-affinity=per-task stream_c.exe

# Google Compute Engine CPU
flux submit -N1 -n 56 -o cpu-affinity=per-task singularity exec /opt/containers/metric-stream_rocky-8.sif stream_c.exe

# Google GKE CPU
flux submit -N1 -n 56 -o cpu-affinity=per-task stream_c.exe
```

Note that Google has a different `-n` as well (56 vs 96).


## On Premises

Note that I confirmed these (from the build directories) appear to be the same builds we used for cloud (albeit different compilers, etc.)

```bash
# Lassen cuda-stream
time -p srun -N ${nnodes} -n ${nnodes} /p/vast1/convcomp/crosspform/benchmarks/GPU/cuda-stream/stream

# Dane
time -p srun -N ${nnodes} -n ${nnodes} /p/vast1/convcomp/crosspform/benchmarks/CPU/STREAM/stream.omp.AVX2.80M.20x.icx
```

Stream is used as a single benchmark, but it looks like for GPU we tried to run across nodes. But we possibly didn't know or decide to do this until after the early EKS GPU runs.
