FROM ghcr.io/converged-computing/azurehpc:flux-gpu
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build  -t ghcr.io/converged-computing/metric-quicksilver-gpu:azure-hpc-gpu-ubuntu2204 .
#  docker push ghcr.io/converged-computing/metric-quicksilver-gpu:azure-hpc-gpu-ubuntu2204

# hpcx
ENV LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib:/usr/local/cuda/lib64
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin:/usr/local/cuda/bin
ENV CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

WORKDIR /opt
RUN git clone https://github.com/LLNL/Quicksilver quicksilver
COPY ./Makefile /opt/quicksilver/src/Makefile
WORKDIR /opt/quicksilver/src
RUN make || nvcc -DHAVE_CUDA -std=c++11 -O2 -Xptxas -v -gencode=arch=compute_70,code=\"sm_70,compute_70\" --compiler-bindir=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin/mpicxx -L/usr/local/cuda/lib64/ -lcuda -lcudart -lm -o qs CollisionEvent.o CoralBenchmark.o CycleTracking.o DecompositionObject.o DirectionCosine.o EnergySpectrum.o GlobalFccGrid.o GridAssignmentObject.o InputBlock.o MCT.o MC_Adjacent_Facet.o MC_Base_Particle.o MC_Domain.o MC_Facet_Crossing_Event.o MC_Fast_Timer.o MC_Load_Particle.o MC_Location.o MC_Particle_Buffer.o MC_RNG_State.o MC_Segment_Outcome.o MC_SourceNow.o MacroscopicCrossSection.o MeshPartition.o MonteCarlo.o MpiCommObject.o NuclearData.o Parameters.o ParticleVault.o ParticleVaultContainer.o PopulationControl.o SendQueue.o SharedMemoryCommObject.o Tallies.o cmdLineParser.o cudaFunctions.o initMC.o main.o parseUtils.o utils.o utilsMpi.o && cp qs /usr/bin/qs

EXPOSE 22
WORKDIR /opt/quicksilver/Examples
