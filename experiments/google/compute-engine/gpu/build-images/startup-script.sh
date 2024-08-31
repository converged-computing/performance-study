# DO THIS FIRST for v100
# https://cloud.google.com/compute/docs/gpus/install-drivers-gpu

wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda-repo-rhel8-12-2-local-12.2.0_535.54.03-1.x86_64.rpm
sudo rpm -i cuda-repo-rhel8-12-2-local-12.2.0_535.54.03-1.x86_64.rpm
sudo dnf clean all
sudo dnf -y module install nvidia-driver:latest-dkms
sudo dnf -y install cuda

cat << "EOF" >> gcsfuse.repo
[gcsfuse]
name=gcsfuse (packages.cloud.google.com)
baseurl=https://packages.cloud.google.com/yum/repos/gcsfuse-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
       https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF

sudo mv ./gcsfuse.repo /etc/yum.repos.d/gcsfuse.repo
sudo dnf update -y
sudo dnf clean all

sudo dnf group install -y "Development Tools"

sudo dnf config-manager --set-enabled powertools
sudo dnf install -y epel-release

sudo dnf install -y \
    cmake \
    munge \
    munge-devel \
    hwloc \
    hwloc-devel \
    pmix \
    pmix-devel \
    lua \
    lua-devel \
    lua-posix \
    libevent-devel \
    czmq-devel \
    jansson-devel \
    lz4-devel \
    sqlite-devel \
    ncurses-devel \
    libarchive-devel \
    libxml2-devel \
    yaml-cpp-devel \
    boost-devel \
    libedit-devel \
    nfs-utils \
    python3-devel \
    python3-cffi \
    python3-yaml \
    python3-jsonschema \
    python3-sphinx \
    python3-docutils \
    aspell \
    aspell-en \
    valgrind-devel \
#    openmpi.x86_64 \
#    openmpi-devel.x86_64 \
    gcsfuse \
    jq \
    wget

# IMPORTANT: the flux user/group must match!
# useradd -M -r -s /bin/false -c "flux-framework identity" flux
sudo groupadd -g 1004 flux
sudo useradd -u 1004 -g 1004 -M -r -s /bin/false -c "flux-framework identity" flux

# install openmpi with cuda
sudo mkdir -p /usr/local/pancakes && \
    wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.2.tar.gz && \
    tar -xzvf openmpi-4.1.2.tar.gz && \
    cd openmpi-4.1.2 && \
    ./configure --with-cuda --prefix=/usr/local/pancakes && \
    make && sudo make install

# These will need to be added to user's home
# PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/pancakes/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# LD_LIBRARY_PATH=/usr/local/pancakes/lib:/opt/miniconda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64

# Update grub
# cat /etc/default/grub | grep GRUB_CMDLINE_LINUX=
# sed -i -e 's/^GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="systemd.unified_cgroup_hierarchy=1"/' /etc/default/grub
# update-grub

sudo dnf install -y grubby 
sudo grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=1"

sudo chown -R $USER /usr/share
cd /usr/share

# These versions are chosen to match the demo container
git clone https://github.com/flux-framework/flux-core.git
git clone https://github.com/flux-framework/flux-security.git
git clone https://github.com/flux-framework/flux-pmix.git

# Install flux security
cd /usr/share/flux-security
./autogen.sh
./configure --prefix=/usr --sysconfdir=/etc
make -j 8
sudo make install

# The VMs will share the same munge key
sudo mkdir -p /var/run/munge && \
    dd if=/dev/urandom bs=1 count=1024 > munge.key && \
    sudo mv munge.key /etc/munge/munge.key && \
    sudo chown -R munge /etc/munge/munge.key /var/run/munge && \
    sudo chmod 600 /etc/munge/munge.key

# Flux core
cd /usr/share/flux-core

# If PKGCONFIG is used here it seems to default to /usr/local
./autogen.sh
./configure --prefix=/usr --sysconfdir=/etc --with-flux-security
make clean
make -j 8
sudo make install

# Flux sched (uses cmake now)
# cmake 3.26.5 is installed

# catch 22?
git clone https://github.com/catchorg/Catch2.git /tmp/catch
cd /tmp/catch
cmake -Bbuild -H. -DBUILD_TESTING=OFF
sudo cmake --build build/ --target install 

# Flux sched
cd /usr/share
wget https://github.com/flux-framework/flux-sched/releases/download/v0.33.0/flux-sched-0.33.0.tar.gz
tar -xzvf flux-sched-0.33.0.tar.gz
cd flux-sched-0.33.0
sudo ln $(which python3) /usr/bin/python
PYTHON=/usr/bin/python3 ./configure --prefix=/usr --sysconfdir=/etc
make -j 8 && sudo make install && sudo ldconfig

