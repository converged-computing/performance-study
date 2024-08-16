FROM ghcr.io/converged-computing/azurehpc:flux-slim

# Build command
#  docker build -t ghcr.io/converged-computing/metric-nek5000:azure-hpc .
#  docker push ghcr.io/converged-computing/metric-nek5000:azure-hpc

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib,sm,self
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt
ENV NRSCONFIG_NOBUILD=1

RUN mkdir nekrs && \
    cd nekrs && \
    git init && \
    git remote add origin https://github.com/Nek5000/nekRS && \
    git fetch --depth 1 origin 4f87e0e2ec0492e2a3edf27791252d6886814d00 && \
    git checkout FETCH_HEAD && \
    CC=mpicc CXX=mpic++ FC=mpif77 ./nrsconfig -DCMAKE_INSTALL_PREFIX=/usr && \
    cd build && \
    cmake ../ && make -j 4 && make install
   
WORKDIR /opt/nekrs
ENV NEKRS_HOME=/usr
EXPOSE 22
# This is trying to handle just in time compiling, which produces a cache with an so
# if you don't do this, the worker nodes can't access it.
WORKDIR /opt/nekrs/examples/turbPipe
