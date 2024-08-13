# Performance Experiments on Kubernetes

> V100 nodes 

- Testing size is 4 GPU nodes, 8 GPU each.

## 1. Setup

Make sure you have aws-iam-authenticator installed first! If you don't you can update your credentials as follows:

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

```console
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

1. Have N people start monitoring the cluster.

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
for i in $(seq 1 15); do     
  echo "Running iteration $i"
  flux run --setattr=user.study-id=$app-4-iter-$i -N 4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 200 -P 4 4 2 -problem 2 |& tee ./$output/$app-4-iter-${i}.out
  flux run --setattr=user.study-id=$app-8-iter-$i -N 8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 200 -P 8 4 2 -problem 2 |& tee ./$output/$app-8-iter-${i}.out
  flux run --setattr=user.study-id=$app-16-iter-$i -N 16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 200 -P 16 4 2 -problem 2 |& tee ./$output/$app-16-iter-${i}.out
  flux run --setattr=user.study-id=$app-32-iter-$i -N 32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 200 -P 32 4 2 -problem 2 |& tee ./$output/$app-32-iter-${i}.out
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
oras login ghcr.io --username vsoch
app=kripke
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"

  time flux run --setattr=user.study-id=$app-4-iter-$i -N4 -n 32 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,2,4  |& tee ./$output/$app-4-iter-${i}.out

  time flux run --setattr=user.study-id=$app-8-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4  |& tee ./$output/$app-8-iter-${i}.out

  time flux run --setattr=user.study-id=$app-16-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,8,4  |& tee ./$output/$app-16-iter-${i}.out

  time flux run --setattr=user.study-id=$app-32-iter-$i -N32 -n 256 -g 1 -o gpu-affinity=per-task kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,8  |& tee ./$output/$app-32-iter-${i}.out

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
oras login ghcr.io --username vsoch
app=laghos
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  
  time flux run -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study-id=$app-4-iter-$i -N4 -n 32 -g 1 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda |& tee ./$output/$app-4-iter-${i}.out

  time flux run -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study-id=$app-8-iter-$i -N8 -n 64 -g 1 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda |& tee ./$output/$app-8-iter-${i}.out

  time flux run -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study-id=$app-16-iter-$i -N16 -n 128 -g 1 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda |& tee ./$output/$app-16-iter-${i}.out

  time flux run -o gpu-affinity=per-task -o cpu-affinity=per-task --setattr=user.study-id=$app-32-iter-$i -N32 -n 256 -g 1 /opt/laghos/cuda/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom -d cuda |& tee ./$output/$app-32-iter-${i}.out

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
oras login ghcr.io --username vsoch
app=lammps
output=./results/$app

# NOTE: the below takes 4 minutes. If taking too long, drop back to 3 iterations
mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"

  flux run --setattr=user.study-id=$app-4-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N4 -n 32 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000  |& tee ./$output/$app-4-iter-${i}.out

  flux run --setattr=user.study-id=$app-8-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N8 -n 64 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000  |& tee ./$output/$app-8-iter-${i}.out

  flux run --setattr=user.study-id=$app-16-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N16 -n 128 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000  |& tee ./$output/$app-16-iter-${i}.out

  flux run --setattr=user.study-id=$app-32-iter-$i -o gpu-affinity=per-task -o cpu-affinity=per-task -N32 -n 256 -g 1 lmp -k on g 4 -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000  |& tee ./$output/$app-32-iter-${i}.out
  
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
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --setattr=user.study-id=$app-1-iter-$i -N1 -n 8 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm |& tee ./$output/$app-1-iter-${i}.out
  time flux run --setattr=user.study-id=$app-vbatched-1-iter-$i -N1 -n 8 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm_vbatched --ngpu 1 |& tee ./$output/$app-vbatched-1-iter-${i}.out

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

# 5.7 seconds
mkdir -p $output
for i in $(seq 1 5); do
  echo "Running iteration $i"

  flux run --setattr=user.study-id=$app-4-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0 |& tee ./$output/$app-4-iter-${i}.out

  flux run --setattr=user.study-id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0 |& tee ./$output/$app-8-iter-${i}.out

  flux run --setattr=user.study-id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0 |& tee ./$output/$app-16-iter-${i}.out

  flux run --setattr=user.study-id=$app-32-iter-$i -N32 -n 256 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 num_devices=8 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0 |& tee ./$output/$app-32-iter-${i}.out

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
oras login ghcr.io --username vsoch
app=mixbench
output=./results/$app

# ~26 seconds
mkdir -p $output
for i in $(seq 1 5); do     
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
oras login ghcr.io --username vsoch
app=mt-gem
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"

  flux run --setattr=user.study-id=$app-4-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100 |& tee ./$output/$app-4-iter-${i}.out

  flux run --setattr=user.study-id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100 |& tee ./$output/$app-8-iter-${i}.out

  flux run --setattr=user.study-id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100 |& tee ./$output/$app-16-iter-${i}.out

  flux run --setattr=user.study-id=$app-32-iter-$i -N32 -n 256 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/gem/mt-dgemm.x 16384 100 |& tee ./$output/$app-32-iter-${i}.out

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
for i in $(seq 1 5); do     
  echo "Running iteration $i"

  flux run --setattr=user.study-id=$app-4-iter-$i -N4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768 |& tee ./$output/$app-4-iter-${i}.out

  flux run --setattr=user.study-id=$app-8-iter-$i -N8 -n 64 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768 |& tee ./$output/$app-8-iter-${i}.out

  flux run --setattr=user.study-id=$app-16-iter-$i -N16 -n 128 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768 |& tee ./$output/$app-16-iter-${i}.out

  flux run --setattr=user.study-id=$app-32-iter-$i -N32 -n 256 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task /opt/multi-gpu-programming-models/mpi/jacobi -niter 10000 -nx 32768 -ny 32768 |& tee ./$output/$app-32-iter-${i}.out

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

Write this script to the filesystem:

```bash
#/bin/bash

