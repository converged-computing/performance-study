# GKE GPU Experiment (size 4)

- Created at : 11:55pm
- Deleted: 2:30am

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

## Experiment

### 1. Setup

Bring up the cluster (with some number of nodes) and install the drivers. Have your GitHub packages (or other registry credential / token) ready. This does not work.

```bash
GOOGLE_PROJECT=myproject
NODES=4
GPUS=8

time gcloud container clusters create gpu-cluster-4 \
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
gpu-cluster-4  us-central1-a  1.29.7-gke.1104000  34.135.142.49  n1-standard-32  1.29.7-gke.1104000  4          RUNNING

real	6m11.385s
user	0m3.760s
sys	0m0.310s

# amg re-runs
NAME           LOCATION       MASTER_VERSION      MASTER_IP     MACHINE_TYPE    NODE_VERSION        NUM_NODES  STATUS
gpu-cluster-4  us-central1-c  1.30.3-gke.1639000  34.31.181.80  n1-standard-32  1.30.3-gke.1639000  4          RUNNING

real	5m53.267s
user	0m2.277s
sys	0m0.206s
```

Sanity check installed on all nodes

```bash
kubectl get nodes -o json | jq .items[].status.allocatable
kubectl get nodes -o json | jq .items[].status.allocatable | grep nvidia | wc -l
```
```
4
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
kubectl get nodes -o json > ./metadata/nodes-4.json
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
nodes=3
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
```
```
kubectl delete -f crd/single-node.yaml
```

### AMG2023 (CPU)

This was mostly an erroneous run because we didn't originally get the GPU container working.

```bash
kubectl apply -f ./crd/amg2023-cpu.yaml
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

# Size 4
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N 4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 128 -P 4 4 2 -problem 2 
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
```
```bash
kubectl delete -f ./crd/amg2023.yaml
```

### AMG2023

```bash
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

Forgot to install oras here:

```
export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/
```

Here is an example loop through sizes and iterations.

```console
flux proxy local:///mnt/flux/view/run/flux/local bash
oras login ghcr.io --username vsoch
export app=amg2023-large
export output=./results/$app
mkdir -p $output

# Size 4
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --setattr=user.study_id=$app-4-iter-$i -N 4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task  amg -n 256 256 128 -P 4 4 2 -problem 2 
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
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

# Size 4
for i in $(seq 2 3); do     
  echo "Running iteration $i"
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,2,4
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
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
    flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-1-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm
done

for i in $(seq 1 5); do     
  echo "Running iteration $i" 
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-vbatched-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
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

# Size 4
for i in $(seq 1 15); do
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
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

# Size 4
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite

  # Does not run at size 4
  # The Cuda allocation returned the error code "cudaErrorMemoryAllocation".)
  # time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
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

for i in $(seq 1 5); do     
    echo "Running iteration $i"
    flux run --setattr=user.study_id=$app-4-iter-$i --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -N4 -n 32 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
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

# 4 Nodes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
```
```bash
kubectl delete -f ./crd/mt-gemm.yaml
```

### Multi GPU Models

**Try and see if works, if not, move on**

Does not work, see size 8.

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
    time flux run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    time flux run -N 2 -n 2 \
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

./flux-run-combinations.sh 4 $app

# 4 Nodes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
  --setattr=user.study_id=$app-4-iter-$i -N 4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task \
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
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

# Cancelled at 15 minutes

# Size 4
for i in $(seq 1 2); do     
    echo "Running iteration $i"
    flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 32 -Y 32 -Z 32 -x 32 -y 32 -z 32 -I 4 -J 4 -K 2 -n 52428800
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
```
```bash
kubectl delete -f ./crd/quicksilver.yaml
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

for i in $(seq 2 15); do
   echo "Running iteration $i"
   flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task stream 
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-4-$app $output
```
```bash
kubectl delete -f ./crd/stream.yaml
```

## Clean up

```bash
gcloud container clusters delete gpu-cluster-4 --region us-central1-a
```

## Results

```console
for tag in $(oras repo tags ghcr.io/converged-computing/metrics-operator-experiments/performance)
  do
    if [[ $tag == *"gke-gpu-4"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
