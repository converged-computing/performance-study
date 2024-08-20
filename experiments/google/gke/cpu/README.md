# GKE CPU Experiment

Status: This experiment has had one testing on GKE, and the configurations are updated here.

 - [ ] TODO: we need to do final parameters for AMG.

## Design

```console
For each experiment (crd in ./crd):
  Create the MiniCluster, and shell in
  Connect to the flux broker, loading spack env if needed
  Create output directory for logs
  For each size of experiment to run (with custom params)?
    For iterations 1..N (likely 1 for now)
      Run the experiment, save to log
  Compress results with oras
  Push to OCI registry for results
```

We will want to either run this on a GKE instance (we all have access to) OR create the cluster and share the kubeconfig with multiple people, in case someone's computer crashes. We also need a means to programatically monitor the container creation times, etc.

## Experiments

### 1. Setup

Bring up the cluster (with some number of nodes) and install the drivers. Have your GitHub packages (or other registry credential / token) ready. This does not work.

```bash
GOOGLE_PROJECT=myproject
NODES=4

gcloud compute networks create mtu9k --mtu=8896 
gcloud compute firewall-rules create mtu9k-firewall --network mtu9k --allow tcp,udp,icmp --source-ranges 0.0.0.0/0

n1-standard-32
v100

time gcloud container clusters create test-cluster \
    --threads-per-core=1 \
    --num-nodes=$NODES \
    --machine-type=c2d-standard-112 \
    --network-performance-configs=total-egress-bandwidth-tier=TIER_1 \
    --enable-gvnic \
    --network=mtu9k \
    --placement-type=COMPACT \
    --system-config-from-file=./system-config.yaml \
    --region=us-central1-a \
    --project=${GOOGLE_PROJECT} 
```

Install the Flux Operator (container digest pinned on August 2, 2024)

```bash
kubectl apply -f ./flux-operator.yaml
```

Now we are ready for different MiniCluster setups. For each of the below, to shell in to the lead broker (index 0) you do:

```bash
kubectl exec -it flux-sample-0-xxx bash
```

Note that we are still getting unique nodes without specifying resources!

```bash
kubectl get pods -o json  | jq -r .items[].spec.nodeName | uniq | wc -l
32
```

Note that the configs are currently set to 8 nodes, with 8 gpu each. size 32vcpu (16 cores) instance (n1-standard-32).


### 2. Applications

#### Single Node Benchmark

We are going to run this via flux batch, running the job across nodes (and then when they are complete, getting the logs from flux)

**IMPORTANT** change the size of the minicluster.yaml to the correct cluster size.


```bash
kubectl apply -f ./crd/single-node.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

*Important*: For each final command we need to add the final output of job info and submit attributes:

```console
oras login ghcr.io --username vsoch
app=single-node
output=./results/$app
nodes=4

mkdir -p $output

for node in $(seq 1 $nodes); do
  flux submit -N 1 --setattr=user.study_id=$app-1-node-$node /bin/bash /entrypoint.sh
done 

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

#### AMG2023

Create the minicluster and shell in. Note this first pull takes the longest (about ~5 minutes)

```bash
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

This one requires sourcing spack:

```bash
. /etc/profile.d/z10_spack_environment.sh
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Test size run:

```bash
# 14.15 seconds
time flux run --env OMP_NUM_THREADS=3 -N 4 -n 224 -o cpu-affinity=per-task amg -n 128 128 64 -P 4 7 8 -problem 2

# 1m 38 seconds
time flux run --env OMP_NUM_THREADS=3 -N 4 -n 224 -o cpu-affinity=per-task amg -n 256 256 128 -P 4 7 8 -problem 2
```

```console
oras login ghcr.io --username vsoch
app=amg2023
output=./results/$app

mkdir -p $output
for i in $(seq 1 15); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1024 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 8 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N 64 -n 2048 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 16 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 4096 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 16 16 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N 256 -n 8192 -o cpu-affinity=per-task amg -n 256 256 128 -P 32 16 16 -problem 2
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```
```bash
kubectl delete -f ./crd/amg2023.yaml
```

#### Kripke


```bash
kubectl apply -f ./crd/kripke.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing on 4 nodes:

```bash
# 1m 48 seconds
time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N 4 -n 64 kripke --layout DGZ --dset 16 --zones 128,128,128 --gset 16 --groups 16 --niter 10 --legendre 2 --quad 16 --procs 4,4,4
```

*Important*: For each final command we need to add the final output of job info and submit attributes:

```console
oras login ghcr.io --username vsoch
app=kripke
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 3072 kripke --layout DGZ --dset 16 --zones 144,448,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 12,16,16

