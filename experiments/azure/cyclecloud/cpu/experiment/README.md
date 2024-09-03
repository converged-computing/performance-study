# "Bare Metal" on Azure with CycleCloud

> Size 32

See the main [README.md](../) for setting up the cluster. The configuration file is here.
You will need to:

1. Create the cluster with Azure web interface (plan at least 6 hours)
2. ssh in
3. Install Singularity and Go
4. Pull all containers
5. Run the study, pushing each result artifact to oras (this part has not been written, see the eks experiments for naming convention)


## Experiment

### 1. Setup

The CycleCloud setup requires creating a dedicated web server. This is accomplished by navigating a byzantine web GUI with thousands of manually specified RBACs and IAM permission options. There is a magic switch that is supposed to configure the identity management, but only seems to do so when Azure engineers are watching. Storage configuration is its own circle of hell, and is region dependent.

SSH into the head node:
```bash
ssh -i ~/.ssh/ldrd-cc-cpu.pem ldrd-cyclecloud@13.84.10.47
```

Install Singularity and pull all containers.

```bash
git clone https://github.com/converged-computing/performance-study.git
cd performance-study/experiments/azure/cyclecloud/cpu
./install-job.sh
source ~/.bashrc
export SINGULARITY_CACHEDIR=/shared/.singularity
mkdir -p /shared/containers
cd /shared/containers

# This is the newer build with spack
singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:azure-hpc-reax || true &&  \
singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:azure-hpc || true && \
singularity pull docker://ghcr.io/converged-computing/metric-amg2023:azure-hpc-cpu-int64-zen3 || true && \
singularity pull docker://ghcr.io/converged-computing/metric-laghos:azure-hpc || true && \
singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu-zen4-tmpfile || true && \
singularity pull docker://ghcr.io/converged-computing/metric-minife:azure-hpc || true && \
singularity pull docker://ghcr.io/converged-computing/metric-mixbench:azure-hpc || true && \
singularity pull docker://ghcr.io/converged-computing/mt-gemm:azure-hpc-1k || true && \
singularity pull docker://ghcr.io/converged-computing/metric-osu-cpu:azure-hpc || true && \
singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-cpu:azure-hpc || true && \
singularity pull docker://ghcr.io/converged-computing/metric-stream:azure-hpc || true && \
singularity pull docker://ghcr.io/converged-computing/metric-nek5000:azure-hpc
```

Sanity check Infiniband is there.

```
# ibv_devinfo  | less
$ ibv_devinfo 
hca_id:	mlx5_an0
	transport:			InfiniBand (0)
	fw_ver:				14.30.1284
	node_guid:			000d:3aff:fe71:2c9f
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

Let's cleanup the singularity install.

```bash
rm -rf singularity-ce-4.1.3
rm singularity-ce*.tar.gz
```

### 2. Applications

#### Single Node Benchmark

Batch script:

redo on 32, 64

```bash
size=64
oras login ghcr.io --username vsoch
srun --time=00:04 -N ${size} slurm-single-node-benchmarks.sh
rm -rf test_file*
cd ../../data/single-node-benchmarks
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-single-node-benchmarks single-node-benchmarks
```

#### AMG2023

All the following examples are for ${size} nodes. Mutatis mutandis for other sizes.
Needed to set UCX_TLS=all for two runs due to ib errors. Seems to drop back to slower available transports if IB devices are missing

```bash
size=128
cd configs/amg2023/
for i in {1..5}; do sbatch --output=../../data/amg2023/%x-%j-iter-${i}.out --error=../../data/amg2023/%x-%j-iter-${i}.err slurm-amg-${size}n.sh; done
cd ../../data/amg2023
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-amg2023 amg2023
```


#### Kripke

```bash
size=128
cd configs/kripke/
for i in {1..5}; do sbatch --output=../../data/kripke/%x-%j-iter-${i}.out --error=../../data/kripke/%x-%j-iter-${i}.err slurm-kripke-${size}n.sh; done
cd ../../data/kripke
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-kripke kripke
```


#### Laghos

```bash
size=128
cd configs/laghos/
for i in {1..5}; do sbatch --output=../../data/laghos/%x-%j-iter-${i}.out --error=../../data/laghos/%x-%j-iter-${i}.err slurm-laghos-${size}n.sh; done
cd ../../data/laghos
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-laghos laghos
```

#### LAMMPS

Note that the first LAMMPS run was only using about 5-6% CPU per process. I reset the environment and resubmitted the jobs and it runs much faster. I need to reset the environment every time to get LAMMPS to consume CPU as expected.
UCX_TLS=all improves LAMMPS peformance by up to 2x.

```bash
size=128
cd configs/lammps/
for i in {1..5}; do sbatch --nodelist=cluster-256-hpc-[129-256] --output=../../data/lammps/%x-%j-iter-${i}.out --error=../../data/lammps/%x-%j-iter-${i}.err slurm-lammps-${size}n.sh; done
cd ../../data/lammps
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-lammps lammps
```

#### MiniFE

Minife only ran once successfully. Other runs only use 5% CPU and environment manipulation doesn't help.
redo on 32, 64

```bash
size=128
cd configs/minife/
for i in {1..5}; do sbatch --output=../../data/minife/%x-%j-iter-${i}.out --error=../../data/minife/%x-%j-iter-${i}.err slurm-minife-${size}n.sh; done
cd ../../data/minife
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-minife minife
```

Don't forget to save the MiniFE yaml output files that generate in the PWD.

#### Mixbench

redo on 32, 64

```bash
size=128
cd configs/mixbench/
for i in {1..5}; do 
  for node in $( sinfo -N -r -l | tail -n +3 | head -n ${size} | awk '{print $1}' ); do 
    sbatch --nodelist=${node} --output=../../data/mixbench/${node}-%x-%j-iter-${i}.out --error=../../data/mixbench/%x-%j-iter-${i}.err slurm-mixbench-1n.sh
  done