# Install openpmix, prrte (for flux-pmix)
sudo mkdir -p /opt/software
sudo chown -R $USER /opt/software
git clone https://github.com/openpmix/openpmix.git /opt/software/openpmix
git clone https://github.com/openpmix/prrte.git /opt/software/prrte
cd /opt/software/openpmix
git checkout fefaed568f33bf86f28afb6e45237f1ec5e4de93
./autogen.pl
./configure --prefix=/usr --disable-static && sudo make -j 4 install
ldconfig 
cd /opt/software/prrte
git checkout 477894f4720d822b15cab56eee7665107832921c
./autogen.pl
./configure --prefix=/usr && sudo make -j 4 install

# Flux-pmix
cd /usr/share/flux-pmix
./autogen.sh
./configure --prefix=/usr --sysconfdir=/etc
make -j8
sudo make install

# IMPORANT: the above installs to /usr/lib64 but you will get a flux_open error if it's
# not found in /usr/lib. So we put in both places :)
sudo cp -R /usr/lib64/flux /usr/lib/flux
sudo cp -R /usr/lib64/libflux-* /usr/lib/

# A quick Python script for handling decoding
# I don't think we are going to use this.
cat << "PYTHON_DECODING_SCRIPT" > ./convert_munge_key.py
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
sudo mv ./convert_munge_key.py /etc/flux/manager/convert_munge_key.py

echo "/usr/etc/flux/imp *(rw,no_subtree_check,no_root_squash)" >> ./exports
echo "/usr/etc/flux/security *(rw,no_subtree_check,no_root_squash)" >> ./exports
echo "/usr/etc/flux/system *(rw,no_subtree_check,no_root_squash)" >> ./exports
echo "/var/nfs/home *(rw,no_subtree_check,no_root_squash)" >> ./exports

sudo mv ./exports /etc/exports

sudo systemctl enable nfs-server

APPTAINER_ASSETS=$(curl -s https://api.github.com/repos/apptainer/apptainer/releases/latest | jq '.[] | match(".*assets$"; "g") | .string' 2>/dev/null | tr -d '"')
APPTAINER_RPM=$(curl -s ${APPTAINER_ASSETS} | jq '.[] | .browser_download_url' | egrep .*apptainer-[[:digit:]].*x86_64 | tr -d '"')
sudo dnf install -y ${APPTAINER_RPM}


# IMPORTANT: if you don't create the disk large, you can  come back later
# to resize (disks in the UI) and then attach, pull, and save a new template
# version

# Pull containers, assume user 1000 will use future terraform deploy
sudo mkdir -p /opt/containers
sudo chown -R 1000 /opt/containers

# oras
export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    sudo mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/

# flux start
# time flux run -o cpu-affinity=per-task -N1 -n 96 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 --pwd /code /home/ubuntu/containers/metric-lammps-cpu_azure-hpc.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 32 -v y 32 -v z 32 -var nsteps 1000

# --bind /usr/lib64/openmpi/lib/libmpi.so:/usr/local/lib/libmpi.so

# singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu
# singularity pull docker://ghcr.io/converged-computing/metric-amg:rocky-8

cd /opt/containers
singularity pull docker://ghcr.io/converged-computing/metric-mixbench:latest && \
singularity pull docker://ghcr.io/converged-computing/metric-magma:mnist && \
singularity pull docker://ghcr.io/converged-computing/metric-osu-gpu:latest && \
singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-int64-zen3 && \
singularity pull docker://ghcr.io/converged-computing/metric-minife:latest && \
singularity pull docker://ghcr.io/converged-computing/metric-lammps-gpu:libfabric-reax && \
singularity pull docker://ghcr.io/converged-computing/metric-lammps-gpu:kokkos-reax && \
singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu && \
singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-gpu:latest && \
singularity pull docker://ghcr.io/converged-computing/mt-gemm:latest && \
singularity pull docker://ghcr.io/converged-computing/metric-kripke-gpu:latest && \
singularity pull docker://ghcr.io/converged-computing/metric-stream:latest

# Install openmpi on host (same as in containers)
# apt-get update && \
#    apt-get install -y fftw3-dev fftw3 pdsh libfabric-dev libfabric1 \
#        openssh-client openssh-server \
#        dnsutils telnet strace git g++ \
#        unzip bzip2

# Create machine image on the command line
# gcloud beta compute machine-images create flux-singularity-rocky-8 --project=llnl-flux --description=Rocky\ 8\ \(HPC\ series\)\ of\ VM\ on\ c2d-standard-112\ \(56\ physical\ cores\)\ with\ Singularity\ installed,\ oras,\ and\ application\ containers\ pulled\ for\ the\ performance\ study. --source-instance=flux-builder --source-instance-zone=us-central1-f --storage-location=us
