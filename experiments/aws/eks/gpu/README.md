# Performance Experiments on EKS (Kubernetes)

For this study we only got 16 p2dn.24xlarge nodes, so we had to adjust size down to be 16,8,4 from 32,16,8. Each has 8 GPU.

> V100 nodes 


## 1. Setup

Make sure you have aws-iam-authenticator installed first! If you don't you can update your credentials as follows:

```bash
eksctl create cluster --config-file ./eks-config.yaml
```
```bash
aws eks update-kubeconfig --region us-east-1 --name performance-study-gpu
```
```console
$ kubectl get nodes -o json | jq .items[].status.allocatable
{
  "cpu": "95690m",
  "ephemeral-storage": "143870061124",
  "hugepages-1Gi": "0",
  "hugepages-2Mi": "21122Mi",
  "memory": "753772012Ki",
  "nvidia.com/gpu": "8",
  "pods": "250",
  "vpc.amazonaws.com/efa": "1"
}
```

Install the flux operator (downloaded on 8/9/2024 and image pinned)

```bash
kubectl apply -f ./flux-operator.yaml
```

```
kubectl get nodes -o json > nodes-16.json
```

## 2. Design

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

## 3. Applications

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

We want to run four separate jobs, across each node. Write this into a batch file.

```console
oras login ghcr.io --username vsoch
export app=single-node-16
export output=./results/$app
mkdir -p $output

# This is the number of nodes -1
nodes=15
for node in $(seq 0 $nodes); do
  flux submit --requires="hosts:flux-sample-$node" -N 1 --setattr=user.study_id=$app-node-$node /bin/bash /entrypoint.sh
done 

# When they are done
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```
kubectl delete -f crd/single-node.yaml
```

### AMG2023

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-amg-$(date +%s).json
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
export app=amg2023-16
export output=./results/$app
mkdir -p $output

# Size 4
for i in $(seq 1 15); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N 4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 128 -P 4 4 2 -problem 2 
done

# Size 8
for i in $(seq 1 15); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N 8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 128 -P 8 4 2 -problem 2 
done

# Size 16
for i in $(seq 1 15); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-16-iter-$i -N 16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 128 -P 16 4 2 -problem 2
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/amg2023.yaml
```

### Kripke

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
export app=kripke-16
export output=./results/$app
mkdir -p $output

# Size 4
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,2,4
done

# Size 8
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4
done

# Size 16
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,8,4
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/kripke.yaml
```

### Laghos

**NOT RUN YET - NOT CUDA ENABLED?**

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
export output=./results/$app
mkdir -p $output

i=1
time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda

# Size 4
for i in $(seq 2 5); do     
  echo "Running iteration $i"  
  time flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda
done

# Size 8
for i in $(seq 1 5); do     
  echo "Running iteration $i"  
  time flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda
done

# Size 16
for i in $(seq 1 5); do     
  echo "Running iteration $i"  
  time flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```

Look for:

```console
MPI is NOT CUDA aware
```

```bash
kubectl delete -f ./crd/laghos.yaml
```

### LAMMPS-REAX

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-lammps-reax-$(date +%s).json
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
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done 

# Size 8
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done

# Size 16
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/lammps.yaml
```

### LAMMPS

**NOT RUN**
**This problem size does not scale, use reax**

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-lammps-reax-$(date +%s).json
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

n=1
time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --env FI_EFA_FORK_SAFE=0 --setattr=user.study_id=$app-4-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N4 -n 32 -g 1 lmp -k on g 8 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000

# Size 4
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N4 -n 32 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000
done 

# Size 8
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N8 -n 64 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000 

# Size 16
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-16-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N16 -n 128 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```

```bash
kubectl delete -f ./crd/lammps.yaml
```

### Magma

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-magma-$(date +%s).json
kubectl apply -f ./crd/magma.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
export app=magma-16
output=./results/$app
mkdir -p $output
nodes=15

for i in $(seq 1 5); do     
  echo "Running iteration $i"
    for node in $(seq 0 $nodes); do
      flux submit --requires="hosts:flux-sample-$node" --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-1-iter-$i -N1 -n 8 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm
  done
done

for i in $(seq 1 5); do     
  echo "Running iteration $i"
    for node in $(seq 0 $nodes); do
    flux submit --requires="hosts:flux-sample-$node" --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-vbatched-node-$node-iter-$i -N1 -n 8 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/magma.yaml
```

### MiniFE

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
app=minife-16
output=./results/$app
mkdir -p $output
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

# Size 4
for i in $(seq 1 15); do
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
done

# Size 8
for i in $(seq 1 15); do
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
done

# Size 16
for i in $(seq 1 5); do
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```

```bash
kubectl delete -f ./crd/minife.yaml
```

### Mixbench

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
export app=mixbench-16
export output=./results/$app
mkdir -p $output

# One less than actual
nodes=15

for i in $(seq 1 5); do     
    echo "Running iteration $i"
    for node in $(seq 0 $nodes); do
    flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --requires="hosts:flux-sample-$node" -N1 -n 1 -g 1 /opt/mixbench/mixbench-cuda/wrapper 32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
