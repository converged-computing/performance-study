# Kubernetes CPU on Azure size 128

- Create time: 6:40pm
- Deletion time: 

## Experiment

For this, we need to start at 99 and scale up.

```bash
# Note I did this in the web interface before, so it's not necessary again.
az ppg create --name aks-placement-test --resource-group flux-usernetes --location southcentralus --type standard

# put id from output above here. Note that the nodepool you create here will have the group with it

az aks create \
    --resource-group flux-usernetes \
    --name performance-study-128 \
    --ppg /subscriptions/c87dfbe8-b453-4fc9-a779-7687a14b87eb/resourceGroups/flux-usernetes/providers/Microsoft.Compute/proximityPlacementGroups/performance-study \
    --network-plugin azure \
    --node-count 99 \
    --node-vm-size standard_hb120-96rs_v3 \
    --location southcentralus \
    --enable-node-public-ip \
    --vm-set-type VirtualMachineScaleSets \
    --load-balancer-sku standard \
    --generate-ssh-keys

//    --aks-custom-headers CustomizedUbuntu=aks-ubuntu-1804,ContainerRuntime=containerd
//    --ssh-key-value ~/.ssh/id_eks.pub \

az aks get-credentials --resource-group aks-gpu-testing-west --name aks-gpu-testing-cluster
```

### 1. Setup

Note that I needed to create this entirely in the UI, and you can't do it automatically. We are required to have at least one node in the agent pool. For testing I used one static, and for production I allowed autoscaling 1-3, not knowing what might be needed. Once your deployment is ready and you can use the Connect -> cloud shell to connect, register the feature for AKSInfinibandSupport:

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
If you are doing this in the cloud shell, you'll next want to copy the entirety of the `~/.kube/config` to your local machine to access the cluster. Let's try to install infiniband next, and we will use a container that is also built with ubuntu 22.04 drivers.

