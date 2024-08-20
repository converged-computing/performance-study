FROM ghcr.io/converged-computing/azurehpc:flux-gpu
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-magma:azure-hpc-gpu-ubuntu2204 .
#  docker push ghcr.io/converged-computing/metric-magma:azure-hpc-gpu-ubuntu2204

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin
ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

WORKDIR /opt/magma
RUN apt-get install -y libblas-dev liblapack-dev gfortran && \
    wget https://icl.utk.edu/projectsfiles/magma/downloads/magma-2.8.0.tar.gz && \
    tar -xzvf magma-2.8.0.tar.gz && cd magma-2.8.0 && \
    mkdir build && cd build && cmake ../ && make && make install

# We need to make examples!
COPY Makefile /opt/magma/magma-2.8.0/example/Makefile
RUN cd /opt/magma/magma-2.8.0/example && make all
WORKDIR /opt/magma/magma-2.8.0/example
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/magma/lib
EXPOSE 22

RUN mkdir -p /data
COPY ./data/t10k-images.idx3-ubyte.zip /data/
COPY ./data/t10k-labels.idx1-ubyte /data/
COPY ./data/train-images.idx3-ubyte.zip /data/
COPY ./data/train-labels.idx1-ubyte /data/
