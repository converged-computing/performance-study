# "Bare Metal" on AWS with EC2

**TODO** 

- [ ] when all apps working, build with oras and containers pre-pulled
- [ ] kripke missing params for most
- [ ] Is redundantly saving results OK (they are saved to same results directory, pushed to different artifacts)

## Experiment

### 0. Pulling Containers

We need to pull all containers to all nodes, as there is no shared filesystem. We will pull to `/home/ubuntu`
since it exists.

```bash
cd /home/ubuntu
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-int64-zen3
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-laghos:libfabric-cpu-zen4 
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:libfabric-zen4
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu-zen4
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-minife:libfabric-cpu-zen4
#flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:zen4
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-mixbench:libfabric-cpu-zen4
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/mt-gemm:libfabric-cpu-zen4
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-osu-cpu:libfabric-zen4
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-cpu:libfabric-zen4
flux exec --dir /home/ubuntu -r all singularity pull docker://ghcr.io/converged-computing/metric-stream:libfabric-cpu-zen4
```

If we need to install oras:

```bash
#!/bin/bash
cd /tmp
export VERSION="1.1.0"
curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz"
mkdir -p oras-install/ && \
tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/
sudo mv oras-install/oras /usr/local/bin/
rm -rf oras_${VERSION}_*.tar.gz oras-install/
```
```bash
chmod +x install_oras.sh
flux archive create --name oras -C /home/ubuntu install_oras.sh
flux exec -x 0 flux archive extract --name oras -C /home/ubuntu
flux run -N $nodes /bin/bash /home/ubuntu/install_oras.sh
```

### 1. Setup

Get the topology:

```bash
aws ec2 describe-instance-topology --region us-east-2 --filters Name=instance-type,Values=hpc6a.48xlarge > topology-2.json
aws ec2 describe-instances --filters "Name=instance-type,Values=hpc6a.48xlarge" --region us-east-1 > instances-2.json
```

Sanity check efa is there.

```console
# fi_info  | less
provider: efa
    fabric: efa
    domain: rdmap0s31-rdm
    version: 121.0
    type: FI_EP_RDM
    protocol: FI_PROTO_EFA
provider: efa
    fabric: efa
    domain: rdmap0s31-dgrm
    version: 121.0
    type: FI_EP_DGRAM
    protocol: FI_PROTO_EFA
```

### 2. Applications

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
export output=./results
mkdir -p $output
```

#### Single Node Benchmark

We are going to run this via flux, running the job across nodes (and then when they are complete, getting the logs from flux).
Here is a modified entrypoint:

```console
oras login ghcr.io --username vsoch
app=single-node
nodes=3

mkdir -p $output

for node in $(seq 1 $nodes); do
  flux submit -N1 --setattr=user.study_id=$app-node-$node singularity exec metric-single-node_cpu-zen4.sif /bin/bash /entrypoint.sh
done 

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

Clean up test files

```bash
flux exec -r all /bin/bash -c "rm -rf /home/ubuntu/test_file*"
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
chmod +x run_amg.sh
flux archive create --name amg -C /home/ubuntu run_amg.sh
flux exec -x 0 flux archive extract --name amg -C /home/ubuntu
```

Test size run:

```bash
# 3 seconds
time flux run --env OMP_NUM_THREADS=3 -N 2 -n 8 -opmi=pmix -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-amg2023_spack-slim-cpu.sif /bin/bash /home/ubuntu/run_amg.sh amg -n 32 32 32 -P 2 2 2 -problem 2
```

