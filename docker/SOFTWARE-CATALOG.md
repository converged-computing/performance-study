# Container Catalog

The stuff in each container. For build specifics, config files, and data, you should reference the associated directory with the Dockerfile for each container below. A lot of these have dependencies that I didn't document - ping me if you need me to shell into a container and look something up!

**Important** many of these have custom code / configs - please look at the Dockerfile.

## Google GPU

### spack

#### ghcr.io/converged-computing/metric-amg2023:spack-slim 

This is the only one that uses spack for GPU, and it is shared between AWS/Google. I'll just put it here under Google and skip AWS.

 - cuda: 12.4.1
 - gcc: 11.4.0
 - cmake: 3.22.1
 - openmpi@4.1.4 fabrics=ofi +legacylaunchers +cuda cuda_arch=70
 - libfabric@1.19.0 fabrics=efa,tcp,udp,sockets,verbs,shm,mrail,rxd,rxm
 - flux-core 0.61.2 +hwloc==2.8.0+zmq==4.3.5
 - flux-sched 0.33.1
 - pmix@4.2.2
 - flux-pmix@0.4.0
 - amg2023 +mpi +cuda cuda_arch=70
 - hypre +cuda cuda_arch=70
 - oras 1.1.0

(Note that Google cannot use libfabric)

### ubuntu gpu

The rest of these containers use the base `nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04` and:

 - gcc: 11.4.0
 - cmake: 3.23.1
 - openmpi@4.1.2 
 - flux-core 0.61.2 +hwloc==2.5.0+zmq==4.3.4
 - flux-sched 0.33.1
 - flux-security 0.11.0
 - python 3.10.12
 - oras 1.1.0
 - cuda: 12.4.1
 - OpenPMIX
  - https://github.com/openpmix/openpmix.git AT `fefaed568f33bf86f28afb6e45237f1ec5e4de93`
 - PRRTE
  - https://github.com/openpmix/prrte.git    AT `477894f4720d822b15cab56eee7665107832921c`

### ghcr.io/converged-computing/metric-kripke-gpu:latest

 - Kripke: 
   - May 15, 2024
   - `f50d0a35b4cd1f77013dfa34d4d7cc426e198f72`
   - https://github.com/LLNL/Kripke 

### ghcr.io/converged-computing/metric-laghos:gpu

 - Laghos
  - https://github.com/CEED/Laghos
  - branch multi-gpu
  - `2a3d27142fc55d132c5543f5ccafde7838ce6cea`

### ghcr.io/converged-computing/metric-lammps-gpu:kokkos

(Lammps automatically installs kokkos)

 - Lammps
  - May 20, 2024
  - `a8687b53724b630fb5f454c8d7be9f9370f8bb3b`
 
### ghcr.io/converged-computing/metric-magma

 - Magma
  - 2.8.0 (release)

### ghcr.io/converged-computing/metric-minife:latest

 - MiniFE
  - `abe328816d84afc319c482d6bc8df414b8f90d79`
  - July 17 2023

### ghcr.io/converged-computing/metric-mixbench:latest

 - Mixbench
   - `440a133a6423840ce613d1eaab43cd586effd389`
   - Feb 23, 2024
   - https://github.com/ekondis/mixbench
   
### ghcr.io/converged-computing/mt-gemm:latest

- Copied from files Ani gave me, no git commit / version. See Dockerfile directory.

### ghcr.io/converged-computing/multi-gpu-models:flux-gpu

 - multi-gpu-models
  - `83a59701cd4933722ca5259fb63d8bb68b0ecd67`
  - March 4, 2024
  - https://github.com/NVIDIA/multi-gpu-programming-models
  
### ghcr.io/converged-computing/metric-nek5000:latest

 - nekrs
  - `4f87e0e2ec0492e2a3edf27791252d6886814d00`
  - May 30, 2024
  - https://github.com/Nek5000/nekRS
  
### ghcr.io/converged-computing/metric-osu-gpu:latest

 - OSU
  - osu version: 5.8
  - http://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-5.8.tgz

### ghcr.io/converged-computing/metric-quicksilver-gpu:latest

 - Quicksilver
  - `eb68bb8d6fc53de1f65011d4e79ff2ed0dd60f3b`
  - August 18, 2023
  - https://github.com/LLNL/Quicksilver

### ghcr.io/converged-computing/pytorch-resnet-experiment:gpu

This uses a different base image: `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-devel`


