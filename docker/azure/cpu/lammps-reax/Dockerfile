FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build -t ghcr.io/converged-computing/metric-lammps-cpu:azure-openmpi .
#  docker push ghcr.io/converged-computing/metric-lammps-cpu:azure

# oras artifact
# oras push ghcr.io/converged-computing/metric-lammps-cpu:libfabric-data ./common 

# Utilities
RUN apt-get update && \
    apt-get -qq install -y --no-install-recommends \
        apt-utils \
        locales \
        ca-certificates \
        wget \
        man \
        git \
        flex \
        ssh \
        sudo \
        vim \
        luarocks \
        munge \
        lcov \
        ccache \
        lua5.2 \
        python3-dev \
        python3-pip \
        valgrind \
        jq && \
    rm -rf /var/lib/apt/lists/*

# Compilers, autotools
RUN apt-get update && \
    apt-get -qq install -y --no-install-recommends \
        build-essential \
        pkg-config \
        autotools-dev \
        libtool \
	libffi-dev \
        autoconf \
        automake \
        make \
        clang \
        clang-tidy \
        gcc \
        g++ && \
    rm -rf /var/lib/apt/lists/*

# Python - instead of a system python we install anaconda
# https://docs.conda.io/en/latest/miniconda.html#linux-installers
RUN pip install --upgrade --ignore-installed \
        "markupsafe==2.0.0" \
        coverage cffi ply six pyyaml "jsonschema>=2.6,<4.0" \
        sphinx sphinx-rtd-theme sphinxcontrib-spelling 
        
RUN apt-get update && \
    apt-get -qq install -y --no-install-recommends \
        libsodium-dev \
        libzmq3-dev \
        libczmq-dev \
        libjansson-dev \
        libmunge-dev \
        libncursesw5-dev \
        liblua5.2-dev \
        liblz4-dev \
        libsqlite3-dev \
        uuid-dev \
        libhwloc-dev \
        libs3-dev \
        libevent-dev \
        libarchive-dev \
        libpam-dev \
        libibverbs-dev \
        librdmacm-dev \
        rdma-core && \
    rm -rf /var/lib/apt/lists/*

# Testing utils and libs
RUN apt-get update && \
    apt-get -qq install -y --no-install-recommends \
        faketime \
        libfaketime \
        pylint \
        cppcheck \
        enchant-2 \
        aspell \
        aspell-en && \
    rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8

# NOTE: luaposix installed by rocks due to Ubuntu bug: #1752082 https://bugs.launchpad.net/ubuntu/+source/lua-posix/+bug/1752082
RUN luarocks install luaposix

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
    rm -rf prrte

ENV LANG=C.UTF-8

ARG FLUX_SECURITY_VERSION=0.11.0

WORKDIR /opt
RUN CCACHE_DISABLE=1 && \
    V=$FLUX_SECURITY_VERSION && \
    PKG=flux-security-$V && \
    URL=https://github.com/flux-framework/flux-security/releases/download && \
    wget ${URL}/v${V}/${PKG}.tar.gz && \
    tar xvfz ${PKG}.tar.gz && \
    cd ${PKG} && \
    ./configure --prefix=/usr --sysconfdir=/etc || cat config.log && \
    make -j 4 && \
    make install && \
    cd .. && \
    rm -rf flux-security-*


# Setup MUNGE directories & key
RUN mkdir -p /var/run/munge && \
    dd if=/dev/urandom bs=1 count=1024 > /etc/munge/munge.key && \
    chown -R munge /etc/munge/munge.key /var/run/munge && \
    chmod 600 /etc/munge/munge.key

RUN wget https://github.com/flux-framework/flux-core/releases/download/v0.61.2/flux-core-0.61.2.tar.gz && \
    tar xzvf flux-core-0.61.2.tar.gz && \
    cd flux-core-0.61.2 && \
    ./configure --prefix=/usr --sysconfdir=/etc && \
    make clean && \
    make && \
    sudo make install

RUN sudo apt-get update
RUN sudo apt-get -qq install -y --no-install-recommends \
	libboost-graph-dev \
	libboost-system-dev \
	libboost-filesystem-dev \
	libboost-regex-dev \
	libyaml-cpp-dev \
	libedit-dev \
        libboost-dev \
        libyaml-cpp-dev \
	curl

# Flux pmix (must be installed after flux core)
RUN git clone https://github.com/flux-framework/flux-pmix /opt/flux-pmix && \
    cd /opt/flux-pmix && \
    ./autogen.sh && \
    ./configure --prefix=/usr && \
    make -j 4 && \
    make install && \
    cd /opt && \
    rm -rf flux-pmix && rm -rf flux-*.tar.gz

ENV LD_LIBRARY_PATH=/opt/miniconda/lib:$LD_LIBRARY_PATH

ENV CMAKE=3.23.1
RUN curl -s -L https://github.com/Kitware/CMake/releases/download/v$CMAKE/cmake-$CMAKE-linux-x86_64.sh > cmake.sh && \
    sudo sh cmake.sh --prefix=/usr/local --skip-license
    
RUN wget https://github.com/flux-framework/flux-sched/releases/download/v0.33.1/flux-sched-0.33.1.tar.gz && \
    tar -xzvf flux-sched-0.33.1.tar.gz && \
    cd flux-sched-0.33.1 && \
    ./configure --prefix=/usr --sysconfdir=/etc && \
    make && \
    sudo make install && \
    ldconfig

RUN apt-get update && \
    apt-get install -y fftw3-dev fftw3 pdsh \
        openssh-client openssh-server \
        dnsutils telnet strace git g++ \
        unzip bzip2

RUN git clone https://github.com/openucx/ucx /opt/ucx && \
    cd /opt/ucx && \
    ./autogen.sh && \
#    ./configure --with-dm --with-ib-hw-tm --with-dc --with-ud --with-rc --disable-optimizations --enable-logging --disable-assertions --enable-mt  --prefix=/usr && \
     ./configure --disable-logging --disable-debug --disable-assertions --disable-params-check --enable-mt --prefix=/usr --enable-examples --without-java --without-go  --without-xpmem && \
   make -j4 && \
   make install

#RUN wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.6.tar.gz && \
#    tar -xzvf openmpi-4.1.6.tar.gz && \
#    cd openmpi-4.1.6 && \
#    ./configure --prefix=/usr --disable-option-checking --disable-silent-rules --disable-maintainer-mode --with-platform=contrib/platform/mellanox/optimized --disable-dependency-tracking --enable-orterun-prefix-by-default && \
#    make -j 4 && make install && ldconfig

# Finally, install oras for saving artifacts
RUN export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/
    
# Ensure we add path where libfabric is!
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib

WORKDIR /opt
RUN oras pull ghcr.io/converged-computing/rdma-infiniband:ubuntu-22.04-tgz && \
    tar -xzvf MLNX_OFED_LINUX-24.04-0.7.0.0-ubuntu22.04-x86_64.tgz && \
    cd MLNX_OFED_LINUX-24.04-0.7.0.0-ubuntu22.04-x86_64/DEBS && \
    dpkg -i ucx_1.17.0-1.2404066_amd64.deb && \
    dpkg -i openmpi_4.1.7a1-1.2404066_all.deb

ENV PATH=/usr/mpi/gcc/openmpi-4.1.7a1/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/mpi/gcc/openmpi-4.1.7a1/lib:$LD_LIBRARY_PATH
WORKDIR /opt
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
  -D MPI_CXX_COMPILER=mpicxx \
  -D BUILD_MPI=yes \
  -D PKG_ML-SNAP=yes \
  -D PKG_GPU=no \
  -D PKG_REAXFF=on \
  -D PKG_KOKKOS=yes \
  ../cmake && make && make install
  
WORKDIR /code
COPY ./common .

# Make a copy for uid 1000, assuming ubuntu user
RUN cp -R /code /lammps && \
    cp -R /code/* /lammps/ && \
    chown -R 1000 /lammps
    
RUN apt-get update && apt-get install -y  infiniband-diags \
    libibumad3 \
    libibmad5 \
    libibnetdisc5 \
    libibmad-dev \
    libibumad-dev \
    libibnetdisc-dev \
    opensm \
    rdma-core rdmacm-utils librdmacm-dev \
    libibmad-dev libibumad-dev libibmad5 infiniband-diags libibnetdisc5
