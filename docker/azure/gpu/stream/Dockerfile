FROM ghcr.io/converged-computing/azurehpc:flux-gpu

# Build command
#  docker build -t ghcr.io/converged-computing/metric-stream:azure-hpc-ubuntu2204 .
#  docker push ghcr.io/converged-computing/metric-stream:azure-hpc-ubuntu2204

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin

WORKDIR /opt/stream
RUN git clone https://github.com/bcumming/cuda-stream
COPY Makefile /opt/stream/cuda-stream/Makefile
RUN cd /opt/stream/cuda-stream && make ARCH=sm_70 && cp stream /usr/local/bin/

EXPOSE 22
