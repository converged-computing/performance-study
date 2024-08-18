#!/bin/bash

set -eu pipefail

sudo chown -R $USER /opt && \
    mkdir -p /opt/prrte && \
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

# prrte you are sure looking perrrty today
cd /opt/prrte/prrte && \
  git checkout 477894f4720d822b15cab56eee7665107832921c && \
  ./autogen.pl && \
  ./configure --prefix=/usr && sudo make -j 4 install

# flux security
git clone --depth 1 https://github.com/flux-framework/flux-security /opt/flux-security && \
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

# Make the flux run directory
mkdir -p /home/ubuntu/run/flux

# Flux core
git clone https://github.com/flux-framework/flux-core /opt/flux-core && \
    cd /opt/flux-core && \
    ./autogen.sh && \
    ./configure --prefix=/usr --sysconfdir=/etc --runstatedir=/home/flux/run --with-flux-security && \
    make clean && \
    make && sudo make install

# Flux pmix (must be installed after flux core)
git clone https://github.com/flux-framework/flux-pmix /opt/flux-pmix && \
  cd /opt/flux-pmix && \
  ./autogen.sh && \
  ./configure --prefix=/usr && \
  make && \
  sudo make install

# Flux sched
sudo git clone https://github.com/flux-framework/flux-sched /opt/flux-sched && \
    sudo chown -R $USER /opt/flux-sched && \ 
    cd /opt/flux-sched && \
    git fetch && \
    mkdir build && \
    cd build
    ../configure --prefix=/usr --sysconfdir=/etc && \
    make -j 4 && sudo make install && sudo ldconfig && \
    echo "DONE flux build"

# Flux curve.cert
# Ensure we have a shared curve certificate
flux keygen /tmp/curve.cert && \
    sudo mkdir -p /etc/flux/system && \
    sudo cp /tmp/curve.cert /etc/flux/system/curve.cert && \
    sudo chown ubuntu /etc/flux/system/curve.cert && \
    sudo chmod o-r /etc/flux/system/curve.cert && \
    sudo chmod g-r /etc/flux/system/curve.cert && \
    # Permissions for imp
    sudo chmod u+s /usr/libexec/flux/flux-imp && \
    sudo chmod 4755 /usr/libexec/flux/flux-imp && \
    # /var/lib/flux needs to be owned by the instance owner
    sudo mkdir -p /var/lib/flux && \
    sudo chown $USER -R /var/lib/flux && \
    # clean up
    cd /
    sudo rm -rf /opt/flux-core /opt/flux-sched /opt/prrte /opt/flux-security
