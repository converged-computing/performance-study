# "Bare Metal" on Compute Engine Size 32

- Note: cannot get compact placement group

## Experiment

Shell in:

```bash
gcloud compute ssh flux-001 --project=converged-computing --zone=us-central1-a --tunnel-through-iap
```

### 0. Pulling Containers

The containers are already pulled and located in `/opt/containers`. Oras is also installed.

```bash
cd /opt/containers
```

### 1. Applications

Write this script to file that we can run incrementally to save output (that does not exist yet)

```bash
#!/bin/bash
output=$1

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    # Get the job study id
    study_id=$(flux job info $jobid jobspec | jq -r ".attributes.user.study_id")    
    if [[ -f "$output/${study_id}-${jobid}.out" ]] || [[ "$study_id" == "null" ]]; then
        continue
    fi
    echo "Parsing jobid ${jobid} and study id ${study_id}"
    flux job attach $jobid &> $output/${study_id}-${jobid}.out 
    echo "START OF JOBSPEC" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid jobspec >> $output/${study_id}-${jobid}.out 
    echo "START OF EVENTLOG" >> $output/${study_id}-${jobid}.out 
    flux job info $jobid guest.exec.eventlog >> $output/${study_id}-${jobid}.out
done
```
```bash
# Results and save script to home!
mkdir -p ./results
chmod +x ./save.sh
```

For each experiment, we need to be instance owner. This also cleans up `flux jobs -a` so you get a clean slate.

```bash
flux alloc -N <total-nodes>
flux alloc -N 32
```

You'll need to login to oras just once:

```bash
oras login ghcr.io --username vsoch
```

#### Single Node Benchmark

Need to pull an updated container

```bash
singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu-zen4-tmpfile
```

Here is a modified entrypoint:

```console
export app=single-node
output=./results/$app
mkdir -p $output

for node in $(seq 1 9); do
  flux submit -N1 --requires="hosts:flux-00${node}" --setattr=user.study_id=$app-node-00${node} singularity exec /home/sochat1_llnl_gov/metric-single-node_cpu-zen4-tmpfile.sif /bin/bash /entrypoint.sh
done 
for node in $(seq 10 32); do
  flux submit -N1 --requires="hosts:flux-0${node}" --setattr=user.study_id=$app-node-00${node} singularity exec /home/sochat1_llnl_gov/metric-single-node_cpu-zen4-tmpfile.sif /bin/bash /entrypoint.sh
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### AMG2023

This one requires sourcing spack, so we need to write a little wrapper for it.

```bash
#!/bin/bash
# run_amg.sh
. /etc/profile.d/z10_spack_environment.sh
$@
```
```bash
# No need to share the file - the filesystem is shared
chmod +x run_amg.sh
```

```console
export app=amg2023
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=2 --env OMPI_MCA_btl_vader_single_copy_mechanism=none --setattr=user.study_id=$app-32-iter-$i -N 32 -n 896 -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg2023_rocky8-cpu-int64-zen3.sif /bin/bash /home/sochat1_llnl_gov/run_amg.sh amg -n 256 256 128 -P 7 8 16 -problem 2
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### Kripke

```console
export app=kripke
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  flux submit --env OMP_NUM_THREADS=1 --env OMPI_MCA_btl_vader_single_copy_mechanism=none --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1792 singularity exec /opt/containers/metric-kripke-cpu_rocky-8.sif kripke --layout DGZ --dset 16 --zones 448,168,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 8,14,16
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### Laghos

```console
export app=laghos-7-threads
export output=results/$app
mkdir -p $output

# Killed at 17 minutes - would go until 50 minutes
for i in $(seq 1 1); do
  echo "Running iteration $i" 
  time flux run --env OMP_NUM_THREADS=7 --cores-per-task=7 --exclusive -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N 32 -n 256 --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-laghos_rocky-8.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
done
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### LAMMPS-REAX

```console
export app=lammps-reax
export output=results/$app
mkdir -p $output

# Lammps data needs to be copied from first container
singularity  shell /opt/containers/metric-lammps-cpu_zen4-reax.sif
cp -R /code /home/sochat1_llnl_gov/lammps-data
exit
cd /home/sochat1_llnl_gov/lammps-data

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task -N32 -n 1792 singularity exec /opt/containers/metric-lammps-cpu_rocky-8.sif /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### MiniFE

```bash
# 8.4 seconds
time flux run -N2 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-minife_rocky-8.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

# the larger problem size segfaults here, it gives a message about running out of memory, but could be only having two nodes.
```

```console
export app=minife
export output=results/$app
mkdir -p $output

i=1
time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 1792 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-minife_rocky-8.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 1792 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-minife_rocky-8.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
done

# Note that minife outputs more result files!!
mkdir -p $output/miniFe
mv miniFE* $output/miniFe
# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### Mixbench

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

```console
export app=mixbench
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-$size-iter-$i -l -N2 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-mixbench_cpu.sif mixbench-cpu 32
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### Mt-Gemm

```console
export app=mt-gemm
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 1792 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec  /opt/containers/mt-gemm_rocky-8.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi  
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### OSU

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
    time flux run -N 2 -n 2 \
      --env OMPI_MCA_btl_vader_single_copy_mechanism=none \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    time flux run -N 2 -n 2 \
      --env OMPI_MCA_btl_vader_single_copy_mechanism=none \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw
      iter=$((iter+1))
  done
done
```

And then run as follows.

```console
export app=osu
export output=results/$app
mkdir -p $output

./flux-run-combinations.sh 32 $app

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 1792 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### Quicksilver

```console
export app=quicksilver
export output=results/$app
mkdir -p $output
    
for i in $(seq 1 5); do
    echo "Running iteration $i"
    time flux run --cores-per-task=7 --exclusive --env OMP_NUM_THREADS=7 --setattr=user.study_id=$app-32-iter-$i -N32 -n 256 singularity exec /opt/containers/metric-quicksilver-cpu_rocky-8.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 64  -Z 64  -x 64  -y 64  -z 64  -I 8  -J 8  -K 4  -n 83886080
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

#### Stream

```console
export app=stream
export output=results/$app
mkdir -p $output

for i in $(seq 1 5); do
  echo "Running iteration $i"
  for node in $(seq 1 9); do
    flux submit --env OMPI_MCA_btl_vader_single_copy_mechanism=none --exclusive  --requires="hosts:flux-00${node}" --setattr=user.study_id=$app-1-iter-$i-node-$node -N1 -n 56 -o cpu-affinity=per-task singularity exec /opt/containers/metric-stream_rocky-8.sif stream_c.exe
  done
  for node in $(seq 10 32); do
    flux submit --env OMPI_MCA_btl_vader_single_copy_mechanism=none --exclusive --requires="hosts:flux-0${node}" --setattr=user.study_id=$app-1-iter-$i-node-$node -N1 -n 56 -o cpu-affinity=per-task singularity exec /opt/containers/metric-stream_rocky-8.sif stream_c.exe
  done
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-32-$app $output
```

### Clean up

When you are done, exit and:

```bash
export GOOGLE_PROJECT=myproject
make destroy
```

```console
for tag in $(oras repo tags ghcr.io/converged-computing/metrics-operator-experiments/performance)
  do
    if [[ $tag == *"compute-engine-cpu-32"* ]]; then
       echo $tag
       oras pull ghcr.io/converged-computing/metrics-operator-experiments/performance:$tag
    fi
  done
```
