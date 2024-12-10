# AMG2023 Analysis

For this benchmark we are primarily interested in the FOM (figure of merit) at the bottom so that is what I'll parse and plot. You need:

```bash
pip install -r requirements.txt
```

Then:

```bash
python 1-run-analysis.py

# Add on premises data (for local only)
python 1-run-analysis.py --on-premises
```

Note that the [1-run-analysis.py](1-run-analysis.py) has a listing of erroneous runs at the top that can be further investigated, most on CycleCloud. I was conservative to not remove extra runs - including runs that were done without the shared memory fix or a placement group or efa (and later redone). We can adjust these for paper figures, but I'm leaving now out of interest for what it looks like.

## Results

### FOM Overall

> Figure of Merit (FOM): nnz_AP / (Setup Phase Time + 3 * Solve Phase Time)

#### FOM Overall CPU

![data/img/amg2023-fom_overall-cpu.png](data/img/amg2023-fom_overall-cpu.png)

#### FOM Overall GPU

![data/img/amg2023-fom_overall-gpu.png](data/img/amg2023-fom_overall-gpu.png)

### FOM Setup

> FOM_Setup: nnz_AP / Setup Phase Time

#### FOM Setup CPU

![data/img/amg2023-fom_setup-cpu.png](data/img/amg2023-fom_setup-cpu.png)

#### FOM Setup GPU

![data/img/amg2023-fom_setup-gpu.png](data/img/amg2023-fom_setup-gpu.png)

### FOM Solve

> FOM_Solve: nnz_AP * iterations / Solve Phase Time

#### FOM Solve CPU

![data/img/amg2023-fom_solve-cpu.png](data/img/amg2023-fom_solve-cpu.png)

#### FOM Solve GPU

![data/img/amg2023-fom_solve-gpu.png](data/img/amg2023-fom_solve-gpu.png)

### Wall Time

> seconds

For slurm this is the job wrapping time, and for flux it is shell.start to done

#### Wall Time CPU

![data/img/amg2023-workload_manager_wrapper_seconds-cpu.png](data/img/amg2023-workload_manager_wrapper_seconds-cpu.png)

#### Wall Time GPU

![data/img/amg2023-workload_manager_wrapper_seconds-gpu.png](data/img/amg2023-workload_manager_wrapper_seconds-gpu.png)

