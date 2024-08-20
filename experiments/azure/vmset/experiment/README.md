# "Bare Metal" on Azure with a VM Scale Set

- [ ] kripke missing params for most
- We are going to be redundantly saving results (they are saved to same results directory, pushed to different artifacts)
- AMG does not use spack (just heads up - the important thing is that it runs)
- miniFe has no problem with larger size (640) and other clouds don't either, should we be constraining clouds because lassen/dane can't do it?
- miniFE outputs result files with quite a bit more metadata, I found them and am going to save to our artifacts

## Experiment

### 0. Pulling Containers

The containers are already pulled and located in `/home/ubuntu/containers`. Oras is also installed.
We need to pull a new one for amg

```bash
flux exec singularity pull docker://ghcr.io/converged-computing/metric-amg2023:azure-hpc-cpu-int64-zen3
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

```bash
# This output directory is used across experiments
export output=/home/ubuntu/containers/results
mkdir -p $output
```

#### Single Node Benchmark

We are going to run this via flux, running the job across nodes (and then when they are complete, getting the logs from flux).
Here is a modified entrypoint:

```console
oras login ghcr.io --username vsoch
app=single-node
nodes=2

for node in $(seq 1 $nodes); do
  flux submit -N1 --setattr=user.study_id=$app-node-$node singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-single-node_cpu-zen4.sif  /bin/bash /entrypoint.sh
done 

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

Clean up test files

```bash
flux exec -r all /bin/bash -c "rm -rf /home/ubuntu/containers/test_file*"
```

#### AMG2023

This container DOES use spack, should be:

```bash
flux exec singularity pull docker://ghcr.io/converged-computing/metric-amg2023:azure-hpc-cpu-int64-zen3
```

Test size run:

```bash
# 25 seconds
time flux run --env OMP_NUM_THREADS=3 -N 2 -n 8 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc-cpu-int64.sif amg -n 32 32 32 -P 2 2 2 -problem 2

# 1m 7 seconds
time flux run --env OMP_NUM_THREADS=3 -N 2 -n 8 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc-cpu-int64.sif amg -n 64 64 64 -P 2 2 2 -problem 2

# 4m 28 seconds
time flux run --env OMP_NUM_THREADS=3 -N 2 -n 8 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc-cpu-int64.sif amg -n 128 128 128 -P 2 2 2 -problem 2
```

```console
oras login ghcr.io --username vsoch
app=amg

# QUESTION: if this takes a long time, 15 iterations might take too long
for i in $(seq 1 15); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1024 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc-cpu-int64.sif amg -n 256 256 128 -P 16 8 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N 64 -n 2048 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc-cpu-int64.sif amg -n 256 256 128 -P 16 16 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 4096 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc-cpu-int64.sif amg -n 256 256 128 -P 16 16 16 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N 256 -n 8192 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc-cpu-int64.sif amg -n 256 256 128 -P 32 16 16 -problem 2
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### AMG

NOTE that if the above works, we don't need this one. This container does not use spack.

Test size run:

```bash
# 25 seconds
time flux run --env OMP_NUM_THREADS=3 -N 2 -n 8 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc.sif amg -n 32 32 32 -P 2 2 2 -problem 2

# 1m 7 seconds
time flux run --env OMP_NUM_THREADS=3 -N 2 -n 8 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc.sif amg -n 64 64 64 -P 2 2 2 -problem 2

# 4m 28 seconds
time flux run --env OMP_NUM_THREADS=3 -N 2 -n 8 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc.sif amg -n 128 128 128 -P 2 2 2 -problem 2
```

```console
oras login ghcr.io --username vsoch
app=amg

# QUESTION: if this takes a long time, 15 iterations might take too long
for i in $(seq 1 15); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1024 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc.sif amg -n 256 256 128 -P 16 8 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N 64 -n 2048 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc.sif amg -n 256 256 128 -P 16 16 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 4096 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc.sif amg -n 256 256 128 -P 16 16 16 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N 256 -n 8192 -opmi=pmix -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-amg_azure-hpc.sif amg -n 256 256 128 -P 32 16 16 -problem 2
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### Kripke

**IMPORTANT: not done yet, we skipped it, so I skipped testing, but added the container name**

```bash
time flux run --env OMP_NUM_THREADS=1 -N 1 -n 96 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-kripke-cpu_azure-hpc.sif kripke
```

```console
oras login ghcr.io --username vsoch
app=kripke

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 3072 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-kripke-cpu_azure-hpc.sif kripke --layout DGZ --dset 16 --zones 144,448,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 12,16,16

# NOT DONE YET
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-kripke-cpu_azure-hpc.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-kripke-cpu_azure-hpc.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,8,4
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-kripke-cpu_azure-hpc.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,8
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### Laghos

Testing:

```bash
# 2m 40s
time flux run -o cpu-affinity=per-task -N2 -n 192 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-laghos_azure-hpc.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 10 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
```

```console
oras login ghcr.io --username vsoch
app=laghos

