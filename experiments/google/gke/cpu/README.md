# GKE CPU Experiment

Status: This experiment has had one testing on GKE, and the configurations are updated here.

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


Monitoring:

```bash
git clone https://github.com/resmoio/kubernetes-event-exporter
cd kubernetes-event-exporter
kubectl create namespace monitoring
# edit deploy/<config> yaml
kubectl apply -f deploy
```

Install the Flux Operator:

```bash
kubectl apply -f ./flux-operator.yaml
```

Now we are ready for different MiniCluster setups. For each of the below, to shell in to the lead broker (index 0) you do:

```bash
kubectl exec -it flux-sample-0-xxx bash
```

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

```console
oras login ghcr.io --username vsoch
app=single-node
output=./results/$app

# This is the number of nodes -1
nodes=31

mkdir -p $output

for node in $(seq 0 $nodes); do
  flux submit --requires="hosts:flux-sample-$node" -N 1 --setattr=user.study_id=$app-node-$node /bin/bash /entrypoint.sh
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
  time flux run --env OMP_NUM_THREADS=2 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 896 -o cpu-affinity=per-task amg -n 256 256 128 -P 7 8 16 -problem 2
  time flux run --env OMP_NUM_THREADS=2 --setattr=user.study_id=$app-64-iter-$i -N 64 -n 1792 -o cpu-affinity=per-task amg -n 256 256 128 -P 8 14 16 -problem 2
  time flux run --env OMP_NUM_THREADS=2 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 3584 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 14 16 -problem 2
  time flux run --env OMP_NUM_THREADS=2 --setattr=user.study_id=$app-256-iter-$i -N 256 -n 7168 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 28 16 -problem 2
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

Dane and Google (Dan in slack, LDRD channel August 20th 2024)
(112 vCPUs/node 56 CPU/node): 32 nodes, 1792 tasks: --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 400 --legendre 2 --quad 16 --procs 8*14*16


*Important*: For each final command we need to add the final output of job info and submit attributes:

```console
oras login ghcr.io --username vsoch
app=kripke
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do
  echo "Running iteration $i"

time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1792 kripke --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 8,14,16

# TODO need for larger sizes
time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1792 kripke --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 8,14,16

# THESE ARE OLD
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
  time flux run --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -N32 -n 1792 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000
  time flux run --setattr=user.study_id=$app-64-iter-$i -o cpu-affinity=per-task -N64 -n 3584 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 7168 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000
  time flux run --setattr=user.study_id=$app-256-iter-$i -o cpu-affinity=per-task -N228 -n 12768 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000
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

```console
oras login ghcr.io --username vsoch
app=mixbench
output=./results/$app
nodes=N

mkdir -p $output
# each single run take about 4.6m
for i in $(seq 1 5); do     
    echo "Running iteration $i"
    for node in $(seq 0 $nodes); do
    flux submit --requires="hosts:flux-sample-$node" --env OMP_NUM_THREADS=96 --setattr=user.study_id=$app-iter-$i -l -N1 -n 1 mixbench-cpu 32
  done
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

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing:

```bash
time flux run -N4 -n 224 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
```

```console
oras login ghcr.io --username vsoch
app=mt-gemm
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 1792 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 3584 /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 7168 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 14336 /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
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
kubectl delete -f ./crd/mt-gemm.yaml
```

#### OSU

```bash
kubectl apply -f ./crd/osu.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

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
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    time flux run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw
    iter=$((iter+1))
done
done
```

Testing:

```bash
./flux-run-combinations.sh 4 $app

# 25 seconds
time flux run -N4 -n 224 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
```

And then run as follows.

```console
oras login ghcr.io --username vsoch
app=osu
output=./results/$app

./flux-run-combinations.sh 32 $app

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 1792 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 3584 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 7168 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 14336 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
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
kubectl delete -f ./crd/osu.yaml
```

#### Quicksilver

```bash
kubectl apply -f ./crd/quicksilver.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

For testing I used the smaller problem size for AKS from Abhik:

```bash
flux run --env OMP_NUM_THREADS=3 -N2 -n 64 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 10485760
```

That seemed to start working (the matrix started getting printed), but I didn't want to wait for it to finish.

```console
oras login ghcr.io --username vsoch
app=quicksilver
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
    echo "Running iteration $i"
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N32 -n 1024  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 128 -x 128 -y 128 -z 128 -I 16 -J 16 -K 8 -n 671088640
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 128 -Z 128 -x 256 -y 128 -z 128 -I 16 -J 16 -K 16 -n 1342117280
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 256 -Z 128 -x 256 -y 256 -z 128 -I 32 -J 16 -K 16 -n 2684354560
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
kubectl delete -f ./crd/quicksilver.yaml
```


#### Stream


```bash
kubectl apply -f ./crd/stream.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing:

```bash
# 4 seconds
time flux run -N1 -n 56 -o cpu-affinity=per-task stream_c.exe
```

```console
oras login ghcr.io --username vsoch
app=stream
output=./results/$app

# This should be zero indexed
nodes=N

mkdir -p $output
for i in $(seq 1 5); do
  echo "Running iteration $i"
  for node in $(seq 1 $nodes); do
    flux submit --requires="hosts:flux-sample-$node" --setattr=user.study_id=$app-1-iter-$i-node-$node -N1 -n 96 -o cpu-affinity=per-task stream_c.exe
  done
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
kubectl delete -f ./crd/stream.yaml
```

### Clean Up

When you are done:

```bash
gcloud container clusters delete test-cluster --region=us-central1-a
```
