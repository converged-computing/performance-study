FROM ubuntu:22.04

# docker build -t ghcr.io/converged-computing/azurehpc:flux-slim .

WORKDIR /opt
RUN apt-get update && apt-get install -y munge git curl wget unzip gpg debian-archive-keyring \  
    pkg-config vim ubuntu-keyring systemctl && apt-get clean
RUN export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/
COPY ./azhpc-images /opt/azhpc-images
WORKDIR /opt/azhpc-images/ubuntu/ubuntu-22.x/ubuntu-22.04-hpc
ENV DEBIAN_FRONTEND=noninteractive

# OSU Benchmarks in hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/ompi/tests/
RUN oras pull ghcr.io/converged-computing/rdma-infiniband:ubuntu-22.04-tgz --output /opt && \
    cd /opt && \
    tar -xzvf MLNX_OFED_LINUX-24.04-0.7.0.0-ubuntu22.04-x86_64.tgz && \
    cd MLNX_OFED_LINUX-24.04-0.7.0.0-ubuntu22.04-x86_64/DEBS/ && \
    dpkg -i mpitests_3.2.23-45a045b.2404066_amd64.deb && \
    dpkg -i ibverbs-providers* && \
    dpkg -i libibverbs* && \
    dpkg -i librdmacm* && \
    dpkg -i libib* && \
    dpkg -i ucx_1.17.0-1.2404066_amd64.deb && \
    dpkg -i sharp_3.7.0.MLNX20240421.48444036-1.2404066_amd64.deb && \
    dpkg -i hcoll_4.8.3227-1.2404066_amd64.deb 

RUN ./install.sh

# NOW ADD FLUX
# Install openpmix, prrte
WORKDIR /opt/prrte
RUN git clone https://github.com/openpmix/openpmix.git && \
    git clone https://github.com/openpmix/prrte.git && \
    ls -l && \
    set -x && \
    cd openpmix && \
    git checkout fefaed568f33bf86f28afb6e45237f1ec5e4de93 && \
    ./autogen.pl && \
    ./configure --prefix=/usr --disable-static && make -j 4 install && \
    ldconfig && \
    cd .. && \
    cd prrte && \
    git checkout 477894f4720d822b15cab56eee7665107832921c && \
    ./autogen.pl && \
    ./configure --prefix=/usr && make -j 4 install && \
    cd ../.. && \
    rm -rf prrte && unset +x

ENV LANG=C.UTF-8
ENV FLUX_SECURITY_VERSION=0.11.0

RUN mkdir -p /var/run/munge && \
    dd if=/dev/urandom bs=1 count=1024 > /etc/munge/munge.key && \
    chown -R munge /etc/munge/munge.key /var/run/munge && \
    chmod 600 /etc/munge/munge.key

RUN apt-get update && apt-get install -y --no-install-recommends \
        libjansson-dev \
        libmunge-dev \
        lua5.2 luarocks liblua5.2-dev \
        libzmq3-dev \
        libczmq-dev \
        liblz4-dev \
        libsqlite3-dev \
        uuid-dev \
        libhwloc-dev \
        libs3-dev \
        libevent-dev \
        libarchive-dev \
        libsodium-dev && apt-get clean

WORKDIR /opt
RUN CCACHE_DISABLE=1 && \
    V=$FLUX_SECURITY_VERSION && \
    PKG=flux-security-$V && \
    URL=https://github.com/flux-framework/flux-security/releases/download && \
    wget ${URL}/v${V}/${PKG}.tar.gz && \
    tar xvfz ${PKG}.tar.gz && \
    cd ${PKG} && \
    ./configure --prefix=/usr --sysconfdir=/etc && \
    make -j 4 && \
    make install && \
    cd .. && \
    rm -rf flux-security-*

RUN pip install cffi ply && \
    wget https://github.com/flux-framework/flux-core/releases/download/v0.61.2/flux-core-0.61.2.tar.gz && \
    tar xzvf flux-core-0.61.2.tar.gz && \
    cd flux-core-0.61.2 && \
    ./configure --prefix=/usr --sysconfdir=/etc && \
    make clean && \
    make -j 4 && \
    make install && cd opt && rm -rf flux-core-0.61.2

RUN apt-get -qq install -y --no-install-recommends \
	libboost-graph-dev \
	libboost-system-dev \
	libboost-filesystem-dev \
	libboost-regex-dev \
	libyaml-cpp-dev \
	libedit-dev \
        libboost-dev \
        libyaml-cpp-dev && \
        apt-get clean

# 3.22.1 already installed of cmake
    
RUN pip install jsonschema && \
    wget https://github.com/flux-framework/flux-sched/releases/download/v0.33.1/flux-sched-0.33.1.tar.gz && \
    tar -xzvf flux-sched-0.33.1.tar.gz && \
    cd flux-sched-0.33.1 && \
    ./configure --prefix=/usr --sysconfdir=/etc && \
    make -j 4 && \
    make install && \
    ldconfig && \
    cd /opt && \
    rm -rf flux-sched-0.33.1

# Flux pmix (must be installed after flux core)
RUN git clone https://github.com/flux-framework/flux-pmix /opt/flux-pmix && \
    cd /opt/flux-pmix && \
    ./autogen.sh && \
    ./configure --prefix=/usr && \
    make -j 4 && \
    make install && \
    cd /opt && \
    rm -rf flux-pmix && rm -rf flux-*.tar.gz

WORKDIR /opt
