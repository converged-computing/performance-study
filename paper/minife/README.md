# Minife Paper Analysis

Minife is fairly straight forward - it's run across nodes, and we did a run of size 230 for nx,ny,nz. For some clouds that seemed really fast I did an additional problem size of 640. This is what the output looks like:

```console
 OMP_NUM_THREADS=1
      creating/filling mesh...0.027025s, total time: 0.027025
generating matrix structure...0.0264151s, total time: 0.0534401
         assembling FE data...0.00221896s, total time: 0.0556591
      imposing Dirichlet BC...0.000389099s, total time: 0.0560482
      imposing Dirichlet BC...1.90735e-06s, total time: 0.0560501
making matrix indices local...0.0480671s, total time: 0.104117
Starting CG solver ... 
Initial Residual = 231.002
Iteration = 20   Residual = 0.0526728
Iteration = 40   Residual = 0.0289731
Iteration = 60   Residual = 0.00257705
Iteration = 80   Residual = 0.00338564
Iteration = 100   Residual = 3.27294e-05
Iteration = 120   Residual = 9.67497e-05
Iteration = 140   Residual = 1.15585e-05
Iteration = 160   Residual = 3.77902e-07
Iteration = 180   Residual = 7.46764e-08
Iteration = 200   Residual = 7.93768e-09
Final Resid Norm: 7.93768e-09
```
But we just care about one FOM reported in an associated YAML file:

> miniFE writes results to a YAML file which should be saved for reporting the figure of merit (FOM). From the YAML files, report "Total CG Mflops" as the FOM for miniFE.

```bash
pip install -r requirements.txt
```

Then:

```bash
python 1-run-analysis.py
```
