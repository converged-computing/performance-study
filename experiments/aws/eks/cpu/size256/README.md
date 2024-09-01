# Kubernetes CPU on AWS size 256

- Start time: 8:15pm Mountain (second time, start time 12:15pm)
- End time: 

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

## Experiment

### 1. Setup

Bring up the cluster. Have your GitHub packages (or other registry credential / token) ready.

```bash
time eksctl create cluster --config-file ./eks-config.yaml
2024-08-22 20:22:56 [✔]  EKS cluster "performance-study-256" in "us-east-2" region is ready

# First time (failed cni)
real	16m18.140s
user	0m0.575s
sys	0m0.200s
```

Note that I always get this error, even with the aws-authenticator, and then get my credentials as follows:

```bash
aws eks update-kubeconfig --region us-east-2 --name performance-study-256
```

This is what we did to fix the cluster - AWS couldn't really give us help so this was a combination of issues, etc. 

```bash
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
kubectl patch daemonset aws-node -n kube-system -p '{"spec": {"template": {"spec": {"initContainers": [{"env":[{"name":"DISABLE_TCP_EARLY_DEMUX","value":"true"}],"name":"aws-vpc-cni-init"}]}}}}'
```

Collect topology and instances:

```bash
aws ec2 describe-instance-topology --region us-east-2 --filters Name=instance-type,Values=hpc6a.48xlarge > ./metadata/topology-3-256.json
aws ec2 describe-instances --filters "Name=instance-type,Values=hpc6a.48xlarge" --region us-east-2 > ./metadata/instances-3-256.json
```

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

Note that the configs are currently set to 4 nodes, and 96 cpu each. Check efa:

```console
# fi_info  | grep efa
provider: efa
    fabric: efa
    domain: efa_0-rdm
provider: efa
    fabric: efa
    domain: efa_0-dgrm
```

Check efa:

```
 kubectl get daemonsets.apps -n kube-system aws-efa-k8s-device-plugin-daemonset 
NAME                                  DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
aws-efa-k8s-device-plugin-daemonset   256       256       256     256          256         <none>          8m31s
```

You should see DESIRED == CURRENT == READY == 256. If that isn't the case, the installer has an issue you need to look into.
Start monitoring:

```bash
kubectl logs -n monitoring event-exporter-6bf9c87d4d-v4rtr -f  |& tee ./events-256-$(date +%s).json
```

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

We want to run four separate jobs, across each node. Write this into a batch file.

```console
oras login ghcr.io --username vsoch
export app=single-node
output=./results/$app
nodes=255
mkdir -p $output

# As we get to larger numbers here, sets of nodes regularly fail
# You will see the submit interface freeze, and then flux jobs -a will show
# a series of jobs in red. Re-run the ranges as shown below
for node in $(seq 0 $nodes); do
  flux submit --requires="hosts:flux-sample-$node" -N 1 --setattr=user.study_id=$app-node-$node /bin/bash /entrypoint.sh
done 

for node in $(seq 110 117); do
  flux submit --requires="hosts:flux-sample-$node" -N 1 --setattr=user.study_id=$app-node-$node /bin/bash /entrypoint.sh
done 

for node in $(seq 118 130); do
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
kubectl delete -f crd/single-node.yaml 
```

#### OSU

```bash
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
    time flux submit -N 2 -n 2 \
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
export FI_EFA_FORK_SAFE=1
mkdir -p $output

./flux-run-combinations.sh 256 $app

# Only time for one, 13+ minutes
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
done

# When they are done:
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
# 20 minutes
kubectl delete -f ./crd/osu.yaml
```

#### Stream

```bash
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
export FI_EFA_FORK_SAFE=1
nodes=255

# All nodes
for i in $(seq 1 5); do
   flux run --setattr=user.study_id=$app-all-nodes-iter-$i -N256 -o cpu-affinity=per-task stream_c.exe
done

# Single nodes (likely we should remove -n, but we already ran the others with it)
for node in $(seq 0 $nodes); do
    flux submit --requires="hosts:flux-sample-$node" --setattr=user.study_id=$app-1-iter-$i-node-$node -N1 -n 96 -o cpu-affinity=per-task stream_c.exe
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
kubectl delete -f ./crd/stream.yaml
```

