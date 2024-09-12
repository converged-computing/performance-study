# "Bare Metal" on Compute Engine Size 8 for GPU

- Note: cannot get compact placement group
- Cluster coming up at 5:50pm Mountain, $160/hour
- Cluster coming down at 7:30pm 

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
flux alloc -N 8
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

for node in $(seq 1 8); do
  flux submit -N1 --requires="hosts:flux-00${node}" --setattr=user.study_id=$app-node-00${node} sudo singularity exec /opt/containers/metric-single-node_cpu-zen4-tmpfile.sif /bin/bash /entrypoint.sh
done 

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

#### AMG2023

```console
export app=amg2023
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run -opmi=pmix --setattr=user.study_id=$app-8-larger-problem-iter-$i -N 8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/metric-amg2023_spack-older-intel.sif /opt/view/bin/amg -n 256 128 128 -P 4 4 4 -problem 2 
  time flux run -opmi=pmix --setattr=user.study_id=$app-8-iter-$i -N 8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/metric-amg2023_spack-older-intel.sif /opt/view/bin/amg -n 128 128 128 -P 4 4 4 -problem 2 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

This is a second run for a container that can hit 256 256 128.

```console
export app=amg2023-large
export output=results/$app
mkdir -p $output

# Confirmed using all 8 GPU
for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run -opmi=pmix --setattr=user.study_id=$app-8-iter-$i -N 8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/metric-amg2023_skylake-manual.sif amg -n 256 256 128 -P 4 4 4 -problem 2 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

#### Kripke

```console
export app=kripke
export output=results/$app
mkdir -p $output

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  # confirmed using all GPU, 100%!
  # time is 2m 31 seconds, converged around step 50
  time flux run -opmi=pmix --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task singularity exec --nv /opt/containers/metric-kripke-gpu_google-gpu.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

### Magma

```console
export app=magma
output=./results/$app
mkdir -p $output

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  # confirmed using all gpu, XX
  time flux run --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-magma_google-gpu.sif /opt/magma/magma-2.8.0/build/testing/testing_dgemm
  # TIME 
  time flux run --setattr=user.study_id=$app-vbatched-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv --bind /usr/local/cuda /opt/containers/metric-magma_google-gpu.sif /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

#### LAMMPS-REAX

```console
export app=lammps-reax
export output=results/$app
mkdir -p $output

for i in $(seq 2 5); do
  echo "Running iteration $i"
  # 32 seconds
  time flux run -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 singularity exec --nv --pwd /code --env FI_PROVIDER=tcp,self /opt/containers/metric-lammps-gpu_google-gpu.sif /opt/lammps/build/lmp -k on g 1 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite

  # 1m 8 seconds
  time flux run -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 singularity exec --nv --pwd /code --env FI_PROVIDER=tcp,self /opt/containers/metric-lammps-gpu_google-gpu.sif /opt/lammps/build/lmp -k on g 1 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

#### MiniFE

```console
export app=minife
export output=results/$app
mkdir -p $output

# Confirmed using all GPU!
for i in $(seq 1 5); do
  echo "Running iteration $i"
  # almost instant, and then about 6 seconds
  time flux run --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-minife_google-gpu.sif miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-minife_google-gpu.sif miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
done

# Note that minife outputs more result files!!
mv miniFE* $output/
# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

#### Mixbench

```console
export app=mixbench
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  # confirmed 100% all GPU, runs in ~4 seconds
  time flux run --setattr=user.study_id=$app-8-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N8 -n 64 -g 1 singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-mixbench_google-gpu.sif mixbench-cuda 32
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

#### Mt-Gemm

```console
export app=mt-gemm
export output=results/$app
mkdir -p $output

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  # Confirmed using all GPU - 100%! 2m 10s, then 2m11 seconds for 8 GPU
  time flux run --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task singularity exec --nv /opt/containers/mt-gemm_google-gpu.sif /opt/gem/mt-dgemm.x 16384 100
done  
    
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
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
    time flux run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      -g 1 -o gpu-affinity=per-task \
      singularity exec --nv /opt/containers/metric-osu-gpu_google-gpu.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda H H
    time flux run -N 2 -n 2 \
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
./flux-run-combinations.sh 8 $app

# D D and H H errors (bad results but we ran anyway):
# The call to cuMemHostRegister(0x78407fe00008, 134217728, 0) failed.
#  Host:  flux-004
#  cuMemHostRegister return value:  1
#  Registration cache:  smcuda

# Note that osu_latency had worse values with D D. H H seems better across the board.
cho "Running iteration $i"

# These were run separately
export app=osu-allreduce
export output=results/$app
mkdir -p $output

# fastest with D D and the OMPI envar.
for i in $(seq 1 5); do
   time flux run --env OMPI_COMM_WORLD_LOCAL_RANK=0 --env OMPI_MCA_pml=ucx --env OMPI_MCA_btl=tcp -N 8 -n 64 -g 1 --setattr=user.study_id=$app-8-iter-$i -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

#### Quicksilver

Run attempt:

```console
export app=quicksilver
export output=results/$app
mkdir -p $output

# Just one iteration to see how far it gets, killing at 15 minutes
for i in $(seq 1 1); do
    echo "Running iteration $i"
   time flux run --exclusive --env OMP_NUM_THREADS=1 --env OMPI_MCA_pml=ucx --env OMPI_MCA_btl=tcp -N 8 -n 64 -g 1 --setattr=user.study_id=$app-8-iter-$i -o cpu-affinity=per-task -o gpu-affinity=per-task qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 104857600    
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

#### Stream

```console
export app=stream
export output=results/$app
mkdir -p $output

# Saw using all GPU! Results almost instant
for i in $(seq 2 15); do
  echo "Running iteration $i"
  flux run --setattr=user.study_id=$app-1-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --bind /usr/local/cuda --nv /opt/containers/metric-stream_google-gpu.sif stream 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
```

### Multi GPU Models

```console
app=multi-gpu-models
output=./results/$app
mkdir -p $output
  
# Size 8
for i in $(seq 2 4); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task singularity exec --nv /opt/containers/multi-gpu-models_google-gpu.sif /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-gpu-8-$app $output
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
    if [[ $tag == *"compute-engine-gpu-8"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
