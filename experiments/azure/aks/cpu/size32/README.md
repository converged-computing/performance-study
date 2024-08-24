# Kubernetes CPU on Azure size 32

- Create time: 1pm Mountain
- Deletion time: 4:40pm Mountain

Notes:

 - Terminal can be flaky - easily was cut off with flux run. I instead did flux run for the first, and flux submit for the rest when it was known working.
 - I accidentally added the "efa" label to these oras artifacts, and only pushed one (the single node) before I noticed. I pulled this artifact and renamed and fixed the rest. TLDR there is one aks-efa-cpu tag that is redundant with the same infinband tag.

## Experiment

- Name: performance-study-2
- Resource Group: flux-usernetes
- Region: (US) South Central US
- Availability Zones: 1
- AKS pricing tier: Standard
- Kubernetes Version: 1.29.7
- No automatic update or upgrade
- Authentication: Local accounts with Kubernetes RBAC
- userpool: HB120-96rs_v3 x 32
- agentpool: I decided for default instance type, autoscale 1-3
- Networking: defaults
- Integrations: disabled Azure policy
- Monitoring, disable:
  - container insights
  - managed prometheus
  - alterts

Note there is no option to add a placement group - I assume with the instance type we get that already.
Hello my name is Vanessa and I've reached a point in my life where putting my favorite toothpastes on subscribe and save has just made me unreasonably excited.

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
```console
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
7: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
7: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
7: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
7: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
7: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
7: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
5: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP mode DEFAULT group default qlen 256
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

Peeking at devices from an amg2023 pod:

<details>

<summary>View of Infiniband</summary>

```console
# lspci 
0101:00:00.0 Infiniband controller: Mellanox Technologies MT28908 Family [ConnectX-6 Virtual Function]
56d0:00:02.0 Ethernet controller: Mellanox Technologies MT27710 Family [ConnectX-4 Lx Virtual Function] (rev 80)
b857:00:00.0 Non-Volatile memory controller: Microsoft Corporation Device b111
dda9:00:00.0 Non-Volatile memory controller: Microsoft Corporation Device b111
root@flux-sample-0:/opt/spack-environment# ibv_devices 
    device          	   node GUID
    ------          	----------------
    mlx5_0          	00155dfffe33ff18
    mlx5_1          	000d3afffe72a6b3
root@flux-sample-0:/opt/spack-environment# ibv_        
ibv_asyncwatch     ibv_devinfo        ibv_srq_pingpong   ibv_ud_pingpong    
ibv_devices        ibv_rc_pingpong    ibv_uc_pingpong    ibv_xsrq_pingpong  
root@flux-sample-0:/opt/spack-environment# ibv_devinfo mlx5_0
hca_id:	mlx5_0
	transport:			InfiniBand (0)
	fw_ver:				20.31.1014
	node_guid:			0015:5dff:fe33:ff18
	sys_image_guid:			1070:fd03:006b:341c
	vendor_id:			0x02c9
	vendor_part_id:			4124
	hw_ver:				0x0
	board_id:			MT_0000000223
	phys_port_cnt:			1
		port:	1
			state:			PORT_ACTIVE (4)
			max_mtu:		4096 (5)
			active_mtu:		4096 (5)
			sm_lid:			228
			port_lid:		383
			port_lmc:		0x00
			link_layer:		InfiniBand

hca_id:	mlx5_1
	transport:			InfiniBand (0)
	fw_ver:				14.30.1284
	node_guid:			000d:3aff:fe72:a6b3
	sys_image_guid:			0000:0000:0000:0000
	vendor_id:			0x02c9
	vendor_part_id:			4118
	hw_ver:				0x80
	board_id:			MSF0010110035
	phys_port_cnt:			1
		port:	1
			state:			PORT_ACTIVE (4)
			max_mtu:		4096 (5)
			active_mtu:		1024 (3)
			sm_lid:			0
			port_lid:		0
			port_lmc:		0x00
			link_layer:		Ethernet
```

</details>

Save node metadata

```
kubectl get nodes -o json > nodes-32.json
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
# export app=single-node-quicksilver
output=./results/$app
nodes=31
mkdir -p $output

for node in $(seq 0 $nodes); do
  flux submit --requires="hosts:flux-sample-$node" -N 1 --setattr=user.study_id=$app-node-$node /bin/bash /entrypoint.sh
done 

# Note I accidentally had an extra single-node prefix on these output file names.
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
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
    time submit run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    time flux submit -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw
    iter=$((iter+1))
done
done
```

Run as follows.

```console
oras login ghcr.io --username vsoch
export app=osu
output=./results/$app
mkdir -p $output

./flux-run-combinations.sh 32 $app

for i in $(seq 2 5); do     
  echo "Running iteration $i"
  flux submit --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
done

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    if [[ "$jobid" == "4439771447296" ]]; then
       continue
    fi
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
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

mkdir -p $output
for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-1-iter-$i -N1 -n 96 -o cpu-affinity=per-task stream_c.exe
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
```
```bash
kubectl delete -f ./crd/stream.yaml
```

#### Mt-Gemm

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-mt-gemm-larger-$(date +%s).json
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

time flux run --setattr=user.study_id=$app-32-iter-1 -N32 -n 3072 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi

mkdir -p $output
for i in $(seq 2 5); do     
  echo "Running iteration $i"
  time flux submit --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
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
mkdir -p $output

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-iter-$i -l -N2 mixbench-cpu 32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
```

#### LAMMPS

Note that I noticed here lammps was 5 seconds faster without the shared memory volume. I removed it from here on.

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

time flux run --setattr=user.study_id=$app-32-iter-1 -o cpu-affinity=per-task -N32 -n 3072 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000

for i in $(seq 2 5); do
  echo "Running iteration $i"
  flux submit --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -N32 -n 3072 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 20000
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
```

```bash
kubectl delete -f ./crd/lammps.yaml --wait
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

time flux run --env OMP_NUM_THREADS=3 --cores-per-task 3 --exclusive --setattr=user.study_id=$app-32-iter-1 -N 32 -n 1024 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 8 8 -problem 2

mkdir -p $output
for i in $(seq 2 5); do
  echo "Running iteration $i"
  flux submit --env OMP_NUM_THREADS=3 --cores-per-task 3 --exclusive --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1024 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 8 8 -problem 2
done

# When they are done:
apt-get update && apt-get install -y jq

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
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

time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-1 -N 32 -n 3072 kripke --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 16,12,16

for i in $(seq 2 5); do
  echo "Running iteration $i"
  flux submit --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 3072 kripke --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 16,12,16
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
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

time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-1 -N32 -n 3072 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom

for i in $(seq 2 5); do
  echo "Running iteration $i" 
  time flux submit -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
```
```bash
kubectl delete -f ./crd/laghos.yaml --wait
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

time flux run --setattr=user.study_id=$app-32-iter-1 -N32 -n 3072 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

mkdir -p $output
for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
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

time flux run --cores-per-task 3 --exclusive --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-1 -N32 -n 1024  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320

for i in $(seq 2 5); do     
    echo "Running iteration $i"
    time flux run --cores-per-task 3 --exclusive --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N32 -n 1024  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-infiniband-cpu-32-$app $output
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
    if [[ $tag == *"aks-infiniband-cpu-32"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
