FROM ghcr.io/converged-computing/azurehpc:flux-slim-nogpu

# AMD
#  docker build -t ghcr.io/converged-computing/metric-laghos:azure-hpc .
#  docker push ghcr.io/converged-computing/metric-laghos:azure-hpc 

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt
ENV MAKE_CXX_FLAG="MPICXX=mpic++"

# Install hypre
RUN apt-get install -y libc6-dev && \
    export hypre_options="--disable-fortran --without-fei" && \
    wget --no-verbose https://github.com/hypre-space/hypre/archive/v2.28.0.tar.gz && \
    tar -xzf v2.28.0.tar.gz && \
    mv hypre-2.28.0 hypre && \
    cd hypre/src && \
   ./configure ${hypre_options} CC=mpicc CXX=mpic++ && \
    make -j 4

# Metis
RUN wget --no-verbose https://github.com/mfem/tpls/raw/gh-pages/metis-4.0.3.tar.gz && \
    tar -xzf metis-4.0.3.tar.gz && \
    mv metis-4.0.3 metis-4.0 && \
    make -j 4 -C metis-4.0/Lib CC=mpicc OPTFLAGS="-Wno-error=implicit-function-declaration -O2"

RUN wget https://github.com/mfem/mfem/archive/refs/tags/v4.7.tar.gz && \
    tar -xzvf v4.7.tar.gz && \
    mv mfem-4.7 /opt/mfem && \
    cd /opt/mfem && \
    unset LD_LIBRARY_PATH && \
    make config MFEM_USE_MPI=YES MPICXX=mpiCC MFEM_MPI_NP=2 MFEM_DEBUG=${DEBUG} CPPFLAGS="${CPPFLAGS}" && \
    make -j 4
        
WORKDIR /opt
RUN wget https://github.com/CEED/Laghos/archive/refs/tags/v3.1.tar.gz && \ 
    tar -xzvf v3.1.tar.gz && \
    mv Laghos-3.1 /opt/laghos && \
    cd /opt/laghos && \
    make -j 4

EXPOSE 22
WORKDIR /opt/laghos
