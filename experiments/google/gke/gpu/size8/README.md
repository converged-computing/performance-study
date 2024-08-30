# GKE GPU Experiment (size 8)

- Created at : 7:30pm
- Deleted at: 10:50pm

Note that it seems we need to create the exact cluster size that flux is going to use and run on.
If you create one that is larger and run smaller, the GPUs won't be used

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

## Notes

### Cost

We previously were asking for 8 across two nodes, now we are going to ask for 8 per node. We won't have time to look at GPU usage and tweak, we just have time to ensure the apps run and generate output we can save. If we do 8 GPU for 8 nodes, this would be 64 x [the cost per hour](https://cloud.google.com/compute/gpus-pricing) $2.48, which is $158/hour. We can adjust from that size depending on our risk tolerance. If we go the full size, 32 nodes * 8 GPU, that would be $634.88 per hour. We'd only get one hour, if we were safe, because we only have 1K in credits left.

## Experiment

### 1. Setup

Bring up the cluster (with some number of nodes) and install the drivers. Have your GitHub packages (or other registry credential / token) ready. This does not work.

```bash
GOOGLE_PROJECT=myproject
NODES=8
GPUS=8

time gcloud container clusters create gpu-cluster-8 \
    --threads-per-core=1 \
    --accelerator type=nvidia-tesla-v100,count=$GPUS,gpu-driver-version=latest \
    --num-nodes=$NODES \
    --machine-type=n1-standard-32 \
    --enable-gvnic \
    --network=mtu9k \
    --system-config-from-file=./system-config.yaml \
    --region=us-central1-a \
    --project=${GOOGLE_PROJECT} 
```
```console
# Testing cluster
real	5m9.361s
user	0m3.251s
sys	0m0.322s

# first cluster
gpu-cluster-8  us-central1-a  1.29.7-gke.1104000  34.172.8.90  n1-standard-32  1.29.7-gke.1104000  8          RUNNING
real	5m14.329s
user	0m2.158s
sys	0m0.198s

# second (final)
gpu-cluster-8  us-central1-a  1.29.7-gke.1104000  104.197.50.137  n1-standard-32  1.29.7-gke.1104000  8          RUNNING

real	5m20.243s
user	0m2.184s
sys	0m0.195s

gpu-cluster-8  us-central1-a  1.29.7-gke.1104000  34.46.90.45  n1-standard-32  1.29.7-gke.1104000  8          RUNNING

real	5m51.054s
user	0m2.628s
sys	0m0.214s

# This was the one we used.
gpu-cluster-8  us-central1-a  1.29.7-gke.1104000  104.197.50.137  n1-standard-32  1.29.7-gke.1104000  8          RUNNING

real	5m45.552s
user	0m2.356s
sys	0m0.224s
```

Sanity check installed on all nodes

```bash
kubectl get nodes -o json | jq .items[].status.allocatable
kubectl get nodes -o json | jq .items[].status.allocatable | grep nvidia | wc -l
```
```
8
```

Install the Flux Operator:

```bash
kubectl apply -f ./flux-operator.yaml
```

Now we are ready for different MiniCluster setups. For each of the below, to shell in to the lead broker (index 0) you do:

```bash
kubectl exec -it flux-sample-0-xxx bash
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

Get nodes:

```bash
kubectl get nodes -o json > ./metadata/nodes-8-fixed-8-29-2024.json
```

Start events, make sure this doesn't die

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-gpu-8-$(date +%s).json
```

## 3. Applications

#### Single Node Benchmark

We are going to run this via flux batch, running the job across nodes (and then when they are complete, getting the logs from flux)

```bash
kubectl apply -f ./crd/single-node.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

We want to run four separate jobs, across each node. Write this into a batch file.

```console
oras login ghcr.io --username vsoch
export app=single-node
export output=./results/$app
mkdir -p $output

# This is the number of nodes -1
nodes=7
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```
kubectl delete -f crd/single-node.yaml
```

### AMG2023

```bash
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

This one requires sourcing spack

```bash
. /etc/profile.d/z10_spack_environment.sh
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Here is an example loop through sizes and iterations.

