# GKE GPU Experiment

Status: This experiment has had one testing on GKE, and the configurations are updated here. We are missing configurations (tested on-premises) for:

- [ ] amg2023
- [x] kripke
- [x] laghos
- [x] lammps
- [ ] magma
- [x] minife
- [x] mixbench
- [x] mt-gemm
- [ ] multi-gpu-models
- [x] nek5000
- [x] osu
- [x] quicksilver
- [ ] resnet
- [ ] stream

Note that the above that are checked may not be complete - I checked those that we have at least something to go off from. 

```console
🧪️
/path/to/on-premises-script.sh
like this
```

Questions:

 - Do we want to mimic the number of CPU on lassen or stick with what Google Cloud has?
 - I'm not sure we can run nek5000 unless we also deploy filestore.

and will update each set of commands after running / testing again.

- Testing times
- Start time: 5:02pm Mountain, end 5:54pm (early 2024)

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

## Notes

### Cost

We previously were asking for 8 across two nodes, now we are going to ask for 8 per node. We won't have time to look at GPU usage and tweak, we just have time to ensure the apps run and generate output we can save. If we do 8 GPU for 8 nodes, this would be 64 x [the cost per hour](https://cloud.google.com/compute/gpus-pricing) $2.48, which is $158/hour. We can adjust from that size depending on our risk tolerance. If we go the full size, 32 nodes * 8 GPU, that would be $634.88 per hour. We'd only get one hour, if we were safe, because we only have 1K in credits left.

## Experiment

### 1. Setup

Bring up the cluster (with some number of nodes) and install the drivers. Have your GitHub packages (or other registry credential / token) ready. This does not work.

```bash
GOOGLE_PROJECT=myproject
NODES=4
GPUS=4

gcloud compute networks create mtu9k --mtu=8896 

time gcloud container clusters create gpu-two-cluster \
    --threads-per-core=1 \
    --accelerator type=nvidia-tesla-v100,count=$GPUS \
    --num-nodes=$NODES \
    --machine-type=n1-standard-32 \
    --network-performance-configs=total-egress-bandwidth-tier=TIER_1 \
    --enable-gvnic \
    --network=mtu9k \
    --system-config-from-file=./system-config.yaml \
    --region=us-central1-a \
    --project=${GOOGLE_PROJECT} 
```

- Up time: 5:54

Testing cluster size:

```console
NODES=16
GPUS=8

time gcloud container clusters create gpu-cluster \
    --threads-per-core=1 \
    --accelerator type=nvidia-tesla-v100,count=$GPUS \
    --num-nodes=$NODES \
    --machine-type=n1-standard-32 \
    --region=us-central1-a \
    --project=${GOOGLE_PROJECT} 
```

- Creation times:
  - Cluster: 6 min 13 seconds

Install the daemonset:

```bash
kubectl apply -f daemonset.yaml
```

Sanity check installed on all nodes

```bash
kubectl get nodes -o json | jq .items[].status.allocatable
kubectl get nodes -o json | jq .items[].status.allocatable | grep nvidia | wc -l
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

### 2. Applications

#### Single Node Benchmark

We are going to run this via flux batch, running the job across nodes (and then when they are complete, getting the logs from flux)

**IMPORTANT** change the size of the minicluster yaml to the correct cluster size.

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

```
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

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

### AMG2023

Create the minicluster and shell in. Note this first pull takes the longest (about ~5 minutes)

```bash
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
4 min 58 seconds

This one requires sourcing spack

```bash
. /etc/profile.d/z10_spack_environment.sh
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

Here is an example loop through sizes and iterations. Note that this is done expecting that parameters
might change for different sizes.

```console
oras login ghcr.io --username vsoch
app=amg2023
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"
  flux run -N 16 -n 128 -g 1 amg -P 4 4 8 -n 64 128 128 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

On two nodes this problem is almost instant.

```bash
kubectl delete -f ./crd/amg2023.yaml
```

### Kripke

```bash
kubectl apply -f ./crd/kripke.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

About 46 seconds extra pull time.

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
🧪️
# /p/vast1/convcomp/crosspform/scripts/GPU/Kripke/2n/flux-test-marathe1.sh 
# CUDA_VISIBLE_DEVICES is exported in the container.

# Note that this is for the same number of tasks on lassen - on Google Cloud we have 16/node (32)
time flux run -N2 -n 8 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,72,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 2,1,1  |& tee ./$output/$app-16-iter-${i}.out

CUDA_VISIBLE_DEVICES=0,1,2,3 \
    srun -N 2 -n 8 \
    ./${kripke_bin} \
    --arch CUDA \
    --layout GDZ \
    --dset 8 \
    --zones 128,72,128 \
    --gset 16 \
    --groups 64 \
    --niter 50 \
    --legendre 8 \
    --quad 8 \
    --procs 2,1,1
