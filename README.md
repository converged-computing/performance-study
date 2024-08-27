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

#### Experiments

- [ ] Microsoft Azure CycleCloud CPU (date)
- [ ] Microsoft Azure CycleCloud GPU (date)
- [ ] Google Cloud HPC Toolkit GPU (date)
- [ ] Google Cloud Compute Engine CPU
  - [x] size 32 (done 8/26/2024)
  - [x] size 64 (done 8/26/2024)
  - [ ] size 128
  - [ ] size 256
- [ ] AWS GPU Parallel Cluster (date)
- [ ] AWS CPU Parallel Cluster (date)
- [ ] Microsoft Azure AKS CPU
  - [x] size 32 (done 8/24/2024)
  - [x] size 64 (done 8/24/2024)
  - [ ] size 128
  - [ ] size 256
- [ ] Google Cloud GKE CPU
  - [x] size 32 (done 8/21/2024)
  - [x] size 64 (done 8/22/2024)
  - [x] size 128 (done 8/23/2024)
  - [x] size 256 (done 8/23/2024)
- [ ] AWS CPU EKS
  - [x] size 32 (done 8/21/2024-8/22/2024)
  - [x] size 64  (done 8/22/2024) 
  - [x] size 128 (done 8/22/2024) 
  - [ ] size 256 (needs [debugging](https://repost.aws/knowledge-center/eks-cni-plugin-troubleshooting))
- [ ] Microsoft Azure AKS GPU
- [ ] Google Cloud GKE GPU
- [ ] AWS GPU EKS
  - [x] size 4 (partial done 8/26/2024, missing lammps, osu, resnet, quicksilver, laghos) did not work
  - [x] size 8 (partial done 8/26/2024, missing lammps, osu, resnet, quicksilver, laghos) did not work
  - [ ] size 16 allocation not possible

For the above, the Azure setups are problematic - the Infiniband does not seem to be effectively combining across many nodes.

## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](https://github.com/converged-computing/cloud-select/blob/main/LICENSE),
[COPYRIGHT](https://github.com/converged-computing/cloud-select/blob/main/COPYRIGHT), and
[NOTICE](https://github.com/converged-computing/cloud-select/blob/main/NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614
