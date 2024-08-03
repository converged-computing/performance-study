FROM ubuntu:22.04 as builder
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu .
#  docker push ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu

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
RUN mkdir /opt/spack-environment \
    &&  (echo "spack:" \
    &&   echo "  specs:" \
    &&   echo "  - openmpi@4.1.4 fabrics=ofi +legacylaunchers" \
    &&   echo "  - libfabric@1.19.0 fabrics=efa,tcp,udp,sockets,verbs,shm,mrail,rxd,rxm" \
    &&   echo "  - flux-sched" \
    &&   echo "  - flux-core" \
    &&   echo "  - pmix@4.2.2" \
    &&   echo "  - flux-pmix@0.4.0" \
    &&   echo "  - amg2023 +mpi" \
    &&   echo "  - hypre" \
    &&   echo "  concretizer:" \
    &&	 echo "    unify: true" \
    &&   echo "  config:" \
    &&   echo "    install_tree: /opt/software" \
    &&   echo "  view: /opt/view") > /opt/spack-environment/spack.yaml


# Install the software, remove unnecessary deps
RUN cd /opt/spack-environment \
    && git clone https://github.com/spack/spack.git \
    && . spack/share/spack/setup-env.sh \
    && spack env activate . \
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

FROM ubuntu:22.04

COPY --from=builder /opt/spack-environment /opt/spack-environment
COPY --from=builder /opt/software /opt/software
COPY --from=builder /opt/view /opt/view
COPY --from=builder /etc/profile.d/z10_spack_environment.sh /etc/profile.d/z10_spack_environment.sh

RUN apt-get update
RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install --no-install-recommends \
    libatomic1 \
    libnuma-dev \
    libgomp1 \
    ca-certificates \
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
