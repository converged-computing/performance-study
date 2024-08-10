# Performance Experiments on Kubernetes

> V100 nodes 

## 1. Setup

Make sure you have aws-iam-authenticator installed first! If you don't you can update your credentials as follows:


- TODO: this instance type is 2 threads per core - how to adjust for that? 96 should be 48
  - need to update the CRD files, figure out how, and adjust that for the other setups that use it.
- TODO for each experiment - update cores for AWS instance, add fork safe envar as needed.
- TODO: Testing shared filesystem, Lustre FSX with smaller cluster
- For each: update size after in CRD, and iters for each based on time
- Update nodes for single node benchmark

```bash
aws eks update-kubeconfig --region us-east-1 --name performance-study
```
```bash
eksctl create cluster --config-file ./eks-config.yaml
```

```bash
$ kubectl get nodes -o json | jq .items[].status.allocatable
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

And now for the [FSx for Lustre](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi.html)

```
export cluster_name=performance-study
export region_code=us-east-1
```

Create a service account for our cluster for FSx

```bash
eksctl create iamserviceaccount \
  --name fsx-csi-controller-sa \
  --namespace kube-system \
  --cluster $cluster_name \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonFSxFullAccess \
  --approve \
  --role-name AmazonEKSFSxLustreCSIDriverFullAccess \
  --region $region_code
```

When that is done, apply the driver:

```bash
# https://github.com/kubernetes-sigs/aws-fsx-csi-driver/branches/all
kubectl apply -k "github.com/kubernetes-sigs/aws-fsx-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.2"
```

Get the ARN created and annotate the service account (I got mine from the kubeconfig update and it's also in cloud formation)

```
aws eks update-kubeconfig --region us-east-1 --name $cluster_name
Updated context arn:aws:eks:us-east-1:633731392008:cluster/performance-study in /home/vanessa/.kube/config
```

```bash
kubectl annotate serviceaccount -n kube-system fsx-csi-controller-sa \
  eks.amazonaws.com/role-arn=arn:aws:eks:us-east-1:633731392008:role/AmazonEKSFSxLustreCSIDriverFullAccess --overwrite=true
```

The security group:

```bash
aws eks describe-cluster --name $cluster_name --query cluster.resourcesVpcConfig.clusterSecurityGroupId --region us-east-1
```

Note that I stopped when I had to manually create a VPC, I am wondering if it's too much anguish for the benefit of one more app.

See [here](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi.html) for full instructions.

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

**IMPORTANT** these are added with size 4 for testing. Before largest size experiments, change the size of the minicluster yaml to the correct cluster size.

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
app=single-node
output=./results/$app

mkdir -p $output

# Note sure if we need iterations here (likely not)
# TODO: update nodes
nodes=4
for i in $(seq 1 1); do     
  echo "Running iteration $i"  
  for node in $(seq 1 $nodes); do
    flux submit --setattr=user.study-id=$app-node-$node /bin/bash /entrypoint.sh |& tee ./$output/$app-node-$node.out
  done 
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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
Here is a single node test:

```bash
# Single node test
flux run -N 1 -n 8 -g 1 amg -P 2 2 2 -n 64 64 64
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
  flux run --setattr=user.study-id=$app-$size-iter-$i -N 16 -n 128 -g 1 amg -P 4 4 8 -n 64 128 128 |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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

```console
🧪️
# /p/vast1/convcomp/crosspform/scripts/GPU/Kripke/2n/flux-test-marathe1.sh 
# CUDA_VISIBLE_DEVICES is exported in the container.

# Note that this is for the same number of tasks on lassen - on Google Cloud we have 16/node (32)
time flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,72,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 2,1,1  |& tee ./$output/$app-16-iter-${i}.out

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
time flux run --setattr=user.study-id=$app-$size-iter-$i -N4 -n 16 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,72,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 2,2,1 |& tee ./$output/$app-4-iter-${i}.out
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

time flux run --setattr=user.study-id=$app-$size-iter-$i -N32 -n 128 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 256,256,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,4  |& tee ./$output/$app-16-iter-${i}.out

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
  time flux run --setattr=user.study-id=$app-$size-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,4,8  |& tee ./$output/$app-16-iter-${i}.out

 time flux run --setattr=user.study-id=$app-$size-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,4,4 |& tee ./$output/$app-8-iter-${i}.out

 time flux run --setattr=user.study-id=$app-$size-iter-$i -N4 -n 32 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,4,2 |& tee ./$output/$app-4-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/laghos/32n/run-laghos.base.sh

time flux run --setattr=user.study-id=$app-$size-iter-$i -N 32 -n 128 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom

lrun -vvv -N 32 -n 128 laghos -pa -p 1 -tf 0.6 -pt 311 -m data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom
```

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/laghos/16n/run-laghos.base.sh

time flux run --setattr=user.study-id=$app-$size-iter-$i -N 16 -n 64 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom

lrun -vvv -N 16 -n 64 ./laghos -pa -p 1 -tf 0.6 -pt 311 -m data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom
```

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/laghos/16n/run-laghos.base.sh

time flux run --setattr=user.study-id=$app-$size-iter-$i -N 4 -n 16 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom

lrun -vvv -N 4 -n 16 ./laghos -pa -p 1 -tf 0.6 -pt 311 -m data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 -d cuda --fom
```

