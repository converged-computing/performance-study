FROM ghcr.io/converged-computing/metric-lammps-gpu:azure-hpc-ubuntu2204

# Build command
#  docker build -t ghcr.io/converged-computing/metric-lammps-gpu:azure-hpc-reax .
#  docker push ghcr.io/converged-computing/metric-lammps-cpu:azure-hpc-reax

WORKDIR /opt
RUN rm -rf /code && rm -rf /opt/lammps && \
    git clone --depth 1 https://github.com/lammps/lammps.git && \
    cd lammps && \
    mkdir build && \
    cd build && \
    cmake -D CMAKE_INSTALL_PREFIX=/usr/local -DCMAKE_LIBRARY_PATH=/usr/local/cuda/lib64/stubs -DBIN2C=/usr/local/cuda/bin/bin2c -D LAMMPS_MACHINE=gpu -D PKG_MOLECULE=on -D PKG_ASPHERE=on -D PKG_BODY=on -D PKG_CLASS2=on -D PKG_COLLOID=on -D PKG_COMPRESS=on -D PKG_CORESHELL=on -D PKG_DIPOLE=on -D PKG_GRANULAR=on -D PKG_KSPACE=on -D PKG_MANYBODY=on -D PKG_MC=on -D PKG_MISC=on -D PKG_PERI=on -D PKG_QEQ=on -D PKG_RIGID=on -D PKG_SHOCK=on -D PKG_SNAP=on -D PKG_SRD=on -D PKG_USER-REAXC=on -D PKG_USER-TALLY=on -D PKG_GPU=on -D GPU_API=cuda -D  GPU_ARCH=sm_70 ../cmake && \
    make && \
    make install     

WORKDIR /code
RUN cp -R /opt/lammps/examples/reaxff/HNS/* /code/ && \
    chown -R 1000 /code /opt/lammps