done
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-mixbench mixbench
```

#### Mt-Gemm
SKIPPING FOR NOW

```bash
size=128
cd configs/mt-gemm/
for i in {1..5}; do sbatch --nodelist=cluster-256-hpc-[129-256] --output=../../data/mt-gemm/%x-%j-iter-${i}.out --error=../../data/mt-gemm/%x-%j-iter-${i}.err slurm-mt-gemm-${size}n.sh; done
cd ../../data/mt-gemm
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-mt-gemm mt-gemm
```

#### Nek5000
SKIPPING error on loop device at size > 64.
```bash
size=128
mkdir /shared/nekrs
cd /shared/nekrs/
oras pull ghcr.io/converged-computing/metric-nek5000:libfabric-cpu-data
for i in {1..5}; do sbatch --nodelist=cluster-256-hpc-[1-128] --output=../../data/nekrs/%x-%j-iter-${i}.out --error=../../data/nekrs/%x-%j-iter-${i}.err slurm-nekrs-${size}n.sh; done
cd ../../data/nekrs
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-nekrs nekrs
```

#### OSU
OSU allreduce stopped working at iteration 4. UCX_TLS tested with all, ud,shm,rc, ib, and all three options have very different characteristics.

redo on 32, 64
```bash
size=128
cd configs/osu/
sbatch --output=../../data/osu/%x-%j-iter-${i}.out --error=../../data/osu/%x-%j-iter-${i}.err slurm-osu-${size}n.sh
cd ../../data/osu
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-osu osu
```

#### Quicksilver

```bash
size=128
cd configs/quicksilver/
for i in {1..5}; do sbatch --nodelist=cluster-256-hpc-[1-128] --output=../../data/quicksilver/%x-%j-iter-${i}.out --error=../../data/quicksilver/%x-%j-iter-${i}.err slurm-quicksilver-${size}n.sh; done
cd ../../data/quicksilver
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-quicksilver quicksilver
```

#### Stream

Redo on 32, 64

```bash
size=128
cd configs/stream/
for i in {1..5}; do 
  for node in $( sinfo -N -r -l | tail -n +3 | head -n ${size} | awk '{print $1}' ); do 
    sbatch --nodelist=${node} --output=../../data/stream/${node}-%x-%j-iter-${i}.out --error=../../data/stream/%x-%j-iter-${i}.err slurm-stream-1n.sh
  done
done
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:azure-cyclecloud-cpu-${size}-node-stream stream
```

