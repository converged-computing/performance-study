#!/bin/bash

# select "GPU" and ubuntu 22.04 amd64, n1-standard-32 with 4gpu
# This is the script used for the build.

# Install nvidia drivers and cuda
sudo systemctl stop google-cloud-ops-agent
curl -L https://github.com/GoogleCloudPlatform/compute-gpu-installation/releases/download/cuda-installer-v1.1.0/cuda_installer.pyz --output cuda_installer.pyz
sudo python3 cuda_installer.pyz install_driver
# Both will log you out, log in again and re-run commands
sudo python3 cuda_installer.pyz install_cuda
sudo python3 cuda_installer.pyz verify_cuda

# Install dependencies (might be some left over from BDF)
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && \
    sudo apt-get upgrade -y && \
    sudo apt-get install -y apt-transport-https ca-certificates curl clang llvm jq apt-utils wget \
         libelf-dev libpcap-dev libbfd-dev binutils-dev build-essential make \
         bpfcc-tools net-tools python3-pip

CMAKE=3.23.1
curl -s -L https://github.com/Kitware/CMake/releases/download/v$CMAKE/cmake-$CMAKE-linux-x86_64.sh > cmake.sh && \
sudo sh cmake.sh --prefix=/usr/local --skip-license

sudo apt-get install -y man flex ssh sudo vim luarocks munge lcov ccache lua5.2 \
         valgrind build-essential pkg-config autotools-dev libtool \
         libffi-dev autoconf automake make clang clang-tidy \
         gcc g++ libpam-dev apt-utils \
         libsodium-dev libzmq3-dev libczmq-dev libjansson-dev libmunge-dev \
         libncursesw5-dev liblua5.2-dev liblz4-dev libsqlite3-dev uuid-dev \
         libhwloc-dev libs3-dev libevent-dev libarchive-dev \
         libboost-graph-dev libboost-system-dev libboost-filesystem-dev \
         libboost-regex-dev libyaml-cpp-dev libedit-dev uidmap dbus-user-session

# pip is installed in image to conda
sudo pip install --upgrade --ignore-installed markupsafe coverage cffi ply six pyyaml jsonschema && \
sudo pip install --upgrade --ignore-installed sphinx sphinx-rtd-theme sphinxcontrib-spelling

sudo apt-get install -y locales
sudo apt-get install -y faketime libfaketime pylint cppcheck aspell aspell-en && \
    sudo locale-gen en_US.UTF-8 && \
    sudo luarocks install luaposix
    
sudo mkdir -p /opt/prrte && \
    sudo chown $USER /opt/prrte && \
    cd /opt/prrte && \
    git clone https://github.com/openpmix/openpmix.git && \
    git clone https://github.com/openpmix/prrte.git && \
    set -x && \
    cd openpmix && \
    git checkout fefaed568f33bf86f28afb6e45237f1ec5e4de93 && \
    ./autogen.pl && \
    ./configure --prefix=/usr --disable-static && sudo make -j 4 install && \
    sudo ldconfig

set +x

cd /opt/prrte/prrte && \
    git checkout 477894f4720d822b15cab56eee7665107832921c && \
   ./autogen.pl && \
   ./configure --prefix=/usr && sudo make -j 4 install

# flux security
sudo git clone --depth 1 https://github.com/flux-framework/flux-security /opt/flux-security && \
    sudo chown -R $USER /opt/flux-security && \ 
    cd /opt/flux-security && \
    ./autogen.sh && \
    ./configure --prefix=/usr --sysconfdir=/etc && \
    make && sudo make install

# The VMs will share the same munge key
sudo mkdir -p /var/run/munge && \
    dd if=/dev/urandom bs=1 count=1024 > munge.key && \
    sudo mv munge.key /etc/munge/munge.key && \
    sudo chown -R munge /etc/munge/munge.key /var/run/munge && \
    sudo chmod 600 /etc/munge/munge.key

# Flux core
sudo git clone https://github.com/flux-framework/flux-core /opt/flux-core && \
    sudo chown -R $USER /opt/flux-core && \ 
    cd /opt/flux-core && \
    ./autogen.sh && \
    ./configure --prefix=/usr --sysconfdir=/etc --runstatedir=/home/flux/run --with-flux-security && \
    make clean && \
    make && sudo make install

# Flux pmix (must be installed after flux core)
sudo git clone https://github.com/flux-framework/flux-pmix /opt/flux-pmix && \
    sudo chown -R $USER /opt/flux-pmix && \ 
    cd /opt/flux-pmix && \
    ./autogen.sh && \
    ./configure --prefix=/usr && \
    make && \
    sudo make install

# Flux sched (installing older version to avoid cmake deps)
cd /opt
sudo wget https://github.com/flux-framework/flux-sched/releases/download/v0.33.1/flux-sched-0.33.1.tar.gz
sudo tar -xzvf flux-sched-0.33.1.tar.gz
sudo mv flux-sched-0.33.1  flux-sched
sudo chown -R $USER /opt/flux-sched
cd flux-sched
./configure --prefix=/usr --sysconfdir=/etc
make -j 8 && sudo make install && sudo ldconfig