```console
LIBRARY_PATH=/usr/local/cuda/lib64/stubs
NV_LIBCUBLAS_VERSION=12.1.3.1-1
NV_NVPROF_DEV_PACKAGE=cuda-nvprof-12-1=12.1.105-1
NV_CUDA_COMPAT_PACKAGE=cuda-compat-12-1
NV_CUDA_NSIGHT_COMPUTE_VERSION=12.1.1-1
HOSTNAME=235516eb0397
SHLVL=0
LD_LIBRARY_PATH=/usr/local/pancakes/lib:/opt/miniconda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:/usr/local/cuda-12.4/compat
NV_LIBNCCL_PACKAGE_VERSION=2.17.1-1
HOME=/root
NV_CUDNN_PACKAGE_NAME=libcudnn8
NV_LIBCUBLAS_DEV_VERSION=12.1.3.1-1
NV_LIBNCCL_DEV_PACKAGE_VERSION=2.17.1-1
NV_LIBNPP_PACKAGE=libnpp-12-1=12.1.0.40-1
NV_CUDNN_PACKAGE=libcudnn8=8.9.0.131-1+cuda12.1
CUDA_VERSION=12.1.1
CUDA_VISIBLE_DEVICES=0,1,2,3
NV_NVPROF_VERSION=12.1.105-1
NV_LIBCUBLAS_PACKAGE_NAME=libcublas-12-1
NVIDIA_REQUIRE_CUDA=cuda>=12.1 brand=tesla,driver>=470,driver<471 brand=unknown,driver>=470,driver<471 brand=nvidia,driver>=470,driver<471 brand=nvidiartx,driver>=470,driver<471 brand=geforce,driver>=470,driver<471 brand=geforcertx,driver>=470,driver<471 brand=quadro,driver>=470,driver<471 brand=quadrortx,driver>=470,driver<471 brand=titan,driver>=470,driver<471 brand=titanrtx,driver>=470,driver<471 brand=tesla,driver>=525,driver<526 brand=unknown,driver>=525,driver<526 brand=nvidia,driver>=525,driver<526 brand=nvidiartx,driver>=525,driver<526 brand=geforce,driver>=525,driver<526 brand=geforcertx,driver>=525,driver<526 brand=quadro,driver>=525,driver<526 brand=quadrortx,driver>=525,driver<526 brand=titan,driver>=525,driver<526 brand=titanrtx,driver>=525,driver<526
NV_LIBCUSPARSE_VERSION=12.1.0.106-1
NVIDIA_DRIVER_CAPABILITIES=compute,utility
NVIDIA_CPU_ONLY=1
NV_CUDA_LIB_VERSION=12.1.1-1
NV_LIBNCCL_PACKAGE_NAME=libnccl2
NV_NVML_DEV_VERSION=12.1.105-1
NV_LIBNPP_DEV_PACKAGE=libnpp-dev-12-1=12.1.0.40-1
TERM=xterm
NV_CUDA_CUDART_VERSION=12.1.105-1
NV_CUDNN_PACKAGE_DEV=libcudnn8-dev=8.9.0.131-1+cuda12.1
PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/pancakes/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
NV_LIBCUBLAS_DEV_PACKAGE_NAME=libcublas-dev-12-1
CMAKE=3.23.1
NV_LIBCUBLAS_PACKAGE=libcublas-12-1=12.1.3.1-1
PYTORCH_VERSION=2.3.0
NVARCH=x86_64
NV_LIBNCCL_DEV_PACKAGE_NAME=libnccl-dev
NV_LIBCUSPARSE_DEV_VERSION=12.1.0.106-1
NV_LIBNCCL_PACKAGE=libnccl2=2.17.1-1+cuda12.1
NVIDIA_PRODUCT_NAME=CUDA
LANG=C.UTF-8
NV_CUDA_CUDART_DEV_VERSION=12.1.105-1
DEBIAN_FRONTEND=noninteractive
NV_LIBCUBLAS_DEV_PACKAGE=libcublas-dev-12-1=12.1.3.1-1
NV_CUDA_NSIGHT_COMPUTE_DEV_PACKAGE=cuda-nsight-compute-12-1=12.1.1-1
NV_LIBNCCL_DEV_PACKAGE=libnccl-dev=2.17.1-1+cuda12.1
NV_NVTX_VERSION=12.1.105-1
NV_LIBNPP_VERSION=12.1.0.40-1
NV_CUDNN_VERSION=8.9.0.131
PWD=/opt
NVIDIA_VISIBLE_DEVICES=all
NCCL_VERSION=2.17.1-1
NV_LIBNPP_DEV_VERSION=12.1.0.40-1
```

And torch:

```bash
# pip freeze | grep torch
torch==2.3.0+cu118
torchaudio==2.3.0+cu118
torchvision==0.18.0+cu118
```

flux, and all the other versions are the same.

### ghcr.io/converged-computing/metric-stream:latest

 - cuda-stream
   - `37d20f6d8dc8b4ad46918d43cf35eb5eb9c9432a`
   - August 17, 2017
   - https://github.com/bcumming/cuda-stream

