FROM ghcr.io/converged-computing/azurehpc:flux-slim

# Build command
#  docker build -t ghcr.io/converged-computing/metric-quicksilver-cpu:azure-hpc .
#  docker push ghcr.io/converged-computing/metric-quicksilver-cpu:azure-hpc

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib,sm,self
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt
COPY ./Makefile /opt/Makefile.qs
RUN mkdir quicksilver && \
    cd quicksilver && \
    git init && \
    git remote add origin https://github.com/LLNL/Quicksilver && \
    git fetch --depth 1 origin eb68bb8d6fc53de1f65011d4e79ff2ed0dd60f3b && \
    git checkout FETCH_HEAD && \
    mv /opt/Makefile.qs src/Makefile
WORKDIR /opt/quicksilver/src
RUN make && cp qs /usr/bin/qs

EXPOSE 22
WORKDIR /opt/quicksilver/Examples
