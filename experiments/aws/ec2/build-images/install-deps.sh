#!/bin/bash

set -eu pipefail

# Install dependencies (might be some left over from BDF)
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && \
    sudo apt-get upgrade -y && \
    sudo apt-get install -y apt-transport-https ca-certificates curl clang llvm jq apt-utils wget \
         libelf-dev libpcap-dev libbfd-dev binutils-dev build-essential make \
         linux-tools-common linux-tools-$(uname -r)  \
         bpfcc-tools python3-pip git net-tools

export CMAKE=3.23.1
export CMAKE=3.23.1
curl -s -L https://github.com/Kitware/CMake/releases/download/v$CMAKE/cmake-$CMAKE-linux-x86_64.sh > cmake.sh && \
sudo sh cmake.sh --prefix=/usr/local --skip-license && \
    sudo apt-get install -y man flex ssh sudo vim luarocks munge lcov ccache lua5.2 \
         valgrind build-essential pkg-config autotools-dev libtool \
         libffi-dev autoconf automake make clang clang-tidy \
         gcc g++ libpam-dev apt-utils \
         libsodium-dev libzmq3-dev libczmq-dev libjansson-dev libmunge-dev \
         libncursesw5-dev liblua5.2-dev liblz4-dev libsqlite3-dev uuid-dev \
         libhwloc-dev libs3-dev libevent-dev libarchive-dev \
         libboost-graph-dev libboost-system-dev libboost-filesystem-dev \
         libboost-regex-dev libyaml-cpp-dev libedit-dev uidmap dbus-user-session

pip install --upgrade --ignore-installed markupsafe coverage cffi ply six pyyaml jsonschema
pip install --upgrade --ignore-installed sphinx sphinx-rtd-theme sphinxcontrib-spelling

# Prepare lua rocks things I don't understand
sudo apt-get install -y faketime libfaketime pylint cppcheck aspell aspell-en && \
    sudo locale-gen en_US.UTF-8 && \
    sudo luarocks install luaposix

# This is needed if you intend to use EFA (HPC instance type)
# Install EFA alone without AWS OPEN_MPI
# Note the version I got was 
export EFA_VERSION=latest
mkdir /tmp/efa 
cd /tmp/efa
curl -O https://s3-us-west-2.amazonaws.com/aws-efa-installer/aws-efa-installer-${EFA_VERSION}.tar.gz
tar -xf aws-efa-installer-${EFA_VERSION}.tar.gz
cd aws-efa-installer
sudo ./efa_installer.sh -y

# fi_info -p efa -t FI_EP_RDM
# Disable ptrace
# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa-start.html
sudo sysctl -w kernel.yama.ptrace_scope=0