## AWS

All of these (except for spack) use:

 - Libfabric
  - `64da1ee41068bffe6d4369e08555f091e04d0461`
  - https://github.com/ofiwg/libfabric.git
  
See Dockerfiles for how it is built with openmpi / efa. 

### ghcr.io/converged-computing/metric-amg2023:spack-slim

See Google GPU entry - same container.

### ghcr.io/converged-computing/metric-lammps-gpu:libfabric

 - Lammps
  - May 20, 2024
  - `a8687b53724b630fb5f454c8d7be9f9370f8bb3b`

### ghcr.io/converged-computing/metric-kripke-gpu:libfabric

 - Kripke: 
   - May 15, 2024
   - `f50d0a35b4cd1f77013dfa34d4d7cc426e198f72`
   - https://github.com/LLNL/Kripke 

### ghcr.io/converged-computing/metric-laghos:libfabric-gpu

 - Laghos
  - https://github.com/CEED/Laghos
  - branch multi-gpu
  - `2a3d27142fc55d132c5543f5ccafde7838ce6cea`

### ghcr.io/converged-computing/metric-magma:libfabric

 - Magma
  - 2.8.0 (release)
  
### ghcr.io/converged-computing/metric-minife:libfabric

 - MiniFE
  - `abe328816d84afc319c482d6bc8df414b8f90d79`
  - July 17 2023

### ghcr.io/converged-computing/metric-mixbench:libfabric 

 - Mixbench
   - `440a133a6423840ce613d1eaab43cd586effd389`
   - Feb 23, 2024
   - https://github.com/ekondis/mixbench

### ghcr.io/converged-computing/mt-gemm:libfabric

- Copied from files Ani gave me, no git commit / version. See Dockerfile directory.

### ghcr.io/converged-computing/multi-gpu-models:libfabric

 - multi-gpu-models
  - `83a59701cd4933722ca5259fb63d8bb68b0ecd67`
  - March 4, 2024
  - https://github.com/NVIDIA/multi-gpu-programming-models
  
### ghcr.io/converged-computing/metric-nek5000:libfabric

 - nekrs
  - `4f87e0e2ec0492e2a3edf27791252d6886814d00`
  - May 30, 2024
  - https://github.com/Nek5000/nekRS

### ghcr.io/converged-computing/metric-osu-gpu:libfabric

 - OSU
  - osu version: 5.8
  - http://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-5.8.tgz

### ghcr.io/converged-computing/metric-quicksilver-gpu:libfabric

 - Quicksilver
  - `eb68bb8d6fc53de1f65011d4e79ff2ed0dd60f3b`
  - August 18, 2023
  - https://github.com/LLNL/Quicksilver

### ghcr.io/converged-computing/pytorch-resnet-experiment:libfabric-gpu

Same as other pytorch base of `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-devel`

### ghcr.io/converged-computing/metric-stream:libfabric 

 - cuda-stream
   - `37d20f6d8dc8b4ad46918d43cf35eb5eb9c9432a`
   - August 17, 2017
   - https://github.com/bcumming/cuda-stream

## Google CPU

### ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu 

This has a base of `ubuntu:22.04` instead of the equivalent for cuda.

 - gcc: 11.4.0
 - cmake: 3.22.1
 - openmpi@4.1.4
 - flux-core 0.61.2 +hwloc==2.5.0+zmq==4.3.4
 - flux-sched 0.33.1
 - pmix: 4.2.2
 - flux-pmix: 0.4.0
 - python 3.11.9
 - oras 1.1.0
 - libfabric 1.19.0
 - develop (built 2 weeks ago, today is Jun 11th) 
 
### ghcr.io/converged-computing/metric-lammps-cpu 

 - Lammps
  - May 20, 2024
  - `a8687b53724b630fb5f454c8d7be9f9370f8bb3b`

### ghcr.io/converged-computing/metric-kripke-cpu

 - Kripke: 
   - May 15, 2024
   - `f50d0a35b4cd1f77013dfa34d4d7cc426e198f72`
   - https://github.com/LLNL/Kripke 

### ghcr.io/converged-computing/metric-laghos:cpu

 - Laghos
  - Feb 21, 2024
  - `a00cb3cba70136f88e6c137d303d6548067a2abf`
  - https://github.com/CEED/Laghos

**THIS IS A DIFFERENT COMMIT**

### ghcr.io/converged-computing/metric-minife:cpu

 - MiniFE
  - `abe328816d84afc319c482d6bc8df414b8f90d79`
  - July 17 2023

