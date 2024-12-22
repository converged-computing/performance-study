# Stream Paper Analysis

We are wanting to group data in the following way. Let's sanity check commands to validate that.
Note that I'm removing extra submit flags to just show resources and primary stuff.

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