```console
oras login ghcr.io --username vsoch
app=amg2023

for i in $(seq 1 15); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 1024 -opmi=pmix -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-amg2023_spack-slim-cpu.sif /bin/bash /home/ubuntu/run_amg.sh amg -n 256 256 128 -P 16 8 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N 64 -n 2048 -opmi=pmix -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-amg2023_spack-slim-cpu.sif /bin/bash /home/ubuntu/run_amg.sh amg -n 256 256 128 -P 16 16 8 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N 128 -n 4096 -opmi=pmix -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-amg2023_spack-slim-cpu.sif /bin/bash /home/ubuntu/run_amg.sh amg -n 256 256 128 -P 16 16 16 -problem 2
  time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N 256 -n 8192 -opmi=pmix -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-amg2023_spack-slim-cpu.sif /bin/bash /home/ubuntu/run_amg.sh amg -n 256 256 128 -P 32 16 16 -problem 2
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### Kripke

**IMPORTANT: not done yet, we skipped it, so I skipped testing, but added the container name**

```bash
time flux run --env OMP_NUM_THREADS=1 -N 1 -n 96 singularity exec /home/ubuntu/metric-kripke-cpu_libfabric-zen4.sif kripke

time flux run --env OMP_NUM_THREADS=3 -N 2 -n 64 singularity exec /home/ubuntu/metric-kripke-cpu_libfabric-zen4.sif kripke --layout DGZ --dset 16 --zones 144,448,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 12,16,16
```

```console
oras login ghcr.io --username vsoch
app=kripke

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-32-iter-$i -N 32 -n 3072 singularity exec /home/ubuntu/metric-kripke-cpu_libfabric-zen4.sif kripke --layout DGZ --dset 16 --zones 144,448,256 --gset 16 --groups 16 --niter 500 --legendre 2 --quad 16 --procs 12,16,16

# NOT DONE YET
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048 singularity exec /home/ubuntu/metric-kripke-cpu_libfabric-zen4.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,4,4
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 singularity exec /home/ubuntu/metric-kripke-cpu_libfabric-zen4.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 4,8,4
  time flux run --env OMP_NUM_THREADS=1 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192 singularity exec /home/ubuntu/metric-kripke-cpu_libfabric-zen4.sif kripke --arch CUDA --layout GDZ --dset 8 --zones 128,128,128 --gset 16 --groups 64 --niter 50 --legendre 8 --quad 8 --procs 8,4,8
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### Laghos

Testing:

```bash
# 1m 41 seconds
time flux run -o cpu-affinity=per-task -N3 -n 288 singularity exec /home/ubuntu/metric-laghos_libfabric-cpu-zen4.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 10 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom

time flux run -o cpu-affinity=per-task -N2 -n  singularity exec /home/ubuntu/metric-laghos_libfabric-cpu-zen4.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 10 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
```

```console
oras login ghcr.io --username vsoch
app=laghos

for i in $(seq 1 5); do
  echo "Running iteration $i" 
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 singularity exec /home/ubuntu/metric-laghos_libfabric-cpu-zen4.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 singularity exec /home/ubuntu/metric-laghos_libfabric-cpu-zen4.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 1 singularity exec /home/ubuntu/metric-laghos_libfabric-cpu-zen4.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
  time flux run -o cpu-affinity=per-task --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 singularity exec /home/ubuntu/metric-laghos_libfabric-cpu-zen4.sif /opt/laghos/laghos -pa -p 1 -tf 0.6 -pt 311 -m /opt/laghos/data/cube_311_hex.mesh --ode-solver 7 --max-steps 400 --cg-tol 0 -cgm 50 -ok 3 -ot 2 -rs 4 -rp 2 --fom
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### LAMMPS-REAX

```bash
cd /opt/containers
cd -
flux exec singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:libfabric-zen4-reax

# 1 seconds wall time, 8 seconds real (hookup)
time flux run -o cpu-affinity=per-task -N3 -n 288 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 2000
```

```console
oras login ghcr.io --username vsoch
app=lammps-reax

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -N32 -n 3072 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4-reax.sif /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
  time flux run --setattr=user.study_id=$app-64-iter-$i -o cpu-affinity=per-task -N64 -n 6144 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4-reax.sif /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 12288 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4-reax.sif /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
  time flux run --setattr=user.study_id=$app-256-iter-$i -o cpu-affinity=per-task -N228 -n 24576 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4-reax.sif /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

