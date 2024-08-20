FROM ghcr.io/converged-computing/azurehpc:flux-gpu
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-amg2023:azure-hpc-gpu-ubuntu2204 .
#  docker push ghcr.io/converged-computing/metric-amg2023:azure-hpc-gpu-ubuntu2204

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin

# What we want to install and how we want to install it
# is specified in a manifest file (spack.yaml)
# IMPORTANT: cpu gets +int64, and gpu +mixedint
WORKDIR /opt/spack-environment
COPY ./spack.yaml /opt/spack-environment/spack.yaml

ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

# NOTE: this does not work, it freezes.
# Install the software, remove unnecessary deps
RUN cd /opt/spack-environment \
    && git clone --depth 1 --branch v0.22.1 https://github.com/spack/spack.git \
    && . spack/share/spack/setup-env.sh \
    && spack env activate . \
    && spack external find openssh \
    && spack external find cmake \
    && spack install --reuse --fail-fast \
    && spack gc -y

# Modifications to the environment that are necessary to run
RUN cd /opt/spack-environment \
    && . spack/share/spack/setup-env.sh \
    && spack env activate --sh -d . >> /etc/profile.d/z10_spack_environment.sh

WORKDIR /opt
EXPOSE 22
