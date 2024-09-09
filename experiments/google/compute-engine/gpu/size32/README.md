# "Bare Metal" on Compute Engine Size 32 for GPU

- Note: cannot get compact placement group
- Cluster coming up at 7:55pm Mountain, $640/hour
- Cluster coming down at 9:02pm

## Experiment

Shell in:

```bash
gcloud compute ssh flux-001 --project=llnl-flux --zone=us-central1-c --tunnel-through-iap
```

### 0. Pulling Containers

The containers are already pulled and located in `/opt/containers`. oras is also installed.

```bash
cd /opt/containers
```

### 1. Applications

Write this script to file that we can run incrementally to save output (that does not exist yet)

```bash
#!/bin/bash
output=$1

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    if [[ -f "$output/${study_id}-${jobid}.out" ]] || [[ "$study_id" == "null" ]]; then
        continue
    fi
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done
```
```bash
# Results and save script to home!
mkdir -p ./results
chmod +x ./save.sh
```

Cluster up: 10pm, down a little before midnight, even with extra runs to test (not too bad).
For each experiment, we need to be instance owner. This also cleans up `flux jobs -a` so you get a clean slate.

```bash
flux alloc -N <total-nodes>
flux alloc -N 32
```

You'll need to login to oras just once:

```bash
oras login ghcr.io --username vsoch
```

#### Single Node Benchmark

```console
export app=single-node
output=./results/$app
mkdir -p $output

for node in $(seq 1 9); do
  flux submit -N1 --requires="hosts:flux-00${node}" --setattr=user.study_id=$app-node-00${node} sudo singularity exec /opt/containers/metric-single-node_cpu-zen4-tmpfile.sif /bin/bash /entrypoint.sh
done 
for node in $(seq 10 32); do
  flux submit -N1 --requires="hosts:flux-0${node}" --setattr=user.study_id=$app-node-00${node} sudo singularity exec /opt/containers/metric-single-node_cpu-zen4-tmpfile.sif /bin/bash /entrypoint.sh
done 

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### AMG2023

Note error at largest size:

```console
[flux-032:04050] *** Process received signal ***
[flux-032:04050] Signal: Segmentation fault (11)
=============================================
[flux-032:04050] Signal code: Address not mapped (1)
Hypre init times:
[flux-032:04050] Failing at address: 0x2df
=============================================
[flux-032:04050] [ 0] Hypre init:
/lib/x86_64-linux-gnu/libc.so.6(+0x42520)[0x7a1b1845d520]
  wall clock time = 0.000053 seconds
[flux-032:04050] [ 1]   Laplacian_7pt:
/opt/software/linux-ubuntu22.04-broadwell/gcc-11.4.0/hypre-2.31.0-rw7lzoqq27f5p27winxataqxbj2mi473/lib/libHYPRE-2.31.0.so(HYPRE_IJMatrixSetObjectType+0x10)[0x7a1b188b62e0]
    (Nx, Ny, Nz) = (2048, 2048, 512)
[flux-032:04050] [ 2] /opt/view/bin/amg(+0xd6be)[0x5ac91e0f06be]
    (Px, Py, Pz) = (8, 8, 4)
[flux-032:04050] [ 3] /opt/view/bin/amg(+0x6143)[0x5ac91e0e9143]

[flux-032:04050] [ 4] /lib/x86_64-linux-gnu/libc.so.6(+0x29d90)[0x7a1b18444d90]
[flux-032:04050] [ 5] /lib/x86_64-linux-gnu/libc.so.6(__libc_start_main+0x80)[0x7a1b18444e40]
[flux-032:04050] [ 6] /opt/view/bin/amg(+0x7075)[0x5ac91e0ea075]
[flux-032:04050] *** End of error message ***
7.425s: flux-shell[31]:  WARN: pmix: notify source=ƒ69mbrU7H.255 event-status=-25
```
```console
export app=amg2023
export output=results/$app
mkdir -p $output

# https://github.com/converged-computing/performance-study/blob/main/experiments/azure/cyclecloud/gpu/results/32-nodes/amg2023/amg-32n-500-iter-1.out#L12
for i in $(seq 1 5); do
  echo "Running iteration $i"
  # 53 seconds confirmed using all 8 gpu, but utilization very low, under 5% until one blip at the end around 75%
  time flux run -opmi=pmix --setattr=user.study_id=$app-32-iter-$i -N 32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/metric-amg2023_spack-older-intel.sif /opt/view/bin/amg -n 256 128 128 -P 8 8 4 -problem 2
  #  also 63 seconds!
  time flux run -opmi=pmix --setattr=user.study_id=$app-32-iter-$i -N 32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/metric-amg2023_spack-older-intel.sif /opt/view/bin/amg -n 128 128 128 -P 8 8 4 -problem 2
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### Kripke

```console
export app=kripke
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  # confirmed using all GPU, dropped into 60s/70s/80s for percentage utilized.
  # 46 seconds
  time flux run -opmi=pmix  --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 -o gpu-affinity=per-task singularity exec --nv /opt/containers/metric-kripke-gpu_google-gpu.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,8
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

### Magma

```console
export app=magma
output=./results/$app
mkdir -p $output

