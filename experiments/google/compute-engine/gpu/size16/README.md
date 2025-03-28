# "Bare Metal" on Compute Engine Size 16 for GPU

- Note: cannot get compact placement group
- Cluster coming up at 4:35pm Mountain, $320/hour
- Cluster coming down at 6:00pm

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
flux alloc -N 16
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
for node in $(seq 10 16); do
  flux submit -N1 --requires="hosts:flux-0${node}" --setattr=user.study_id=$app-node-00${node} sudo singularity exec /opt/containers/metric-single-node_cpu-zen4-tmpfile.sif /bin/bash /entrypoint.sh
done 

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

#### AMG2023

```console
export app=amg2023
export output=results/$app
mkdir -p $output

# This only works for the smallest size...
for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run -opmi=pmix --setattr=user.study_id=$app-16-iter-$i -N 16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/metric-amg2023_spack-older-intel.sif /opt/view/bin/amg -n 128 128 128 -P 8 4 4 -problem 2 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

This is a second run for a container that can hit 256 256 128.

```console
export app=amg2023-large
export output=results/$app
mkdir -p $output

# Confirmed using all 8 GPU
for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run -opmi=pmix --setattr=user.study_id=$app-16-iter-$i -N 16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/metric-amg2023_skylake-manual.sif amg -n 256 256 128 -P 8 4 4 -problem 2 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

#### Kripke

```console
export app=kripke
export output=results/$app
mkdir -p $output

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  # confirmed using all GPU, close to 100%!
  # time is 1m 20s from 2m 21s!
  time flux run -opmi=pmix --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task singularity exec --nv /opt/containers/metric-kripke-gpu_google-gpu.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,8,4
done

# Additional sizes for experiment (not tested yet)
time flux run -opmi=pmix  --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 -g 1 -o gpu-affinity=per-task singularity exec --nv /opt/containers/metric-kripke-gpu_google-gpu.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,8

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

### Magma

```console
export app=magma
output=./results/$app
mkdir -p $output

for i in $(seq 2 5); do
  echo "Running iteration $i"
  # confirmed using all gpu, XX
  flux run --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-magma_google-gpu.sif /opt/magma/magma-2.8.0/build/testing/testing_dgemm
  flux run --setattr=user.study_id=$app-16-vbatched-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-magma_google-gpu.sif /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

#### LAMMPS-REAX

```console
export app=lammps-reax
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do
  # 30 seconds
  time flux run -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 singularity exec --nv --pwd /code --env FI_PROVIDER=tcp,self /opt/containers/metric-lammps-gpu_google-gpu.sif /opt/lammps/build/lmp -k on g 1 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite
  # 42 seconds
  time flux run -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 singularity exec --nv --pwd /code --env FI_PROVIDER=tcp,self /opt/containers/metric-lammps-gpu_google-gpu.sif /opt/lammps/build/lmp -k on g 1 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

#### MiniFE

```console
export app=minife
export output=results/$app
mkdir -p $output

# Confirmed using all GPU!
for i in $(seq 1 5); do
  echo "Running iteration $i"
  flux run --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-minife_google-gpu.sif miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  flux run --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-minife_google-gpu.sif miniFE.x nx=640 ny=640 nz=640 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
done

# Note that minife outputs more result files!!
mv miniFE* $output/
# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

#### Mixbench

```console
export app=mixbench
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-16-n-128-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-mixbench_google-gpu.sif mixbench-cuda 32
done

# Remainder of runs at different sizes
flux run --setattr=user.study_id=$app-32-iter-$i -N32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-mixbench_google-gpu.sif mixbench-cuda 32

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

#### Mt-Gemm

```console
export app=mt-gemm
export output=results/$app
mkdir -p $output

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  # Confirmed using all GPU - 100%! Time consistent at 2m12s
  time flux run --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv /opt/containers/mt-gemm_google-gpu.sif /opt/gem/mt-dgemm.x 16384 100
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

#### OSU

Write this script to the filesystem `flux-run-combinations.sh`
Note that the initial study in August 2024 used flux submit, which isn't blocking (and erroneous since they run at the same time). We redid this size in March 2025 with flux run, ensuring it would be blocking.

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
    flux run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      -g 1 -o gpu-affinity=per-task \
      singularity exec --nv /opt/containers/metric-osu-gpu_google-gpu.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda H H
    flux run -N 2 -n 2 \
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
./flux-run-combinations.sh 16 $app

# These were run separately
export app=osu-allreduce
export output=results/$app
mkdir -p $output

# fastest with D D and the OMPI envar.
for i in $(seq 1 5); do
   time flux run --env OMPI_COMM_WORLD_LOCAL_RANK=0 --env OMPI_MCA_pml=ucx --env OMPI_MCA_btl=tcp -N 16 -n 128 -g 1 --setattr=user.study_id=$app-16-iter-$i -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H
done

# When they are done:
./save.sh $output

# August 2024
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output

# March 2025 with fixed osu latency and osu bw
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app-fixed $output
```

#### Quicksilver

```console
export app=quicksilver
export output=results/$app
mkdir -p $output

# confirmed using all 8 GPU, 100%
# Allowing 15 minutes to run then cancel
for i in $(seq 1 1); do
    echo "Running iteration $i"
   time flux run --exclusive --env OMP_NUM_THREADS=1 --env OMPI_MCA_pml=ucx --env OMPI_MCA_btl=tcp -N 16 -n 128 -g 1 --setattr=user.study_id=$app-16-iter-$i -o cpu-affinity=per-task -o gpu-affinity=per-task qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 64  -Z 32  -x 64  -y 64  -z 32  -I 8  -J 4  -K 4  -n 209715200
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

#### Stream

```console
export app=stream
export output=results/$app
mkdir -p $output

# Saw using all GPU! Results almost instant
for i in $(seq 1 15); do
  echo "Running iteration $i"
flux run --setattr=user.study_id=$app-1-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-stream_google-gpu.sif stream 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
```

### Multi GPU Models

```console
app=multi-gpu-models
output=./results/$app
mkdir -p $output
  
# Size 16
for i in $(seq 2 2); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/multi-gpu-models_google-gpu.sif /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-16-$app $output
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
    if [[ $tag == *"compute-engine-gpu-16"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
