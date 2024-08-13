# Single Run Experiment on AWS

**THESE RUNS HAVE NOT BEEN UPDATED WITH CONFIGS**

- Cluster creation start: 10:33 am
- Cluster deleted at: 3:05pm

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

###  High level thoughts:

- If we can compare container sizes across experiments (clouds) we can compare pull times (e.g., the amg2023 image is the same between)
- kripke still needs a rebuild (for both CPU variants)
- We need an equivalent wrapper for mixbench-cpu that allows us to control the problem size. It also seems to be running one instance per node (akin to kripke).
- mt-gemm for CPU works! But we need a wrapper / customization to control the iterations or problem size - it runs too quickly even on the smallest size.
- Stream runs really quickly (under 5 seconds) - not sure if we can increase run time
- resnet only works on GPU - so we either drop or find a different variant.
- Quicksilver doesn't run - it runs (starts) but hangs. I can see 100% utilization on the other nodes. The problems provided are too large I think for 4 nodes, so either we try on larger sizes (and skip 4) or find/make a smaller problem. cpu affinity does not help.

## Experiment

### 1. Setup

Bring up the cluster (with 4 nodes). Have your GitHub packages (or other registry credential / token) ready. This does not work.


Let's prototype the CPU runs on hpc6a. Create the cluster:

```bash
time eksctl create cluster --config-file ./eks-config.yaml
```

Total time: 16 minutes 16 seconds.
Get topology for later:

```bash
aws ec2 describe-instance-topology --region us-east-1 --filters Name=instance-type,Values=hpc7g.4xlarge > topology-33.json
aws ec2 describe-instances --filters "Name=instance-type,Values=hpc7g.4xlarge" --region us-east-1 > instances-33.json
```

Install the Flux Operator:

```bash
kubectl apply -f https://raw.githubusercontent.com/flux-framework/flux-operator/main/examples/dist/flux-operator.yaml
```

Now we are ready for different MiniCluster setups. For each of the below, to shell in to the lead broker (index 0) you do:

```bash
kubectl exec -it flux-sample-0-xxx bash
```

Note that the configs are currently set to 4 nodes, and 94 cpu each. Check efa:

```
# fi_info  | grep efa
provider: efa
    fabric: efa
    domain: efa_0-rdm
provider: efa
    fabric: efa
    domain: efa_0-dgrm
```

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

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-$app $output
```

#### AMG2023

Create the minicluster and shell in.

```bash
kubectl apply -f ./crd/amg2023.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

Pull time: 47 seconds.

This one requires sourcing spack

```bash
. /etc/profile.d/z10_spack_environment.sh
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Here is an example loop through sizes and iterations. Note that this is done expecting that parameters
might change for different sizes.

Summary:

- cpu affinity helps
- from 4 to 2 it gets faster... 

```console
oras login ghcr.io --username vsoch
app=amg2023
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"

  # 39.22 seconds
  time flux run -N 4 -n 384 amg -P 12 8 4 -n 64 64 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 32.33 seconds
  time flux run -N 4 -n 384 -o cpu-affinity=per-task amg -P 12 8 4 -n 64 64 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 59.32 seconds
  time flux run -N 4 -n 384 amg -P 12 8 4 -n 64 128 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 47.3 seconds
  time flux run -N 4 -n 384 -o cpu-affinity=per-task amg -P 12 8 4 -n 64 128 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 1m 43 seconds
  time flux run -N 4 -n 384 amg -P 12 8 4 -n 128 128 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 1m 17 seconds
  time flux run -N 4 -n 384 -o cpu-affinity=per-task amg -P 12 8 4 -n 128 128 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 31.71 seconds
  time flux run -N 2 -n 192 amg -P 6 8 4 -n 64 64 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 28.277 seconds
  time flux run -N 2 -n 192 -o cpu-affinity=per-task amg -P 6 8 4 -n 64 64 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 47 seconds
  time flux run -N 2 -n 192 amg -P 6 8 4 -n 64 128 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 42.98 seconds
  time flux run -N 2 -n 192 -o cpu-affinity=per-task amg -P 6 8 4 -n 64 128 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 1 minute 34 seconds
  time flux run -N 2 -n 192 amg -P 6 8 4 -n 128 128 128 |& tee ./$output/$app-$size-iter-${i}.out

  # 1 minute 13 seconds
  time flux run -N 2 -n 192 -o cpu-affinity=per-task amg -P 6 8 4 -n 128 128 128 |& tee ./$output/$app-$size-iter-${i}.out

