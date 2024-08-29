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

## Experiments

### "Bare Metal"

- [ ] Microsoft Azure CycleCloud CPU (date)
  - [x] size 32 (abhik done 6 apps 8/28/2024)
  - [x] size 64 (abhik done 6 apps 8/28/2024)
  - [ ] size 128 (TBA)
  - [ ] size 256 (TBA)
- [ ] Microsoft Azure CycleCloud GPU (date)
  - [ ] size 32 (TBA)
  - [ ] size 64 (TBA)
  - [ ] size 128 (TBA)
  - [ ] size 256 (TBA)
- [ ] AWS GPU Parallel Cluster (date)
   - Not going to do, cannot build image
- [ ] AWS CPU Parallel Cluster (date)
  - [ ] size 32 (TBA)
  - [ ] size 64 (TBA)
  - [ ] size 128 (TBA)
  - [ ] size 256 (TBA)
- [x] Google Cloud Compute Engine CPU
  - [x] size 32 (vsoch done 8/26/2024)
  - [x] size 64 (vsoch done 8/26/2024)
  - [x] size 128 (vsoch done 8/27/2024)
  - [x] size 256 (vsoch done 8/27/2024)
- [ ] Google Compute Engine GPU (TBA 8/26/2024)
  - New VM and automation needed with Terraform 
  - [ ] size 4 (vsoch TBA 8/31/2024)
  - [ ] size 8 (vsoch TBA 8/31/2024)
  - [ ] size 16 (vsoch TBA 8/31/2024)
  - [ ] size 32 (vsoch TBA 8/31/2024)

### Kubernetes

- [ ] Microsoft Azure AKS CPU
  - [x] size 32 (vsoch done 8/24/2024), redone with placement (vsoch 8/28/2024)
  - [x] size 64 (vsoch done 8/24/2024), redone with placement (vsoch 8/28/2024)
  - [x] size 128 (vsoch done 8/28/2024)
  - [ ] size 256 (vsoch TBA 8/29/2024)
- [x] Google Cloud GKE CPU
  - [x] size 32 (vsoch done 8/21/2024)
  - [x] size 64 (vsoch done 8/22/2024)
  - [x] size 128 (vsoch done 8/23/2024)
  - [x] size 256 (vsoch done 8/23/2024)
- [x] AWS CPU EKS
  - [x] size 32 (vsoch done 8/21/2024-8/22/2024)
  - [x] size 64  (vsoch done 8/22/2024) 
  - [x] size 128 (vsoch done 8/22/2024) 
  - [ ] size 256 (needs [debugging](https://repost.aws/knowledge-center/eks-cni-plugin-troubleshooting) but unlikely, flagging as done)
- [x] AWS GPU EKS
  - [x] size 4 (partial done 8/26/2024, missing resnet, quicksilver, laghos) did not work
  - [x] size 8 (partial done 8/26/2024, missing resnet, quicksilver, laghos) did not work
  - [x] size 16 (partial done 8/26/2024, missing resnet, quicksilver, laghos) did not work
- [ ] Google Cloud GKE GPU
  - [ ] size 4 (vsoch TBA 8/29/2024)
  - [ ] size 8 (vsoch TBA 8/29/2024)
  - [ ] size 16 (vsoch TBA 8/29/2024)
  - [ ] size 32 (vsoch TBA 8/29/2024)
- [ ] Microsoft Azure AKS GPU
  - [ ] size 4 (vsoch TBA 8/30/2024)
  - [ ] size 8 (vsoch TBA 8/30/2024)
  - [ ] size 16 (vsoch TBA 8/30/2024)
  - [ ] size 32 (vsoch TBA 8/30/2024)

## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](https://github.com/converged-computing/cloud-select/blob/main/LICENSE),
[COPYRIGHT](https://github.com/converged-computing/cloud-select/blob/main/COPYRIGHT), and
[NOTICE](https://github.com/converged-computing/cloud-select/blob/main/NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614
