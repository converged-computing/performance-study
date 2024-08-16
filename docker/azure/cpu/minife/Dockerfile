FROM ghcr.io/converged-computing/azurehpc:flux-slim

# Build command
#  docker build -t ghcr.io/converged-computing/metric-minife:azure-hoc .
#  docker push ghcr.io/converged-computing/metric-minife:azure-hpc

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib,sm,self
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt
ENV MAKE_CXX_FLAG="MPICXX=mpic++"

WORKDIR /opt
RUN mkdir minife && \
    cd minife && \
    git init && \
    git remote add origin https://github.com/Mantevo/minife && \
    git fetch --depth 1 origin abe328816d84afc319c482d6bc8df414b8f90d79 && \
    git checkout FETCH_HEAD

# We are adding this to be able to customize parameters moreso
RUN cd /opt/minife/openmp/src && make && cp miniFE.x /usr/local/bin/miniFE.x
EXPOSE 22
WORKDIR /opt/minife