done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
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
About 30 seconds extra pull time.

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=kripke
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"

  # This still runs on each node, needs to be recompiled
  time flux run -N 4 -n 384 -o cpu-affinity=per-task kripke |& tee ./$output/$app-$size-iter-${i}.out

  # This still runs on each node, needs to be recompiled
  time flux run -N 2 -n 192 -o cpu-affinity=per-task kripke |& tee ./$output/$app-$size-iter-${i}.out

done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

```bash
kubectl delete -f ./crd/kripke.yaml
```

#### Laghos

```bash
kubectl apply -f ./crd/laghos.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- Extra pull time: ~10 seconds
- Termination time:


```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=laghos
output=./results/$app

mkdir -p $output
for i in $(seq 1 1); do     
  echo "Running iteration $i"

  # "You are trying to bisect a graph into too many parts! Cannot bisect a graph with 0 vertices!**
  # 18 seconds
  time flux run -N 4 -n 384 /opt/laghos/laghos -p 1 -m ./data/cube01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out

  # This one seems to work well (no weird errors)
  # 18.75 seconds (too fast)
  time flux run -N 4 -n 384 /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out

  # Trying with affinity
  # 17.7 seconds (faster)
  time flux run -N 4 -n 384 -o cpu-affinity=per-task /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20 |& tee ./$output/$app-$size-iter-${i}.out

  # Let's increase steps
  # 52.75 seconds
  time flux run -N 4 -n 384 -o cpu-affinity=per-task /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 100 |& tee ./$output/$app-$size-iter-${i}.out

  # 2 minutes 21 seconds
  time flux run -N 4 -n 384 -o cpu-affinity=per-task /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 300 |& tee ./$output/$app-$size-iter-${i}.out

  # 2 minutes 12 seconds
  time flux run -N 2 -n 192 -o cpu-affinity=per-task /opt/laghos/laghos -p 1 -m ./data/box01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 300 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

This can be controlled fairly well by adding more steps. I'm still surprised size 2 is a little faster...

```bash
kubectl delete -f ./crd/laghos.yaml --wait
```

Deletion time: ~30 seconds minute


#### LAMMPS

```bash
kubectl apply -f ./crd/lammps.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- Additional pull time: 10 seconds

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=lammps
output=./results/$app

# 1 minute 1 second on 2 nodes
mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # 2 minutes 2 seconds
  time flux run -N 4 -n 384 -o cpu-affinity=per-task lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000 |& tee ./$output/$app-$size-iter-${i}.out

  # 2 minutes 5 seconds (without cpu affinity)s
  time flux run -N 4 -n 384 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000 |& tee ./$output/$app-$size-iter-${i}.out

  # 1 minute 37 seconds
  time flux run -N 2 -n 192 -o cpu-affinity=per-task lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000 |& tee ./$output/$app-$size-iter-${i}.out

  # 1 minute 40 seconds
  time flux run -N 2 -n 192 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

It's strange that cpu affinity helped with the larger size (a little bit) but not the size 2. It must make a trivial difference, but maybe would be more useful at larger sizes.

```bash
kubectl delete -f ./crd/lammps.yaml --wait
```

About 30 seconds to terminate.

#### MiniFE

```bash
kubectl apply -f ./crd/minife.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- 5 seconds extra pull time.

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=minife
output=./results/$app

# 5.7 seconds
mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # 33.25 seconds
  time flux run -N4 -n 384 -o cpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out

  # Wow, doesn't seem to really run without affinity! (went for a few minutes and I didn't feel like waiting)
  time flux run -N4 -n 384 miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out

  # 1 minute 1 second
  time flux run -N2 -n 192 -o cpu-affinity=per-task miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0 |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

```bash
kubectl delete -f ./crd/minife.yaml
```

- Terminating about ~45 seconds

#### Mixbench

```bash
kubectl apply -f ./crd/mixbench.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- ~7 seconds extra pull time.

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=mixbench
output=./results/$app

# ~26 seconds
mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # This went for 10 minutes - and seems to be running on one core. We need to figure out how to shorten this.
  time flux run -N4 -n 384 mixbench-cpu |& tee ./$output/$app-$size-iter-${i}.out
  
  # This is running on one cpu / node without flux - we need this across nodes
  # Actually this might be the single node app, in which case this is OK. Let's time that.
  # 1 minute 7 seconds
  time mixbench-cpu

  # This at least runs one copy per node - but we would have a hard time separating the (interleaved) rows of data
  # 1 minute 18 seconds
  time flux run -N4 mixbench-cpu |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```
```bash
kubectl delete -f ./crd/mixbench.yaml
```

#### Mt Gem


