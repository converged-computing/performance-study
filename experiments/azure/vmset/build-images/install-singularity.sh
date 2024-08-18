#!/bin/bash

set -eu pipefail

cd /opt

# flux start mpirun -n 6 singularity exec singularity-mpi_mpich.sif /opt/mpitest
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

# make room
sudo rm -rf /opt/mvapich2-2.3.7-1/
sudo apt autoremove && sudo apt clean

# install go
cd /tmp
sudo wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
sudo tar -xvf go1.21.0.linux-amd64.tar.gz
sudo rm go1.21.0.linux-amd64.tar.gz
export PATH=/tmp/go/bin:$PATH
export GOCACHE=/tmp/.cache/go

# Install singularity
export VERSION=4.0.1 && \
    sudo wget https://github.com/sylabs/singularity/releases/download/v${VERSION}/singularity-ce-${VERSION}.tar.gz && \
    sudo tar -xzf singularity-ce-${VERSION}.tar.gz && \
    sudo chown -R $USER singularity-ce-${VERSION} && \
    cd singularity-ce-${VERSION}

./mconfig && \
 make -C builddir && \
 sudo make -C builddir install

# IMPORTANT: if you don't create the disk large, you can  come back later
# to resize (disks in the UI) and then attach, pull, and save a new template
# version
cd /tmp
sudo rm -rf singularity-ce-4.0.1 singularity-ce*.tar.gz

# Pull containers
sudo mkdir -p /mnt/tmp /mnt/.singularity
sudo chown -R $USER /mnt/tmp /mnt/.singularity
export SINGULARITY_CACHEDIR=/mnt/.singularity
export SINGULARITY_TMPDIR=/mnt/tmp
echo "export SINGULARITY_CACHEDIR=/mnt/.singularity" >> /home/ubuntu/.bashrc
echo "export SINGULARITY_TMPDIR=/mnt/tmp" >> /home/ubuntu/.bashrc
mkdir -p /home/ubuntu/containers
cd /home/ubuntu/containers

# Testing lammps after pull
export OMPI_MCA_btl="^openib"
export UCX_TLS=ib
export UCX_UNIFIED_MODE=y
export UCX_NET_DEVICES=mlx5_ib0:1
export OMPI_MCA_btl_openib_warn_no_device_params_found=0

echo "export OMPI_MCA_btl=\"^openib\"" >> /home/ubuntu/.bashrc
echo "export UCX_TLS=ib" >> /home/ubuntu/.bashrc
echo "export UCX_UNIFIED_MODE=y" >> /home/ubuntu/.bashrc
echo "export UCX_NET_DEVICES=mlx5_ib0:1" >> /home/ubuntu/.bashrc
echo "export OMPI_MCA_btl_openib_warn_no_device_params_found=0" >> /home/ubuntu/.bashrc

# flux start
# time flux run -o cpu-affinity=per-task -N1 -n 96 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 --pwd /code /home/ubuntu/containers/metric-lammps-cpu_azure-hpc.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 32 -v y 32 -v z 32 -var nsteps 1000

singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:azure-hpc
singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:azure-hpc
singularity pull docker://ghcr.io/converged-computing/metric-amg:azure-hpc 
singularity pull docker://ghcr.io/converged-computing/metric-laghos:azure-hpc
singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu-zen4
singularity pull docker://ghcr.io/converged-computing/metric-minife:azure-hpc
singularity pull docker://ghcr.io/converged-computing/metric-mixbench:azure-hpc
singularity pull docker://ghcr.io/converged-computing/mt-gemm:azure-hpc
singularity pull docker://ghcr.io/converged-computing/metric-osu-cpu:azure-hpc
singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-cpu:azure-hpc
singularity pull docker://ghcr.io/converged-computing/metric-stream:azure-hpc

