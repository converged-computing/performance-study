FROM ghcr.io/converged-computing/azurehpc:flux-gpu
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/multi-gpu-models:azure-hpc-gpu-ubuntu2204 .
#  docker push ghcr.io/converged-computing/multi-gpu-models:azure-hpc-gpu-ubuntu2204

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin
ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

WORKDIR /opt
ENV CUDA_HOME=/usr/local/cuda

# If I run make it says it isn't cuda aware, but running it, it is definitely looking for GPU.
# We will need to test.
RUN git clone https://github.com/NVIDIA/multi-gpu-programming-models && \
    cd multi-gpu-programming-models/mpi && \
    nvcc -DHAVE_CUB -lineinfo -gencode arch=compute_70,code=sm_70 -gencode arch=compute_80,code=sm_80 -gencode arch=compute_90,code=sm_90 -gencode arch=compute_90,code=compute_90 -std=c++14 jacobi_kernels.cu -c && \
    mpicxx -DSKIP_CUDA_AWARENESS_CHECK -DUSE_NVTX -I/usr/local/cuda/include -std=c++14 jacobi.cpp jacobi_kernels.o -L/usr/local/cuda/lib64 -lcudart -lnvToolsExt -o jacobi

EXPOSE 22
WORKDIR /opt/multi-gpu-programming-models/mpi