```

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/Kripke/4n/kripke-run.sh         
time flux run -N4 -n 16 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,72,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 2,2,1 |& tee ./$output/$app-4-iter-${i}.out
done

CUDA_VISIBLE_DEVICES=0,1,2,3 \
    srun -N 4 -n 16 \
    ./${kripke_bin} \
    --arch CUDA \
    --layout GDZ \
    --dset 8 \
    --zones 128,72,128 \
    --gset 16 \
    --groups 64 \
    --niter 50 \
    --legendre 8 \
    --quad 8 \
    --procs 2,2,1
```

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/Kripke/32n/kripke-run.sh 

time flux run -N32 -n 128 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 256,256,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,4  |& tee ./$output/$app-16-iter-${i}.out

CUDA_VISIBLE_DEVICES=0,1,2,3 \
    srun -N 32 -n 128 \
    ${kripke_bin} \
    --arch CUDA \
    --layout GDZ \
    --dset 8 \
    --zones 256,256,128 \
    --gset 16 \
    --groups 64 \
    --niter 50 \
    --legendre 8 \
    --quad 8 \
    --procs 8,4,4
```

```console
oras login ghcr.io --username vsoch
app=kripke
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"
  time flux run -N16 -n 128 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,4,8  |& tee ./$output/$app-16-iter-${i}.out

 time flux run -N8 -n 64 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,4,4 |& tee ./$output/$app-8-iter-${i}.out

 time flux run -N4 -n 32 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,4,2 |& tee ./$output/$app-4-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

```bash
kubectl delete -f ./crd/kripke.yaml
```

Times:

 - 16 nodes: 23 seconds
 - 8 nodes: 41 seconds
 - 4 nodes: 1m 28s


### Laghos

```bash
kubectl apply -f ./crd/laghos.yaml
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


```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/laghos/32n/run-laghos.base.sh

time flux run -N 32 -n 128 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom

lrun -vvv -N 32 -n 128 laghos -pa -p 1 -tf 0.6 -pt 311 -m data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom
```

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/laghos/16n/run-laghos.base.sh

time flux run -N 16 -n 64 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom

lrun -vvv -N 16 -n 64 ./laghos -pa -p 1 -tf 0.6 -pt 311 -m data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom
```

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/laghos/16n/run-laghos.base.sh

time flux run -N 4 -n 16 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom

lrun -vvv -N 4 -n 16 ./laghos -pa -p 1 -tf 0.6 -pt 311 -m data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom
```

```console
oras login ghcr.io --username vsoch
app=laghos
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"
  time flux run -N16 -n 128 -g 1 /opt/laghos/cuda/laghos -p 1 -m ./data/cube01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

This might be a problem:

```console
MPI is NOT CUDA aware
```

Note that I stopped here, went back and rebuilt all containers, adding oras and removing mpich and the associated library.

Times for 20 max steps:

  - 4 nodes: 36 seconds
  - 8 nodes: 30 seconds 
  - 16 nodes: 58 seconds

```bash
kubectl delete -f ./crd/laghos.yaml
```


### LAMMPS

```bash
kubectl apply -f ./crd/lammps.yaml
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


```console
🧪️
# Note from vsoch: I think -n needs to be set at 8, because each GPU only uses 8 cpu?
# I matched mpirun for now but I think this is wrong (see my original command)
/p/vast1/convcomp/crosspform/scripts/GPU/LAMMPS/16n/run_micro_V100_16n.sh 

flux run -N4 -n 64 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 256 -v y 256 -v z 256 -var nsteps 1000  |& tee ./$output/$app-$size-iter-${i}.out

mpirun -np 64 --hostfile hostfile -N 4 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in common/in.snap.test -var snapdir common/2J8_W.SNAP -var nx 256 -var ny 256 -var nz 256 -var nsteps 1000
```

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/LAMMPS/32n/run_micro_V100_32n.sh 

flux run -N32 -n 128 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 256 -v y 256 -v z 256 -var nsteps 1000  |& tee ./$output/$app-$size-iter-${i}.out

mpirun -np 128 --hostfile hostfile -N 32 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in common/in.snap.test -var snapdir common/2J8_W.SNAP -var nx 256 -var ny 256 -var nz 256 -var nsteps 1000
```

```console
oras login ghcr.io --username vsoch
app=lammps
output=./results/$app

# 1 minute 1 second on 2 nodes
# 53 seconds on lassen 2 nodes
# 21.161 seconds on lassen 8 nodes
# 1 minute 45 seconds for 8 nodes
mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N2  -n 8 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000  |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

```bash
kubectl delete -f ./crd/lammps.yaml
```


### Magma

> With or without mnist data?

```bash
kubectl apply -f ./crd/magma.yaml
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

