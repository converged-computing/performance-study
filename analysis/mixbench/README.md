# Mixbench Analysis

Mixbench can be run in a few ways:

- one sample per node
- across nodes
- wrapper or without wrappe

and we first need to catalog how each was done.

## Catalog

I'll group these based on similarity

**5x on 2 nodes, no wrapper mixbench-cpu 32**

- aws eks CPU: run 5x on 2 nodes without wrapper, mixbench-cpu 32
- google compute-engine CPU: run 5x on 2 nodes without wrapper, mixbench-cpu 32

**mixbench-cuda (no wrapper) 32 across all nodes**

- google compute-engine GPU: run 5x across all nodes without wrapper, mixbench-cuda 32

**no wrapper (mixbench-cpu 32) each single node**

- google gke CPU: run 5x on each single node with mixbench-cpu 32
- azure aks CPU: run 5x without wrapper, mixbench-cpu 32 each single node
- azure cyclecloud CPU: run once without wrapper mixbench-cpu 32 on each node

**wrapper 32 across all nodes**

- azure aks GPU: run 5x across all nodes with wrapper 32 and GPU
- azure cyclecloud GPU: run across nodes with wrapper 32
- google gke GPU: run across all nodes with wrapper 32

**wrapper 32 on each single node**

- aws eks GPU: run once with wrapper 32 on each individual node
- aws parallel-cluster CPU: run once with wrapper 32 on each node

I don't know if it's possible to derive anything meaningful, comparison wise, from the above. I think the wrapper turned out to be problematic too because it wouldn't hit all GPU, which is why I used mixbench-cuda directly when I saw that on Google Compute Engine.
