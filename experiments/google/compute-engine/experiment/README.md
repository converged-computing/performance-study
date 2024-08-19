# "Bare Metal" on Compute Engine

- [ ] kripke missing params for most
- Google Cloud is the first one where larger miniFE problem size (640) causes an error - it runs out of memory, but only 2 nodes
- amg is the 2013 version, spack builds do not work

## Experiment

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
mkdir -p ./results
chmod +x ./save.sh
```

We need to be instance owner.

```bash
flux alloc -N <total-nodes>
flux alloc -N 2
```

```bash
# This output directory is used across experiments
sudo chown -R $USER /opt/containers/
flux exec -x 0 /bin/bash -c "sudo chown -R sochat1_llnl_gov /opt/containers"
export output=/opt/containers/results
mkdir -p $output
```

#### Single Node Benchmark

We are going to run this via flux, running the job across nodes (and then when they are complete, getting the logs from flux).
Here is a modified entrypoint:

```console
oras login ghcr.io --username vsoch
app=single-node
nodes=2

flux run -N1 singularity exec /opt/containers/metric-single-node_cpu-zen4.sif /bin/bash /entrypoint.sh

for node in $(seq 1 $nodes); do
  flux submit -N1 --setattr=user.study_id=$app-node-$node singularity exec /opt/containers/metric-single-node_cpu-zen4.sif  /bin/bash /entrypoint.sh
done 

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

