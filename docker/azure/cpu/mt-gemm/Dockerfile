FROM ghcr.io/converged-computing/azurehpc:flux-slim-nogpu

# Build command
#  docker build -t ghcr.io/converged-computing/mt-gemm:azure-hpc .
#  docker push ghcr.io/converged-computing/mt-gemm:azure-hpc

ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

WORKDIR /opt
RUN git clone https://repository.prace-ri.eu/git/CodeVault/hpc-kernels/dense_linear_algebra.git
COPY gemm_mpi.cpp /opt/dense_linear_algebra/gemm/mpi/src/
ENV C_FLAGS="-I/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/include"
ENV CXX_FLAGS="-I/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/include"
RUN cp -R /opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/ompi/include/* /usr/include/ && \
    cd /opt/dense_linear_algebra/gemm/mpi && \
    mkdir build && cd build && \
    cmake ../ && make -j 4 && make install

# command is 1_dense_gemm_mpi
WORKDIR /opt/dense_linear_algebra/gemm/mpi