# 3 seconds wall time almost instant
time flux run -o cpu-affinity=per-task -N2 -n 112 --env OMPI_MCA_btl_vader_single_copy_mechanism=none singularity exec --pwd /code /opt/containers/metric-lammps-cpu_rocky-8-reax.sif /usr/bin/lmp -v x 64 -v y 64 -v z 32 -in in.reaxff.hns -nocite


#### LAMMPS

**Do not use this one, does not scale well**

```bash
# 1 seconds wall time, 8 seconds real (hookup)
time flux run -o cpu-affinity=per-task -N3 -n 288 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 2000
```

```console
oras login ghcr.io --username vsoch
app=lammps

# NOTE: the below takes 4 minutes. If taking too long, drop back to 3 iterations
# IMPORTANT: Ani is testing if 128 works on lassen and 1500 vs 1000 steps

# TODO THIS NEEDS TO BE THE UPDATED ONE
# time flux run --setattr=user.study_id=$app-32-iter-$i-20k -o cpu-affinity=per-task -N32 -n 3072 lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 512 -v y 512 -v z 512 -var nsteps 20000

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -o cpu-affinity=per-task -N32 -n 3072 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-64-iter-$i -o cpu-affinity=per-task -N64 -n 6144 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-128-iter-$i -o cpu-affinity=per-task -N128 -n 12288 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
  time flux run --setattr=user.study_id=$app-256-iter-$i -o cpu-affinity=per-task -N228 -n 24576 singularity exec --pwd /code /home/ubuntu/metric-lammps-cpu_zen4.sif lmp -k on -sf kk -pk kokkos newton on neigh half -in in.snap.test -var snapdir 2J8_W.SNAP -v x 128 -v y 128 -v z 128 -var nsteps 1000
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### MiniFE

```bash
# 8 seconds
time flux run -N3 -n 288 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-minife_libfabric-cpu-zen4.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0

# 
time flux run -N3 -n 288 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-minife_libfabric-cpu-zen4.sif miniFE.x nx=640 ny=640 nz=640 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
```

```console
oras login ghcr.io --username vsoch
app=minife

for i in $(seq 1 5); do
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-minife_libfabric-cpu-zen4.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-minife_libfabric-cpu-zen4.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-minife_libfabric-cpu-zen4.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-minife_libfabric-cpu-zen4.sif miniFE.x nx=230 ny=230 nz=230 use_locking=1 elem_group_size=10 use_elem_mat_fields=300 verify_solution=0 

done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### Mixbench

```bash
flux proxy local:///mnt/flux/view/run/flux/local bash
```

Testing:

```bash
time flux run -l -N2 mixbench-cpu 64
```

```console
oras login ghcr.io --username vsoch
app=mixbench

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-$size-iter-$i -l -N2 singularity exec /home/ubuntu/metric-mixbench_libfabric-cpu.sif mixbench-cpu 64
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### Mt-Gemm

Ani is testing the MPI variant and then we will update here.

Testing:

```bash
# runs but output is gibberish (7 seconds)
time flux run -N3 -n 288 -o cpu-affinity=per-task singularity exec /home/ubuntu/mt-gemm_libfabric-cpu-zen4.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
```

```console
oras login ghcr.io --username vsoch
app=mt-gem

for i in $(seq 1 2); do     
  echo "Running iteration $i"
  
  # 9 seconds
  time flux run -N4 -n 384 -o cpu-affinity=per-task singularity exec /home/ubuntu/mt-gemm_libfabric-cpu-zen4.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  
  # 9.66 seconds
  time flux run -N4 -n 384 singularity exec /home/ubuntu/mt-gemm_libfabric-cpu-zen4.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi

  # 8.34 seconds
  time flux run -N2 -n 192 -o cpu-affinity=per-task singularity exec /home/ubuntu/mt-gemm_libfabric-cpu-zen4.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
  
  # 8.66 seconds
  time flux run -N2 -n 192 singularity exec /home/ubuntu/mt-gemm_libfabric-cpu-zen4.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
done

./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### OSU

