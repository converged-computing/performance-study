#!/usr/bin/env python3

import argparse
import os
import re
import sys
import seaborn as sns
import numpy as np
import matplotlib.pylab as plt

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="muted")
flierprops = {"marker": "o", "markersize": 1}


def get_parser():
    parser = argparse.ArgumentParser(
        description="Run analysis",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--root",
        help="root directory with experiments",
        default=os.path.join(root, "experiments"),
    )
    parser.add_argument(
        "--out",
        help="directory to save parsed results",
        default=os.path.join(here, "data"),
    )
    return parser


def main():
    """
    Find application result files to parse.
    """
    parser = get_parser()
    args, _ = parser.parse_known_args()

    # Output images and data
    outdir = os.path.abspath(args.out)
    indir = os.path.abspath(args.root)
    args.on_premises = True
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories (this will include stream-cuda)
    files = ps.find_inputs(indir, "stream", args.on_premises)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


def parse_item(item):
    """
    Parse individual results from an item.
    Each (I think) is a node or core, and it's OK we ran these
    a little differently. A complete result has these four fields
    I think, and we can use the "best rate" MB/s as the metric we
    care about:

    -------------------------------------------------------------
    Function    Best Rate MB/s  Avg time     Min time     Max time
    Copy:           11271.6     0.028207     0.014195     0.031694
    Scale:           5904.2     0.042100     0.027099     0.046774
    Add:             8845.0     0.056286     0.027134     0.066129
    Triad:           9128.6     0.056622     0.026291     0.067381
    """
    # Note that these are interleaved, so we can't always associate them
    # together as a group.
    metrics = []
    lines = item.split("\n")
    for line in lines:
        if re.search("(Copy|Scale|Add|Triad):", line):
            values = [x for x in line.split(" ") if x.strip()]
            value = float(values[1])
            label = values[0].replace(":", "").strip()
            metrics.append({"label": label, "value": value})

    return metrics


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ResultParser("stream")

    # For flux we can save jobspecs and other event data
    data = {}
    result_counts = set()

    # Since the data is huge, saving to dfs as we go is really slow
    items = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:
        # Underscore means skip, also skip configs and runs without efa
        # runs with google and shared memory were actually slower...
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        exp = ps.ExperimentNameParser(filename, indir)
        if exp.prefix not in data:
            data[exp.prefix] = []

        # Size 2 was typically testing
        if exp.size == 2:
            continue

        # Calculate number of gpus from nodes
        number_gpus = 0
        if exp.env_type == "gpu":
            number_gpus = (
                (exp.size * 4) if "on-premises" in filename else (exp.size * 8)
            )

        # If gpu and lassen, must be stream-cuda
        if (
            exp.env_type == "gpu"
            and "lassen" in filename
            and "stream-cuda" not in filename
        ):
            continue

        # We can't use Dane for comparison to anything now
        if "dane" in filename:
            continue

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size, gpu_count=number_gpus)
        exp.show()

        # Now we can read each result file to get metrics.
        results = list(ps.get_outfiles(filename))
        for result in results:
            # EKS CPU had single runs except for largest had multiple at size 256, 32
            if exp.env_type == "cpu" and "eks" in filename and "-node-" not in result:
                continue

            # Basename that start with underscore are test or otherwise should not be included
            if os.path.basename(result).startswith("_"):
                continue
            item = ps.read_file(result)
            
            # These are what we use in our paper
            if (exp.size == 32 and exp.env_type == "cpu") or (exp.size == 64 and exp.env_type == "gpu"):
                result_counts.add(result)

            # If this is a flux run, we have a jobspec and events here
            if "JOBSPEC" in item:
                item, _, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            elif "on-premises" in filename:
                metadata = {}

            else:
                metadata = {}
                item = ps.remove_slurm_duration(item)

            # Let's skip adding this - the runs might not be comparable.
            # p.add_result("workload_manager_wrapper_seconds", duration)

            # For now, let's assume that the benchmark runs across
            # cores, regardless of how many we chose. Each is a valid
            # sample for the cloud / environment. Note that these should
            # be labeled "best_rate_X_mb_per_second"
            for result in parse_item(item):
                label = result["label"]
                if label not in items:
                    items[label] = {}
                if exp.env_type not in items[label]:
                    items[label][exp.env_type] = {}
                if exp.size not in items[label][exp.env_type]:
                    items[label][exp.env_type][exp.size] = {}
                if exp.prefix not in items[label][exp.env_type][exp.size]:
                    items[label][exp.env_type][exp.size][exp.prefix] = []

                # label -> env -> size -> experiment -> lists of values
                items[label][exp.env_type][exp.size][exp.prefix].append(result["value"])

    print(f"Done parsing {len(result_counts)} stream results!")
    ps.write_json(items, os.path.join(outdir, "stream-results.json"))
    ps.write_json(data, os.path.join(outdir, "stream-parsed.json"))
    return items


