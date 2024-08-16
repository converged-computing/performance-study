FROM ghcr.io/converged-computing/azurehpc:flux-slim

# Build command
#  docker build -t ghcr.io/converged-computing/metric-mixbench:azure-hpc .
#  docker push ghcr.io/converged-computing/metric-mixbench:azure-hpc

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib,sm,self
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt
RUN mkdir mixbench && \
    cd mixbench && \
    git init && \
    git remote add origin https://github.com/ekondis/mixbench && \
    git fetch --depth 1 origin 440a133a6423840ce613d1eaab43cd586effd389 && \
    git checkout FETCH_HEAD && \
    cd /opt/mixbench/mixbench-cpu && \
    mkdir build && \
    cd build && \
    cmake ../ && \
    cmake --build ./ && make && \
    cp mixbench-cpu /usr/local/bin

EXPOSE 22
WORKDIR /opt/mixbench
