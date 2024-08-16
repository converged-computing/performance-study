FROM ghcr.io/converged-computing/azurehpc:flux-slim

# Build command
#  docker build -t ghcr.io/converged-computing/metric-kripke-cpu:azure-hpc .
#  docker push ghcr.io/converged-computing/metric-kripke-cpu:azure-hpc

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib,sm,self
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt
COPY ./gke.cmake /opt/gke.cmake

RUN git clone https://github.com/LLNL/Kripke && \
    cd Kripke && \
    git submodule update --init --recursive && \
    mkdir build && \
    mv /opt/gke.cmake /opt/Kripke/host-configs/gke.cmake && \
    cd /opt/Kripke/build && \
    cmake  -C../host-configs/gke.cmake ../ && make && \
    mv /opt/Kripke/build/kripke.exe /usr/local/bin/kripke && \
    rm -rf /opt/Kripke

# Put those bad bois on the path!
ENV PATH=/opt/Kripke:/opt/Kripke/build/bin:$PATH

EXPOSE 22
WORKDIR /opt/Kripke