```

### Mt-Gemm

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-mt-gemm-$(date +%s).json
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
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100
done

# 8 Nodes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100
done

# 16 Nodes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/mt-gemm.yaml
```

### Multi GPU Models

**DOES NOT RUN** segmentation fault

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-multi-gpu-models-$(date +%s).json
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
  
# Size 4
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768
done

# Size 8
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768
done

# Size 16
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/multi-gpu-models.yaml
```

### OSU

Note: we're running host to host (`H H`) buffer tests since the device-device tests are segfaulting, and the capacity reservation extends across datacenters.

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-osu-$(date +%s).json
kubectl apply -f ./crd/osu.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```
```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Write `flux-run-combinations.sh` to the filesystem:

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
    time flux run -N 2 -n 2 -g 1 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      --env OMPI_MCA_btl=tcp,self --env FI_EFA_FORK_SAFE=1 --env FI_PROVIDER=efa \
      --env CUDA_VISIBLE_DEVICES=0 -o cpu-affinity=per-task -o gpu-affinity=per-task \
      --requires="hosts:${i},${j}" \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda H H
    time flux run -N 2 -n 2 -g 1 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      --env OMPI_MCA_btl=tcp,self --env FI_EFA_FORK_SAFE=1 --env FI_PROVIDER=efa \
      --env CUDA_VISIBLE_DEVICES=0 -o cpu-affinity=per-task -o gpu-affinity=per-task \
      --requires="hosts:${i},${j}" \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw -d cuda H H
    iter=$((iter+1))
  done
done
```

And then run as follows.

```console
oras login ghcr.io --username vsoch
app=osu
output=./results/$app
mkdir -p $output/
size=4

./flux-run-combinations.sh ${size} $app

# 4 Nodes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --env OMPI_MCA_btl=tcp,self --env FI_EFA_FORK_SAFE=1 --env FI_PROVIDER=efa \
  --setattr=user.study_id=$app-4-iter-$i -N 4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task \
  /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H
done

# 8 Nodes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --env OMPI_MCA_btl=tcp,self --env FI_EFA_FORK_SAFE=1 --env FI_PROVIDER=efa \
  --setattr=user.study_id=$app-4-iter-$i -N 8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task \
  /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda H H
done

# 16 Nodes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --env OMPI_MCA_btl=tcp,self --env FI_EFA_FORK_SAFE=1 --env FI_PROVIDER=efa \
  --setattr=user.study_id=$app-4-iter-$i -N 16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task \
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/osu.yaml
```

### Quicksilver

**only done at size 16, cancelled at 17 minutes**

Runs were way too slow...

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
app=quicksilver
output=./results/$app
mkdir -p $output

# Size 4
for i in $(seq 1 2); do     
    echo "Running iteration $i"
    flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 32 -Y 32 -Z 32 -x 32 -y 32 -z 32 -I 4 -J 4 -K 2 -n 52428800
    flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-8-iter-$i -N8 -n 64 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 104857600
done

# Size 16
for i in $(seq 1 2); do     
    echo "Running iteration $i"
    flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-16-iter-$i -N16 -n 128 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 64  -Z 32  -x 64  -y 64  -z 32  -I 8  -J 4  -K 4  -n 209715200
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```

Both options:

```bash
flux run --setattr=user.study_id=$app-$size-iter-$i -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp

# Coral 2 example
flux run --setattr=user.study_id=$app-$size-iter-$i -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem2/Coral2_P2.inp
```
```bash
kubectl delete -f ./crd/quicksilver.yaml
```

### Resnet

**Did not work**

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-single-node-$(date +%s).json
kubectl apply -f ./crd/resnet.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=resnet
output=./results/$app
mkdir -p $output
i=1
flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N 4 -g 1 /bin/bash ./launch.sh flux-sample 4 32 32

# This is what works on Google
flux run -N 2 --gpus-per-node 4 /bin/bash ./launch.sh flux-sample 2 4 16

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N 4 -n 32 -g 1 /bin/bash ./launch.sh flux-sample 4 32 32
done

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-8-iter-$i -N 8 -n 64 -g 1 /bin/bash ./launch.sh flux-sample 8 64 32
done

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-16-iter-$i -N 16 -n 128 -g 1 /bin/bash ./launch.sh flux-sample 16 128 32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/resnet.yaml
```

### Stream

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-single-node-$(date +%s).json
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
nodes=15

for i in $(seq 1 15); do
  for node in $(seq 1 $nodes)
    do
     echo "Running iteration $i"
     flux submit --requires="hosts:flux-sample-$node" --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-1-node-$node-iter-$i -N1 -n 8 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task stream 
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-gpu-16-$app $output
```
```bash
kubectl delete -f ./crd/stream.yaml
```

## Clean up

```bash
eksctl delete cluster --config-file ./eks-config.yaml
```

## Results


```console
for tag in $(oras repo tags ghcr.io/converged-computing/metrics-operator-experiments/performance)
  do
    if [[ $tag == *"eks-gpu-16"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
