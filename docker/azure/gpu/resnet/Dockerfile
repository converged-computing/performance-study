FROM ghcr.io/converged-computing/azurehpc:flux-gpu

# docker build -t ghcr.io/converged-computing/pytorch-resnet-experiment:azure-gpu .
# docker push ghcr.io/converged-computing/pytorch-resnet-experiment:azure-gpu

ARG PYTHON_VERSION=3.11
ENV DEBIAN_FRONTEND=noninteractive
ENV UCX_NET_DEVICES=mlx5_0:1
ENV UCX_TLS=ib
ENV OMPI_MCA_btl_openib_warn_no_device_params_found=0

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        ccache \
        cmake \
        curl \
        git \
        libjpeg-dev \
        libpng-dev && \
    rm -rf /var/lib/apt/lists/*

RUN /usr/sbin/update-ccache-symlinks
RUN mkdir /opt/ccache && ccache --set-config=cache_dir=/opt/ccache
ENV PATH=/opt/conda/bin:$PATH

RUN curl -fsSL -v -o ~/miniconda.sh -O  "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"

COPY requirements.txt .
# Manually invoke bash on miniconda script per https://github.com/conda/conda/issues/10431
RUN chmod +x ~/miniconda.sh && \
    bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda install -y python=${PYTHON_VERSION} cmake conda-build pyyaml numpy ipython && \
    /opt/conda/bin/python -mpip install -r requirements.txt && \
    /opt/conda/bin/conda clean -ya

WORKDIR /opt
ENV TORCH_CUDA_ARCH_LIST="7.0 7.2 7.5 8.0 8.6 8.7 8.9 9.0"
RUN git clone -b v2.3.0 --depth 1 https://github.com/pytorch/pytorch && \
    cd pytorch && \
    conda install pytorch::torchtriton && \
    git submodule update --init --recursive && \
    PYTORCH_BUILD_VERSION=2.3.0 PYTORCH_BUILD_NUMBER=1 python setup.py bdist_wheel
COPY main.py launch.sh ./
CMD printenv