```console
oras login ghcr.io --username vsoch
app=magma
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N2 -n 8 -g 1 -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

Other commands

```bash
flux run -N2 -n 8 -g 1 -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm
time flux run -N1 -n 4 -g 1 -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm --ngpu 1

# Note this seemed to allow running across gpu (the --gpus 4 worked) but in practice we didn't see them running.
# export MAGMA_NUM_GPUS=4
time flux run -N2 -n 8 -g 1 -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1
```
```console
using MAGMA GPU interface
magma_zgesv failed with info=    1
magma_zgesv failed with info=    1
using MAGMA GPU interface
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
🧪️
# note from vsoch: I couldn't find nnodes/ntasks variables here.
/p/vast1/convcomp/crosspform/scripts/GPU/miniFE/32n/minife-run.sh  

# This only was different in elem_group_size
flux run -N2 -n 8 -g 1 -o gpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=1 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out

srun -N ${nnodes} -n ${ntasks} ./miniFE.x nx=${inputx} ny=${inputy} nz=${inputz} num_devices=4 use_locking=1 elem_group_size=1 use_elem_mat_fields=10 verify_solution=0
```

```console
oras login ghcr.io --username vsoch
app=minife
output=./results/$app

# 5.7 seconds
mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N2 -n 8 -g 1 -o gpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

```bash
kubectl delete -f ./crd/minife.yaml
```

### Mixbench

```bash
kubectl apply -f ./crd/mixbench.yaml
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

```console
🧪️
# note from vsoch: couldn't find these variables on lassen - where is the wrapper?
srun -N ${nnodes} -n ${ntasks} ./mixbench-cuda ${input}
```

```console
oras login ghcr.io --username vsoch
app=mixbench
output=./results/$app

# ~26 seconds
mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N2 -n 8 -g 1 ./wrapper 64 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

```bash
kubectl delete -f ./crd/mixbench.yaml
```


### Mt-Gemm


```bash
kubectl apply -f ./crd/mt-gem.yaml
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


```console
🧪️
# /p/vast1/convcomp/crosspform/scripts/GPU/mt-gemm/32n
srun -N 32 -n 128 ./mt-dgemm.x 16384 60
```

```console
🧪️
# /p/vast1/convcomp/crosspform/scripts/GPU/mt-gemm/4n
srun -N 2 -n 8 ./mt-dgemm.x 8192 200
```

```console
oras login ghcr.io --username vsoch
app=mt-gem
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N2 -n 8 -g 1 /opt/gem/mt-dgemm.x 8192 200 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

```bash
kubectl delete -f ./crd/mt-gem.yaml
```

### Multi GPU Models

```bash
kubectl apply -f ./crd/multi-gpu-models.yaml
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


```console
oras login ghcr.io --username vsoch
app=multi-gpu-models
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N1 --gpus-per-node 4 /opt/multi-gpu-programming-models/mpi/jacobi -niter 20000 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

Other options:

```bash
# This was 30 seconds, and took up about 100% of each of 4 gpu
flux submit --watch -N1 --gpus-per-node 4 /opt/multi-gpu-programming-models/mpi/jacobi -niter 5000

# 48 seconds
flux submit --watch -N1 --gpus-per-node 4 /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000

# 1 minute 30 seconds
flux submit --watch -N1 --gpus-per-node 4 /opt/multi-gpu-programming-models/mpi/jacobi -niter 20000

# 28 seconds
flux run -N2 -n 8 -g 1 /opt/multi-gpu-programming-models/mpi/jacobi -niter 5000

# 50 seconds
flux run -N2 -n 8 -g 1 /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000

# 1 minute 36 seconds
flux run -N2 -n 8 -g 1 /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000
```


```bash
kubectl delete -f ./crd/multi-gpu-models.yaml
```

### Nek5000

```bash
kubectl apply -f ./crd/nek5000.yaml
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

```console
🧪️
# Note from vsoch: this config doesn't seem to have changed, just resources.
time jsrun -n 128 --rs_per_host=4 --tasks_per_rs=1 -l cpu-cpu ${app_base}/build/nekrs --setup turbPipe.par
```

```console
oras login ghcr.io --username vsoch
app=nek5000
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N2 -n 8 -g 1 nekrs --setup turbPipe.par |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

Other commands:

