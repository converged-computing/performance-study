FROM rockylinux:8

# AMD
#  docker build -t ghcr.io/converged-computing/flux-rocky:8 .
#  docker push ghcr.io/converged-computing/metric-amg:rocky-8

RUN dnf update -y && dnf clean all && \
    dnf group install -y "Development Tools" && \
    dnf config-manager --set-enabled powertools && \
    dnf install -y epel-release

RUN dnf install -y \
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
    wget \
    jq

# IMPORTANT: the flux user/group must match!
# useradd -M -r -s /bin/false -c "flux-framework identity" flux
RUN groupadd -g 1004 flux && \
    useradd -u 1004 -g 1004 -M -r -s /bin/false -c "flux-framework identity" flux

RUN dnf install -y grubby && \
    grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=1"

WORKDIR /usr/share

# These versions are chosen to match the demo container
RUN git clone https://github.com/flux-framework/flux-core.git && \
    git clone https://github.com/flux-framework/flux-security.git && \
    git clone https://github.com/flux-framework/flux-pmix.git

# Install flux security
RUN cd /usr/share/flux-security && \
    ./autogen.sh && \
    ./configure --prefix=/usr --sysconfdir=/etc  && \
    make -j 4 && make install

# The VMs will share the same munge key
RUN mkdir -p /var/run/munge && \
    dd if=/dev/urandom bs=1 count=1024 > munge.key && \
    mv munge.key /etc/munge/munge.key && \
    chown -R munge /etc/munge/munge.key /var/run/munge && \
    chmod 600 /etc/munge/munge.key

# Flux core
RUN cd /usr/share/flux-core && \
    ./autogen.sh && \
    ./configure --prefix=/usr --sysconfdir=/etc --with-flux-security && \
    make clean && \
    make -j 4 && make install

# Flux sched
RUN cd /usr/share && \
    wget https://github.com/flux-framework/flux-sched/releases/download/v0.33.1/flux-sched-0.33.1.tar.gz && \
    tar -xzvf flux-sched-0.33.1.tar.gz && \
    cd flux-sched-0.33.1 && \
    ln $(which python3) /usr/bin/python && \
    PYTHON=/usr/bin/python3 ./configure --prefix=/usr --sysconfdir=/etc && \
    make -j 4 && make install && ldconfig

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
    rm -rf prrte && set +x

# Flux-pmix
RUN cd /usr/share/flux-pmix && \
    ./autogen.sh && \
    ./configure --prefix=/usr --sysconfdir=/etc  && \
    make -j4  && \
    make install

RUN yum install -y git
RUN cd /tmp && wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.2.tar.gz && \
    tar -xzvf openmpi-4.1.2.tar.gz && \
    cd openmpi-4.1.2 && \
    ./configure --prefix=/usr/local && \
    make -j4 && make install && ldconfig

# IMPORANT: the above installs to /usr/lib64 but you will get a flux_open error if it's
# not found in /usr/lib. So we put in both places :)
RUN cp -R /usr/lib64/flux /usr/lib/flux && cp -R /usr/lib64/libflux-* /usr/lib/
