FROM ghcr.io/converged-computing/azurehpc:flux-gpu
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/mt-gemm:azure-hpc-gpu-ubuntu2204 .
#  docker push ghcr.io/converged-computing/mt-gemm:azure-hpc-gpu-ubuntu2204

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin
ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

ENV CUDA_HOME=/usr/local/cuda
WORKDIR /opt/gem
COPY ./src /opt/gem
RUN make

EXPOSE 22
WORKDIR /opt/gem

