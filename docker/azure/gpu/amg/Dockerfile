FROM ghcr.io/converged-computing/azurehpc:flux-gpu
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-amg:azure-hpc-gpu-ubuntu2204 .
#  docker push ghcr.io/converged-computing/metric-amg:azure-hpc-gpu-ubuntu2204

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin
ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7,8

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
    make

# Metis
RUN wget --no-verbose https://github.com/mfem/tpls/raw/gh-pages/metis-4.0.3.tar.gz && \
    tar -xzf metis-4.0.3.tar.gz && \
    mv metis-4.0.3 metis-4.0 && \
    make -C metis-4.0/Lib CC=mpicc OPTFLAGS="-Wno-error=implicit-function-declaration -O2"

ENV MFEM_BUILD="pcuda -j CUDA_ARCH=sm_70"
RUN wget https://github.com/mfem/mfem/archive/refs/tags/v4.7.tar.gz && \
    tar -xzvf v4.7.tar.gz && \
    mv mfem-4.7 /opt/mfem && \
    cd /opt/mfem && \
    make config MFEM_USE_MPI=YES MPICXX=mpiCC MFEM_MPI_NP=2 MFEM_DEBUG=${DEBUG} CPPFLAGS="${CPPFLAGS}" && \
    make MFEM_BUILD=${MFEM_BUILD}
        
WORKDIR /opt
RUN git clone https://github.com/LLNL/AMG.git && \
    cd ./AMG && \
    make

ENV PATH=/opt/AMG/test:$PATH

EXPOSE 22
WORKDIR /opt/AMG
