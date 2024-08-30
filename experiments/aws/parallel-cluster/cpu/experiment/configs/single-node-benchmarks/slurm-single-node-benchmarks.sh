#!/bin/bash

sudo /shared/bin/singularity exec /shared/containers/metric-single-node_cpu-zen4-tmpfile.sif \
    /bin/bash /entrypoint.sh > ../../data/single-node-benchmarks/$( hostname )-single-node.out