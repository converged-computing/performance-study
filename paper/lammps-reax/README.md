# LAMMPS Paper Analysis

For LAMMPS we are interested in m-atom steps per second, for each of CPU and GPU.

```bash
pip install -r requirements.txt
```

Then:

```bash
python 1-run-analysis.py
```

Note that the [1-run-analysis.py](1-run-analysis.py) has a listing of erroneous runs at the top that can be further investigated, most on CycleCloud. 

## Results

Several problem sizes were run.

### Matom Steps Per Second

You can read about this benchmark [here](https://asc.llnl.gov/sites/asc/files/2020-09/CORAL2_Benchmark_Summary_LAMMPS.pdf). We use the exact number reported in the LAMMPS output, which is calculated [in this block](https://github.com/lammps/lammps/blob/59bbc5bcc1104bdb4fb45107cd65b5d4d76dbc00/src/finish.cpp#L133-L172). The calculation does some rounding, but using this value is slightly fewer rounds than the others!

#### Matom Steps Per Second GPU 64 x 32 x 32

![data/img/lammps-reax-matom_steps_per_second-64x32x32-gpu.png](data/img/lammps-reax-matom_steps_per_second-64x32x32-gpu.png)

#### Matom Steps Per Second CPU 64 x 64 x 32

![data/img/lammps-reax-matom_steps_per_second-64x64x32-cpu.png](data/img/lammps-reax-matom_steps_per_second-64x64x32-cpu.png)

