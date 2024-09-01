# AKS GPU Experiment (size 4)

- Created at: 
- Deleted: 

This will use:

- ND40rs_v2 (about $22/hour) in west US 2

For this, we need to start at 4 and scale up.

```bash
# Note I did this in the web interface before, so it's not necessary again.
az ppg create --name aks-placement-test --resource-group flux-usernetes --location southcentralus --type standard

# put id from output above here. Note that the nodepool you create here will have the group with it

az aks create \
    --resource-group aks-gpu-testing-west  \
    --name performance-study-gpu \
    --ppg /subscriptions/c87dfbe8-b453-4fc9-a779-7687a14b87eb/resourceGroups/flux-usernetes/providers/Microsoft.Compute/proximityPlacementGroups/performance-study-west \
    --network-plugin azure \
    --node-count 2 \
    --location westus2 \
    --enable-node-public-ip \
    --node-vm-size standard_nd40rs_v2 \
    --vm-set-type VirtualMachineScaleSets \
    --load-balancer-sku standard \
    --generate-ssh-keys \
    --aks-custom-headers "CustomizedUbuntu=aks-ubuntu-1804,ContainerRuntime=containerd" \
    --node-resource-group aks-group-testing-west_performance-study-gpu-cluster_nodes_westus2 

//    --aks-custom-headers CustomizedUbuntu=aks-ubuntu-1804,ContainerRuntime=containerd
//    --ssh-key-value ~/.ssh/id_eks.pub \

az aks get-credentials --resource-group aks-gpu-testing-west --name aks-gpu-testing-cluster
```

```console
# These are the available transports: cma, dc, dc_mlx5, dc_x, ib, mm, posix, rc, rc_mlx5, rc_v, rc_verbs, rc_x, self, shm, sm, sysv, tcp, ud, ud_mlx5, ud_v, ud_verbs, ud_x
```

## Testing

Create a resource group:

```bash
az group create --name aks-gpu-testing-west --location westus2
```
```
az feature register --namespace Microsoft.ContainerService --name UseCustomizedUbuntuPreview
```
Create the cluster:

```bash
az aks create \
    --resource-group aks-gpu-testing-west \
    --name aks-gpu-16 \
    --node-count 16 \
    --network-plugin azure \
    --enable-node-public-ip \
    --vm-set-type VirtualMachineScaleSets \
    --load-balancer-sku standard \
    --node-vm-size standard_nd40rs_v2 \
    --node-resource-group aks-group-testing-west_aks-gpu-testing-cluster_nodes_westus2 \
    --aks-custom-headers CustomizedUbuntu=aks-ubuntu-1804,ContainerRuntime=containerd

//    --ssh-key-value ~/.ssh/id_eks.pub \

az aks get-credentials --resource-group aks-gpu-testing-west --name aks-gpu-testing-cluster
```
That will generate the kube config to save to your local machine.

## Experiment

### 1. Setup

Register the feature for AKSInfinibandSupport:

```bash
az feature register --namespace Microsoft.ContainerService --name AKSInfinibandSupport
```

When you see it is "Registered"

```bash
az feature list -o table --query "[?contains(name, 'Microsoft.ContainerService/AKSInfinibandSupport')].{Name:name,State:properties.state}"
```
```console
Name                                             State
-----------------------------------------------  ----------
Microsoft.ContainerService/AKSInfinibandSupport  Registered
```

Run this final step:

```bash
az provider register --namespace Microsoft.ContainerService
```

Note that if you shell in now and install `ibverbs-utils` and do `ibv_devices` it will be empty.
If you are doing this in the cloud shell, you'll next want to copy the entirety of the `~/.kube/config` to your local machine to access the cluster.


#### Install the GPU Driver

Add a taint:

```bash
for node in $(kubectl get nodes -o json | jq -r  .items[].metadata.name)
do
  kubectl taint node $node sku=gpu:NoSchedule
done
```

Apply the daemonset, and check the logs.

```bash
kubectl apply -f nvidia-device-plugin.yaml
kubectl logs -n kube-system nvidia-device-plugin-daemonset-28f6q 
```

Check that the gpus are there (8)

```bash
kubectl get nodes -o json | jq .items[].status.allocatable
{
  "cpu": "39500m",
  "ephemeral-storage": "119703055367",
  "hugepages-1Gi": "0",
  "hugepages-2Mi": "0",
  "memory": "691098664Ki",
  "nvidia.com/gpu": "8",
  "pods": "110"
}
```

Once applied we should see the device on the nodes:

```bash
kubectl describe node <nodename>
```
```console
Roles:              agent
Labels:             accelerator=nvidia
```

When they are done, untaint:

```bash
for node in $(kubectl get nodes -o json | jq -r  .items[].metadata.name)
do
  kubectl taint node $node sku=gpu:NoSchedule-
done
```

#### Install the Inifiniband Driver

Let's try to install infiniband next, and we will use a container that is also built with ubuntu 22.04 drivers.
We are going to use the configs I prepared [here](https://github.com/converged-computing/aks-infiniband-install). Instructions are provided there and briefly here.

```bash
git clone https://github.com/converged-computing/aks-infiniband-install ./infiniband
kubectl apply -f infiniband/driver-installation-with-gpu.yaml
```

When they are done, here is how to check that it was successful.

```bash
for pod in $(kubectl get pods -o json | jq -r .items[].metadata.name)
do
   kubectl exec -it $pod -- nsenter -t 1 -m /usr/sbin/ip link | grep 'ib0:'
done
```

That should equal the number of nodes. 

If you want to test Infiniband, you can use pingpong.

```bash
# First node
kubectl node-shell aks-userpool-14173555-vmss000000
ibv_rc_pingpong

# Second node
kubectl node-shell aks-userpool-14173555-vmss000001 
ibv_rc_pingpong aks-userpool-14173555-vmss000000
```

Apply the daemonset to make it available to pods:

```bash
kubectl apply -k infiniband/daemonset/
```

Now install the Flux Operator:

```bash
kubectl apply -f ./flux-operator.yaml
```

Now we are ready for different MiniCluster setups. For each of the below, to shell in to the lead broker (index 0) you do:

```bash
kubectl exec -it flux-sample-0-xxx bash
```

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-gpu-8-$(date +%s).json
```

## Experiment

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

# Size 4
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-4-iter-$i -N 4 -n 32 -g 1 -o gpu-affinity=per-task -o cpu-affinity=per-task amg -n 256 256 128 -P 4 4 2 -problem 2 
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

# Note that these failed, and it's not clear why.
for i in $(seq 1 5); do
  echo "Running iteration $i"
    flux submit --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 --setattr=user.study_id=$app-1-iter-$i -N4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task /opt/magma/magma-2.8.0/build/testing/testing_dgemm
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

cd /code/lammps/examples/reaxff/HNS

# Size 4
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 32 -v z 32 -in in.reaxff.hns -nocite
  time flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 -o cpu-affinity=per-task --setattr=user.study_id=$app-4-iter-$i -N4 -n 32 -g 1 lmp -k on g 8 -sf kk -pk kokkos cuda/aware off newton on neigh half -in in.reaxff.hns -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done 

# When they are done:
cd -
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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
for i in $(seq 2 5); do     
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

# Run without cuda
# 4 Nodes
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  flux run --env CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
  --setattr=user.study_id=$app-4-iter-$i -N 4 -n 32 -g 1 -o cpu-affinity=per-task -o gpu-affinity=per-task \
  /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-gpu-4-$app $output
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
    if [[ $tag == *"aks-gpu-4"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```