FROM ubuntu:22.04

# docker build -t ghcr.io/converged-computing/azurehpc:flux-slim-gpu .
# docker push ghcr.io/converged-computing/azurehpc:flux-slim-gpu
# Note that I built this a bit manually after extraction - the reason is I had
# to figure out the order of installs. I would up doing many apt --fix-broken install, etc.

WORKDIR /opt
RUN apt-get update && apt-get install -y munge git curl wget unzip gpg debian-archive-keyring \  
    pkg-config vim ubuntu-keyring systemctl libgomp1 libibverbs1 \
    libnvidia-compute-550-server && apt-get clean
RUN export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/
COPY git clone -b azure-performance-study-gpu-build-2024 https://github.com/researchapps/azurehpc-images /opt/azhpc-images
WORKDIR /opt/azhpc-images/ubuntu/ubuntu-22.x/ubuntu-22.04-hpc
ENV DEBIAN_FRONTEND=noninteractive

# Note that I needed to do
# apt-get install -y libnl-3-dev
# apt --fix-broken install

# OSU Benchmarks in hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/ompi/tests/
RUN oras pull ghcr.io/converged-computing/rdma-infiniband:ubuntu-22.04-tgz --output /opt && \
    cd /opt && \
    tar -xzvf MLNX_OFED_LINUX-24.04-0.7.0.0-ubuntu22.04-x86_64.tgz && \
    cd MLNX_OFED_LINUX-24.04-0.7.0.0-ubuntu22.04-x86_64/DEBS/ && \
    dpkg -i mpitests_3.2.23-45a045b.2404066_amd64.deb && \
    apt-get install -y libnl-3-dev || true && \
    apt --fix-broken install && \
    apt-get install -y libnl-route-3-dev || true && \
    apt --fix-broken install && \
    dpkg -i ibverbs-providers* && \
    dpkg -i libibverbs* && \
    dpkg -i librdmacm* && \
    dpkg -i libib* && \
    dpkg -i ucx_1.17.0-1.2404066_amd64.deb && \
    dpkg -i sharp_3.7.0.MLNX20240421.48444036-1.2404066_amd64.deb && \
    dpkg -i hcoll_4.8.3227-1.2404066_amd64.deb && \
    # Add stuff for cuda 
    dpkg -i dpcp_1.1.48-1.2404066_amd64.deb && \
    dpkg -i infiniband-diags_2404mlnx51-1.2404066_amd64.deb && \ 
    dpkg -i ucx-cuda_1.17.0-1.2404066_amd64.deb

# This is the contents of install.sh spread out into layers.
# Most registries allow only 10GB per layer. "only"
ENV GPU="NVIDIA"

# install pre-requisites
RUN ./install_prerequisites.sh && \
    . ./set_properties.sh && \
    $UBUNTU_COMMON_DIR/remove_unused_packages.sh

RUN . ./set_properties.sh && \
    ./install_utils.sh

# install PMIX
RUN . ./set_properties.sh && \
    $UBUNTU_COMMON_DIR/install_pmix.sh

# install mpi libraries
RUN . ./set_properties.sh && \
    $UBUNTU_COMMON_DIR/install_mpis.sh

# install nvidia gpu driver
RUN . ./set_properties.sh && \
    ./install_nvidiagpudriver.sh
    
RUN . ./set_properties.sh && \
    # Install NCCL
    $UBUNTU_COMMON_DIR/install_nccl.sh || true

# Install NVIDIA docker container
RUN . ./set_properties.sh && \
    $UBUNTU_COMMON_DIR/install_docker.sh || true

# cleanup downloaded tarballs - clear some space
RUN rm -rf *.tgz *.bz2 *.tbz *.tar.gz *.run *.deb *_offline.sh && \
    rm -rf /tmp/MLNX_OFED_LINUX* /tmp/*conf* && \
    rm -rf /var/intel/ /var/cache/* && \
    rm -Rf -- */

# Install DCGM
RUN . ./set_properties.sh && \
    $UBUNTU_COMMON_DIR/install_dcgm.sh || true

# install Intel libraries
# skipping this because it builds kernel stuff.
# $COMMON_DIR/install_intel_libs.sh

# install diagnostic script
RUN . ./set_properties.sh && \
    $COMMON_DIR/install_hpcdiag.sh || true

# install persistent rdma naming
RUN . ./set_properties.sh && \
    $COMMON_DIR/install_azure_persistent_rdma_naming.sh  || true

# optimizations
RUN . ./set_properties.sh && \
     $UBUNTU_COMMON_DIR/hpc-tuning.sh || true

# Install AZNFS Mount Helper
# $COMMON_DIR/install_aznfs.sh

RUN . ./set_properties.sh && \
    # copy test file
    $COMMON_DIR/copy_test_file.sh && \
    $COMMON_DIR/install_monitoring_tools.sh || true && \
    $COMMON_DIR/install_amd_libs.sh || true && \
    $COMMON_DIR/setup_sku_customizations.sh || true

# NOW ADD FLUX
# Install openpmix, prrte
WORKDIR /opt/prrte
RUN git clone https://github.com/openpmix/openpmix.git && \
    git clone https://github.com/openpmix/prrte.git && \
    ls -l && \
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
    rm -rf prrte

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
    make install && cd /opt && rm -rf flux-core-0.61.2

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
