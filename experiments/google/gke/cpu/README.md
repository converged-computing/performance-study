# GKE CPU Experiment

Status: This experiment has had one testing on GKE, and the configurations are updated here. We are missing configurations (tested on-premises) for:

- [ ] amg2023
- [ ] kripke
- [ ] laghos
- [ ] lammps
- [ ] minife
- [ ] mixbench
- [ ] mt-gemm
- [ ] nek5000
- [ ] osu
- [x] quicksilver
- [ ] stream

I will write the configurations from Confluence / on-premises scripts in comment blocks (when I have them).

> like this

and will update each set of commands after running / testing again.

These are previous TODOs that need to be tested again to verify if they are still issues.

Action items for team:

 - [ ] mt-gemm needs either a refactor (different source) or better script (and should be longer I think)
 - [ ] mixbench-cpu needs an equivalent wrapper to modify problem size and run across nodes
 - [ ] quicksilver doesn't run for any of the coral benchmarks, it only works at really small sizes
 - [ ] stream does not appear to be for multiple nodes
 - [ ] I'm not sure we can run nekRS (5000) unless we add Filestore
  
Concerns

 - one node (cores) on one cloud != cores on another. If we try to make them close, we are comparing different things, network wise. That hurts Google a lot, which has fewer cores/node. I'm not sure how to consolidate this, but I did tests according to number of nodes (as we spec'd out).
 - amg2023 is really flaky - I keep getting "address already in use" at random times.

Full testing times:

 - ~2 hours (early 2024)


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
NODES=32

gcloud compute networks create mtu9k --mtu=8896 
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

- cluster creation times:
  - 5m 29 seconds.
  - 5m 31 seconds (early 2024)
  

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
$ kubectl get pods -o json  | jq -r .items[].spec.nodeName | uniq | wc -l
32
```

Note that the configs are currently set to 8 nodes, with 8 gpu each. size 32vcpu (16 cores) instance (n1-standard-32).


### 2. Applications

#### Single Node Benchmark

We are going to run this via flux batch, running the job across nodes (and then when they are complete, getting the logs from flux)

```bash
kubectl apply -f ./crd/single-node.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
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

We want to run four separate jobs, across each node. Write this into a batch file.

```console
oras login ghcr.io --username vsoch
app=single-node
output=./results/$app

mkdir -p $output

# Note sure if we need iterations here
for i in $(seq 1 1); do
  echo "Running iteration $i"  
  for node in $(seq 1 4); do
    flux submit /bin/bash /entrypoint.sh
  done 
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

#### AMG2023

Create the minicluster and shell in. Note this first pull takes the longest (about ~5 minutes)

```bash
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

This one requires sourcing spack

