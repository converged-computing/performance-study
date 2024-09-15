# LAMMPS Analysis

For this benchmark we are primarily interested in the wall time and CPU utilization, but we will also parse and save the full result.

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

### CPU Utilization

> As reported by LAMMPS

#### CPU Utilization for GPU 64 x 32 x 32

![data/img/lammps-reax-cpu_utilization-64x32x32-gpu.png](data/img/lammps-reax-cpu_utilization-64x32x32-gpu.png)

#### CPU Utilization for GPU 64 x 64 x 32

![data/img/lammps-reax-cpu_utilization-64x64x32-gpu.png](data/img/lammps-reax-cpu_utilization-64x64x32-gpu.png)

#### CPU Utilization for CPU 64 x 32 x 32

![data/img/lammps-reax-cpu_utilization-64x64x32-cpu.png](data/img/lammps-reax-cpu_utilization-64x64x32-cpu.png)

### Workload Manager Wrapper Seconds

#### Wrapper Time Seconds GPU 64 x 32 x 32

![data/img/lammps-reax-seconds-64x32x32-gpu.png](data/img/lammps-reax-seconds-64x32x32-gpu.png)

#### Wrapper Time Seconds GPU 64 x 64 x 32

![data/img/lammps-reax-seconds-64x64x32-gpu.png](data/img/lammps-reax-seconds-64x64x32-gpu.png)

#### Wrapper Time Seconds CPU 64 x 64 x 32

![data/img/lammps-reax-seconds-64x64x32-cpu.png](data/img/lammps-reax-seconds-64x64x32-cpu.png)

### Wall Time LAMMPS

#### Wall Time LAMMPS GPU 64 x 32 x 32

![data/img/lammps-reax-wall_time-64x32x32-gpu.png](data/img/lammps-reax-wall_time-64x32x32-gpu.png)

#### Wall Time LAMMPS GPU 64 x 64 x 32

![data/img/lammps-reax-wall_time-64x64x32-gpu.png](data/img/lammps-reax-wall_time-64x64x32-gpu.png)

#### Wall Time LAMMPS CPU 64 x 64 x 32

![data/img/lammps-reax-wall_time-64x64x32-cpu.png](data/img/lammps-reax-wall_time-64x64x32-cpu.png)