Write this script to the filesystem `flux_run_combinations.sh`

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
      singularity exec /home/ubuntu/metric-osu-cpu_libfabric-zen4.sif  /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency
    time flux run -N 2 -n 2 \
      --setattr=user.study_id=$app-2-iter-$iter \
      --requires="hosts:${i},${j}" \
      -o cpu-affinity=per-task \
      singularity exec /home/ubuntu/metric-osu-cpu_libfabric-zen4.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw
      iter=$((iter+1))
  done
done
```

Testing:

```bash
./flux_run_combinations.sh 3 $app

# 10 seconds
time flux run -N3 -n 288 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-osu-cpu_libfabric-zen4.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
```

And then run as follows.

```console
oras login ghcr.io --username vsoch
app=osu

./flux_run_combinations.sh 32 $app

for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-32-iter-$i -N32 -n 3072 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-osu-cpu_libfabric-zen4.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
  time flux run --setattr=user.study_id=$app-64-iter-$i -N64 -n 6144 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-osu-cpu_libfabric-zen4.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
  time flux run --setattr=user.study_id=$app-128-iter-$i -N128 -n 12288 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-osu-cpu_libfabric-zen4.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
  time flux run --setattr=user.study_id=$app-256-iter-$i -N256 -n 24576 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-osu-cpu_libfabric-zen4.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce 
done

# When they are done:
./save.sh $output
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### Quicksilver

For testing I used the smaller problem size for AKS from Abhik:

```bash
time flux run --cores-per-task 3 --env OMP_NUM_THREADS=3 -N2 -n 64 singularity exec /home/ubuntu/metric-quicksilver-cpu_libfabric-zen4.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 64  -Y 32  -Z 32  -x 64  -y 32  -z 32  -I 4  -J 4  -K 4 -n 10485760
```

    time flux run --env OMP_NUM_THREADS=3 -N32 -n 1024 singularity exec /home/ubuntu/metric-quicksilver-cpu_libfabric-zen4.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320


That seemed to start working (the matrix started getting printed), but I didn't want to wait for it to finish.

```console
oras login ghcr.io --username vsoch
app=quicksilver

for i in $(seq 1 5); do     
    echo "Running iteration $i"
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-32-iter-$i -N32 -n 1024 singularity exec /home/ubuntu/metric-quicksilver-cpu_libfabric-zen4.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 64 -x 128 -y 128 -z 64 -I 16 -J 8 -K 8 -n 335544320
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-64-iter-$i -N64 -n 2048 singularity exec /home/ubuntu/metric-quicksilver-cpu_libfabric-zen4.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 128 -Y 128 -Z 128 -x 128 -y 128 -z 128 -I 16 -J 16 -K 8 -n 671088640
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-128-iter-$i -N128 -n 4096 singularity exec /home/ubuntu/metric-quicksilver-cpu_libfabric-zen4.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 128 -Z 128 -x 256 -y 128 -z 128 -I 16 -J 16 -K 16 -n 1342117280
    time flux run --env OMP_NUM_THREADS=3 --setattr=user.study_id=$app-256-iter-$i -N256 -n 8192 singularity exec /home/ubuntu/metric-quicksilver-cpu_libfabric-zen4.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp -X 256 -Y 256 -Z 128 -x 256 -y 256 -z 128 -I 32 -J 16 -K 16 -n 2684354560
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

#### Stream

Testing:

```bash
# 4 seconds
time flux run -N1 -n 96 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-stream_libfabric-cpu-zen4.sif stream_c.exe
```

```console
oras login ghcr.io --username vsoch
app=stream

mkdir -p $output
for i in $(seq 1 5); do     
  echo "Running iteration $i"
  time flux run --setattr=user.study_id=$app-1-iter-$i -N1 -n 96 -o cpu-affinity=per-task singularity exec /home/ubuntu/metric-stream_libfabric-cpu-zen4.sif stream_c.exe 
done

# When they are done:
./save.sh $output

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:ec2-cpu-$app $output
```

### Clean up

When you are done, exit and:

```bash
make destroy
```

And don't forget to type "yes" !
