# Kripke Paper Analysis

For the paper, we are interested in Grind time. 

```console
Figures of Merit
================

  Throughput:         2.683674e+10 [unknowns/(second/iteration)]
  Grind time :        3.726235e-11 [(seconds/iteration)/unknowns]
  Sweep efficiency :  17.43900 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 4932501504
```

We strong scaled it (and will just present cpu, as gpu was oversubscribed).

```bash
pip install -r requirements.txt
```

Then:

```bash
python 1-run-analysis.py
```
