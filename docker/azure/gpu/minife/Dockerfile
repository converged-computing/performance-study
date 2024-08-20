FROM ghcr.io/converged-computing/azurehpc:flux-gpu
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-minife:azure-hpc-gpu-ubuntu2204 .
#  docker push ghcr.io/converged-computing/metric-minife:azure-hpc-gpu-ubuntu2204

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin
ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

WORKDIR /opt
RUN git clone https://github.com/Mantevo/minife
COPY ./Makefile minife/cuda/src/Makefile

# We are adding this to be able to customize parameters moreso
COPY ./Parameters.hpp ./utils.hpp /opt/minife/cuda/utils/
RUN cd /opt/minife/cuda/src && make && cp miniFE.x /usr/local/bin/miniFE.x
EXPOSE 22
WORKDIR /opt/minife
