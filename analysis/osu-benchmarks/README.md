# OSU Benchmarks Analysis

This will generate plots for the OSU benchmarks. No surprise there.

```bash
pip install -r requirements.txt
```

Then:

```bash
python 1-run-analysis.py
```

This was immensely hard to parse, but I did my best. Nuances of the different runs are included below
and in the script comments.

## Results

### AllReduce

> Collections benchmark

#### AllReduce CPU

![data/img/osu_allreduce_cpu.png](data/img/osu_allreduce_cpu.png)

#### AllReduce GPU

![data/img/osu_allreduce_gpu.png](data/img/osu_allreduce_gpu.png)

### Bandwidth

> Point to point benchmark

#### Bandwidth CPU

![data/img/osu_bw_cpu.png](data/img/osu_bw_cpu.png)

#### Bandwidth GPU

Note that Google GKE was run without the cuda flags, didn't work. Those results do not use the GPU.

![data/img/osu_bw_gpu.png](data/img/osu_bw_gpu.png)

### Latency

> Point to point benchmark

#### Latency CPU

![data/img/osu_latency_cpu.png](data/img/osu_latency_cpu.png)

#### Latency GPU

Note that Google GKE was run without the cuda flags, didn't work. Those results do not use the GPU.

![data/img/osu_latency_gpu.png](data/img/osu_latency_gpu.png)
