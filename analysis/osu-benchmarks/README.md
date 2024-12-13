# OSU Benchmarks Analysis

This will generate plots for the OSU benchmarks. No surprise there.

```bash
pip install -r requirements.txt
```

Then:

```bash
python 1-run-analysis.py

# On premises
python 1-run-analysis.py --on-premises
```

This was immensely hard to parse, but I did my best. Nuances of the different runs are included below
and in the script comments.

## Results

### AllReduce

> Collections benchmark

#### AllReduce CPU

![data/img/osu_allreduce_size-256_cpu.png](data/img/osu_allreduce_size-256_cpu.png)
![data/img/osu_allreduce_size-128_cpu.png](data/img/osu_allreduce_size-128_cpu.png)
![data/img/osu_allreduce_size-64_cpu.png](data/img/osu_allreduce_size-64_cpu.png)
![data/img/osu_allreduce_size-32_cpu.png](data/img/osu_allreduce_size-32_cpu.png)

#### AllReduce GPU

![data/img/osu_allreduce_size-32_gpu.png](data/img/osu_allreduce_size-32_gpu.png)
![data/img/osu_allreduce_size-16_gpu.png](data/img/osu_allreduce_size-16_gpu.png)
![data/img/osu_allreduce_size-8_gpu.png](data/img/osu_allreduce_size-8_gpu.png)
![data/img/osu_allreduce_size-4_gpu.png](data/img/osu_allreduce_size-4_gpu.png)

### Bandwidth

> Point to point benchmark

#### Bandwidth CPU

![data/img/osu_bw_size-256_cpu.png](data/img/osu_bw_size-256_cpu.png)
![data/img/osu_bw_size-128_cpu.png](data/img/osu_bw_size-128_cpu.png)
![data/img/osu_bw_size-64_cpu.png](data/img/osu_bw_size-64_cpu.png)
![data/img/osu_bw_size-32_cpu.png](data/img/osu_bw_size-32_cpu.png)

#### Bandwidth GPU

Note that Google GKE was run without the cuda flags, didn't work. Those results do not use the GPU.

![data/img/osu_bw_size-32_gpu.png](data/img/osu_bw_size-32_gpu.png)
![data/img/osu_bw_size-16_gpu.png](data/img/osu_bw_size-16_gpu.png)
![data/img/osu_bw_size-8_gpu.png](data/img/osu_bw_size-8_gpu.png)
![data/img/osu_bw_size-4_gpu.png](data/img/osu_bw_size-4_gpu.png)

### Latency

> Point to point benchmark

#### Latency CPU

![data/img/osu_latency_size-256_cpu.png](data/img/osu_latency_size-256_cpu.png)
![data/img/osu_latency_size-128_cpu.png](data/img/osu_latency_size-128_cpu.png)
![data/img/osu_latency_size-64_cpu.png](data/img/osu_latency_size-64_cpu.png)
![data/img/osu_latency_size-32_cpu.png](data/img/osu_latency_size-32_cpu.png)

#### Latency GPU

![data/img/osu_latency_size-16_gpu.png](data/img/osu_latency_size-16_gpu.png)
![data/img/osu_latency_size-32_gpu.png](data/img/osu_latency_size-32_gpu.png)
![data/img/osu_latency_size-4_gpu.png](data/img/osu_latency_size-4_gpu.png)
![data/img/osu_latency_size-8_gpu.png](data/img/osu_latency_size-8_gpu.png)

Note that Google GKE was run without the cuda flags, didn't work. Those results do not use the GPU.