for i in $(seq 1 5); do
  echo "Running iteration $i" 
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-laghos_azure-hpc.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-laghos_azure-hpc.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 1 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-laghos_azure-hpc.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-laghos_azure-hpc.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### LAMMPS

```bash
# 0 seconds wall time, 12 seconds real (hookup)
time flux run -o cpu-affinity=per-task -N2 -n 192 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 --pwd /code /home/ubuntu/containers/metric-lammps-cpu_azure-hpc.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000 
```

```console
oras login ghcr.io --username vsoch
app=lammps

# NOTE: the below takes 4 minutes. If taking too long, drop back to 3 iterations
# IMPORTANT: Ani is testing if 128 works on lassen and 1500 vs 1000 steps

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -N32 -n 3072 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 --pwd /code /home/ubuntu/containers/metric-lammps-cpu_azure-hpc.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-64-iter-$i -o cpu-affinity=per-task -N64 -n 6144 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 --pwd /code /home/ubuntu/containers/metric-lammps-cpu_azure-hpc.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 12288 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 --pwd /code /home/ubuntu/containers/metric-lammps-cpu_azure-hpc.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-256-iter-$i -o cpu-affinity=per-task -N228 -n 24576 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 --pwd /code /home/ubuntu/containers/metric-lammps-cpu_azure-hpc.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### MiniFE

```bash
# 12 seconds
time flux run -N2 -n 192 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-minife_azure-hpc.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

# 54 seconds
time flux run -N2 -n 192 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-minife_azure-hpc.sif miniFE.x nx=640 ny=640 nz=640 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
```

```console
oras login ghcr.io --username vsoch
app=minife

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-minife_azure-hpc.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-minife_azure-hpc.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-minife_azure-hpc.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-minife_azure-hpc.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0 
done

# Note that minife outputs more result files!!
mkdir -p $output/miniFe
mv miniFE* $output/miniFe
# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### Mixbench

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing:

```bash
time flux run -l -N2 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-mixbench_azure-hpc.sif mixbench-cpu 64
```

```console
oras login ghcr.io --username vsoch
app=mixbench

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-$size-iter-$i -l -N2 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-mixbench_azure-hpc.sif mixbench-cpu 64
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### Mt-Gemm

Testing:

```bash
time flux run -N2 -n 192 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/mt-gemm_azure-hpc.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
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
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/mt-gemm_azure-hpc.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi  
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/mt-gemm_azure-hpc.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/mt-gemm_azure-hpc.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi  
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/mt-gemm_azure-hpc.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### OSU

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
    iter="${i}-${j}"
    time flux run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-osu-cpu_azure-hpc.sif  /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    time flux run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw
      iter=$((iter+1))
  done
done
```

Testing:

```bash
./flux_run_combinations.sh 2 $app

# 59 seconds
time flux run -N2 -n 192 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
```

And then run as follows.

```console
oras login ghcr.io --username vsoch
app=osu

./flux_run_combinations.sh 32 $app

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-osu-cpu_azure-hpc.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### Quicksilver

For testing I used the smaller problem size for AKS from Abhik:

```bash
flux run --env OMP_NUM_THREADS=3 -N2 -n 64 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-quicksilver-cpu_azure-hpc.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 10485760
```

That seemed to start working (the matrix started getting printed), but I didn't want to wait for it to finish.

```console
oras login ghcr.io --username vsoch
app=quicksilver

for i in $(seq 1 5); do     
    echo "Running iteration $i"
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N32 -n 1024 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-quicksilver-cpu_azure-hpc.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-quicksilver-cpu_azure-hpc.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 128 -x 128 -y 128 -z 128 -I 16 -J 16 -K 8 -n 671088640
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-quicksilver-cpu_azure-hpc.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 128 -Z 128 -x 256 -y 128 -z 128 -I 16 -J 16 -K 16 -n 1342117280
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192 singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-quicksilver-cpu_azure-hpc.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 256 -Z 128 -x 256 -y 256 -z 128 -I 32 -J 16 -K 16 -n 2684354560
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

#### Stream

Testing:

```bash
# 7.8 seconds
time flux run -N1 -n 96 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-stream_azure-hpc.sif stream_c.exe
```

```console
oras login ghcr.io --username vsoch
app=stream

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-1-iter-$i -N1 -n 96 -o cpu-affinity=per-task singularity exec --env UCX_NET_DEVICES=mlx5_ib0:1 /home/ubuntu/containers/metric-stream_azure-hpc.sif stream_c.exe 
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cpu-$app $output
```

### Clean up

When you are done, exit and delete everything in the Azure web interface. 
