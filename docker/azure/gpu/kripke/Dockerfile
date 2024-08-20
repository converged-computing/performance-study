FROM ghcr.io/converged-computing/azurehpc:flux-gpu
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-kripke-gpu:azure-hpc-gpu-ubuntu2204 .
#  docker push ghcr.io/converged-computing/metric-kripke-gpu:azure-hpc-gpu-ubuntu2204

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin
ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

WORKDIR /opt
RUN git clone https://github.com/LLNL/Kripke && \
    cd Kripke && \
    git submodule update --init --recursive && \
    mkdir build 

COPY ./gke.cmake /opt/Kripke/host-configs/gke.cmake
RUN cd /opt/Kripke/build && \
    cmake -DENABLE_CUDA=true -C../host-configs/gke.cmake ../ && make && \
    # Expose kripke.exe as kripke in bin
    mv /opt/Kripke/build/kripke.exe /opt/Kripke/build/bin/kripke

# Put those bad bois on the path!
ENV PATH=/opt/Kripke:/opt/Kripke/build/bin:$PATH

EXPOSE 22
WORKDIR /opt/Kripke
