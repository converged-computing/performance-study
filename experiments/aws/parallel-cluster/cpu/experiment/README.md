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
aws ec2 describe-instance-topology --region us-east-2 --filters Name=instance-type,Values=hpc6a.48xlarge --filters Name=tag-key,Values=cluster-tag-value > topology-size32.json
aws ec2 describe-instances --filters "Name=instance-type,Values=hpc6a.48xlarge" --region us-east-2 > instances-size32.json
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
singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu-int64-zen3 && \
singularity pull docker://ghcr.io/converged-computing/metric-laghos:libfabric-cpu-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-single-node:cpu-zen4-tmpfile && \
singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:libfabric-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-minife:libfabric-cpu-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-mixbench:libfabric-cpu && \
singularity pull docker://ghcr.io/converged-computing/mt-gemm:libfabric-cpu-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-osu-cpu:libfabric-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-quicksilver-cpu:libfabric-zen4 && \
singularity pull docker://ghcr.io/converged-computing/metric-stream:libfabric-cpu-zen4 &&
singularity pull docker://ghcr.io/converged-computing/metric-nek5000:libfabric-cpu-data
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
cd ../../data/single-node-benchmarks
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-single-node-benchmarks single-node-benchmarks
```

#### AMG2023

All the following examples are for 32 nodes. Mutatis mutandis for other sizes.

```bash
# May want to try these env variables in the job scripts:
#export FI_EFA_FORK_SAFE=1
#export FI_PROVIDER=efa
cd configs/amg2023/
for i in {1..5}; do sbatch --output=../../data/amg2023/%x-%j-iter-${i}.out --error=../../data/amg2023/%x-%j-iter-${i}.err slurm-amg-32n.sh; done
cd ../../data/amg2023
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-amg2023 amg2023
```


#### Kripke

```bash
cd configs/kripke/
for i in {1..5}; do sbatch --output=../../data/kripke/%x-%j-iter-${i}.out --error=../../data/kripke/%x-%j-iter-${i}.err slurm-kripke-32n.sh; done
cd ../../data/kripke
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-kripke kripke
```


#### Laghos

```bash
cd configs/laghos/
for i in {1..5}; do sbatch --output=../../data/laghos/%x-%j-iter-${i}.out --error=../../data/laghos/%x-%j-iter-${i}.err slurm-laghos-32n.sh; done
cd ../../data/laghos
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-laghos laghos
```

#### LAMMPS

```bash
cd configs/lammps/
for i in {1..5}; do sbatch --output=../../data/lammps/%x-%j-iter-${i}.out --error=../../data/lammps/%x-%j-iter-${i}.err slurm-lammps-32n.sh; done
cd ../../data/lammps
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-lammps lammps
```

#### MiniFE

```bash
cd configs/minife/
for i in {1..5}; do sbatch --output=../../data/minife/%x-%j-iter-${i}.out --error=../../data/minife/%x-%j-iter-${i}.err slurm-minife-32n.sh; done
cd ../../data/minife
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-minife minife
```

Don't forget to save the MiniFE yaml output files that generate in the PWD.

#### Mixbench

```bash
cd configs/mixbench/
for i in {1..5}; do 
  for node in $( sinfo -N -r -l | tail -n +3 | awk '{print $1}' ); do 
    sbatch --nodelist=${node} --output=../../data/mixbench/${node}-%x-%j-iter-${i}.out --error=../../data/mixbench/%x-%j-iter-${i}.err slurm-mixbench-1n.sh
  done
done
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-mixbench mixbench
```

#### Mt-Gemm

```bash
cd configs/mt-gemm/
for i in {1..5}; do sbatch --output=../../data/mt-gemm/%x-%j-iter-${i}.out --error=../../data/mt-gemm/%x-%j-iter-${i}.err slurm-mt-gemm-32n.sh; done
cd ../../data/mt-gemm
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-mt-gemm mt-gemm
```

#### Nek5000

```bash
mkdir /shared/nekrs
cd /shared/nekrs/
oras pull ghcr.io/converged-computing/metric-nek5000:libfabric-cpu-data
for i in {1..5}; do sbatch --output=../../data/nekrs/%x-%j-iter-${i}.out --error=../../data/nekrs/%x-%j-iter-${i}.err slurm-nekrs-32n.sh; done
cd ../../data/nekrs
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-nekrs nekrs
```

#### OSU

```bash
cd configs/osu/
sbatch --output=../../data/osu/%x-%j-iter-${i}.out --error=../../data/osu/%x-%j-iter-${i}.err slurm-osu-32n.sh
cd ../../data/osu
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-osu osu
```

#### Quicksilver

```bash
cd configs/quicksilver/
for i in {1..5}; do sbatch --output=../../data/quicksilver/%x-%j-iter-${i}.out --error=../../data/quicksilver/%x-%j-iter-${i}.err slurm-quicksilver-32n.sh; done
cd ../../data/quicksilver
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-quicksilver quicksilver
```

#### Stream

```bash
cd configs/stream/
for i in {1..5}; do 
  for node in $( sinfo -N -r -l | tail -n +3 | awk '{print $1}' ); do 
    sbatch --nodelist=${node} --output=../../data/stream/${node}-%x-%j-iter-${i}.out --error=../../data/stream/%x-%j-iter-${i}.err slurm-stream-1n.sh
  done
done
oras push ghcr.io/converged-computing/metrics-operator-experiments/performance:aws-parallelcluster-cpu-32node-stream stream
```

