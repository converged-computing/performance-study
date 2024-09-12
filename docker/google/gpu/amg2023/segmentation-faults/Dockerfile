FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04 as builder
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-amg2023:spack-slim .
#  docker push ghcr.io/converged-computing/metric-amg2023:spack-slim

# Built on n1-standard-96 image on Google Cloud 
#  ghcr.io/converged-computing/metric-amg2023:spack-intel-int64 .
#  docker push  ghcr.io/converged-computing/metric-amg2023:spack-intel-int64

# The final one that worked was on an old skylake I have from grad school
# with the +mixedint removed
# docker build -t ghcr.io/converged-computing/metric-amg2023:spack-older-intel .

# Note that we are still testing a derivative of the below (this Dockerfile with spack.yaml)
# to get to the larger problem size - no luck so far.

# cmake -DHYPRE_PREFIX=/opt/software/linux-ubuntu22.04-haswell/gcc-11.4.0/hypre-2.31.0-pk6f7bem62g3l3g5prbb7ddhowbstgnd/ -DAMG_WITH_CUDA=ON -DAMG_WITH_MPI=ON ..

# singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-n1-standard-haswell-manual

RUN apt-get update
RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install \
    autotools-dev \
    autoconf \
    automake \
    cmake \
    git \
    python3 \
    dnsutils \
    libatomic1 \
    libnuma-dev \
    libgomp1 \
    openssh-server \
    openssh-client \
    apt-utils \
    gcc \
    unzip \
    gfortran \
    g++ \
    build-essential \
    software-properties-common

# What we want to install and how we want to install it
# is specified in a manifest file (spack.yaml)
# IMPORTANT: cpu gets +int64, and gpu +mixedint
WORKDIR /opt/spack-environment
COPY ./spack.yaml ./spack.yaml

ENV CUDACXX=/usr/local/cuda/bin/nvcc
ENV PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:$LD_LIBRARY_PATH

# Install the software, remove unnecessary deps
RUN cd /opt/spack-environment \
    && git clone https://github.com/spack/spack.git \
    && . spack/share/spack/setup-env.sh \
    && spack env activate . \
    && spack compiler find \
    && spack external find openssh \
    && spack external find cmake \
    && spack install --reuse --fail-fast \
    && spack gc -y

# Modifications to the environment that are necessary to run
RUN cd /opt/spack-environment \
    && . spack/share/spack/setup-env.sh \
    && spack env activate --sh -d . >> /etc/profile.d/z10_spack_environment.sh

WORKDIR /opt
EXPOSE 22

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-amg2023:spack-slim .
#  docker push ghcr.io/converged-computing/metric-amg2023:spack-slim

FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

COPY --from=builder /opt/spack-environment /opt/spack-environment
COPY --from=builder /opt/software /opt/software
COPY --from=builder /opt/view /opt/view
COPY --from=builder /etc/profile.d/z10_spack_environment.sh /etc/profile.d/z10_spack_environment.sh

ENV CUDACXX=/usr/local/cuda/bin/nvcc
ENV PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64:$LD_LIBRARY_PATH

RUN apt-get update
RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install --no-install-recommends \
    libatomic1 \
    libnuma-dev \
    libgomp1 \
    openssh-server \
    openssh-client \
    dnsutils \
    curl \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
    
# Finally, install oras for saving artifacts
RUN export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/
