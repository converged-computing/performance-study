FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-devel

# docker build -t ghcr.io/converged-computing/pytorch-resnet-experiment:cpu .
# docker push ghcr.io/converged-computing/pytorch-resnet-experiment:cpu

ENV DEBIAN_FRONTEND=noninteractive

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
        python3-jsonschema \
        python3-cffi \
        python3-sphinx \
        python3-six \
        python3-ply \
        gcc \
        g++ && \
    rm -rf /var/lib/apt/lists/*

# Python - instead of a system python we install anaconda
# https://docs.conda.io/en/latest/miniconda.html#linux-installers
RUN python3 -m pip install --upgrade --ignore-installed \
        "markupsafe==2.0.0" \
        coverage sphinx-rtd-theme pyyaml ply sphinxcontrib-spelling 
        
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
        libpam-dev && \
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
    apt-get install -y fftw3-dev fftw3 pdsh libfabric-dev libfabric1 \
        openssh-client openssh-server \
        dnsutils telnet strace git g++ \
        unzip bzip2

# install openmpi with cuda
WORKDIR /opt
RUN wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.2.tar.gz && \
    tar -xzvf openmpi-4.1.2.tar.gz && \
    cd openmpi-4.1.2 && \
    ./configure && \
    make && make install && ldconfig

RUN pip install tqdm && \
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
COPY main.py launch.sh ./
CMD printenv

# Finally, install oras for saving artifacts
RUN export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/