# install openmpi with cuda
cd /opt
sudo mkdir -p /usr/local/pancakes && \
    sudo wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.2.tar.gz && \
    sudo tar -xzvf openmpi-4.1.2.tar.gz && \
    cd openmpi-4.1.2 && \
    sudo chown -R $USER $(pwd) && \
    ./configure --with-cuda --prefix=/usr/local/pancakes && \
    make -j 20 && sudo make install

# TODO check these, should be provided in flux environment later
# ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
# ENV PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/pancakes/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# ENV LD_LIBRARY_PATH=/usr/local/pancakes/lib:/opt/miniconda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64

cd /opt

# Flux curve.cert (this is also generated on create)   

# SINGULARITY
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
sudo wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
sudo tar -xvf go1.21.0.linux-amd64.tar.gz
sudo mv go /usr/local && sudo rm go1.21.0.linux-amd64.tar.gz
export PATH=/usr/local/go/bin:$PATH

# Install singularity
export VERSION=4.0.1 && \
    sudo wget https://github.com/sylabs/singularity/releases/download/v${VERSION}/singularity-ce-${VERSION}.tar.gz && \
    sudo tar -xzf singularity-ce-${VERSION}.tar.gz && \
    sudo chown -R $USER singularity-ce-${VERSION} && \
    cd singularity-ce-${VERSION}

./mconfig && \
 make -C builddir && \
 sudo make -C builddir install

cd /opt
sudo rm -rf singularity-ce-4.0.1

