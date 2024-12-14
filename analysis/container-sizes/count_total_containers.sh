#!/bin/bash

# requires oras
which oras || (echo "Please install oras" && exit)

# 1+23+10+8+8+28+21+11+15+14+16+12+4+6+4+4+15+6+5+8+1
# Out[1]: 220

oras repo tags ghcr.io/converged-computing/osu-benchmark | wc -l
oras repo tags ghcr.io/converged-computing/metric-lammps-cpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-kripke-cpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-quicksilver-cpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-quicksilver-cpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-amg2023 | wc -l
oras repo tags ghcr.io/converged-computing/mt-gemm | wc -l
oras repo tags ghcr.io/converged-computing/metric-osu-cpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-mixbench | wc -l
oras repo tags ghcr.io/converged-computing/metric-minife | wc -l
oras repo tags ghcr.io/converged-computing/metric-stream | wc -l
oras repo tags ghcr.io/converged-computing/metric-lammps-gpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-kripke-gpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-magma | wc -l
oras repo tags ghcr.io/converged-computing/metric-osu-gpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-quicksilver-gpu | wc -l
oras repo tags ghcr.io/converged-computing/metric-nek5000 | wc -l
oras repo tags ghcr.io/converged-computing/multi-gpu-models | wc -l
oras repo tags ghcr.io/converged-computing/metric-linpack-cpu | wc -l
oras repo tags ghcr.io/converged-computing/azurehpc | wc -l
oras repo tags ghcr.io/converged-computing/metrics-quicksilver-cpu | wc -l
