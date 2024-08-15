# Docker Containers

## Data

These containers require data:

- linpack
- laghos
- lammps
- nek5000
- quicksilver
- resnet

## GPU

### Google Cloud

Since we need to vary builds across clouds, let's keep track of that here. These only include the ones we are intending to run.

| Container                                                      | Cloud     | GPU | Dockerfile                          | Notes             |
|----------------------------------------------------------------|-----------|-----|------------------------------------|--------------------|
| ghcr.io/converged-computing/metric-amg:gpu-zen4                | Google    | yes |[Dockerfile](docker/google/gpu/amg) |  |
| ghcr.io/converged-computing/metric-amg2023:spack-slim | Google | yes |[Dockerfile](docker/google/gpu/amg2023) | Using slim variant |
| ghcr.io/converged-computing/metric-laghos:gpu-zen4             | Google    | yes |[Dockerfile](docker/google/gpu/laghos)  | Needs to be built on large machine  |
| ghcr.io/converged-computing/metric-single-node:cpu-zen4 | Google | no |[Dockerfile](docker/google/cpu/single-node) | |  
| ghcr.io/converged-computing/metric-kripke-gpu:latest           | Google    | yes |[Dockerfile](docker/google/gpu/kripke)  | |
| ghcr.io/converged-computing/metric-lammps-gpu:kokkos           | Google    | yes |[Dockerfile](docker/google/gpu/lammps)  | using Kokkos build |
| ghcr.io/converged-computing/metric-magma                       | Google    | yes |[Dockerfile](docker/google/gpu/magma)   |  |
| ghcr.io/converged-computing/metric-minife:latest               | Google    | yes |[Dockerfile](docker/google/gpu/minife)  | | 
| ghcr.io/converged-computing/metric-mixbench:latest             | Google    | yes |[Dockerfile](docker/google/gpu/mixbench)| |
| ghcr.io/converged-computing/mt-gemm:latest                     | Google    | yes |[Dockerfile](docker/google/gpu/mt-gemm-base)| |
| ghcr.io/converged-computing/multi-gpu-models:flux-gpu          | Google    | yes |[Dockerfile](docker/google/gpu/multi-gpu-models)| |
| ghcr.io/converged-computing/metric-nek5000:latest              | Google    | yes |[Dockerfile](docker/google/gpu/nek5000) | |
| ghcr.io/converged-computing/metric-osu-gpu:latest              | Google    | yes |[Dockerfile](docker/google/gpu/osu) | |
| ghcr.io/converged-computing/metric-quicksilver-gpu:latest      | Google    | yes |[Dockerfile](docker/google/gpu/quicksilver) | |
| ghcr.io/converged-computing/pytorch-resnet-experiment:gpu      | Google    | yes |[Dockerfile](docker/google/gpu/resnet) | |
| ghcr.io/converged-computing/metric-stream:zen4                 | Google    | yes |[Dockerfile](docker/google/gpu/stream) | | 

### Amazon Web Services

| Container                                                      | Cloud     | GPU | Dockerfile                          | Notes             |
|----------------------------------------------------------------|-----------|-----|------------------------------------|--------------------|
| ghcr.io/converged-computing/metric-amg:libfabric-gpu-zen4      | AWS       | yes  |[Dockerfile](docker/aws/gpu/amg) |  |
| ghcr.io/converged-computing/metric-amg2023:spack-slim | AWS    | yes |[Dockerfile](docker/google/gpu/amg2023) | Same as Google, already has libfabric |
| ghcr.io/converged-computing/metric-laghos:libfabric-gpu-zen4   | yes |[Dockerfile](docker/aws/gpu/laghos)  | Needs to be built on large machine |
| ghcr.io/converged-computing/metric-single-node:cpu-zen4 | AWS | no |[Dockerfile](docker/google/cpu/single-node) | |  
| ghcr.io/converged-computing/metric-lammps-gpu:libfabric   | AWS | yes |[Dockerfile](docker/aws/gpu/lammps) | |
| ghcr.io/converged-computing/metric-kripke-gpu:libfabric   | AWS | yes |[Dockerfile](docker/aws/gpu/kripke)  | |
| ghcr.io/converged-computing/metric-magma:libfabric        | AWS | yes |[Dockerfile](docker/aws/gpu/magma)   |  |
| ghcr.io/converged-computing/metric-minife:libfabric       | AWS | yes |[Dockerfile](docker/aws/gpu/minife)  | | 
| ghcr.io/converged-computing/metric-mixbench:libfabric     | AWS | yes |[Dockerfile](docker/aws/gpu/mixbench)| |
| ghcr.io/converged-computing/mt-gemm:libfabric             | AWS | yes |[Dockerfile](docker/aws/gpu/mt-gemm-base)| |
| ghcr.io/converged-computing/multi-gpu-models:libfabric    | AWS | yes |[Dockerfile](docker/aws/gpu/multi-gpu-models)| |
| ghcr.io/converged-computing/metric-nek5000:libfabric      | AWS | yes |[Dockerfile](docker/aws/gpu/nek5000) | |
| ghcr.io/converged-computing/metric-osu-gpu:libfabric      | AWS | yes |[Dockerfile](docker/aws/gpu/osu) | |
| ghcr.io/converged-computing/metric-quicksilver-gpu:libfabric| AWS | yes |[Dockerfile](docker/aws/gpu/quicksilver) | |
| ghcr.io/converged-computing/pytorch-resnet-experiment:libfabric-gpu | AWS   | yes |[Dockerfile](docker/aws/gpu/resnet) | |
| ghcr.io/converged-computing/metric-stream:libfabric-zen4       | AWS  | yes | [Dockerfile](docker/aws/gpu/stream) | |