Clean up test files (note this won't work here)

```bash
flux exec -r all /bin/bash -c "rm -rf /opt/containers/test_file*"
```

#### AMG

This container does not use spack.

Test size run:

```bash
# 5 seconds
time flux run --env OMP_NUM_THREADS=3 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -N 2 -n 8 -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg_rocky-8.sif amg -n 32 32 32 -P 2 2 2 -problem 2

# 2 minutes 43 seconds
time flux run --env OMP_NUM_THREADS=3 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -N 2 -n 8 -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg_rocky-8.sif amg -n 64 64 64 -P 2 2 2 -problem 2

# 2 minutes 43 seconds
time flux run --env OMP_NUM_THREADS=3 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -N 2 -n 8 -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg_rocky-8.sif amg -n 128 128 128 -P 2 2 2 -problem 2

# 2 minutes 44 seconds
time flux run --env OMP_NUM_THREADS=3 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -N 2 -n 8 -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg_rocky-8.sif amg -n 256 256 256 -P 2 2 2 -problem 2

# testing amg2023 (segfaults with flux)
time flux run --env OMP_NUM_THREADS=3 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -opmi=pmix -N 2 -n 8 -o cpu-affinity=per-task singularity exec /home/sochat1_llnl_gov/metric-amg2023_spack-slim-int64-c2d.sif /bin/bash /home/sochat1_llnl_gov/run_amg.sh amg -n 32 32 32 -P 2 2 2 -problem 2
```

```console
oras login ghcr.io --username vsoch
app=amg

# QUESTION: if this takes a long time, 15 iterations might take too long
for i in $(seq 1 15); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1024 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg_rocky-8.sif amg -n 256 256 128 -P 16 8 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N 64 -n 2048 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg_rocky-8.sif amg -n 256 256 128 -P 16 16 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 4096 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg_rocky-8.sif amg -n 256 256 128 -P 16 16 16 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N 256 -n 8192 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-amg_rocky-8.sif amg -n 256 256 128 -P 32 16 16 -problem 2
done


# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### Kripke

**IMPORTANT: not done yet, we skipped it, so I skipped testing, but added the container name**

```bash
time flux run --env OMP_NUM_THREADS=1 -N 1 -n 56 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-kripke-cpu_rocky-8.sif kripke
```

```console
oras login ghcr.io --username vsoch
app=kripke

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=1 --env OMPI_MCA_btl_vader_single_copy_mechanism=none --setattr=user.study_id=$app-32-iter-$i -N 32 -n 3072 singularity exec /home/ubuntu/containers/metric-kripke-cpu_azure-hpc.sif kripke --layout DGZ --dset 16 --zones 144,448,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 12,16,16

# NOT DONE YET
  time flux run --env OMP_NUM_THREADS=1  --env OMPI_MCA_btl_vader_single_copy_mechanism=none --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048 singularity exec /opt/containers/metric-kripke-cpu_rocky-8.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4
  time flux run --env OMP_NUM_THREADS=1 --env OMPI_MCA_btl_vader_single_copy_mechanism=none --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 singularity exec /opt/containers/metric-kripke-cpu_rocky-8.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,8,4
  time flux run --env OMP_NUM_THREADS=1 --env OMPI_MCA_btl_vader_single_copy_mechanism=none --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192 singularity exec /opt/containers/metric-kripke-cpu_rocky-8.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,8
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### Laghos

Testing:

```bash
# 3m 42 seconds
time flux run -o cpu-affinity=per-task -N2 -n 112 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-laghos_rocky-8.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 10 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
```

```console
oras login ghcr.io --username vsoch
app=laghos

for i in $(seq 1 5); do
  echo "Running iteration $i" 
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-laghos_rocky-8.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-laghos_rocky-8.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 1 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-laghos_rocky-8.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-laghos_rocky-8.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### LAMMPS

```bash
# 3 seconds wall time almost instant
time flux run -o cpu-affinity=per-task -N2 -n 112 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec --pwd /code /opt/containers/metric-lammps-cpu_rocky-8.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
```

```console
oras login ghcr.io --username vsoch
app=lammps

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -N32 -n 3072 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec --pwd /code /opt/containers/metric-lammps-cpu_rocky-8.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-64-iter-$i -o cpu-affinity=per-task -N64 -n 6144 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec --pwd /code /opt/containers/metric-lammps-cpu_rocky-8.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 12288 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec --pwd /code /opt/containers/metric-lammps-cpu_rocky-8.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-256-iter-$i -o cpu-affinity=per-task -N228 -n 24576 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec --pwd /code /opt/containers/metric-lammps-cpu_rocky-8.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### MiniFE

```bash
# 8.4 seconds
time flux run -N2 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-minife_rocky-8.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

# the larger problem size segfaults here, it gives a message about running out of memory, but could be only having two nodes.
```

```console
oras login ghcr.io --username vsoch
app=minife

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-minife_rocky-8.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-minife_rocky-8.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-minife_rocky-8.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-minife_rocky-8.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0 
done

# Note that minife outputs more result files!!
mkdir -p $output/miniFe
mv miniFE* $output/miniFe
# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### Mixbench

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing:

```bash
time flux run -l -N1 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-mixbench_cpu.sif mixbench-cpu 64
```

```console
oras login ghcr.io --username vsoch
app=mixbench

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-$size-iter-$i -l -N2 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-mixbench_cpu.sif mixbench-cpu 64
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### Mt-Gemm

Testing:

```bash
time flux run -N1 -o cpu-affinity=per-task --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec /opt/containers/mt-gemm_rocky-8.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
```
```console
Performance= 784.96 GFlop/s, Time= 2.548 msec, Size= 2000000000 Ops

real	0m13.146s
user	0m0.067s
sys	0m0.012s
```

```console
oras login ghcr.io --username vsoch
app=mt-gem

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec  /opt/containers/mt-gemm_rocky-8.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi  
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec /opt/containers/mt-gemm_rocky-8.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/mt-gemm_rocky-8.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi  
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec /opt/containers/mt-gemm_rocky-8.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### OSU

Write this script to the filesystem `flux-run-combinations.sh`

```bash
time flux run -N 1 -n 2 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency

time flux run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      singularity exec /home/ubuntu/containers/metric-osu-
```

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
    iter="${i}-${j}"
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

Testing:

```bash
# 28 seconds and 13 seconds, latency is ~38.
./flux_run_combinations.sh 2 $app

# 59 seconds
time flux run -N2 -n 112 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
```

And then run as follows.

```console
oras login ghcr.io --username vsoch
app=osu

./flux_run_combinations.sh 32 $app

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 --env OMPI_MCA_btl_vader_single_copy_mechanism=none -o cpu-affinity=per-task singularity exec /opt/containers/metric-osu-cpu_rocky-8.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### Quicksilver

Can't test - keeping both containers hope it works!

```bash
flux run --env OMP_NUM_THREADS=3 -N2 -n 64 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-quicksilver-cpu_rocky-8.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 10485760
```

That seemed to start working (the matrix started getting printed), but I didn't want to wait for it to finish.

```console
oras login ghcr.io --username vsoch
app=quicksilver

for i in $(seq 1 5); do
    echo "Running iteration $i"
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N32 -n 1024 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-quicksilver-cpu_rocky-8.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320 
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-quicksilver-cpu_rocky-8.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 128 -x 128 -y 128 -z 128 -I 16 -J 16 -K 8 -n 671088640
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-quicksilver-cpu_rocky-8.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 128 -Z 128 -x 256 -y 128 -z 128 -I 16 -J 16 -K 16 -n 1342117280
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192 singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-quicksilver-cpu_rocky-8.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 256 -Z 128 -x 256 -y 256 -z 128 -I 32 -J 16 -K 16 -n 2684354560
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

#### Stream

Testing:

```bash
time flux run -N1 -n 56 -o cpu-affinity=per-task singularity exec --env OMPI_MCA_btl_vader_single_copy_mechanism=none /opt/containers/metric-stream_rocky-8.sif stream_c.exe
```

```console
oras login ghcr.io --username vsoch
app=stream

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-1-iter-$i --env OMPI_MCA_btl_vader_single_copy_mechanism=none -N1 -n 56 -o cpu-affinity=per-task singularity exec /opt/containers/metric-stream_rocky-8.sif stream_c.exe 
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:compute-engine-cpu-$app $output
```

### Clean up

When you are done, exit and:

```bash
export GOOGLE_PROJECT=myproject
make destroy
```
