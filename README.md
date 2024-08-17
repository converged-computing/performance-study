# Performance Study

This study will test HPC application performance across three clouds. The repository is organized as follows:

- [docker](docker): includes container builds for different environments. Containers are shared between environments when possible to reduce redundancy.
  - [google](docker/google): includes Google builds for each of CPU an GPU
  - [aws](docker/aws): includes AWS builds for each of CPU and GPU. The distinguishing feature is building with libfabric for EFA.

- [experiments](experiments): are organized first by cloud, and then the underlying environment. In each, a README with the full experiment protocol (and usually commands to run) are included.
 - [Google Cloud](experiments/google) includes HPC Toolkit (Compute Engine), and GKE (Kubernetes) for each of CPU and GPU
 - [Amazon Web Services](experiments/aws) includes Parallel Cluster (EC2), and EKS (KUbernetes) for each of CPU and GPU
 - [Microsoft Azure](experiments/azure) includes CycleCloud (VMs), and AKS (Kubernetes) for each of CPU and GPU.

## Timing

This is a checklist for the setups we have tested and timed:

### Tested

Tested means we have verified that things run on a small set of resources (e.g., 2 nodes). We can proceed to timing when all issues have been addressed for each.

- [ ] Microsoft Azure CycleCloud CPU (date)
- [ ] Microsoft Azure CycleCloud GPU (date)
- [ ] Microsoft Azure AKS GPU (date)
- [x] [Microsoft Azure AKS CPU (8/16/2024)](experiments/azure/aks/cpu) Issues addressed? (no)
- [ ] Google Cloud HPC Toolkit GPU (date)
- [ ] Google Cloud HPC Toolkit CPU (date)
- [ ] Google Cloud GKE GPU (date)
- [ ] Google Cloud GKE CPU (date)
- [ ] AWS GPU Parallel Cluster (date)
- [ ] AWS CPU Parallel Cluster (date)
- [x] [AWS GPU EKS (8/16/2024)](experiments/aws/eks/cpu) Issues addressed? (no)
- [ ] AWS CPU EKS (date)

### Timed

- [ ] Microsoft Azure CycleCloud CPU (date)
- [ ] Microsoft Azure CycleCloud GPU (date)
- [ ] Microsoft Azure AKS GPU (date)
- [ ] Microsoft Azure AKS CPU (date)
- [ ] Google Cloud HPC Toolkit GPU (date)
- [ ] Google Cloud HPC Toolkit CPU (date)
- [ ] Google Cloud GKE GPU (date)
- [ ] Google Cloud GKE CPU (date)
- [ ] AWS GPU Parallel Cluster (date)
- [ ] AWS CPU Parallel Cluster (date)
- [ ] AWS GPU EKS (date)
- [ ] AWS CPU EKS (date)

## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](https://github.com/converged-computing/cloud-select/blob/main/LICENSE),
[COPYRIGHT](https://github.com/converged-computing/cloud-select/blob/main/COPYRIGHT), and
[NOTICE](https://github.com/converged-computing/cloud-select/blob/main/NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614
