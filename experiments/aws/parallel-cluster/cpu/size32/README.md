# "Bare Metal" on AWS with Parallel Cluster

> Size 32

See the main [README.md](../) for setting up the cluster. The configuration file is here.
You will need to:

1. Create the cluster with pcluster
2. ssh in
3. Install Singularity and Go
4. Pull all containers
5. Run the study, pushing each result artifact to oras (this part has not been written, see the eks experiments for naming convention)


## Experiment

### 0. Pull Containers

Pull all containers.

```bash
export SINGULARITY_CACHEDIR=/shared/.singularity
mkdir -p /shared/containers
cd /shared/containers

# This is the newer build with spack
singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-int64-zen3

# This is the previous one - works, but not in some environments.
# singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu
singularity pull docker://ghcr.io/converged-computing/metric-laghos:libfabric-cpu-zen4 
singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu-zen4
singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:libfabric-zen4
singularity pull docker://ghcr.io/converged-computing/metric-minife:libfabric-cpu-zen4
singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:zen4
singularity pull docker://ghcr.io/converged-computing/metric-mixbench:libfabric-cpu-zen4
singularity pull docker://ghcr.io/converged-computing/mt-gemm:libfabric-cpu-zen4
singularity pull docker://ghcr.io/converged-computing/metric-osu-cpu:libfabric-zen4
singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-cpu:libfabric-zen4
singularity pull docker://ghcr.io/converged-computing/metric-stream:libfabric-cpu-zen4
```

### 1. Setup

Get the topology:

```bash
aws ec2 describe-instance-topology --region us-east-2 --filters Name=instance-type,Values=hpc6a.48xlarge > topology-2.json
aws ec2 describe-instances --filters "Name=instance-type,Values=hpc6a.48xlarge" --region us-east-1 > instances-2.json
```

Sanity check efa is there.

```
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

Let's cleanup the singularity install.

```bash
rm -rf singularity-ce-4.1.3
rm singularity-ce*.tar.gz
```

### 2. Applications

#### Single Node Benchmark

Batch script:

```bash
#!/bin/bash
# run_node_benchmark.sh
/shared/bin/singularity exec /shared/containers/metric-single-node_cpu-zen4.sif /bin/bash /entrypoint.sh
rm -rf test_file*
```

```console
oras login ghcr.io --username vsoch
app=single-node
output=./results/$app

# Note sure if we need iterations here
for node in $(seq 1 4); do
  # Does this mean one on each node?
  sbatch -N 1 /shared/run_node_benchmark.sh
done 

# When they are done:
for jobid in $(flux jobs -a --json | jq -r .jobs[].id)
  do
    flux job attach $jobid &> ./$output/$app-${jobid}.out 
  done

oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:test-$app $output
```

From Alan sill to save jobs (needs to be tested):

```
For the first, you might be able to use the “--extra=<string>” flag for salloc or srun. (Disclaimer: I’ve never used this.)
For the second, you can use sacct
sacct -u (user) -S (start datetime) --json | jq -r .jobs.job_id
```

#### AMG2023

Since this container requires sourcing spack, we need to write a bash script to run on the host.

```bash
#!/bin/bash
# run-amg.sh
. /etc/profile.d/z10_spack_environment.sh
/shared/bin/singularity exec /shared/containers/metric-amg2023_spack-slim-cpu.sif ./run_amg.sh
singularity amg -P 8 6 4 -n 64 64 128
```

And then copy the script and run.

```bash
sbatch -N 4 /shared/bin/singularity exec /shared/containers/metric-amg2023_spack-slim-cpu.sif ./run_amg.sh

# 21.46 seconds
time mpirun -np 192 --hostfile ./hostfile.txt /shared/bin/singularity exec /shared/containers/metric-amg2023_spack-slim-cpu.sif /bin/bash ./run_amg.sh
```

I couldn't get this working with flux, so I tried mpirun alone:

```console
mpirun --hostfile ./hostlist.txt -N 2 -n 192 singularity exec metric-amg2023_spack-slim-cpu.sif /bin/bash ./run-amg.sh
```
That didn't work either - I suspect the spack environment / bash script is adding issue. Needs more thinking - maybe requiring bindings to the host (ew).


#### Kripke

```bash
# 1 minute 5 seconds
time singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:libfabric

# works!
# 2 minutes 49 seconds
time mpirun -np 192 --hostfile ./hostfile.txt /shared/bin/singularity exec /shared/containers/metric-kripke-cpu_libfabric.sif kripke --layout GDZ --dset 8 --zones 96,96,96 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 4,6,8
```


#### Laghos

```bash
# 54 seconds
time singularity pull docker://ghcr.io/converged-computing/metric-laghos:libfabric-cpu

# 9.34 seconds
time mpirun -np 192 --hostfile ./hostfile.txt /shared/bin/singularity exec --pwd /opt/laghos metric-laghos_libfabric-cpu.sif /opt/laghos/laghos -p 1 -m ./data/cube01_hex.mesh -rs 2 -tf 0.6 -pa -cfl 0.08 --max-steps 20
```

#### LAMMPS

```bash
# 1 minute 1 seconds
time singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:libfabric