for i in $(seq 2 5); do
  echo "Running iteration $i"
  # 1m3s confirmed using all gpu, spotty between 0 to 10 to 100%.
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-magma_google-gpu.sif /opt/magma/magma-2.8.0/build/testing/testing_dgemm
  # ditto  but faster, 18 seconds
  time flux run --setattr=user.study_id=$app-32-vbatched-iter-$i -N32 -n 256 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-magma_google-gpu.sif /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### LAMMPS-REAX

```console
export app=lammps-reax
export output=results/$app
mkdir -p $output

for i in $(seq 2 5); do
  # GPU utilization high 40s to 50s, 27 seconds
  time flux run -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 singularity exec --nv --pwd /code --env FI_PROVIDER=tcp,self /opt/containers/metric-lammps-gpu_google-gpu.sif /opt/lammps/build/lmp -k on g 1 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite
  # same for GPU, maybe more 50s and some 60s, 32 seconds 
  # My sense is these GPUs could be fed a lot more problem size.
  time flux run -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 singularity exec --nv --pwd /code --env FI_PROVIDER=tcp,self /opt/containers/metric-lammps-gpu_google-gpu.sif /opt/lammps/build/lmp -k on g 1 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### MiniFE

```console
export app=minife
export output=results/$app
mkdir -p $output

# Confirmed using all GPU!
for i in $(seq 1 5); do
  echo "Running iteration $i"
  # almost instant
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-minife_google-gpu.sif miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  # 7 seconds, also uses all, up to 10-20%s, but hard to catch.
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-minife_google-gpu.sif miniFE.x nx=640 ny=640 nz=640 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
done

# Note that minife outputs more result files!!
mv miniFE* $output/
# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### Mixbench

```console
export app=mixbench
export output=results/$app
mkdir -p $output

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  # wow, all 8 gpu up to 100%!
  # only takes 7 seconds to run
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-mixbench_google-gpu.sif mixbench-cuda 32
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### Mt-Gemm

```console
export app=mt-gemm
export output=results/$app
mkdir -p $output

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  # Confirmed using all GPU - 100%! Time consistent at 2m12s
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv /opt/containers/mt-gemm_google-gpu.sif /opt/gem/mt-dgemm.x 16384 100
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### OSU

Write this script to the filesystem `flux-run-combinations.sh`

```bash
#/bin/bash

nodes=$1
app=$2

# At most 28 combinations, 8 nodes 2 at a time
hosts=$(flux run -N $1 hostname | shuf -n 8 | tr '\n' ' ')
list=${hosts}

dequeue_from_list() {
  shift;
  list=$@
}

iter=0
for i in $hosts; do
  dequeue_from_list $list
  for j in $list; do
    echo "${i} ${j}"
    flux submit -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      -g 1 -o gpu-affinity=per-task \
      singularity exec --nv /opt/containers/metric-osu-gpu_google-gpu.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda H H
    flux submit -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      -g 1 -o gpu-affinity=per-task \
      singularity exec --nv /opt/containers/metric-osu-gpu_google-gpu.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw -d cuda H H
    iter=$((iter+1))
done
done
```

And then run as follows.

```console
export app=osu
export output=results/$app
mkdir -p $output

# Note I ran this with each of D D (device) and H H (...)
# We should do H H - better values across the board
./flux-run-combinations.sh 32 $app

# These were run separately
export app=osu-allreduce
export output=results/$app
mkdir -p $output

# fastest with D D and the OMPI envar.
for i in $(seq 1 5); do
   time flux run --env OMPI_COMM_WORLD_LOCAL_RANK=0 --env OMPI_MCA_pml=ucx --env OMPI_MCA_btl=tcp -N 32 -n 256 -g 1 --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### Quicksilver

```console
export app=quicksilver
export output=results/$app
mkdir -p $output

# confirmed using all 8 GPU, 100%
# Allowing 15 minutes to run
for i in $(seq 1 1); do
    echo "Running iteration $i"
    time flux run --exclusive --env OMP_NUM_THREADS=1 --env OMPI_MCA_pml=ucx --env OMPI_MCA_btl=tcp -N 32 -n 256 -g 1 --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -o gpu-affinity=per-task qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 64  -Z 64  -x 64  -y 64  -z 64  -I 8  -J 8  -K 4 -n 419430400
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

#### Stream

```console
export app=stream
export output=results/$app
mkdir -p $output

# Saw using all GPU! Results almost instant
for i in $(seq 1 15); do
  echo "Running iteration $i"
  flux run --setattr=user.study_id=$app-1-iter-$i -N32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-stream_google-gpu.sif stream 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

### Multi GPU Models

```console
app=multi-gpu-models
output=./results/$app
mkdir -p $output
  
for i in $(seq 2 2); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-16-iter-$i -N32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/multi-gpu-models_google-gpu.sif /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-32-$app $output
```

### Clean up

When you are done, exit and:

```bash
export GOOGLE_PROJECT=myproject
make destroy
```

```console
for tag in $(oras repo tags ghcr.io/converged-computing/metrics-operator-experiments/performance)
  do
    if [[ $tag == *"compute-engine-gpu-32"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
