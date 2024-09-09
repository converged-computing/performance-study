# Debugging

This is looking at running the osu all_reduce benchmark with flux (as the flux user) and with Singularity.
I did this in two ways:

- `strace -f`
- `strace -f -s 128`

And from the outside and within the container.

## Traces

### [flux-singularity-trace-f.txt](flux-singularity-trace-f.txt)

```bash
strace -f flux run -opmi=pmix --env OMPI_COMM_WORLD_LOCAL_RANK=0 -N 1 -n 8 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task   singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-osu-gpu_google-gpu.sif    /bin/bash -c "/opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H" 2> flux-singularity-trace-f.txt
```

### [flux-singularity-trace-s-f.txt](flux-singularity-trace-s-f.txt)

```bash
strace -f -s 128 flux run -opmi=pmix --env OMPI_COMM_WORLD_LOCAL_RANK=0 -N 1 -n 8 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task   singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-osu-gpu_google-gpu.sif    /bin/bash -c "/opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H" 2> flux-singularity-trace-s-f.txt
```

### [flux-singularity-inside-container-trace-f.txt](flux-singularity-inside-container-trace-f.txt)

```bash
flux run -opmi=pmix --env OMPI_COMM_WORLD_LOCAL_RANK=0 -N 1 -n 8 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task   singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-osu-gpu_google-gpu.sif    /bin/bash -c "strace -f /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H" 2> flux-singularity-inside-container-trace-f.txt
```

### [flux-singularity-inside-container-trace-s-f.txt](flux-singularity-inside-container-trace-s-f.txt)

```bash
flux run -opmi=pmix --env OMPI_COMM_WORLD_LOCAL_RANK=0 -N 1 -n 8 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task   singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-osu-gpu_google-gpu.sif    /bin/bash -c "strace -f -s 128 /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H" 2> flux-singularity-inside-container-trace-s-f.txt
```
