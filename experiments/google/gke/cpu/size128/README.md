# GKE CPU Experiment Size 128

- Creation time: 11:25am
- Done at 3:26pm

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

Notes:

 - Much easier to interact with GKE because the tool automatically updates credentials - aws needs to run the command in terminals that want that, plus having the AWS environment variables. The default environment variables don't work. This is because the kubeconfig for aws has a command that uses the aws-authenticator to get credentials (that expire) over just giving a token. It perhaps is "better" practice but makes usability worse.

## Experiments

### 1. Setup

Bring up the cluster (with some number of nodes) and install the drivers. Have your GitHub packages (or other registry credential / token) ready. This does not work.

```bash
GOOGLE_PROJECT=converged-computing
NODES=128

# Already created with 32
# gcloud compute networks create mtu9k --mtu=8896 
# gcloud compute firewall-rules create mtu9k-firewall --network mtu9k --allow tcp,udp,icmp --source-ranges 0.0.0.0/0

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
```console
Kripke cluster September 15
test-cluster  us-central1-a  1.30.3-gke.1639000  104.198.45.99  c2d-standard-112  1.30.3-gke.1639000  128        RUNNING
real	5m41.094s
user	0m2.157s
sys	0m0.209s
```

Install the Flux Operator (container digest pinned on August 2, 2024)

```bash
kubectl apply -f ./flux-operator.yaml
```

Save nodes:

```bash
kubectl get nodes -o json > metadata/nodes-quicksilver-128.json 
kubectl get nodes -o json > metadata/nodes-lammps-128.json 
kubectl get nodes -o json > metadata/nodes-kripke-128.json 
```

Get placement (note this is for the quicksilver cluster, August 23rd 8:48pm)

```console
mkdir placement
cd placement
for node in $(kubectl get -o json nodes | jq -r .items[].metadata.name)
  do
   echo $node
   gcloud compute instances describe $node --zone=us-central1-a > $node.txt
done
cd ../
```

Now we are ready for different MiniCluster setups. For each of the below, to shell in to the lead broker (index 0) you do:

```bash
kubectl exec -it flux-sample-0-xxx bash
```

Here is how to check that we are getting unique nodes assigned to pods (after you have a minicluster deployed)

```bash
kubectl get pods -o json  | jq -r .items[].spec.nodeName | uniq | wc -l
128
```

Monitoring:

```bash
git clone https://github.com/resmoio/kubernetes-event-exporter
cd kubernetes-event-exporter
kubectl create namespace monitoring
# edit deploy/<config> yaml
kubectl apply -f deploy
```

Now we are ready for different MiniCluster setups. For each of the below, to shell in to the lead broker (index 0) you do:

```bash
kubectl exec -it flux-sample-0-xxx bash
```

### 2. Applications

#### Single Node Benchmark

We are going to run this via flux batch, running the job across nodes (and then when they are complete, getting the logs from flux)

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-single-node-$(date +%s).json
kubectl apply -f ./crd/single-node.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
export app=single-node
output=./results/$app

# This is the number of nodes -1
nodes=127

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f crd/single-node.yaml
```

#### AMG2023

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-amg-$(date +%s).json
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

This one requires sourcing spack:

```bash
. /etc/profile.d/z10_spack_environment.sh
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=amg2023
output=./results/$app
mkdir -p $output

for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --exclusive --cores-per-task 2 --exclusive --env OMP_NUM_THREADS=2 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 3584 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 14 16 -problem 2
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/amg2023.yaml
```

#### Kripke

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-kripke-$(date +%s).json
kubectl apply -f ./crd/kripke.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=kripke
output=./results/$app
mkdir -p $output

# Each is ~6m 18s, running 3 iterations
for i in $(seq 2 3); do
  echo "Running iteration $i"
  time flux run --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 7168 kripke --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 32,14,16
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/kripke.yaml
```

#### Laghos

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-laghos-$(date +%s).json
kubectl apply -f ./crd/laghos.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=laghos
output=./results/$app

mkdir -p $output
for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --exclusive --env OMP_NUM_THREADS=1 --cores-per-task 1 -o cpu-affinity=per-task --setattr=user.study_id=$app-128-iter-$i -N128 -n 7168 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
done

# 64, 128, 256 should only change N and n , so -N 64 -n 3584, -N 128 -n 7168, -N 256 -n 14336

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```

```bash
kubectl delete -f ./crd/laghos.yaml --wait
```

#### LAMMPS-REAX

```bash
kubectl apply -f ./crd/lammps-reax.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=lammps-reax
output=./results/$app
mkdir -p $output

for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 7168 /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```

```bash
kubectl delete -f ./crd/lammps-reax.yaml --wait
```

#### LAMMPS

**We did not wind up using this problem - does not scale correctly**

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-lammps-$(date +%s).json
kubectl apply -f ./crd/lammps.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
export app=lammps
output=./results/$app

mkdir -p $output
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 7168 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/lammps.yaml
```

#### MiniFE

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-minife-$(date +%s).json
kubectl apply -f ./crd/minife.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
export app=minife
output=./results/$app
mkdir -p $output

for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 7168 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/minife.yaml
```

#### Mixbench

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-mixbench-$(date +%s).json
kubectl apply -f ./crd/mixbench.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=mixbench
output=./results/$app

# One less than actual
nodes=127
mkdir -p $output

# each single run take about 4.6m
for i in $(seq 1 5); do
    echo "Running iteration $i"
    for node in $(seq 0 $nodes); do
    flux submit --requires="hosts:flux-sample-$node" --env OMP_NUM_THREADS=56 --setattr=user.study_id=$app-128-iter-$i -l -N1 -n 1 mixbench-cpu 32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
```

#### Mt-Gemm

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-mtgemm-$(date +%s).json
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
export FI_PROVIDER=tcp,self

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 7168 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/mt-gemm.yaml
```

#### OSU

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-osu-$(date +%s).json
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

```console
oras login ghcr.io --username vsoch
export app=osu
output=./results/$app
mkdir -p $output

./flux-run-combinations.sh 128 $app

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 7168 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/osu.yaml
```

#### Quicksilver

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-quicksilver-$(date +%s).json
kubectl apply -f ./crd/quicksilver.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
export app=quicksilver
output=./results/$app
mkdir -p $output

for i in $(seq 2 5); do     
    echo "Running iteration $i"
    time flux run --env OMP_NUM_THREADS=7 --cores-per-task=7 --exclusive --setattr=user.study_id=$app-128-iter-$i -N128 -n 1024  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp  -X 128 -Y 128 -Z 64  -x 128 -y 128 -z 64  -I 16 -J 8  -K 8  -n 335544320
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app-7-threads $output
```
```bash
kubectl delete -f ./crd/quicksilver.yaml
```

#### Stream

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-stream-$(date +%s).json
kubectl apply -f ./crd/stream.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=stream
output=./results/$app

# This should be zero indexed
nodes=127
mkdir -p $output

for i in $(seq 1 5); do
  echo "Running iteration $i"
  for node in $(seq 1 $nodes); do
    flux submit --requires="hosts:flux-sample-$node" --setattr=user.study_id=$app-1-iter-$i-node-$node -N1 -n 56 -o cpu-affinity=per-task stream_c.exe
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/stream.yaml
```

### Clean Up

When you are done:

```bash
gcloud container clusters delete test-cluster --region=us-central1-a
```

### Results

```console
for tag in $(oras repo tags ghcr.io/converged-computing/metrics-operator-experiments/performance)
  do
    if [[ $tag == *"gke-cpu-128"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