### ghcr.io/converged-computing/metric-mixbench:cpu

 - Mixbench
   - `440a133a6423840ce613d1eaab43cd586effd389`
   - Feb 23, 2024
   - https://github.com/ekondis/mixbench
   
### ghcr.io/converged-computing/metric-nek5000:cpu 

 - nekrs
  - `4f87e0e2ec0492e2a3edf27791252d6886814d00`
  - May 30, 2024
  - https://github.com/Nek5000/nekRS
  
### ghcr.io/converged-computing/metric-osu-cpu

 - OSU
  - osu version: 5.8
  - http://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-5.8.tgz

### ghcr.io/converged-computing/metric-quicksilver-cpu 

 - Quicksilver
  - `eb68bb8d6fc53de1f65011d4e79ff2ed0dd60f3b`
  - August 18, 2023
  - https://github.com/LLNL/Quicksilver

### ghcr.io/converged-computing/metric-stream:cpu

This was all added via the Docker build, no clones / versions available.

### ghcr.io/converged-computing/mt-gemm:cpu 

 - Mt-gemm
  - `4787deb76e9afb602511ff3eceb1b3c00361d5be`
  - https://repository.prace-ri.eu/git/CodeVault/hpc-kernels/dense_linear_algebra.git
  - June 19, 2018

### ghcr.io/converged-computing/metric-linpack-cpu 

 - Linkpack
   - https://github.com/ULHPC/tutorials
   - HPL version 2.3  
   - http://www.netlib.org/benchmark/hpl/hpl-${HPL_VERSION}.tar.gz
    
## AWS CPU

Bases (with libfabric):

 - libfabric: 1.24.0
 - gcc: 11.4.0
 - cmake: 3.23.1
 - openmpi@4.1.2 
 - flux-core 0.61.2 +hwloc==2.5.0+zmq==4.3.4
 - flux-sched 0.33.1
 - flux-security 0.11.0
 - python 3.10.12
 - oras 1.1.0
 - OpenPMIX
  - https://github.com/openpmix/openpmix.git AT `fefaed568f33bf86f28afb6e45237f1ec5e4de93`
 - PRRTE
  - https://github.com/openpmix/prrte.git    AT `477894f4720d822b15cab56eee7665107832921c`

### ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu 

See Google CPU container again!

### ghcr.io/converged-computing/metric-kripke-cpu:libfabric 

 - Kripke: 
   - May 15, 2024
   - `f50d0a35b4cd1f77013dfa34d4d7cc426e198f72`
   - https://github.com/LLNL/Kripke 

### ghcr.io/converged-computing/metric-laghos:libfabric-cpu   

 - Laghos
  - Feb 21, 2024
  - `a00cb3cba70136f88e6c137d303d6548067a2abf`
  - https://github.com/CEED/Laghos

### ghcr.io/converged-computing/metric-lammps-cpu  

 - Lammps
  - May 20, 2024
  - `a8687b53724b630fb5f454c8d7be9f9370f8bb3b`

### ghcr.io/converged-computing/metric-minife:libfabric-cpu 

 - MiniFE
  - `abe328816d84afc319c482d6bc8df414b8f90d79`
  - July 17 2023

### ghcr.io/converged-computing/metric-mixbench:libfabric-cpu 

 - Mixbench
   - `440a133a6423840ce613d1eaab43cd586effd389`
   - Feb 23, 2024
   - https://github.com/ekondis/mixbench
   
### ghcr.io/converged-computing/mt-gemm:libfabric-cpu 

 - Mt-gemm
  - `4787deb76e9afb602511ff3eceb1b3c00361d5be`
  - https://repository.prace-ri.eu/git/CodeVault/hpc-kernels/dense_linear_algebra.git
  - June 19, 2018

### ghcr.io/converged-computing/metric-nek5000:libfabric-cpu 

 - nekrs
  - `4f87e0e2ec0492e2a3edf27791252d6886814d00`
  - May 30, 2024
  - https://github.com/Nek5000/nekRS

### ghcr.io/converged-computing/metric-osu-cpu:libfabric 

 - OSU
  - osu version: 5.8
  - http://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-5.8.tgz

### ghcr.io/converged-computing/metric-quicksilver-cpu:libfabric 

 - Quicksilver
  - `eb68bb8d6fc53de1f65011d4e79ff2ed0dd60f3b`
  - August 18, 2023
  - https://github.com/LLNL/Quicksilver

### ghcr.io/converged-computing/metric-stream:libfabric-cpu 

Custom build - see src directory.

### ghcr.io/converged-computing/metric-linpack-cpu:libfabric 

 - Linkpack
   - https://github.com/ULHPC/tutorials
   - HPL version 2.3  
   - http://www.netlib.org/benchmark/hpl/hpl-${HPL_VERSION}.tar.gz