```console
oras login ghcr.io --username vsoch
export app=amg2023
export output=./results/$app
mkdir -p $output

# Size 8
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N 8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 128 -P 8 4 2 -problem 2 
done

apt-get update && apt-get install -y jq

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/amg2023.yaml
```

### Kripke

```bash
kubectl apply -f ./crd/kripke.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=kripke
export output=./results/$app
mkdir -p $output

# Size 8
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/kripke.yaml
```

### Magma

```bash
kubectl apply -f ./crd/magma.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
export app=magma
output=./results/$app
mkdir -p $output

for i in $(seq 1 5); do     
  echo "Running iteration $i"
    flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-1-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm
done

for i in $(seq 2 5); do     
  echo "Running iteration $i" 
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-vbatched-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/magma.yaml
```

### MiniFE

```bash
kubectl apply -f ./crd/minife.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
app=minife
output=./results/$app
mkdir -p $output
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

# Size 8
for i in $(seq 1 15); do
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N8 -n 16 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```

```bash
kubectl delete -f ./crd/minife.yaml
```

### LAMMPS-REAX

```bash
kubectl apply -f ./crd/lammps-reax.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
app=lammps-reax
output=./results/$app
mkdir -p $output

# Size 8
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/lammps-reax.yaml
```

### Mixbench

```bash
kubectl apply -f ./crd/mixbench.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
export app=mixbench
export output=./results/$app
mkdir -p $output

# This wasn't compiled
cd /opt/mixbench/mixbench-cuda
flux exec -r all make
cd -

# One less than actual
nodes=7

# Also try (do this first if it works)

for i in $(seq 2 5); do     
    echo "Running iteration $i"
    flux run --setattr=user.study_id=$app-8-iter-$i --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N8 -n 64 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
```

### Mt-Gemm

```bash
kubectl apply -f ./crd/mt-gemm.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=mt-gemm
output=./results/$app
mkdir -p $output

# 8 Nodes
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/mt-gem.yaml
```

### Multi GPU Models

**Try and see if works, if not, move on**

(did not work)

```
[flux-sample-3:00074] Failed to register remote memory, rc=-1
[flux-sample-5:00074] Failed to register remote memory, rc=-1
```
```bash
kubectl apply -f ./crd/multi-gpu-models.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
app=multi-gpu-models
output=./results/$app
mkdir -p $output
  
# Size 8
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/multi-gpu-models.yaml
```

### OSU

```bash
kubectl apply -f ./crd/osu.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Write this script to the filesystem:

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
      --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
      --requires="hosts:${i},${j}" \
      -o gpu-affinity=per-task \
      -o cpu-affinity=per-task \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    flux submit -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw
    iter=$((iter+1))
done
done
```

And then run as follows.

```console
oras login ghcr.io --username vsoch
app=osu
output=./results/$app
mkdir -p $output

# This was run without GPU - likely it's the same issue with Google Cloud
# not using all GPU
./flux-run-combinations.sh 8 $app

# 8 Nodes
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
  --setattr=user.study_id=$app-8-iter-$i -N 8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task \
  /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/osu.yaml
```

### Quicksilver

```bash
kubectl apply -f ./crd/quicksilver.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=quicksilver
output=./results/$app
mkdir -p $output

# Cut at 20 minutes

# Size 4
for i in $(seq 1 2); do     
    echo "Running iteration $i"
    flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 104857600
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```

### Stream

```bash
kubectl apply -f ./crd/stream.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
app=stream
output=./results/$app
mkdir -p $output

for i in $(seq 1 15); do
   echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-1-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task stream 
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-8-2-$app $output
```
```bash
kubectl delete -f ./crd/stream.yaml
```

## Clean up

```bash
gcloud container clusters delete gpu-cluster-8 --region us-central1-a
```

## Results

```console
for tag in $(oras repo tags ghcr.io/converged-computing/metrics-operator-experiments/performance)
  do
    if [[ $tag == *"gke-gpu-8-2"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