I was originally looking at [https://github.com/Mellanox/ib-kubernetes](https://github.com/Mellanox/ib-kubernetes). You can just do but then I switched to [https://github.com/Azure/aks-rdma-infiniband](https://github.com/Azure/aks-rdma-infiniband) and then put together a customized variant [here](https://github.com/converged-computing/aks-infiniband-install). Instructions are provided there and briefly here.

```bash
git clone https://github.com/converged-computing/aks-infiniband-install ./infiniband
kubectl apply -f infiniband/driver-installation.yaml
```

When they are done, here is how to check that it was successful. Note that this takes about 5 minutes, but some start finishing around 4.

```bash
for pod in $(kubectl get pods -o json | jq -r .items[].metadata.name)
do
   kubectl exec -it $pod -- nsenter -t 1 -m /usr/sbin/ip link | grep 'ib0:'
done
```

That should equal the number of nodes. Note that I'm not deleting it in case a node is re-created.
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
Next, choose a cluster size in one of the experiment folders.
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

Backup to install oras:

```bash
export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/
```
```
kubectl get nodes -o json > nodes-128.json
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

We want to run four separate jobs, across each node. Write this into a batch file.

```console
oras login ghcr.io --username vsoch
export app=single-node
output=./results/$app
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
    echo "Parsing jobid ${jobid} and study id $app${study_id}"
    flux job attach $jobid &> $output/$app${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/$app${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/$app${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/$app${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/$app${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```
```bash
kubectl delete -f crd/single-node.yaml 
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

flux-is-gr8-HPCIC-2024!

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
    flux submit -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    flux submit -N 2 -n 2 \
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
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/osu.yaml
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
nodes=127
mkdir -p $output

for i in $(seq 1 5); do
  echo "Running iteration $i"
  for node in $(seq 0 $nodes); do
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/stream.yaml
```

#### Mt-Gemm

**DID NOT RUN**

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

# The command below failed, testing is below this block.
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```

```console
# Size 128 with flags in crd failed
[1724899770.139804] [flux-sample-30:194  :0]         ib_mlx5.h:911  UCX  ERROR mlx5_0: mlx5dv_devx_umem_reg(size=524288 access=0x1) failed: Operation canceled
[1724899770.139765] [flux-sample-30:157  :0]         ib_mlx5.h:911  UCX  ERROR mlx5_0: mlx5dv_devx_umem_reg(size=131072 access=0x0) failed: Operation canceled
...
[1724899775.260309] [flux-sample-30:71   :0]      ib_mlx5_dv.c:420  UCX  ERROR mlx5dv_devx_obj_create(DCT) failed on mlx5_0, syndrome 0x0: Connection timed out
[1724899775.261483] [flux-sample-30:245  :0]      ib_mlx5_dv.c:420  UCX  ERROR mlx5dv_devx_obj_create(DCT) failed on mlx5_0, syndrome 0x0: Connection timed out

[flux-sample-30:00201] pml_ucx.c:309  Error: Failed to create UCP worker
[flux-sample-30:00066] pml_ucx.c:309  Error: Failed to create UCP worker
```

Different one (bad?) on bottom:

```
19: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
19: ib0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 4092 qdisc mq state DOWN mode DEFAULT group default qlen 256
```

Then tested:
```console
time flux run --setattr=user.study_id=$app-128-iter-1 --env UCX_TLS="ud_x,rc_mlx5,cma" --env UCX_UNIFIED_MODE="y" --env UCX_NET_DEVICES="mlx5_0:1" -N128 -n 12288 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
```

```bash
kubectl delete -f ./crd/mt-gemm.yaml
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

# This should be total -1
nodes=127

mkdir -p $output
# each single run take about 4.6m
for i in $(seq 1 5); do     
    echo "Running iteration $i"
    for node in $(seq 0 $nodes); do
    flux submit --requires="hosts:flux-sample-$node" --env OMP_NUM_THREADS=96 --setattr=user.study_id=$app-iter-$i -l -N1 -n 1 mixbench-cpu 32
  done
done

# Note I only got a subset of these.
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```
```bash
# 9 minutes
kubectl delete -f ./crd/mixbench.yaml
```

#### LAMMPS-REAX

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-mixbench-$(date +%s).json
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

for i in $(seq 2 3); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 12288 /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```

```bash
kubectl delete -f ./crd/lammps-reax.yaml --wait
```


#### AMG2023

Create the minicluster and shell in.

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-amg2023-$(date +%s).json
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

This container is a bit borked (envar is missing for path) so we need to set it, oops.

```bash
kubectl exec -it flux-sample-0-xxx /bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/games:/usr/local/go/bin
source /root/.bashrc
. /etc/profile.d/z10_spack_environment.sh
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```console
oras login ghcr.io --username vsoch
export app=amg2023
output=./results/$app

time flux run --env OMP_NUM_THREADS=3 --cores-per-task 3 --exclusive --setattr=user.study_id=$app-64-iter-i -N 64 -n 2048 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 16 8 -problem 2

mkdir -p $output
for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=3 --cores-per-task 3 --exclusive --setattr=user.study_id=$app-128-iter-$i -N 128 -n 4096 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 16 16 -problem 2
done

# When they are done:
apt-get update
apt-get install -y jq

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
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

for i in $(seq 2 4); do
  echo "Running iteration $i"
  time flux run --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 12288 kripke --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 32,12,32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/kripke.yaml
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
for i in $(seq 2 4); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
done

# Minife has extra results files
mv miniFE* $output/

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/minife.yaml
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

# NOTE only ran 2 iterations
for i in $(seq 2 3); do     
    echo "Running iteration $i"
    time flux run --cores-per-task 3 --exclusive --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 128 -Z 128 -x 256 -y 128 -z 128 -I 16 -J 16 -K 16 -n 1342117280
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-128-$app $output
```
```bash
kubectl delete -f ./crd/quicksilver.yaml
```
### Clean Up

When you are done, delete the cluster from the web interface.

### Results

```console
for tag in $(oras repo tags ghcr.io/converged-computing/metrics-operator-experiments/performance)
  do
    if [[ $tag == *"aks-infiniband-cpu-128"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
