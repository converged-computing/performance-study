# Kubernetes on Azure (AKS)

Still needs to be done:

 - [ ] amg is working but needs final decision on params since is different from amg2023
 - [ ] kripke parameters not done

For all runs, we need to subtract the "hookup time" to get the actual runtime. We can use lammps since it records the actual runtime.
The hookup time (for 2 nodes) is 12-14 seconds, and this might scale badly given 256 nodes. Not much to do about it but account for it. We need to test when we time a larger cluster.

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

Note that we need to create this in the web interface.

- HB120-96rs_v3

And this uses infiniband. 

```console
# These are the available transports: cma, dc, dc_mlx5, dc_x, ib, mm, posix, rc, rc_mlx5, rc_v, rc_verbs, rc_x, self, shm, sm, sysv, tcp, ud, ud_mlx5, ud_v, ud_verbs, ud_x
```

## Experiment

### 1. Setup

Note that I needed to create this entirely in the UI, and you can't do automatic. We are required to have at least one node in hte agent pool. I created a cluster with 3 nodes to test (1 agent, 2 workers or user pool). Register the feature for AKSInfinibandSupport:

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
Let's try to install infiniband next, and we will use a container that is also built with ubuntu 22.04 drivers.

I was originally looking at [https://github.com/Mellanox/ib-kubernetes](https://github.com/Mellanox/ib-kubernetes). You can just do but then I switched to [https://github.com/Azure/aks-rdma-infiniband](https://github.com/Azure/aks-rdma-infiniband) and then put together a customized variant [here](https://github.com/converged-computing/aks-infiniband-install). Instructions are provided there and briefly here.

```bash
git clone https://github.com/converged-computing/aks-infiniband-install ./infiniband
kubectl apply -f infiniband/driver-installation.yaml
```

When they are done, here is how to check that it was successful.

```bash
for pod in $(kubectl get pods -o json | jq -r .items[].metadata.name)
do
   kubectl exec -it $pod -- nsenter -t 1 -m /usr/sbin/ip link | grep 'ib0:'
done
```

That should equal the number of nodes. Then.

```bash
kubectl delete -f infiniband/driver-installation.yml 
```

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



### 2. Applications

#### Single Node Benchmark

We are going to run this via flux batch, running the job across nodes (and then when they are complete, getting the logs from flux)

**IMPORTANT** change the size of the minicluster.yaml to the correct cluster size.

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
nodes=2
mkdir -p $output

for node in $(seq 1 $nodes); do
  flux submit -N 1 --setattr=user.study_id=$app-1-node-$node /bin/bash /entrypoint.sh
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```

#### AMG

We are using AMG because AMG2023 segfaults.
Create the minicluster and shell in.

```bash
kubectl apply -f ./crd/amg.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```
```bash
# Testing amg sizes on 2 nodes
# 34 seconds
time flux run --env OMP_NUM_THREADS=1 -N 2 -n 192 -o cpu-affinity=per-task amg -n 32 32 32 -P 4 6 8 -problem 2

# 1m 51 seconds
time flux run --env OMP_NUM_THREADS=1 -N 2 -n 192 -o cpu-affinity=per-task amg -n 64 64 64 -P 4 6 8 -problem 2

# 1m 55 seconds
time flux run --env OMP_NUM_THREADS=3 -N 2 -n 192 -o cpu-affinity=per-task amg -n 64 64 64 -P 4 6 8 -problem 2

# 3m 15 seconds
time flux run --env OMP_NUM_THREADS=1 -N 2 -n 192 -o cpu-affinity=per-task amg -n 128 64 64 -P 4 6 8 -problem 2

# 5m 55 seconds
time flux run --env OMP_NUM_THREADS=1 -N 2 -n 192 -o cpu-affinity=per-task amg -n 128 128 64 -P 4 6 8 -problem 2
```

**IMPORTANT** we have not finalized the below yet since the AMG is different. See above runs for reference.

```console
oras login ghcr.io --username vsoch
app=amg
output=./results/$app

mkdir -p $output
for i in $(seq 1 15); do
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1024 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 8 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N 64 -n 2048 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 16 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 4096 -o cpu-affinity=per-task amg -n 256 256 128 -P 16 16 16 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N 256 -n 8192 -o cpu-affinity=per-task amg -n 256 256 128 -P 32 16 16 -problem 2
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```

There must be something wrong running on GKE when the problem is instant - that doesn't make sense.

```bash
kubectl delete -f ./crd/amg2023.yaml
```

#### Kripke

```bash
kubectl apply -f ./crd/kripke.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing size - note I didn't know the parameters here, so this didn't run, but it looked like it would (it was just angry about my parameter specification)

```console
time flux run --env OMP_NUM_THREADS=1 -N 2 -n 160 kripke --layout DGZ --dset 8 --zones 16,16,16 --gset 8 --groups 8 --niter 100 --legendre 2 --quad 16 --procs 4,5,8

# This worked
kripke
```

```console
oras login ghcr.io --username vsoch
app=kripke
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 3072 kripke --layout DGZ --dset 16 --zones 144,448,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 12,16,16

  # TODO these are not done. The CUDA needs to be removed
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048 kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,8,4
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192 kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,8
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```
```bash
kubectl delete -f ./crd/kripke.yaml
```


#### Laghos


```bash
kubectl apply -f ./crd/laghos.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing on 2 nodes:

```bash
# 2m 39 seconds
time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N2 -n 192 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 10 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
```

```console
oras login ghcr.io --username vsoch
app=laghos
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do
  echo "Running iteration $i" 
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 1 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m ./data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```
```bash
kubectl delete -f ./crd/laghos.yaml --wait
```

Deletion time: ~30 seconds minute


#### LAMMPS

```bash
kubectl apply -f ./crd/lammps.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

# TODO THIS NEEDS TO BE THE UPDATED ONE
# time flux run --setattr=user.study_id=$app-32-iter-$i-20k -o cpu-affinity=per-task -N32 -n 3072 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 512 -v y 512 -v z 512 -var nsteps 20000

```bash
# Testing on 2 nodes
# 14 seconds wrapped, 0 seconds wall time?
time flux run -o cpu-affinity=per-task -N2 -n 192 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000

# Maybe this is supposed to be 10k steps?
# 6 seconds wall time, 14 seconds hookup
time flux run -o cpu-affinity=per-task -N2 -n 192 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 10000

# Try 100,000...
# 1m 9 seconds wall time, same hookup
time flux run -N 2 -n 192 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 1000
```

<details>

<summary>Original testing</summary>

```console
# time: 26 seconds, Total wall time: 4 seconds
time flux run -N 2 -n 192 --env UCX_TLS=rc  lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 64 -v y 64 -v z 64 -var nsteps 1000

# time: 22.5 seconds, Total wall time: 0 seconds (so cpu affinity helps)
time flux run -N 2 -n 192 --env UCX_TLS=rc -o cpu-affinity=per-task  lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 64 -v y 64 -v z 64 -var nsteps 1000

# rc_mlx5 does not work, with or without pmix
ml_ucx.c:424  Error: ucp_ep_create(proc=60) failed: Destination is unreachable)
select.c:634  UCX  ERROR   no auxiliary transport to <no debug data>: Unsupported operation

# ib, 14 seconds, Total wall time 1 seconds (the best so far)
time flux run -N 2 -n 192 --env UCX_TLS=ib -o cpu-affinity=per-task lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 64 -v y 64 -v z 64 -var nsteps 1000

# ib,shm did not work

# 17 seconds Total Wall time 4 seconds
time flux run -N 2 -n 192 --env UCX_TLS=ib,self  lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 64 -v y 64 -v z 64 -var nsteps 1000

# error with rc_verbs (same as above)

# 23.5 seconds, Total wall time 3 seconds
time flux run -N 2 -n 192 --env UCX_TLS=rc_v  lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 64 -v y 64 -v z 64 -var nsteps 1000
```

With openmpi

```
time flux run -N 2 -n 192 --env UCX_TLS=ib -o cpu-affinity=per-task -opmi=pmix lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 64 -v y 64 -v z 64 -var nsteps 1000
```

With mpich segfaults


```console
ulimit -a
real-time non-blocking time  (microseconds, -R) unlimited
core file size              (blocks, -c) unlimited
data seg size               (kbytes, -d) unlimited
scheduling priority                 (-e) 0
file size                   (blocks, -f) unlimited
pending signals                     (-i) 1837992
max locked memory           (kbytes, -l) unlimited
max memory size             (kbytes, -m) unlimited
open files                          (-n) 1048576
pipe size                (512 bytes, -p) 8
POSIX message queues         (bytes, -q) 819200
real-time priority                  (-r) 0
stack size                  (kbytes, -s) 8192
cpu time                   (seconds, -t) unlimited
max user processes                  (-u) unlimited
virtual memory              (kbytes, -v) unlimited
file locks                          (-x) unlimited
```

</details>

```console
oras login ghcr.io --username vsoch
app=lammps
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -N32 -n 3072 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-64-iter-$i -o cpu-affinity=per-task -N64 -n 6144 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 12288 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-256-iter-$i -o cpu-affinity=per-task -N228 -n 24576 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```

```bash
kubectl delete -f ./crd/lammps.yaml --wait
```

About 30 seconds to terminate.

#### MiniFE

```bash
kubectl apply -f ./crd/minife.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

Testing size:

```bash
# 14 seconds
time flux run -N2 -n 192 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

# 58.6 seconds
time flux run -N2 -n 192 -o cpu-affinity=per-task miniFE.x nx=640 ny=640 nz=640 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=minife
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```

```bash
kubectl delete -f ./crd/minife.yaml
```

#### Mixbench CPU

**Should work with intel, but not tested yet**

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
  time flux run --setattr=user.study_id=$app-$size-iter-$i -l -N2 -n 192 mixbench-cpu 64
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
```


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


#### Mt-Gemm

```bash
kubectl apply -f ./crd/mt-gem.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- ~13 seconds extra pull time

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing 2 nodes:

```bash
# 12 seconds, but performance output is wrong
time flux run -N2 -n 192 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
```

```console
oras login ghcr.io --username vsoch
app=mt-gemm
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi  
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```
```bash
kubectl delete -f ./crd/mt-gemm.yaml
```

#### OSU

```bash
kubectl apply -f ./crd/osu.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

<details>

<summary>Original testing</summary>

This works!

```bash
# hpc-x
flux run --env LD_LIBRARY_PATH=$LD_LIBRARY_PATH --env OMPI_MCA_btl_openib_warn_no_device_params_found=0 --env PATH=$PATH --env UCX_TLS=ib,sm,self --env UCX_NET_DEVICES=mlx5_0:1 -N2 -n2 /opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/tests/osu-micro-benchmarks/osu_latency

LD_LIBRARY_PATH=/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/lib:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hcoll/lib
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/hpcx-v2.19-gcc-mlnx_ofed-ubuntu22.04-cuda12-x86_64/hpcx-rebuild/bin

# openmpi
# need to build the benchmarks for this
flux run --env LD_LIBRARY_PATH=$LD_LIBRARY_PATH --env PATH=$PATH --env UCX_TLS=ib,self --env UCX_NET_DEVICES=mlx5_0:1 -N2 -n2 /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
```

</details>

Write this script to the filesystem `flux-run-combinations.sh`

```bash
#/bin/bash

nodes=$1
app=$2

# At most 28 combinations, 8 nodes 2 at a time
hosts=$(flux run -N $1 hostname | shuf -n 28 | tr '\n' ' ')
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

Testing 2 nodes:

```bash
app=osu
output=./results/$app
mkdir -p $output
./flux-run-combinations.sh 2 $app
time flux run -N2 -n 192 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
```

And then run as follows.

```console
oras login ghcr.io --username vsoch
app=osu
output=./results/$app

./flux-run-combinations.sh 32 $app

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```

```bash
kubectl delete -f ./crd/osu.yaml
```

#### Quicksilver

```bash
kubectl apply -f ./crd/quicksilver.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing on 2 nodes:

```bash
# parameters provided by Abhik
# This app is fussy like that. Wonker.
flux run --env OMP_NUM_THREADS=3 -N2 -n 64 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 10485760
```

```console
oras login ghcr.io --username vsoch
app=quicksilver
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
    echo "Running iteration $i"
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N32 -n 1024  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320 
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 128 -x 128 -y 128 -z 128 -I 16 -J 16 -K 8 -n 671088640
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 128 -Z 128 -x 256 -y 128 -z 128 -I 16 -J 16 -K 16 -n 1342117280
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 256 -Z 128 -x 256 -y 256 -z 128 -I 32 -J 16 -K 16 -n 2684354560
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```

```bash
kubectl delete -f ./crd/quicksilver.yaml
```

#### Stream


```bash
kubectl apply -f ./crd/stream.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing on 2 nodes:

```bash
time flux run -N1 -n 96 -o cpu-affinity=per-task stream_c.exe
```

```console
oras login ghcr.io --username vsoch
app=stream
output=./results/$app

mkdir -p $output
for i in $(seq 1 5); do     
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aks-cpu-$app $output
```
```bash
kubectl delete -f ./crd/stream.yaml
```

### Clean Up

When you are done, make sure to delete your cluster in the user interface!
