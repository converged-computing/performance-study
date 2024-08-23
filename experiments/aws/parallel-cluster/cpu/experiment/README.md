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

### 1. Setup

Create the subnets with `pcluster`:
```bash
pcluster configure -c cluster.config
```
Get the subnet from the config file above, and add the subnets to `config-file.yaml`. Then create the cluster with pcluster:
```bash
pcluster create-cluster --cluster-configuration config-file.yaml --cluster-name config-pcluster --region us-east-2 
```
Monitor the creation progress:
```bash
pcluster describe-cluster --cluster-name config-pcluster --region us-east-2
{
  "creationTime": "2024-08-23T00:20:25.209Z",
  "headNode": {
    "launchTime": "2024-08-23T00:24:36.000Z",
    "instanceId": "i-06f55b4c0ae6f9875",
    "publicIpAddress": "18.117.224.238",
    "instanceType": "c6a.2xlarge",
    "state": "running",
    "privateIpAddress": "10.0.7.111"
  },
  "version": "3.10.1",
  "clusterConfiguration": {
    "url": "https://parallelcluster-debe587c55769216-v1-do-not-delete.s3.us-east-2.amazonaws.com/parallelcluster/3.10.1/clusters/config-pcluster-wux6ofn2cwdnc8bh/configs/cluster-config.yaml?versionId=kVSLNiOZNfo5V2czATECaEGPqWtly9pB&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAU6GDU2KJGFFTCLGH%2F20240823%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20240823T002442Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEJD%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMiJHMEUCIQCZvHihW1kNDjCMJvKXTabPpdjHwN3M%2F49zKOxTOPmpyAIgWtAy8m6yLhmMMtT0NkdYIk8e5KNYXgwwiHNWleS5g9kq8gIImf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgwzMzk3MTI3MjU2NTAiDOzcmsKzmlBxlc%2BONSrGAnaiKqwEqlZmTz4hDNNnAIWJdzDH7kqcfJTF3EKf32YRv8ONIP82AVXS5ythMbibg3ThTE3e84snxJfRLqBBClDbwMA98Vuu84J0dXZqmijKtACOGbze5lPpaYYmByJR1ErMq8cEFDaLq%2B7fkjEZJo6B%2F5InGFCWSKFEg22Pxf9riAnVaB9fdHTnlk5V6NQew6PxMdNhGjSskUVZMh%2Bj9nUjMWKE1orTuaofwBxeVCVIogmDPdWdCsABp9T7qmpnqYSEdRmiLdioCdkBtT2%2BE6y6wGys4X8aifyIy%2BCRVc3Xb%2FH0WabY9C%2F4c2xVP6GmyK0bG7y1z1XvDuhcl55Ao7yF4ZcipsEWClT9ZZU%2BncHpbocg%2FS09lTP04bstsxBj7Lo0Gsu4yuzPNpj%2BPiU8QfPEvLsU3Tsiv7p9UsS9o%2Fsdz8gJaeECMK36nrYGOocCckXrFqkaOCqL8nDIaWE7OF6el1Rz7iodOTYAir%2FEcrZUt%2BDSWmFn6G2U4vcbANtktQHBsUSpT4S7eOwC6lZMoQW9Q9UlY6sOsvZwXrhDd5coVoUbxuMPk1JHLNnIy60ijHd9xd6tRNn1CjEzY80wgI0bshIInPj9JKk6O9NM0TEG61u8xExATipSSgIbijcIGB87COy9nbF0Oif9w7BsKxdypoIyRf0ZbRrzuLmNFXc2Gj86ElmYHy7BuoZ1KcIPHgFrPZzyy%2FKU5kEjA%2FefyXErNgcW4ewh36lqBwvNgUeJDIAHxBwttKTq%2BpujAhsR0h7hmPMNbO6mIImvrossHYRkYDsP4L4%3D&X-Amz-Signature=61c625e162ca2ce91e2237bacaef2ee6374138ae250b37806c825499fa60f9e5"
  },
  "tags": [
    {
      "value": "3.10.1",
      "key": "parallelcluster:version"
    },
    {
      "value": "config-pcluster",
      "key": "parallelcluster:cluster-name"
    }
  ],
  "cloudFormationStackStatus": "CREATE_IN_PROGRESS",
  "clusterName": "config-pcluster",
  "computeFleetStatus": "UNKNOWN",
  "cloudformationStackArn": "arn:aws:cloudformation:us-east-2:339712725650:stack/config-pcluster/7e12bff0-60e5-11ef-b767-02a11e3472ff",
  "lastUpdatedTime": "2024-08-23T00:20:25.209Z",
  "region": "us-east-2",
  "clusterStatus": "CREATE_IN_PROGRESS",
  "scheduler": {
    "type": "slurm"
  }
}
```

SSH into the head node:
```bash
ssh -i ~/.ssh/milroy1-ldrd-east2-ed2.pem ubuntu@ec2-18-117-224-238.us-east-2.compute.amazonaws.com -o PubkeyAcceptedKeyTypes=ssh-ed25519 -o IgnoreUnknown=UseKeychain
```

Get the topology:

```bash
aws ec2 describe-instance-topology --region us-east-2 --filters Name=instance-type,Values=hpc6a.48xlarge --filters Name=tag-key,Values=cluster-tag-value > topology-2.json
aws ec2 describe-instances --filters "Name=instance-type,Values=hpc6a.48xlarge" --region us-east-2 > instances-2.json
```

Install Singularity and pull all containers.

```bash
git clone https://github.com/converged-computing/performance-study.git
cd performance-study/experiments/aws/parallel-cluster/cpu
./install-job.sh
source ~/.bashrc
export SINGULARITY_CACHEDIR=/shared/.singularity
mkdir -p /shared/containers
cd /shared/containers

# This is the newer build with spack
singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-int64-zen3

# This is the previous one - works, but not in some environments.
# singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu
singularity pull docker://ghcr.io/converged-computing/metric-laghos:libfabric-cpu-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu-zen4-tmpfile && \
singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:libfabric-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-minife:libfabric-cpu-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-mixbench:libfabric-cpu-zen4 && \
singularity pull docker://ghcr.io/converged-computing/mt-gemm:libfabric-cpu-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-osu-cpu:libfabric-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-cpu:libfabric-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-stream:libfabric-cpu-zen4 &&
singularity pull docker://ghcr.io/converged-computing/metric-nek5000:libfabric-cpu-zen4
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

```console
oras login ghcr.io --username vsoch
srun --time=00:04 -N 2 slurm-single-node-benchmarks.sh
rm -rf test_file*
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-single-node-benchmark single-node-benchmark
```

#### AMG2023

Since this container requires sourcing spack, we need to write a bash script to run on the host.

```bash
cd configs/amg2023/
for i in {1..5}; do sbatch --output=../data/amg2023/amg-2n-%x-%j-iter-${i}.out --error=../data/amg2023/amg-2n-%x-%j-iter-${i}.err slurm-amg-2n.sh; done
```


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

