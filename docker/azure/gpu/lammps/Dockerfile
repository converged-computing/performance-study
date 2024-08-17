FROM ghcr.io/converged-computing/azurehpc:flux-gpu 

# Build command
#  docker build -t ghcr.io/converged-computing/metric-lammps-gpu:azure-hpc .
#  docker push ghcr.io/converged-computing/metric-lammps-cpu:azure-hpc

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt

WORKDIR /code
COPY ./common .

# Note that I ran this interactively after cloning to test flags.
RUN python3 -m pip install clang-format && \
   mkdir lammps && \
   cd lammps && \
   git init && \
   git remote add origin https://github.com/lammps/lammps.git && \
   git fetch --depth 1 origin a8687b53724b630fb5f454c8d7be9f9370f8bb3b && \
   git checkout FETCH_HEAD && \
   mkdir build && \
   cd build && \
   cmake \
  -D CMAKE_INSTALL_PREFIX=/usr \
  -D CMAKE_BUILD_TYPE=Release \
  -D Kokkos_ARCH_VOLTA70=ON \
  -D MPI_CXX_COMPILER=mpicxx \
  -D BUILD_MPI=yes \
  -D PKG_ML-SNAP=yes \
  -D PKG_GPU=no \
  -D PKG_REAXFF=on \
  -D PKG_KOKKOS=yes \
  -D Kokkos_ENABLE_CUDA=yes \
  ../cmake && make -j 4 && make install
