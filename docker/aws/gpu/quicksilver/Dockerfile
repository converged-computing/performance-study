FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build -t ghcr.io/converged-computing/metric-quicksilver-gpu:libfabric .
#  docker push ghcr.io/converged-computing/metric-quicksilver-gpu:libfabric

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
    apt-get install -y fftw3-dev fftw3 pdsh \
        openssh-client openssh-server \
        dnsutils telnet strace git g++ \
        unzip bzip2

# Needed for libfabric
RUN apt-get install -y \
        libibverbs-dev \
        librdmacm-dev \
        rdma-core
        
RUN git clone https://github.com/ofiwg/libfabric.git /opt/libfabric && \
    cd libfabric && ./autogen.sh && \
    ./configure --enable-efa=yes --enable-tcp=yes --enable-udp=yes --enable-sockets=yes --enable-verbs=yes --enable-shm=yes --enable-mrail=yes --enable-rxd=yes --enable-rxm=yes && \
    make && make install

# install openmpi with cuda
WORKDIR /opt
RUN mkdir -p /usr/local/pancakes && \
    wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.2.tar.gz && \
    tar -xzvf openmpi-4.1.2.tar.gz && \
    cd openmpi-4.1.2 && \
    ./configure --with-cuda --with-ofi=/usr/local --prefix=/usr/local/pancakes && \
    make && make install

ENV CUDA_VISIBLE_DEVICES=0,1,2,3
ENV PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/pancakes/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV LD_LIBRARY_PATH=/usr/local/pancakes/lib:/opt/miniconda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64

WORKDIR /opt

# Example command
# qs /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp

# All examples:
# /opt/quicksilver/Examples/AllScattering/scatteringOnly.inp
# /opt/quicksilver/Examples/NoCollisions/no.collisions.inp
# /opt/quicksilver/Examples/NonFlatXC/NonFlatXC.inp
# /opt/quicksilver/Examples/CORAL2_Benchmark/Problem2/Coral2_P2_4096.inp
# /opt/quicksilver/Examples/CORAL2_Benchmark/Problem2/Coral2_P2.inp
# /opt/quicksilver/Examples/CORAL2_Benchmark/Problem2/Coral2_P2_1.inp
# /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp
# /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1_1.inp
# /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1_4096.inp
# /opt/quicksilver/Examples/CTS2_Benchmark/CTS2.inp
# /opt/quicksilver/Examples/CTS2_Benchmark/CTS2_36.inp
# /opt/quicksilver/Examples/CTS2_Benchmark/CTS2_1.inp
# /opt/quicksilver/Examples/AllAbsorb/allAbsorb.inp
# /opt/quicksilver/Examples/Homogeneous/homogeneousProblem_v4_ts.inp
# /opt/quicksilver/Examples/Homogeneous/homogeneousProblem_v5_ts.inp
# /opt/quicksilver/Examples/Homogeneous/homogeneousProblem.inp
# /opt/quicksilver/Examples/Homogeneous/homogeneousProblem_v3_wq.inp
# /opt/quicksilver/Examples/Homogeneous/homogeneousProblem_v7_ts.inp
# /opt/quicksilver/Examples/Homogeneous/homogeneousProblem_v4_tm.inp
# /opt/quicksilver/Examples/Homogeneous/homogeneousProblem_v3.inp
# /opt/quicksilver/Examples/AllEscape/allEscape.inp
# /opt/quicksilver/Examples/NoFission/noFission.inp

RUN apt-get update && \
    apt-get install -y fftw3-dev fftw3 pdsh \
        openssh-client openssh-server \
        dnsutils telnet strace cmake git g++ \
        unzip bzip2

WORKDIR /opt
RUN git clone https://github.com/LLNL/Quicksilver quicksilver
COPY ./Makefile /opt/quicksilver/src/Makefile
WORKDIR /opt/quicksilver/src
RUN make || nvcc -DHAVE_CUDA -std=c++11 -O2 -Xptxas -v -gencode=arch=compute_70,code=\"sm_70,compute_70\" --compiler-bindir=/usr/local/pancakes/bin/mpicxx -L/usr/local/cuda/lib64/ -lcuda -lcudart -lm -o qs CollisionEvent.o CoralBenchmark.o CycleTracking.o DecompositionObject.o DirectionCosine.o EnergySpectrum.o GlobalFccGrid.o GridAssignmentObject.o InputBlock.o MCT.o MC_Adjacent_Facet.o MC_Base_Particle.o MC_Domain.o MC_Facet_Crossing_Event.o MC_Fast_Timer.o MC_Load_Particle.o MC_Location.o MC_Particle_Buffer.o MC_RNG_State.o MC_Segment_Outcome.o MC_SourceNow.o MacroscopicCrossSection.o MeshPartition.o MonteCarlo.o MpiCommObject.o NuclearData.o Parameters.o ParticleVault.o ParticleVaultContainer.o PopulationControl.o SendQueue.o SharedMemoryCommObject.o Tallies.o cmdLineParser.o cudaFunctions.o initMC.o main.o parseUtils.o utils.o utilsMpi.o && cp qs /usr/bin/qs

EXPOSE 22
WORKDIR /opt/quicksilver/Examples

# Finally, install oras for saving artifacts
RUN export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/

# Ensure we add path where libfabric is!
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