#### Mt-Gemm

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
export FI_EFA_FORK_SAFE=1
mkdir -p $output

# Hookup is slow - processes will be sleeping
for i in $(seq 2 5); do  
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
kubectl delete -f ./crd/mt-gemm.yaml
```

#### Mixbench

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
output=./results/$app
export FI_EFA_FORK_SAFE=1
mkdir -p $output

# This should be total (256) -1
nodes=255

# Try mixbench on all nods
for i in $(seq 2 5); do     
    flux run --env OMP_NUM_THREADS=96 --setattr=user.study_id=$app-test-all-nodes-$i -l -N256 mixbench-cpu 32
done

# One on each single node
for node in $(seq 0 $nodes); do
    flux submit --requires="hosts:flux-sample-$node" --env OMP_NUM_THREADS=96 --setattr=user.study_id=$app-iter-$i -l -N1 -n 1 mixbench-cpu 32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
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

# Long hookup (~2m20s)
for i in $(seq 2 4); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-256-iter-$i -o cpu-affinity=per-task -N256 -n 24576 /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-efa-cpu-256-$app $output
```

```bash
kubectl delete -f ./crd/lammps-reax.yaml --wait
```

#### AMG2023

Create the minicluster and shell in.

```bash
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

This one requires sourcing spack:

```bash
. /etc/profile.d/z10_spack_environment.sh
flux proxy local:///mnt/flux/view/run/flux/local bash
export FI_EFA_FORK_SAFE=1
```

```console
oras login ghcr.io --username vsoch
export app=amg2023
output=./results/$app
export FI_EFA_FORK_SAFE=1

mkdir -p $output
for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=3 --cores-per-task 3 --exclusive --setattr=user.study_id=$app-256-iter-$i -N 256 -n 8192 -o cpu-affinity=per-task amg -n 256 256 128 -P 32 16 16 -problem 2
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
# 12 minutes
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
```console
oras login ghcr.io --username vsoch
export app=kripke
output=./results/$app
export FI_EFA_FORK_SAFE=1
mkdir -p $output

# Hookup is slow, kripke runs pretty quickly after that!
for i in $(seq 2 5); do
  echo "Running iteration $i"
  time flux run --cores-per-task 1 --exclusive --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-256-iter-$i -N 256 -n 24576 kripke --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 32,24,32
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
# 14 minutes
kubectl delete -f ./crd/kripke.yaml
```

#### Laghos

**DID NOT DO**

```bash
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
export FI_EFA_FORK_SAFE=1
mkdir -p $output

# Only ran this once
# started at 34 after, only give 15 mins (49)
for i in $(seq 1 5); do
  echo "Running iteration $i" 
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
# 20 minutes
kubectl delete -f ./crd/laghos.yaml --wait
```

#### MiniFE

```bash
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
export FI_EFA_FORK_SAFE=1
mkdir -p $output

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
kubectl delete -f ./crd/minife.yaml
```

#### Quicksilver

```bash
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
export FI_EFA_FORK_SAFE=1

# NOTE only ran 2 iterations
mkdir -p $output
for i in $(seq 1 2); do     
    echo "Running iteration $i"
    time flux run --cores-per-task 3 --exclusive --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192  qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 256 -Z 128 -x 256 -y 256 -z 128 -I 32 -J 16 -K 16 -n 2684354560
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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:eks-cpu-256-$app $output
```
```bash
kubectl delete -f ./crd/quicksilver.yaml
```

### Clean Up

When you are done:

```bash
time eksctl delete cluster --config-file ./eks-config.yaml --wait
```
```console
2024-08-31 22:26:20 [✔]  all cluster resources were deleted

real	7m59.805s
user	0m0.151s
sys	0m0.065s
```

**IMPORTANT** AWS sometimes has a bug that it won't delete, ever, unless you force delete all pods. It will say:

```console
2024-05-25 14:52:56 [!]  1 pods are unevictable from node ip-192-168-19-163.us-east-2.compute.internal
```
And you need to do:

```bash
kubectl delete pods --all-namespaces --all
```

### Results

Note that I downloaded results as I went, but this is a post-run option.

```console
for tag in $(oras repo tags ghcr.io/converged-computing/metrics-operator-experiments/performance)
  do
    if [[ $tag == *"eks-cpu-256"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