time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048 kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,8,4
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192 kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,8
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```
```bash
kubectl delete -f ./crd/kripke.yaml
```

#### Laghos

```bash
kubectl apply -f ./crd/laghos.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

Testing 4 nodes

```bash
# 1 minute 24 seconds
time flux run -o cpu-affinity=per-task -N4 -n 224 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 10 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
```


```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
app=laghos
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N32 -n 1792 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-64-iter-$i -N64 -n 3584 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-128-iter-$i -N128 -n 7168 1 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-256-iter-$i -N256 -n 14336 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

```bash
kubectl delete -f ./crd/laghos.yaml --wait
```

#### LAMMPS

```bash
kubectl apply -f ./crd/lammps.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

*Important*: For each final command we need to add the final output of job info and submit attributes:

```bash
time flux run -o cpu-affinity=per-task -N4 -n 224 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000 

time flux run -o cpu-affinity=per-task -N4 -n 224 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 10000
```

```console
oras login ghcr.io --username vsoch
app=lammps
output=./results/$app

# NOTE: the below takes 4 minutes. If taking too long, drop back to 3 iterations
# IMPORTANT: Ani is testing if 128 works on lassen and 1500 vs 1000 steps
mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -N32 -n 1792 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-64-iter-$i -o cpu-affinity=per-task -N64 -n 3584 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 7168 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-256-iter-$i -o cpu-affinity=per-task -N228 -n 12768 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

Note that for "opposite scaling" apps like lammps, we are going to need to decide a maximum time to wait for something to run, otherwise we will get in trouble. Given the closeness with the affinity/without affinity times and how it improved the larger sizes, I recommend using the flag over not.

```bash
kubectl delete -f ./crd/lammps.yaml
```

#### MiniFE

```bash
kubectl apply -f ./crd/minife.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
time flux run -N4 -n 224 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

time flux run -N4 -n 224 -o cpu-affinity=per-task miniFE.x nx=640 ny=640 nz=640 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
```

```console
oras login ghcr.io --username vsoch
app=minife
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 1792 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 3584 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 7168 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 14336 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```
```bash
kubectl delete -f ./crd/minife.yaml
```

#### Mixbench

```bash
kubectl apply -f ./crd/mixbench.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing:

```bash
time flux run -l -N2 -n 112 mixbench-cpu 64
```

```console
oras login ghcr.io --username vsoch
app=mixbench
output=./results/$app

# ~26 seconds
mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-$size-iter-$i -l -N2 -n 112 mixbench-cpu 64 |& tee ./$output/$app-2-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
```

#### Mt-Gemm

```bash
kubectl apply -f ./crd/mt-gemm.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

Testing:

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```bash
time flux run -l -N2 -n 112 mixbench-cpu 64
```

```console
oras login ghcr.io --username vsoch
app=mixbench
output=./results/$app

# ~26 seconds
mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-$size-iter-$i -l -N2 -n 192 mixbench-cpu 64 |& tee ./$output/$app-2-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
```


oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

The above needs a redo - either improved printing of metrics (and increase in runtime) or a new repository.

```bash
kubectl delete -f ./crd/mt-gemm.yaml
```

#### OSU

```bash
kubectl apply -f ./crd/osu.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- ~4 seconds additional pull time

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

*Important*: For each final command we need to add the final output of job info and submit attributes:

```console

# Identifier should be application, size, and iteration, this matches the other output file
--setattr=user.study-id=$app-$size-iter-$i

# When they are done
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
  done
```

```console
oras login ghcr.io --username vsoch
app=osu
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # 5.58 seconds (requires exactly 2)
  time flux run -N2 -n2 /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw |& tee ./$output/$app-osu_bw-$size-iter-${i}.out  
 
  # 18.45 seconds
  flux run -N4 -n224 /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce |& tee ./$output/$app-osu_allreduce-$size-iter-${i}.out

  # 16.35 seconds
  time flux run -N8 -n448 /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce |& tee ./$output/$app-osu_allreduce-$size-iter-${i}.out

  # 28.9 seconds
  time flux run -N16 -n896 /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce |& tee ./$output/$app-osu_allreduce-$size-iter-${i}.out

  # 32.6 seconds
  time flux run -N32 -n 1792 /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce |& tee ./$output/$app-osu_allreduce-$size-iter-${i}.out

  # 21.182 seconds (requires exactly 2 processes)
  time flux run -N2 -n2 /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency |& tee ./$output/$app-osu_latency-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

```bash
kubectl delete -f ./crd/osu.yaml
```

#### Quicksilver

```bash
kubectl apply -f ./crd/quicksilver.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

Configuration to test from Abhik: 🥳️

