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

#### HPC in a Box Options

- [ ] Microsoft Azure CycleCloud CPU (date)
- [ ] Microsoft Azure CycleCloud GPU (date)
- [ ] Google Cloud HPC Toolkit GPU (date)
- [ ] Google Cloud HPC Toolkit CPU (date)
- [ ] AWS GPU Parallel Cluster (date)
- [ ] AWS CPU Parallel Cluster (date)

#### Bare Metal Options

- [x] [Microsoft Azure VM Set (CPU) (8/18/2024)](experiments/azure/vmset/cpu)
- [x] [Google Cloud Compute Engine CPU (8/19/2024)](experiments/google/compute-engine/cpu)
- [x] [AWS CPU EC2 CPU (8/17/2024)](experiments/aws/ec2/cpu)
- [ ] Microsoft Azure VM Set (GPU) (8/18/2024)
- [ ] Google Cloud Compute Engine GPU (date)
- [ ] AWS GPU EC2 GPU (date)

- [x] [Microsoft Azure AKS CPU (8/16/2024)](experiments/azure/aks/cpu)
- [x] [Google Cloud GKE CPU (8/19/2024)](experiments/google/eks/cpu)
- [x] [AWS CPU EKS (8/16/2024)](experiments/aws/eks/cpu)
- [ ] Microsoft Azure AKS GPU (date)
- [ ] Google Cloud GKE GPU (date)
- [ ] AWS GPU EKS (8/19/2024)]

#### Experiments

- [ ] Microsoft Azure AKS CPU
  - [ ] size 32
  - [ ] size 64
  - [ ] size 128
  - [ ] size 256
- [ ] Google Cloud GKE CPU
  - [x] size 32 (done 8/21/2024)
  - [ ] size 64
  - [ ] size 128
  - [ ] size 256
- [ ] AWS CPU EKS
  - [x] size 32 (done 8/21/2024-8/22/2024)
  - [x] size 64  (done 8/22/2024)
  - [ ] size 128
  - [ ] size 256
- [ ] Microsoft Azure AKS GPU
- [ ] Google Cloud GKE GPU
- [ ] AWS GPU EKS

## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](https://github.com/converged-computing/cloud-select/blob/main/LICENSE),
[COPYRIGHT](https://github.com/converged-computing/cloud-select/blob/main/COPYRIGHT), and
[NOTICE](https://github.com/converged-computing/cloud-select/blob/main/NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614