```bash
# Local test
cd /opt/nekrs/examples/turbPipePeriodic

# this uses about 80% of each of 2
mpirun --allow-run-as-root -np 2 nekrs --setup turbPipe.par

# this uses about 68-74% of each of 4
mpirun --allow-run-as-root -np 4 nekrs --setup turbPipe.par

# 4 GPU does not converge
mpirun --allow-run-as-root -n 4 nekrs --setup turbPipe.par

# Flux with one node and two nodes
flux run -N1 -n 4 -g 1 nekrs --setup turbPipe.par
flux run -N2 -n 8 -g 1 nekrs --setup turbPipe.par
```

```bash
kubectl delete -f ./crd/nek5000.yaml
```

### OSU

```bash
kubectl apply -f ./crd/osu.yaml
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

Note that these are from confluence - I didn't check against cluster.

```console
🧪️
# Note from vsoch: I'm not sure how to map these!
time jsrun -n 1280 --rs_per_host=40 --tasks_per_rs=1 -l cpu-cpu /p/vast1/convcomp/crosspform/benchmarks/GPU/osu-micro-benchmarks-5.8/install/libexec/osu-micro-benchmarks/mpi/collective/osu_ibarrier

time jsrun -n 1280 --rs_per_host=40 --tasks_per_rs=1 -l cpu-cpu /p/vast1/convcomp/crosspform/benchmarks/GPU/osu-micro-benchmarks-5.8/install/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce
```

```console
oras login ghcr.io --username vsoch
app=osu
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N2 -n2 -g 1 /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw -d cuda D D |& tee ./$output/$app-osu_bw-$size-iter-${i}.out
  flux run -N2 -n8 -g 1 -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda D D |& tee ./$output/$app-osu_allreduce-$size-iter-${i}.out
  flux run -N2 -n2 -g 1 -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda D D |& tee ./$output/$app-osu_latency-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

```bash
kubectl delete -f ./crd/osu.yaml
```

### Quicksilver

```bash
kubectl apply -f ./crd/quicksilver.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
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

Testing setup from Abhik!

```bash
🧪️
flux run -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 16 -Y 16 -Z 16 -x 16 -y 16 -z 16 -I 2 -J 2 -K 1 -n 163840  |& tee ./$output/$app-$size-iter-${i}.out
flux run -N4 -n 16 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 32 -Y 16 -Z 16 -x 32 -y 16 -z 16 -I 2 -J 2 -K 2 -n 327680  |& tee ./$output/$app-$size-iter-${i}.out
flux run -N8 -n 32 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  Y 64 -Z 32 -x 64 -y 64 -z 32 -I 8 -J 4 -K 4 -n 167772160 |& tee ./$output/$app-$size-iter-${i}.out

# note from vsoch - did I miss 16?
flux run -N32 -n 128 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 32 -Y 32 -Z 32 -x 32 -y 32 -z 32 -I 4 -J 4 -K 2 -n 1310720 |& tee ./$output/$app-$size-iter-${i}.out

srun -N2 -n8 qs -i Coral2_P1.inp -X 32 -Y 16 -Z 16 -x 32 -y 16 -z 16 -I 2 -J 2 -K 2 -n 327680
srun -N4 -n16 qs -i Coral2_P1.inp -X 32 -Y 32 -Z 16 -x 32 -y 32 -z 16 -I 4 -J 2 -K 2 -n 655360
srun -N8 -n32 qs -i Coral2_P1.inp -X 32 -Y 32 -Z 32 -x 32 -y 32 -z 32 -I 4 -J 4 -K 2 -n 1310720
srun -N32 -n128 qs -i Coral2_P1.inp -X 64  Y 64 -Z 32 -x 64 -y 64 -z 32 -I 8 -J 4 -K 4 -n 167772160
srun -N32 -n512 qs -i Coral2_P1.inp -X 64 -Y 64 -Z 32 -x 64 -y 64 -z 32 -I 8 -J 8 -K 8 -n 83886080
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=quicksilver
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp  |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

Both options:

```bash
flux run -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp

# Coral 2 example
flux run -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem2/Coral2_P2.inp
```

```bash
kubectl delete -f ./crd/quicksilver.yaml
```

### Resnet

```bash
kubectl apply -f ./crd/resnet.yaml
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

```console
oras login ghcr.io --username vsoch
app=resnet
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run -N 2 --gpus-per-node 4 /bin/bash ./launch.sh flux-sample 2 4 16 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

```bash
kubectl delete -f ./crd/resnet.yaml
```

### Stream

```bash
kubectl apply -f ./crd/stream.yaml
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


```console
oras login ghcr.io --username vsoch
app=stream
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"  
  flux run -N2 -n 8 -g 1 -o gpu-affinity=per-task stream  |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:gke-gpu-$app $output
```

```bash
kubectl delete -f ./crd/stream.yaml
```

### Clean Up

When you are done:

```bash
gcloud container clusters delete test-cluster --region=us-central1-a
```