export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s`
echo "deb [signed-by=/usr/share/keyrings/cloud.google.asc] https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo tee /usr/share/keyrings/cloud.google.asc
sudo apt-get update
sudo apt-get install gcsfuse

# Not sure if we need this, go for it anyway
sudo groupadd -g 1004 flux
sudo useradd -u 1004 -g 1004 -M -r -s /bin/false -c "flux-framework identity" flux

# Update grub
cat /etc/default/grub | grep GRUB_CMDLINE_LINUX=
sudo sed -i -e 's/^GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="systemd.unified_cgroup_hierarchy=1"/' /etc/default/grub
sudo update-grub

# A quick Python script for handling decoding
# I don't think we are going to use this.
cat << "PYTHON_DECODING_SCRIPT" > /tmp/convert_munge_key.py
#!/usr/bin/env python3

import sys
import base64

string = sys.argv[1]
dest = sys.argv[2]
encoded = string.encode('utf-8')
with open(dest, 'wb') as fd:
    fd.write(base64.b64decode(encoded))
PYTHON_DECODING_SCRIPT

sudo mkdir -p /etc/flux/manager
sudo mv /tmp/convert_munge_key.py /etc/flux/manager/convert_munge_key.py

echo "/etc/flux/imp *(rw,no_subtree_check,no_root_squash)" >> /tmp/exports
echo "/etc/flux/security *(rw,no_subtree_check,no_root_squash)" >> /tmp/exports
echo "/etc/flux/system *(rw,no_subtree_check,no_root_squash)" >> /tmp/exports
echo "/var/nfs/home *(rw,no_subtree_check,no_root_squash)" >> /tmp/exports

sudo mv /tmp/exports /etc/exports
sudo apt-get install -y nfs-kernel-server
sudo systemctl enable nfs-server

# Other flux prep we do here instead of on init
sudo mkdir -p /var/lib/flux
sudo mkdir -p /usr/etc/flux/system/conf.d
sudo chown -R flux /var/lib/flux

cd /tmp
echo "flux R encode --hosts=flux-[001-999]"
flux R encode --hosts=flux-[001-999] --local > R
sudo mv R /usr/etc/flux/system/R

sudo mkdir -p /etc/flux/imp/conf.d/
cat <<EOT >> ./imp.toml
[exec]
allowed-users = [ "flux", "root" ]
allowed-shells = [ "/usr/libexec/flux/flux-shell" ]
EOT
sudo mv ./imp.toml /etc/flux/imp/conf.d/imp.toml

cat <<EOT >> /tmp/system.toml
[exec]
imp = "/usr/libexec/flux/flux-imp"

[access]
allow-guest-user = true
allow-root-owner = true

[bootstrap]
curve_cert = "/etc/flux/system/curve.cert"

default_port = 8050
default_bind = "tcp://ens12:%p"
default_connect = "tcp://%h:%p"

hosts = [{host="flux-[001-999]"}]

# Speed up detection of crashed network peers (system default is around 20m)
[tbon]
tcp_user_timeout = "2m"

# Point to resource definition generated with flux-R(1).
# Uncomment to exclude nodes (e.g. mgmt, login), from eligibility to run jobs.
[resource]
path = "/usr/etc/flux/system/R"

# Remove inactive jobs from the KVS after one week.
[job-manager]
inactive-age-limit = "7d"
EOT
sudo mv /tmp/system.toml /usr/etc/flux/system/conf.d/system.toml

sudo chmod u+s /usr/libexec/flux/flux-imp
sudo chmod 4755 /usr/libexec/flux/flux-imp
sudo chmod 0644 /etc/flux/imp/conf.d/imp.toml
sudo chown -R flux:flux /usr/etc/flux/system/conf.d

flux keygen curve.cert
sudo mkdir -p /etc/flux/system
sudo mv curve.cert /etc/flux/system/curve.cert
sudo chmod u=r,g=,o= /etc/flux/system/curve.cert
sudo chown flux:flux /etc/flux/system/curve.cert

sudo mkdir -p /run/flux
sudo chown -R flux:flux /run/flux

# Remove group and other read
sudo chmod o-r /etc/flux/system/curve.cert
sudo chmod g-r /etc/flux/system/curve.cert
sudo chown -R flux /run/flux /var/lib/flux /etc/flux/system/curve.cert

sudo chmod u+s /usr/libexec/flux/flux-imp 
sudo chmod 4755 /usr/libexec/flux/flux-imp
sudo chown -R root /etc/flux/imp/conf.d

# Write service file
# /usr/lib/systemd/system/flux.service

# Add this to /etc/environment
# export FLUX_URI=local:///run/flux/local

cat << "FIRST_BOOT_UNIT" > ./flux.service
[Unit]
Description=Flux message broker
Wants=munge.service

[Service]
Type=simple
NotifyAccess=main
TimeoutStopSec=90
KillMode=mixed
ExecStart=/usr/bin/flux start --broker-opts --config /usr/etc/flux/system/conf.d -Stbon.fanout=256  -Srundir=/run/flux -Sbroker.rc2_none -Sstatedir=/var/lib/flux -Slocal-uri=local:///run/flux/local -Stbon.connect_timeout=5s -Stbon.zmqdebug=1  -Slog-stderr-level=7 -Slog-stderr-mode=local
SyslogIdentifier=flux
LimitMEMLOCK=infinity
TasksMax=infinity
LimitNPROC=infinity
Restart=always
RestartSec=5s
RestartPreventExitStatus=42
SuccessExitStatus=42
User=flux
Group=flux
PermissionsStartOnly=true
Delegate=yes

[Install]
WantedBy=multi-user.target
FIRST_BOOT_UNIT

sudo mv ./flux.service /usr/lib/systemd/system/flux.service
sudo systemctl enable flux.service

# IMPORTANT: if you don't create the disk large, you can  come back later
# to resize (disks in the UI) and then attach, pull, and save a new template
# version

# Pull containers, assume user 1000 will use future terraform deploy
sudo mkdir -p /opt/containers
sudo chown -R 1000 /opt/containers

# Don't forget to add entries to /etc/systemd/system.conf and /etc/systemd/user.conf and /etc/security/limits.conf for MEMLOCK and NPROC (in the first, should be infinity, in the second security should be unlimited) 

# oras
cd /tmp
export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    sudo mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/

cd /opt/containers
sudo chown -R $USER /opt/containers
# singularity pull docker://ghcr.io/converged-computing/metric-mixbench:latest && \
# singularity pull docker://ghcr.io/converged-computing/metric-magma:mnist && \
# singularity pull docker://ghcr.io/converged-computing/metric-osu-gpu:latest && \
#singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-int64-zen3 && \
# singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim
# singularity pull docker://ghcr.io/converged-computing/metric-minife:latest && \
# singularity pull docker://ghcr.io/converged-computing/metric-lammps-gpu:libfabric-reax && \
# singularity pull docker://ghcr.io/converged-computing/metric-lammps-gpu:kokkos-reax && \
# singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu-zen4-tmpfile && \
# singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-gpu:latest && \
# singularity pull docker://ghcr.io/converged-computing/mt-gemm:latest && \
# singularity pull docker://ghcr.io/converged-computing/metric-kripke-gpu:latest && \
# singularity pull docker://ghcr.io/converged-computing/metric-stream:latest

singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-int64-zen3 && \
# singularity pull docker://ghcr.io/converged-computing/metric-amg2023:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/metric-kripke-gpu:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/metric-lammps-gpu:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/metric-minife:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/metric-mixbench:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/mt-gemm:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/multi-gpu-models:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/metric-osu-gpu:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-gpu:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/pytorch-resnet-experiment:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/metric-stream:google-gpu && \
singularity pull docker://ghcr.io/converged-computing/metric-magma:google-gpu 

# Create machine image on the command line
# gcloud beta compute machine-images create flux-singularity-rocky-8 --project=llnl-flux --description=Rocky\ 8\ \(HPC\ series\)\ of\ VM\ on\ c2d-standard-112\ \(56\ physical\ cores\)\ with\ Singularity\ installed,\ oras,\ and\ application\ containers\ pulled\ for\ the\ performance\ study. --source-instance=flux-builder --source-instance-zone=us-central1-f --storage-location=us

# NCCL fast socket!
sudo apt-get update
sudo apt-get install -y --no-install-recommends --allow-change-held-packages apt-transport-https ca-certificates curl gnupg

# I did this manually.
sudo echo "deb https://packages.cloud.google.com/apt google-fast-socket main" | tee /etc/apt/sources.list.d/google-fast-socket.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add
sudo apt update && sudo apt install -y --no-install-recommends google-fast-socket=0.0.5