def plot_stream_metric(v, label, img_outdir, save_prefix):
    """
    Common function to generate boxplot and histogram
    """
    # Create the figure and axes
    plt.figure(figsize=(8, 6))
    fig, ax = plt.subplots()
    bplot = ax.boxplot(
        list(v.values()),
        positions=list(range(1, len(v) + 1)),
        flierprops=flierprops,
        widths=0.6,
        patch_artist=True,
    )

    colors = {}
    for cloud in v.keys():
        colors[cloud] = ps.match_color(cloud)
    colors = list(colors.values())
    for patch, color in zip(bplot["boxes"], colors):
        patch.set_facecolor(color)

    # Important: this assumes the listing of keys/values lines up
    labels = [x.rsplit("/", 1)[0] for x in v.keys()]
    ax.set_xticklabels(labels)
    ax.set_ylabel(label)
    title = f'Stream Best Rate "{label}" MB/s CPU'
    ax.set_title(title)
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(os.path.join(img_outdir, f"{save_prefix}-boxplot.png"))
    plt.clf()
    plt.close()


def plot_results(results, outdir):
    """
    Plot analysis results
    """
    # Pandas is too slow here, so we will assemble vectors for each thing
    # across the environments. It's harder, but I hope will work.
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Within a setup, compare between experiments for GPU and cpu
    for label, env_types in results.items():
        for env_type, sizes in env_types.items():
            size_list = list(sizes.keys())
            
            # Create a vector for each environment, with each entry (list)
            # a size from least to greatest.
            vectors = {}

            # CPU gets split into two groups
            # Other single runs (sizes 64/128 combined) that don't have threads set
            vectors_single = {}

            # Azure and CycleCloud with OMP_NUM_THREADS at size 32
            vectors_single_threads = {}

            for size in size_list:
                for cloud_env, values in sizes[size].items():
                    # Truncate the size - we just need <cloud>/<env>/<env_type>
                    experiment = os.path.dirname(cloud_env)

                    # 2. CPU: We can compare Azure CycleCloud with AWS Parallel Cluster, but only size 32.
                    # That should be OK if we just are running on single nodes anyway, but we would want to choose size 32
                    # for CycleCloud to be consistent. Both map 1 ppr per node and use `OMP_NUM_THREADS=96`
                    if env_type == "cpu" and (
                        "cyclecloud" in experiment or "parallel-cluster" in experiment
                    ):
                        if size != 32:
                            continue
                        if experiment not in vectors_single:
                            vectors_single_threads[experiment] = []
                        # This should only be one list
                        vectors_single_threads[experiment].append(values)
                        if label == "Triad":
                            print(f"CPU for {label} size {size} experiment {experiment}: {np.median(values)}: std {np.std(values)}")

                    # 3. CPU: AWS EKS, Azure AKS, Google Compute Engine, and Google GKE also run on one node,
                    # but without `OMP_NUM_THREADS` and also specifying `-n`. Note that the little n is different
                    # it is 56 for Google and 96 for AWS. I'm not sure if that makes this set not comparable.
                    # For this setup, we are missing EKS single node at size 256 and 32. Let's JUST
                    # use sizes 64 across environments to be consistent.
                    elif env_type == "cpu" and re.search(
                        "(eks|aks|compute-engine|gke)", experiment
                    ):
                        if size != 64:
                            continue
                        if experiment not in vectors_single:
                            vectors_single[experiment] = []
                        # This will add only size 64
                        vectors_single[experiment] += values
                        if label == "Triad":
                            print(f"CPU for {label} size {size} experiment {experiment}: {np.median(values)}: std {np.std(values)}")

                    # 1. GPU: Azure CycleCloud, Lassen, Azure AKS, Google GKE, and Google Compute Engine all
                    # run across nodes and specify -n so I think we can compare them. I don't see OMP_NUM_THREADS anywhere.
                    elif env_type == "gpu" and re.search(
                        "(lassen|aks|cyclecloud|gke|compute-engine)", experiment
                    ):
                        # This would be, for example, all the values for
                        # a specific environment and size. Then the
                        # next append will be the next size
                        if experiment not in vectors:
                            vectors[experiment] = []
                        vectors[experiment].append(values)
                        
                        # Reporting size 32 in paper
                        if size == 32 and label == "Triad":
                            print(f"GPU for {label} size {size} for {env_type} and {experiment} has median {np.median(values)} std {np.std(values)}")

            if env_type == "cpu":
                suffix = "single-node-no-omp-threads-mb-per-second"
                save_prefix = f"best-rate-{label}-{env_type}-{suffix}"
                # This handles a histogram and boxplot (second is better I think)
                plot_stream_metric(vectors_single, label, img_outdir, save_prefix)

                # This should be only 2 environments, size 32
                fig, ax = plt.subplots()
                offsets = [-0.25, 0.25]
                for experiment, values in vectors_single_threads.items():
                    positions = np.array(np.arange(len(values))) * 2.0 + offsets.pop(0)
                    plot = plt.boxplot(
                        values,
                        positions=positions,
                        flierprops=flierprops,
                        widths=0.3,
                        patch_artist=True,
                        showfliers=False,
                    )
                    ps.set_group_color_properties(
                        plot, ps.match_color(experiment), experiment
                    )

                # set the x label values, the sizes
                ax.set_xticklabels(list(vectors_single_threads.keys()))
                plt.title(f'Stream Best Rate "{label}" MB/s {env_type}', fontsize=16)
                frame = plt.gca()
                frame.axes.xaxis.set_ticklabels([])
                plt.tight_layout()
                plt.savefig(
                    os.path.join(
                        img_outdir,
                        f"best-rate-{label}-{env_type}-single-node-omp-threads-mb-per-second.png",
                    )
                )
                plt.close()

            elif env_type == "gpu":
                # We do one plot excluding azure cyclecloud because (we think) the GPU setting
                # being inconsistent led to huge variation, and you can't see the others in
                # the plot
                plot_stream_gpu(vectors, label, img_outdir, size_list)
                plot_stream_gpu(
                    vectors,
                    label,
                    img_outdir,
                    size_list,
                    exclude=["azure/cyclecloud/gpu"],
                )


def plot_stream_gpu(vectors, label, img_outdir, size_list, exclude=None):
    """
    Plot stream GPU can handle removing
    """
    offsets = [-0.75, -0.5, -0.25, 0.25, 0.5, 0.75]
    if exclude is not None:
        offsets = offsets[len(exclude) :]
    for experiment, values in vectors.items():
        if exclude is not None and experiment in exclude:
            continue
        positions = np.array(np.arange(len(values))) * 2.0 + offsets.pop(0)
        plot = plt.boxplot(
            values,
            positions=positions,
            widths=0.3,
            flierprops=flierprops,
            patch_artist=True,
            showfliers=False,
        )
        ps.set_group_color_properties(plot, ps.match_color(experiment), experiment)

    # set the x label values, the sizes
    plt.xticks(np.arange(0, len(size_list) * 2, 2), size_list)
    plt.title(f'Stream Best Rate "{label}" GB/s GPU', fontsize=16)
    if exclude is not None:
        excluded = "+".join([x.replace("/", "-") for x in exclude])
        label = f"{label}-without-{excluded}"
    plt.savefig(os.path.join(img_outdir, f"best-rate-{label}-gpu-mb-per-second.png"))
    plt.close()


if __name__ == "__main__":
    main()