# pull the data
cd /home/ubuntu
oras pull ghcr.io/converged-computing/metric-lammps-cpu:libfabric-data
cd /shared/containers

# 22.14 seconds
time mpirun -np 192 --hostfile ./hostfile.txt /shared/bin/singularity exec --pwd /home/ubuntu/common /shared/containers/metric-lammps-cpu_libfabric.sif  lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000
```

#### MiniFE

**Important** this is 8x slower than an equivalent setup with flux / efa / libfabric etc also on AWS.

```bash
# 49.84 seconds
time singularity pull docker://ghcr.io/converged-computing/metric-minife:libfabric-cpu

# 8 minutes!
time mpirun -np 96 -map-by ppr:48:node --hostfile ./hostfile.txt /shared/bin/singularity exec /shared/containers/metric-minife_libfabric-cpu.sif miniFE.x nx=620 ny=620 nz=620 num_devices=4 use_locking=1 elem_group_size=2 use_elem_mat_fields=10 verify_solution=0
```

Don't forget to save the MiniFE yaml output files that generate in the PWD.

#### Mixbench

This wasn't on the path.

```bash
# 49.78 seconds
time singularity pull docker://ghcr.io/converged-computing/metric-mixbench:libfabric-cpu

# 24 seconds
time mpirun -np 2 --hostfile ./hostfile.txt /shared/bin/singularity exec /shared/containers/metric-mixbench_libfabric-cpu.sif mixbench-cpu
```

Again, this seems like it's for one node only, and needs a wrapper.

#### Mt-Gemm

```bash
# 51 seconds
time singularity pull docker://ghcr.io/converged-computing/mt-gemm:libfabric-cpu

# 7.35 seconds
time mpirun -np 192 --hostfile ./hostfile.txt /shared/bin/singularity exec /shared/containers/mt-gemm_libfabric-cpu.sif /opt/dense_linear_algebra/gemm/mpi/build/1_dense_gemm_mpi
```

#### Nek5000

```bash
# 1 minute 9 seconds
time singularity pull docker://ghcr.io/converged-computing/metric-nek5000:libfabric-cpu

mkdir -p /home/ubuntu/nekrs
cd /home/ubuntu/nekrs
oras pull ghcr.io/converged-computing/metric-nek5000:libfabric-cpu-data

time mpirun -np 192 --hostfile /shared/containers/hostfile.txt /shared/bin/singularity exec --pwd /home/ubuntu/nekrs/turbPipe /shared/containers/metric-nek5000_libfabric-cpu.sif nekrs --setup /home/ubuntu/nekrs/turbPipe/turbPipe.par
```

This works but runs forever - needs tweaking of parameters.

#### OSU

```bash
# 1 minute
time singularity pull docker://ghcr.io/converged-computing/metric-osu-cpu:libfabric

# 3 minutes 47 seconds
time mpirun -np 2 -map-by ppr:1:node --hostfile /shared/containers/hostfile.txt /shared/bin/singularity exec /shared/containers/metric-osu-cpu_libfabric.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_bw

# 11.928 seconds
time mpirun -np 2 -map-by ppr:1:node --hostfile /shared/containers/hostfile.txt /shared/bin/singularity exec /shared/containers/metric-osu-cpu_libfabric.sif /opt/osu-benchmark/build.openmpi/mpi/pt2pt/osu_latency

# 12.5 seconds
time mpirun -np 192 --hostfile /shared/containers/hostfile.txt /shared/bin/singularity exec /shared/containers/metric-osu-cpu_libfabric.sif /opt/osu-benchmark/build.openmpi/mpi/collective/osu_allreduce
```

#### Quicksilver

```bash
# 1 minute 12 seconds
time singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-cpu:libfabric

# This hangs
time mpirun -np 192 --hostfile /shared/containers/hostfile.txt /shared/bin/singularity exec /shared/containers/metric-quicksilver-cpu_libfabric.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp

# This runs in 34.48 seconds
time mpirun -np 8 -map-by ppr:4:node --hostfile /shared/containers/hostfile.txt /shared/bin/singularity exec /shared/containers/metric-quicksilver-cpu_libfabric.sif qs --inputFile /opt/quicksilver/Examples/CORAL2_Benchmark/Problem1/Coral2_P1.inp
```

#### Stream

```bash
# 49.51 seconds
time singularity pull docker://ghcr.io/converged-computing/metric-stream:libfabric-cpu

# 6.44 seconds
time mpirun -np 192 -map-by ppr:96:node --hostfile /shared/containers/hostfile.txt /shared/bin/singularity exec /shared/containers/metric-stream_libfabric-cpu.sif stream_c.exe
```

This doesn't seem like it's mapping right.

```
Solution Validates: avg error less than 1.000000e-13 on all three arrays
```