```bash
kubectl apply -f ./crd/mt-gem.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- ~13 seconds extra pull time

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=mt-gem
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  
  # 9 seconds
  time flux run -N4 -n 384 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi |& tee ./$output/$app-$size-iter-${i}.out
  
  # 9.66 seconds
  time flux run -N4 -n 384 /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi |& tee ./$output/$app-$size-iter-${i}.out

  # 8.34 seconds
  time flux run -N2 -n 192 -o cpu-affinity=per-task /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi |& tee ./$output/$app-$size-iter-${i}.out
  
  # 8.66 seconds
  time flux run -N2 -n 192 /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

```bash
kubectl delete -f ./crd/mt-gem.yaml
```

#### Nek5000

```bash
kubectl apply -f ./crd/nek5000.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- ~14 seconds extra pull time

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Note: this takes a while to run, we likely need to decrease the size (somewhere) because it goes over 1k steps.
It gives summary output stats every 1500 steps.

```console
oras login ghcr.io --username vsoch
app=nek5000
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"
  
  # This first run is going to fail - we need to JIT compile then copy
  time flux run -N4 -n 384 nekrs --setup turbPipe.par

  # We will need to do this likely for each problem size
  # time for flux run (includes only second JIT) is 
  flux archive create --name cache-4 -C /opt/nekrs/examples/turbPipe .cache/*
  flux archive list --name cache-4
  flux exec -x 0 flux archive extract --name cache-4 -C /opt/nekrs/examples/turbPipe
  flux exec -x 0 ls /opt/nekrs/examples/turbPipe/.cache
  time flux run -N4 -n 384 nekrs --setup turbPipe.par |& tee ./$output/$app-$size-iter-${i}.out
  flux archive remove --name cache-4
  flux exec -x 0 rm -rf /opt/nekrs/examples/turbPipe/.cache
done


oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

Note that this seems to still require the shared FS for checkpoints. It hangs indefinitely and doesn't finish.


```bash
kubectl delete -f ./crd/nek5000.yaml
```

#### OSU

```bash
kubectl apply -f ./crd/osu.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- Additional pull time: 8.67 seconds.

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
oras login ghcr.io --username vsoch
app=osu
output=./results/$app

mkdir -p $output
for i in $(seq 1 2); do     
  echo "Running iteration $i"

  # These requires 2 nodes, 2 procs
  # 2.8 seconds (affinity doesn't make a difference)
  time flux run -N2 -n2 /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw |& tee ./$output/$app-osu_bw-iter-${i}.out

  # 11.58 seconds
  time flux run -N2 -n2 /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency |& tee ./$output/$app-osu_latency-iter-${i}.out

  # 30.64 seconds
  time flux run -N4 -n384 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce |& tee ./$output/$app-osu_allreduce-4-iter-${i}.out

  # 27.86 seconds
  time flux run -N2 -n192 -o cpu-affinity=per-task /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce |& tee ./$output/$app-osu_allreduce-2-iter-${i}.out

done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

```bash
kubectl delete -f ./crd/osu.yaml
```

#### Quicksilver

```bash
kubectl apply -f ./crd/quicksilver.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- 4.889 seconds


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

  # This problem size does not run - hangs after parameters. I can see 100% CPU utilization on other nodes, waited 15 mins
  time flux run -o cpu-affinity=per-task -N4 -n 384 qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

I can't get any of these to run - they start and then nothing, with our without affinity. For later ones (not listed above) I also see:

```
file=initMC.cc: line=273 ERROR
```
```bash
kubectl delete -f ./crd/quicksilver.yaml
```

#### Resnet

```bash
kubectl apply -f ./crd/resnet.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- This is an entirely new container, so 2m 42 seconds is the entire pull.

Gah, this torch model requires GPU does not work.


#### Stream

```bash
kubectl apply -f ./crd/stream.yaml
time kubectl wait --for=condition=ready pod -l job-name=flux-sample --timeout=600s
```

- pull time: 4 minutes 45 seconds

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

  # It's not clear if this is intended for multiple nodes?
  # 4.68 seconds
  # cpu affinity does nothing
  time flux run -N4 -n 384 ./stream_c.exe  |& tee ./$output/$app-$size-iter-${i}.out

  # 4.52 seconds
  time flux run -N2 -n 192 ./stream_c.exe  |& tee ./$output/$app-$size-iter-${i}.out
done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-aws-$app $output
```

```bash
kubectl delete -f ./crd/stream.yaml
```

### Clean Up

When you are done:

```bash
time eksctl delete cluster --config-file ./eks-config.yaml --wait
```

Deletion time is 8minutes 46 seconds

**IMPORTANT** AWS has a bug that it won't delete, ever, unless you force delete all pods. It will say:

```
2024-05-25 14:52:56 [!]  1 pods are unevictable from node ip-192-168-19-163.us-east-2.compute.internal
```
And you need to do:

```bash
kubectl delete pods --all-namespaces --all
```
