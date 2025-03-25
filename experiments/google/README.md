# Google Cloud Experiments

This directory will hold experiments for Google Cloud. 

- [gke/cpu](gke/cpu): CPU experiments for Google Kubernetes Engine
- [gke/gpu](gpu/gpu): GPU experiments for Google Kubernetes Engine

## OSU Benchmarks

Note that for our first experiments, we ran OSU across sizes, however we made the mistake of using flux submit for the GPU runs, which isn't blocking, and meant that osu latency would interfere with bandwidth. To fix this we re-ran GPU for sizes 16 nodes for each of Compute Engine and GKE. This size is what should be used for data analysis.
