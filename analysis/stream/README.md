# Stream Analysis

Stream is used as a single benchmark, but it looks like for GPU we tried to run across nodes. But we possibly didn't know or decide to do this until after the early EKS GPU runs.

## Catalog

There are two ways to run stream - across nodes, or on single nodes.

**both**

- aws eks cpu: all nodes and single nodes

**single nodes**

- aws eks gpu: just single nodes
- aws parallel cluster cpu: just single nodes
- azure aks cpu: just single node
- azure cyclecloud cpu: just single node
- google compute-engine cpu: just single node
- google gke cpu: just single node

**all nodes**

- azure aks gpu:just all nodes
- azure cyclecloud gpu: just across nodes
- google compute-engine gpu: just all nodes
- google gke gpu: just acoss nodes

I looked at the data, and I actually think the way we ran it doesn't matter. It runs on each processor, so we can combine regardless of how many nodes it was run on.

```bash
pip install -r requirements.txt
```

Then:

```bash
python 1-run-analysis.py
```

See the issue [here](https://lc.llnl.gov/gitlab/converged-computing/cross-platform-study/-/issues/1) for discussion of the plots and comparisons to make. TLDR, the differences come down to:
        
- Running on one node vs. an entire set
- Running with -n (processes) specified or not
- Running with OMP_NUM_THREADS or not
- Having data across all sizes, or just one size
- When -n is used, the number being the same (or different) across environments.

I've removed extra environment variables and kept things related to nodes, processes, and threads. From the groups below, here is my proposal for what we can plot / group together:

1. GPU: Azure CycleCloud, Lassen, Azure AKS, Google GKE, and Google Compute Engine all run across nodes and specify -n so I think we can compare them. I don't see OMP_NUM_THREADS anywhere.
2. CPU: We can compare Azure CycleCloud with AWS Parallel Cluster, but only size 32. That should be OK if we just are running on single nodes anyway, but we would want to choose size 32 for CycleCloud to be consistent. Both map 1 ppr per node and use OMP_NUM_THREADS=96
3. CPU: AWS EKS, Azure AKS, Google Compute Engine, and Google GKE also run on one node, but without OMP_NUM_THREADS and also specifying -n. Note that the little n is different - it is 56 for Google and 96 for AWS. I'm not sure if that makes this set not comparable.