```console
oras login ghcr.io --username vsoch
app=laghos
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study-id=$app-$size-iter-$i -N16 -n 128 -g 1 /opt/laghos/cuda/laghos -p 1 -m ./data/cube01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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

```console
🧪️
# Note from vsoch: I think -n needs to be set at 8, because each GPU only uses 8 cpu?
# I matched mpirun for now but I think this is wrong (see my original command)
/p/vast1/convcomp/crosspform/scripts/GPU/LAMMPS/16n/run_micro_V100_16n.sh 

flux run --setattr=user.study-id=$app-$size-iter-$i -N4 -n 64 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 256 -v y 256 -v z 256 -var nsteps 1000  |& tee ./$output/$app-$size-iter-${i}.out

mpirun -np 64 --hostfile hostfile -N 4 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in common/in.snap.test -var snapdir common/2J8_W.SNAP -var nx 256 -var ny 256 -var nz 256 -var nsteps 1000
```

```console
🧪️
/p/vast1/convcomp/crosspform/scripts/GPU/LAMMPS/32n/run_micro_V100_32n.sh 

flux run --setattr=user.study-id=$app-$size-iter-$i -N32 -n 128 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 256 -v y 256 -v z 256 -var nsteps 1000  |& tee ./$output/$app-$size-iter-${i}.out

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
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2  -n 8 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000  |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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

```console
oras login ghcr.io --username vsoch
app=magma
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
```

Other commands

```bash
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm
time flux run -N1 -n 4 -g 1 -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm --ngpu 1

# Note this seemed to allow running across gpu (the --gpus 4 worked) but in practice we didn't see them running.
# export MAGMA_NUM_GPUS=4
time flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1
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

```console
🧪️
# note from vsoch: I couldn't find nnodes/ntasks variables here.
/p/vast1/convcomp/crosspform/scripts/GPU/miniFE/32n/minife-run.sh  

# This only was different in elem_group_size
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 -o gpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=1 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out

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
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 -o gpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 ./wrapper 64 |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 /opt/gem/mt-dgemm.x 8192 200 |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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

```console
oras login ghcr.io --username vsoch
app=multi-gpu-models
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run --setattr=user.study-id=$app-$size-iter-$i -N1 --gpus-per-node 4 /opt/multi-gpu-programming-models/mpi/jacobi -niter 20000 |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 /opt/multi-gpu-programming-models/mpi/jacobi -niter 5000

# 50 seconds
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000

# 1 minute 36 seconds
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000
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
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 nekrs --setup turbPipe.par |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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
flux run --setattr=user.study-id=$app-$size-iter-$i -N1 -n 4 -g 1 nekrs --setup turbPipe.par
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 nekrs --setup turbPipe.par
```

```bash
kubectl delete -f ./crd/nek5000.yaml
```

For running on dane (test):

```
singularity exec --pwd /tmp/turb ./metric-nek5000_cpu.sif /usr/local/bin/mpirun -np 2 nekrs --setup turbPipe.par
```

### OSU

```bash
kubectl apply -f ./crd/osu.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
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
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n2 -g 1 /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw -d cuda D D |& tee ./$output/$app-osu_bw-$size-iter-${i}.out
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n8 -g 1 -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda D D |& tee ./$output/$app-osu_allreduce-$size-iter-${i}.out
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n2 -g 1 -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda D D |& tee ./$output/$app-osu_latency-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
```

```bash
kubectl delete -f ./crd/osu.yaml
```

### Quicksilver

```bash
kubectl apply -f ./crd/quicksilver.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

Testing setup from Abhik!

```bash
🧪️
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 16 -Y 16 -Z 16 -x 16 -y 16 -z 16 -I 2 -J 2 -K 1 -n 163840  |& tee ./$output/$app-$size-iter-${i}.out
flux run --setattr=user.study-id=$app-$size-iter-$i -N4 -n 16 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 32 -Y 16 -Z 16 -x 32 -y 16 -z 16 -I 2 -J 2 -K 2 -n 327680  |& tee ./$output/$app-$size-iter-${i}.out
flux run --setattr=user.study-id=$app-$size-iter-$i -N8 -n 32 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  Y 64 -Z 32 -x 64 -y 64 -z 32 -I 8 -J 4 -K 4 -n 167772160 |& tee ./$output/$app-$size-iter-${i}.out

# note from vsoch - did I miss 16?
flux run --setattr=user.study-id=$app-$size-iter-$i -N32 -n 128 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 32 -Y 32 -Z 32 -x 32 -y 32 -z 32 -I 4 -J 4 -K 2 -n 1310720 |& tee ./$output/$app-$size-iter-${i}.out

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
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp  |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
```

Both options:

```bash
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp

# Coral 2 example
flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem2/Coral2_P2.inp
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

```console
oras login ghcr.io --username vsoch
app=resnet
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  flux run --setattr=user.study-id=$app-$size-iter-$i -N 2 --gpus-per-node 4 /bin/bash ./launch.sh flux-sample 2 4 16 |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
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

```console
oras login ghcr.io --username vsoch
app=stream
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"  
  flux run --setattr=user.study-id=$app-$size-iter-$i -N2 -n 8 -g 1 -o gpu-affinity=per-task stream  |& tee ./$output/$app-$size-iter-${i}.out
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
    flux job info $jobid jobspec &> ./$output/$app-${jobid}.out 
    flux job info $jobid guest.exec.eventlog &> ./$output/$app-${jobid}.out
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:parallel-cluster-gpu-$app $output
```

```bash
kubectl delete -f ./crd/stream.yaml
```

## Clean up

```bash
eksctl delete cluster --config-file ./eks-config.yaml
```
