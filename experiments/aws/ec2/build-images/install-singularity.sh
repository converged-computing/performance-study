#!/bin/bash

set -eu pipefail

cd /opt

sudo apt-get update && sudo apt-get install -y libseccomp-dev libglib2.0-dev cryptsetup \
   libfuse-dev \
   squashfs-tools \
   squashfs-tools-ng \
   uidmap \
   zlib1g-dev \
   iperf3

sudo apt-get install -y \
   autoconf \
   automake \
   cryptsetup \
   git \
   libfuse-dev \
   libglib2.0-dev \
   libseccomp-dev \
   libtool \
   pkg-config \
   runc \
   squashfs-tools \
   squashfs-tools-ng \
   uidmap \
   wget \
   zlib1g-dev

# install go
wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
tar -xvf go1.21.0.linux-amd64.tar.gz
sudo mv go /usr/local && rm go1.21.0.linux-amd64.tar.gz
export PATH=/usr/local/go/bin:$PATH

# Install singularity
export VERSION=4.0.1 && \
    wget https://github.com/sylabs/singularity/releases/download/v${VERSION}/singularity-ce-${VERSION}.tar.gz && \
    tar -xzf singularity-ce-${VERSION}.tar.gz && \
    cd singularity-ce-${VERSION}

./mconfig && \
 make -C builddir && \
 sudo make -j 4 -C builddir install
