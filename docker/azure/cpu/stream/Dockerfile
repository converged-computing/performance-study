FROM ghcr.io/converged-computing/azurehpc:flux-slim-nogpu

# Build command
#  docker build -t ghcr.io/converged-computing/metric-stream:azure-hpc .
#  docker push ghcr.io/converged-computing/metric-stream:azure-hpc

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt/stream
COPY ./src .
RUN apt-get install -y gfortran && \
    make && cp stream_c.exe /usr/local/bin && cp stream_f.exe /usr/local/bin

EXPOSE 22

