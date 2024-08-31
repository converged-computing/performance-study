cat << "EOF" >> /etc/yum.repos.d/gcsfuse.repo
[gcsfuse]
name=gcsfuse (packages.cloud.google.com)
baseurl=https://packages.cloud.google.com/yum/repos/gcsfuse-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg
       https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOF


dnf update -y
dnf clean all

dnf group install -y "Development Tools"

dnf config-manager --set-enabled powertools
dnf install -y epel-release

dnf install -y \
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
    openmpi.x86_64 \
    openmpi-devel.x86_64 \
    gcsfuse \
    jq

# IMPORTANT: the flux user/group must match!
# useradd -M -r -s /bin/false -c "flux-framework identity" flux
groupadd -g 1004 flux
useradd -u 1004 -g 1004 -M -r -s /bin/false -c "flux-framework identity" flux

# Update grub
# cat /etc/default/grub | grep GRUB_CMDLINE_LINUX=
# sed -i -e 's/^GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="systemd.unified_cgroup_hierarchy=1"/' /etc/default/grub
# update-grub

dnf install -y grubby 
grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=1"

cd /usr/share

# These versions are chosen to match the demo container
git clone https://github.com/flux-framework/flux-core.git
git clone https://github.com/flux-framework/flux-sched.git
git clone https://github.com/flux-framework/flux-security.git
git clone https://github.com/flux-framework/flux-pmix.git

# Install flux security
cd /usr/share/flux-security
./autogen.sh
./configure --prefix=/usr --sysconfdir=/etc
make -j 8
make install

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
./configure --prefix=/usr --sysconfdir=/etc --runstatedir=/home/flux/run --with-flux-security
make clean
make -j 8
make install

# Flux sched (uses cmake now)
export CMAKE=3.23.1
curl -s -L https://github.com/Kitware/CMake/releases/download/v$CMAKE/cmake-$CMAKE-linux-x86_64.sh > cmake.sh 
sh cmake.sh --prefix=/usr/local --skip-license

cd /usr/share/flux-sched
./autogen.sh
./configure --prefix=/usr --sysconfdir=/etc

make -j 8
make install

# Install openpmix, prrte (for flux-pmix)
git clone https://github.com/openpmix/openpmix.git /opt/openpmix
git clone https://github.com/openpmix/prrte.git /opt/prrte
cd /opt/openpmix
git checkout fefaed568f33bf86f28afb6e45237f1ec5e4de93
./autogen.pl
./configure --prefix=/usr --disable-static && make -j 4 install
ldconfig 
cd /opt/prrte
git checkout 477894f4720d822b15cab56eee7665107832921c
./autogen.pl
./configure --prefix=/usr && make -j 4 install

# Flux-pmix
cd /usr/share/flux-pmix
./autogen.sh
./configure --prefix=/usr --sysconfdir=/etc

make
make install

# IMPORANT: the above installs to /usr/lib64 but you will get a flux_open error if it's
# not found in /usr/lib. So we put in both places :)
cp -R /usr/lib64/flux /usr/lib/flux
cp -R /usr/lib64/libflux-* /usr/lib/

# A quick Python script for handling decoding
# I don't think we are going to use this.
cat << "PYTHON_DECODING_SCRIPT" > /etc/flux/manager/convert_munge_key.py
#!/usr/bin/env python3

import sys
import base64

string = sys.argv[1]
dest = sys.argv[2]
encoded = string.encode('utf-8')
with open(dest, 'wb') as fd:
    fd.write(base64.b64decode(encoded))
PYTHON_DECODING_SCRIPT

echo "/usr/etc/flux/imp *(rw,no_subtree_check,no_root_squash)" >> /etc/exports
echo "/usr/etc/flux/security *(rw,no_subtree_check,no_root_squash)" >> /etc/exports
echo "/usr/etc/flux/system *(rw,no_subtree_check,no_root_squash)" >> /etc/exports

systemctl enable nfs-server
