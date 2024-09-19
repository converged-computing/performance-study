# Quicksilver Analysis

I just parse the workload manager wrapper time (for completed runs) and the figure of merit.

```bash
pip install -r requirements.txt
```

```bash
python 1-run-analysis.py
```

## Results

I think this shows us we only have completed GPU runs for Azure CycleCloud.

![data/img/quicksilver-num_segments_over_cycle_tracking_time-cpu.png](data/img/quicksilver-num_segments_over_cycle_tracking_time-cpu.png)
![data/img/quicksilver-num_segments_over_cycle_tracking_time-gpu.png](data/img/quicksilver-num_segments_over_cycle_tracking_time-gpu.png)
![data/img/quicksilver-workload_manager_wrapper_seconds-cpu.png](data/img/quicksilver-workload_manager_wrapper_seconds-cpu.png)
![data/img/quicksilver-workload_manager_wrapper_seconds-gpu.png](data/img/quicksilver-workload_manager_wrapper_seconds-gpu.png)