> srun -N1 -n4 qs -i Coral2_P1.inp -X 16 -Y 16 -Z 16 -x 16 -y 16 -z 16 -I 2 -J 2 -K 1 -n 163840
> srun -N2 -n8 qs -i Coral2_P1.inp -X 32 -Y 16 -Z 16 -x 32 -y 16 -z 16 -I 2 -J 2 -K 2 -n 327680

- Additional pull time: 9.89 seconds

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

*Important*: For each final command we need to add the final output of job info and submit attributes:

```console

# Identifier should be application, size, and iteration, this matches the other output file
--setattr=user.study-id=$app-$size-iter-$i

# When they are done
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
  done
```

```console
oras login ghcr.io --username vsoch
app=quicksilver
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # None of the problem sizes seem to run - we likely need a custom one
  # OR to get one working on lassen, and then compare to clouds.
  # Note this doesn't work on AWS either.
  time flux run -o cpu-affinity=per-task -N4 -n 224 qs --nParticles 1000 --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

This seems buggy - when I changed the input file, the output values didn't change, even with `--inputFile` (this was an error we saw before). The command line flags seemed to work, these:

```
 Arguments are: 
   --help             -h  arg=0 type=i  print this message
   --dt               -D  arg=1 type=d  time step (seconds)
   --fMax             -f  arg=1 type=d  max random mesh node displacement
   --inputFile        -i  arg=1 type=s  name of input file
   --energySpectrum   -e  arg=1 type=s  name of energy spectrum output file
   --crossSectionsOut -S  arg=1 type=s  name of cross section output file
   --loadBalance      -l  arg=0 type=i  enable/disable load balancing
   --cycleTimers      -c  arg=1 type=i  enable/disable cycle timers
   --debugThreads     -t  arg=1 type=i  set thread debug level to 1, 2, 3
   --lx               -X  arg=1 type=d  x-size of simulation (cm)
   --ly               -Y  arg=1 type=d  y-size of simulation (cm)
   --lz               -Z  arg=1 type=d  z-size of simulation (cm)
   --nParticles       -n  arg=1 type=u  number of particles
   --batchSize        -g  arg=1 type=u  number of particles in a vault/batch
   --nBatches         -b  arg=1 type=u  number of vault/batch to start (sets batchSize automaticaly)
   --nSteps           -N  arg=1 type=i  number of time steps
   --nx               -x  arg=1 type=i  number of mesh elements in x
   --ny               -y  arg=1 type=i  number of mesh elements in y
   --nz               -z  arg=1 type=i  number of mesh elements in z
   --seed             -s  arg=1 type=i  random number seed
   --xDom             -I  arg=1 type=i  number of MPI ranks in x
   --yDom             -J  arg=1 type=i  number of MPI ranks in y
   --zDom             -K  arg=1 type=i  number of MPI ranks in z
   --bTally           -B  arg=1 type=i  number of balance tally replications
   --fTally           -F  arg=1 type=i  number of scalar flux tally replications
   --cTally           -C  arg=1 type=i  number of scalar cell tally replications
```

Note that when we run on a tiny number of processes, it works: e.g., both options:

```bash
time flux run -N2 -n 8 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp

# Coral 2 example
time flux run -N2 -n 8 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem2/Coral2_P2.inp
```

It might be that the input params need to match the size? Or network is huge here? 
I don't understand what it's doing to know.

```bash
kubectl delete -f ./crd/quicksilver.yaml
```

But it doesn't seem to scale to more than 2 nodes.


#### Stream

```bash
kubectl apply -f ./crd/stream.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- Additional pull time: 5.56 seconds

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

*Important*: For each final command we need to add the final output of job info and submit attributes:

```console

# Identifier should be application, size, and iteration, this matches the other output file
--setattr=user.study-id=$app-$size-iter-$i

# When they are done
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
  done
```

This does not appear to be for multiple nodes.

```console
oras login ghcr.io --username vsoch
app=stream
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"  

  # It's not clear if this is intended for multiple nodes?
  # 2.69 seconds
  # cpu affinity does nothing   
  time flux run -N4 -n 224 ./stream_c.exe  |& tee ./$output/$app-$size-iter-${i}.out

  # 2.92 seconds
  time flux run -N8 -n 448 ./stream_c.exe  |& tee ./$output/$app-$size-iter-${i}.out

  # 3.60 seconds
  time flux run -N16 -n 896 ./stream_c.exe  |& tee ./$output/$app-$size-iter-${i}.out

  # 4.60 seconds
  time flux run -N32 -n 1792 ./stream_c.exe  |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

```bash
kubectl delete -f ./crd/stream.yaml
```

### Clean Up

When you are done:

```bash
gcloud container clusters delete test-cluster --region=us-central1-a
```
