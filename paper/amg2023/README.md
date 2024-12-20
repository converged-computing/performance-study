# AMG2023 Paper Analysis

For this benchmark we are primarily interested in the FOM (figure of merit) at the bottom so that is what I'll parse and plot. You need:

```bash
pip install -r requirements.txt
```

Then:

```bash
python 1-run-analysis.py
```

Note that the [1-run-analysis.py](1-run-analysis.py) has a listing of erroneous runs at the top that can be further investigated, most on CycleCloud. I was conservative to not remove extra runs - including runs that were done without the shared memory fix or a placement group or efa (and later redone). We can adjust these for paper figures, but I'm leaving now out of interest for what it looks like.

## Results

### FOM Overall

> Figure of Merit (FOM): nnz_AP / (Setup Phase Time + 3 * Solve Phase Time)

#### FOM Overall CPU

![data/img/amg2023-fom_overall-cpu.png](data/img/amg2023-fom_overall-cpu.png)

#### FOM Overall GPU

![data/img/amg2023-fom_overall-gpu.png](data/img/amg2023-fom_overall-gpu.png)