## CPU

### Azure

| Container                                                      | Cloud     | GPU | Dockerfile                          | Notes             |
|----------------------------------------------------------------|-----------|-----|------------------------------------|--------------------|
| ghcr.io/converged-computing/metric-lammps-cpu:ucx                  | Azure  | no |[Dockerfile](docker/azure/cpu/lammps) |  |




### Google Cloud

| Container                                                      | Cloud     | GPU | Dockerfile                          | Notes             |
|----------------------------------------------------------------|-----------|-----|------------------------------------|--------------------|
| ghcr.io/converged-computing/metric-amg:cpu-zen4                | Google   | no |[Dockerfile](docker/google/cpu/amg) |  |
| ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-zen4 | Google | no |[Dockerfile](docker/google/cpu/amg2023) |  |
| ghcr.io/converged-computing/metric-laghos:cpu-zen4             | Google | no |[Dockerfile](docker/google/cpu/laghos)  | |
| ghcr.io/converged-computing/metric-kripke-cpu:zen4            | Google | no |[Dockerfile](docker/google/cpu/kripke)  | |
| ghcr.io/converged-computing/metric-lammps-cpu:zen4            | Google | no |[Dockerfile](docker/google/cpu/lammps) | |
| ghcr.io/converged-computing/metric-minife:cpu-zen4            | Google | no |[Dockerfile](docker/google/cpu/minife)  | | 
| ghcr.io/converged-computing/mt-gemm:cpu-zen4                  | Google | no |[Dockerfile](docker/google/cpu/mt-gemm-base)| |
| ghcr.io/converged-computing/metric-nek5000:cpu-zen4           | Google | no |[Dockerfile](docker/google/cpu/nek5000) | |
| ghcr.io/converged-computing/metric-osu-cpu:zen4               | Google | no |[Dockerfile](docker/google/cpu/osu) | |
| ghcr.io/converged-computing/metric-quicksilver-cpu:zen4       | Google | no |[Dockerfile](docker/google/cpu/quicksilver) | |
| ghcr.io/converged-computing/metric-single-node:cpu-zen4       | Google | no |[Dockerfile](docker/google/cpu/single-node) | |  
| ghcr.io/converged-computing/metric-stream:cpu-zen4            | Google | no |[Dockerfile](docker/google/cpu/stream) | |
| ghcr.io/converged-computing/metric-mixbench:cpu-zen4           | Google | no |[Dockerfile](docker/google/cpu/mixbench)| |

### Amazon Web Services

| Container                                                      | Cloud     | GPU | Dockerfile                          | Notes             |
|----------------------------------------------------------------|-----------|-----|------------------------------------|--------------------|
| ghcr.io/converged-computing/metric-amg:libfabric-cpu-zen4      | AWS   | no |[Dockerfile](docker/google/aws/amg) |  |
| ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-zen4 | AWS | no |[Dockerfile](docker/google/cpu/amg2023) |  Same as Google, already has
 libfabric |
| ghcr.io/converged-computing/metric-laghos:libfabric-cpu-zen4   |  AWS | no |[Dockerfile](docker/aws/cpu/laghos) | |
| ghcr.io/converged-computing/metric-single-node:cpu-zen4   | AWS | no |[Dockerfile](docker/google/cpu/single-node) | |  
| ghcr.io/converged-computing/metric-kripke-cpu:libfabric-zen4 | AWS | no |[Dockerfile](docker/aws/cpu/amg2023) | |
| ghcr.io/converged-computing/metric-minife:libfabric-cpu-zen4  | AWS | yes |[Dockerfile](docker/aws/gpu/minife)  | | 
| ghcr.io/converged-computing/metric-lammps-cpu:zen4            | AWS | no |[Dockerfile](docker/aws/cpu/lammps) | | 
| ghcr.io/converged-computing/metric-mixbench:libfabric-cpu-zen4 | AWS | no |[Dockerfile](docker/aws/cpu/mixbench) | |
| ghcr.io/converged-computing/mt-gemm:libfabric-cpu-zen4         | AWS | no |[Dockerfile](docker/aws/cpu/mt-gemm) | |
| ghcr.io/converged-computing/metric-nek5000:libfabric-cpu-zen4  | AWS | no |[Dockerfile](docker/aws/cpu/nek5000) | |
| ghcr.io/converged-computing/metric-osu-cpu:libfabric-zen4   | AWS | no |[Dockerfile](docker/aws/cpu/osu) | |
| ghcr.io/converged-computing/metric-quicksilver-cpu:libfabric-zen4 | AWS | no |[Dockerfile](docker/aws/cpu/quicksilver)| |
| ghcr.io/converged-computing/metric-stream:libfabric-cpu-zen4 | AWS | no | [Dockerfile](docker/aws/cpu/stream) | |


The AWS images are based off of the original Google cloud, but have oras and libfabric added.  The CPU variants are the same as the GPU, with CPU stuffs removed. The exception is resnet, which uses the same pytorch base.