```bash
. /etc/profile.d/z10_spack_environment.sh
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Here is an example loop through sizes and iterations. Note that we want to use affinity - the times are faster.
During testing I saw one MPI error about hostnames "address already in use" but it didn't re-occur.


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
app=amg2023
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"
  
  # 28 seconds!
  time flux run -N 32 -n 1792 -o cpu-affinity=per-task amg -P 64 7 4 -n 64 64 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 34 seconds
  time flux run -N 16 -n 896 amg -P 32 7 4 -n 64 64 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 21.810 seconds
  # Note that this seems to sometimes error that an ip address is already in use...
  # We will want to watch this closely and try re-run (or just allow to fail) those that do
  time flux run -N 16 -n 896 -o cpu-affinity=per-task amg -P 32 7 4 -n 64 64 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 25 seconds
  time flux run -N 8 -n 448 amg -P 16 7 4 -n 64 64 128  |& tee ./$output/$app-$size-iter-${i}.out

  # 15.93 seconds
  time flux run -N 8 -n 448 -o cpu-affinity=per-task amg -P 16 7 4 -n 64 64 128  |& tee ./$output/$app-$size-iter-${i}.out

  # 20 seconds
  time flux run -N 4 -n 224 amg -P 8 7 4 -n 64 64 128  |& tee ./$output/$app-$size-iter-${i}.out

  # 13.548 seconds
  time flux run -N 4 -n 224 -o cpu-affinity=per-task amg -P 8 7 4 -n 64 64 128 |& tee ./$output/$app-$size-iter-${i}.out
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

About 42-46 seconds extra pull time.

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
app=kripke
output=./results/$app

# 32 nodes from Ani: --zones 144,448,256 --procs 14,16,8


mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"

  # 1 minute 50 seconds
  time flux run -N 4 -n 224 -o cpu-affinity=per-task kripke --layout GDZ --dset 8 --zones 112,112,112 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,7,8 |& tee ./$output/$app-$size-iter-${i}.out

  # 45.239 seconds
  time flux run -N 8 -n 448 -o cpu-affinity=per-task kripke --layout GDZ --dset 8 --zones 112,112,112 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 7,8,8 |& tee ./$output/$app-$size-iter-${i}.out

  # 20.749 seconds
  time flux run -N 16 -n 896 -o cpu-affinity=per-task kripke --layout GDZ --dset 8 --zones 112,112,112 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 7,8,16 |& tee ./$output/$app-$size-iter-${i}.out

  # 13.435 seconds
  time flux run -N 32 -n 1792 -o cpu-affinity=per-task kripke --layout GDZ --dset 8 --zones 112,112,112 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 8,14,16 |& tee ./$output/$app-$size-iter-${i}.out
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

- Extra pull time of 8.6 seconds

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
app=laghos
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"

  # None of the cube configs work here, with or without affinity
  # time flux run -N32 -n 1792 -o cpu-affinity=per-task /opt/laghos/laghos -p 1 -m ./data/cube01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out
  # time flux run -N16 -n 896 /opt/laghos/laghos -p 1 -m ./data/cube01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out

  # Does not work this size and above - "***You are trying to partition a graph into too many parts!* 
  # time flux run -N16 -n 896 /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20

  # 26 seconds first cluster
  # 12.56 seconds second cluster
  # Times are same with/without CPU affinity.
  time flux run -N8 -n 448 /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out

  # 18 seconds first cluster
  # 10 seconds second cluster
  time flux run -N4 -n 224 /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out

  # 7 seconds first cluster
  # 6.22 seconds second cluster
  time flux run -N2 -n 112 /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out
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

- Additional pull time: 15.34 seconds

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
app=lammps
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # 42.68 seconds with cpu affinity
  # 41.38 seconds without affinity
  time flux run -N 4 -n 224 -o cpu-affinity=per-task lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000 |& tee ./$output/$app-$size-iter-${i}.out

  # 1 minute 6 seconds seconds without affinity
  # 1 minute 5.6 seconds with affinity
  time flux run -N 8 -n 448 -o cpu-affinity=per-task lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000 |& tee ./$output/$app-$size-iter-${i}.out

  # 1 minute 22 seconds without affinity
  # 1 minute 18 seconds with affinity (first time faster with affinity)
  time flux run -N 16 -n 896 -o cpu-affinity=per-task lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000 |& tee ./$output/$app-$size-iter-${i}.out

  # 2 minutes 12 seconds without affinity
  # 1 minute 53 seconds seconds with affinity (again faster)
  time flux run -N 32 -n 1792 -o cpu-affinity=per-task lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000 |& tee ./$output/$app-$size-iter-${i}.out
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

- Additional pull time: 5.6 seconds

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
app=minife
output=./results/$app

# 5.7 seconds
mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # 25.9 seconds with affinity
  # without affinity didn't finish after 1 minute, cancelled
  time flux run -N4 -n 224 -o cpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out

  # 14.6 seconds
  time flux run -N8 -n 448 -o cpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out

  # 9.6 seconds
  time flux run -N16 -n 896 -o cpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out

  # 8.24 seconds
  time flux run -N32 -n 1792 -o cpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

```bash
kubectl delete -f ./crd/minife.yaml
```

#### Mixbench

NOTE: this doesn't have a wrapper, and seems to be oriented to run on one node. We either need to:

 - Run as a single node test for the CPU case
 - write an equivalent wrapper that extends across nodes

```bash
kubectl apply -f ./crd/mixbench.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- ~4 seconds extra pull time, likely mostly screen printing! (trivial)

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
app=mixbench
output=./results/$app

# ~26 seconds
mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # Note that this seems to run on single nodes / processes.
  # I timed for just this first case to have one, but I don't think this is the right way to do it
  # We either need to delegate this to single node, or write a custom wrapper
  # This will run for 512 iters
  # 1 minute 18 seconds
  time mixbench-cpu
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

```bash
kubectl delete -f ./crd/mixbench.yaml
```

#### Mt-Gemm

```bash
kubectl apply -f ./crd/mt-gem.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- Additional pull time: 6 seconds

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
app=mt-gem
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # 2 seconds
  time flux run -N4 -n 224 /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi |& tee ./$output/$app-$size-iter-${i}.out

  # 3 seconds
  time flux run -N16 -n 896 /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi |& tee ./$output/$app-$size-iter-${i}.out

done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-cpu-$app $output
```

The above needs a redo - either improved printing of metrics (and increase in runtime) or a new repository.

```bash
kubectl delete -f ./crd/mt-gem.yaml
```
#### Nek5000

```bash
kubectl apply -f ./crd/nek5000.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
- Extra pull time: 19.18 seconds


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

See the AWS runs for this setup - I couldn't get it working. The reason is because it requires a shared cache. For some reason, the initial run (and cache generation) didn't work at all here, so my strategy to flux archive / flux exec across nodes didn't work. Aside from deploying a shared filesystem (Google Filestore) for this one run we might just consider removing it.


```bash
kubectl delete -f ./crd/nek5000.yaml
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