nodes=$1
output=$2
app=$3
hosts=$4

# At most 28 combinations, 8 nodes 2 at a time
hosts=$(flux run -N $1 hostname | shuf -n 28 | tr '\n' ' ')
list=${hosts}

dequeue_from_list() {
  shift;
  list=$@
}

for i in $hosts; do
  dequeue_from_list $list
  for j in $list; do
    echo "${i} ${j}"
    iter="${i}-${j}"
    flux run -N 2 -n 2 -g 1 \
      --setattr=user.study-id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o gpu-affinity=per-task \
      -o cpu-affinity=per-task \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency -d cuda D D |& tee ./$output/$app-osu_latency-2-iter-${iter}.out 
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw -d cuda D D |& tee ./$output/$app-osu_bw-2-iter-${iter}.out 
  done
done
```

And then run as follows.

```console
oras login ghcr.io --username vsoch
app=osu
output=./results/$app

./flux-run-combinations-cuda.sh 32 $output $app 8

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --setattr=user.study-id=$app-4-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda D D |& tee ./$output/$app-osu_allreduce-4-iter-${i}.out

  flux run --setattr=user.study-id=$app-8-iter-$i -N8 -n 64 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda D D |& tee ./$output/$app-osu_allreduce-8-iter-${i}.out

  flux run --setattr=user.study-id=$app-16-iter-$i -N16 -n 128 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda D D |& tee ./$output/$app-osu_allreduce-16-iter-${i}.out

  flux run --setattr=user.study-id=$app-32-iter-$i -N32 -n 256 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce -d cuda D D |& tee ./$output/$app-osu_allreduce-32-iter-${i}.out

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
    flux run --setattr=user.study-id=$app-4-iter-$i -N4 -n 32 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 32 -Y 32 -Z 32 -x 32 -y 32 -z 32 -I 4 -J 4 -K 2 -n 52428800  |& tee ./$output/$app-4-iter-${i}.out
    flux run --setattr=user.study-id=$app-8-iter-$i -N8 -n 64 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 104857600 |& tee ./$output/$app-8-iter-${i}.out
    flux run --setattr=user.study-id=$app-16-iter-$i -N16 -n 128 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 64  -Z 32  -x 64  -y 64  -z 32  -I 8  -J 4  -K 4  -n 209715200 |& tee ./$output/$app-16-iter-${i}.out
    flux run --setattr=user.study-id=$app-32-iter-$i -N32 -n 256 -g 1 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 64  -Z 64  -x 64  -y 64  -z 64  -I 8  -J 8  -K 4 -n 419430400  |& tee ./$output/$app-32-iter-${i}.out
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
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --setattr=user.study-id=$app-4-iter-$i -N 4 -n 32 -g 1 /bin/bash ./launch.sh flux-sample 4 32 32 |& tee ./$output/$app-4-iter-${i}.out
  flux run --setattr=user.study-id=$app-8-iter-$i -N 8 -n 64 -g 1 /bin/bash ./launch.sh flux-sample 8 64 32 |& tee ./$output/$app-8-iter-${i}.out
  flux run --setattr=user.study-id=$app-16-iter-$i -N 16 -n 128 -g 1 /bin/bash ./launch.sh flux-sample 16 128 32 |& tee ./$output/$app-16-iter-${i}.out
  flux run --setattr=user.study-id=$app-32-iter-$i -N 32 -n 256 -g 1 /bin/bash ./launch.sh flux-sample 32 256 32 |& tee ./$output/$app-32-iter-${i}.out
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
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux run --setattr=user.study-id=$app-1-iter-$i -N1 -n 8 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task stream  |& tee ./$output/$app-1-iter-${i}.out
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
