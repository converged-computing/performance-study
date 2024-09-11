# Single Node Benchmark Analysis

The single node benchmark analysis was run across GPU and CPU setups, for each node, to get a fingerprint of the node. While we cannot get an exact identifier to uniquely identify a node, we can get enough metadata to get a sense of the architectures that are provisioned. When we see different models for a common architecture (e.g., Skylake and Haswell for Intel) we call this the supermarket fish problem. 🐟

This analysis will parse and prepare the data into a data frame, and provide simple data exploratory plots that look at it. These steps include:

1. Processing the data from raw results files into data frames
2. Basic plots to compare within and between environments (another repository)

## 1. Process raw data

The first script [1-prepare-data.py](1-prepare-data.py) does not have special Python library requirements and can be run as follows:

```bash
python 1-prepare-data.py
```

The data directory was then moved to [converged-computing/supermarket-fish-problem](https://github.com/converged-computing/supermarket-fish-problem) for further analysis.

