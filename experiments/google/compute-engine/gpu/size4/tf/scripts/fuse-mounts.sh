#!/bin/bash

# --implicit-dirs is only needed if you have existing nested files you want to see
mkdir /mnt/workflow
gcsfuse -o ro,allow_other --implicit-dirs flux-operator-bucket /mnt/workflow

mkdir /mnt/variables
gcsfuse -o rw,allow_other --implicit-dirs llnl-flux_variables /mnt/variables
