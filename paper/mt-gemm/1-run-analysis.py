#!/usr/bin/env python3

import argparse
import os
import re
import sys

import matplotlib.pylab as plt
import seaborn as sns

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="pastel")

# These are files I found erroneous - no result, or incomplete result
errors = []
error_regex = "(%s)" % "|".join(errors)


def get_parser():
    parser = argparse.ArgumentParser(
        description="Run analysis",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--non-anon",
        help="Generate non-anon",
        action="store_true",
        default=False,
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
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories
    args.on_premises = True
    files = ps.find_inputs(indir, "mt-gemm", args.on_premises)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


def parse_cpu_gemm(item):
    """
    Parse CPU gemm

    Performance= 370.99 GFlop/s, Time= 5.391 msec, Size= 2000000000 Ops\n'
    """
    metrics = {}
    for line in item.strip().split(","):
        if "Performance" in line:
            parts = [x for x in line.split(" ") if x]
            metrics["performance_gflops_per_second"] = float(parts[1])
    return metrics


def parse_gpu_gemm(item):
    """
    Parse GPU gemm
    """
    metrics = {}
    for line in item.split("\n"):
        # We are only plotting this for the paper
        if "GFLOP/s rate" in line:
            seconds = line.split(":")[-1].strip().replace("GF/s", "").strip()
            metrics["gflops_per_second_rate"] = float(seconds)
    return metrics


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ResultParser("mt-gemm")

    # For flux we can save jobspecs and other event data
    data = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:
        # Underscore means skip, also skip configs and runs without efa
        # runs with google and shared memory were actually slower...
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        # For GKE size 32 I ran both the 1k and 9k sizes. 9k seemed to work here,
        # but would not work anywhere else, so we can't use it.
        if "mt-gemm-9k" in filename:
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

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size, gpu_count=number_gpus)
        exp.show()

        # Now we can read each result file to get metrics.
        results = list(ps.get_outfiles(filename))
        for result in results:
            # Skip over found erroneous results
            if errors and re.search(error_regex, result):
                print(f"Skipping {result} due to known missing result or error.")
                continue

            # Basename that start with underscore are test or otherwise should not be included
            if os.path.basename(result).startswith("_"):
                continue
            item = ps.read_file(result)

            # If this is a flux run, we have a jobspec and events here
            if "on-premises" in result:
                metadata = {}
                item = item.split("logout")[0]
                print(result)
                print(item)

            elif "JOBSPEC" in item:
                item, _, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            else:
                metadata = {}
                item = ps.remove_slurm_duration(item)

            # Add the duration in seconds
            # Note - different output for GPU vs. CPU!
            if exp.env_type == "gpu":
                metrics = parse_gpu_gemm(item)
            else:
                metrics = parse_cpu_gemm(item)
            for metric, value in metrics.items():
                p.add_result(metric, value)

    print("Done parsing mt-gemm results!")
    p.df.to_csv(os.path.join(outdir, "mt-gemm-results.csv"))
    ps.write_json(data, os.path.join(outdir, "mt-gemm-parsed.json"))
    return p.df


def plot_results(df, outdir, non_anon=False):
    """
    Plot analysis results
    """
    # Let's get some shoes! Err, plots.
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # For anonymization
    if not non_anon:
        df["experiment"] = df["experiment"].str.replace(
            "on-premises/lassen", "on-premises/b"
        )
        df["experiment"] = df["experiment"].str.replace(
            "on-premises/dane", "on-premises/a"
        )

    # We are going to put the plots together, and the colors need to match!
    cloud_colors = {}
    for cloud in df.experiment.unique():
        cloud_colors[cloud] = ps.match_color(cloud)

    # Within a setup, compare between experiments for GPU and cpu
    data_frames = {}
    for env in df.env_type.unique():
        subset = df[df.env_type == env]

        # Make a plot for each metric
        for metric in subset.metric.unique():
            print(metric, env)
            if "gflops" not in metric.lower():
                continue
            metric_df = subset[subset.metric == metric]
            data_frames[env] = metric_df

    fig = plt.figure(figsize=(18, 3))
    gs = plt.GridSpec(1, 3, width_ratios=[2, 2, 1])
    axes = []
    axes.append(fig.add_subplot(gs[0, 0]))
    axes.append(fig.add_subplot(gs[0, 1]))
    axes.append(fig.add_subplot(gs[0, 2]))

    sns.set_style("whitegrid")
    sns.barplot(
        data_frames["cpu"],
        ax=axes[0],
        x="nodes",
        y="value",
        hue="experiment",
        hue_order=[
            "aws/eks/cpu",
            "aws/parallel-cluster/cpu",
            "google/gke/cpu",
            "azure/aks/cpu",
            "google/compute-engine/cpu",
        ],
        err_kws={'color': 'darkred'},           
        palette=cloud_colors,
        dodge=True,
        order=[32, 64, 128, 256],
    )
    axes[0].set_title("MT-GEMM Metric GFlops/Second (CPU)", fontsize=12)
    axes[0].set_ylabel("GFlops/Second", fontsize=12)
    axes[0].set_xlabel("Nodes", fontsize=12)

    sns.barplot(
        data_frames["gpu"],
        ax=axes[1],
        x="gpu_count",
        y="value",
        hue="experiment",
        err_kws={'color': 'darkred'},   
        hue_order=[
            "azure/cyclecloud/gpu",
            "on-premises/b/gpu",
            "google/gke/gpu",
            "aws/eks/gpu",
            "azure/aks/gpu",
            "google/compute-engine/gpu",
        ],
        palette=cloud_colors,
        order=[32, 64, 128, 256],
        dodge=True,
    )
    axes[1].set_title("MT-GEMM Metric GFlops/Second (GPU)", fontsize=14)
    axes[1].set_ylabel("")
    axes[1].set_xlabel("GPU Count", fontsize=14)

    handles, labels = axes[1].get_legend_handles_labels()
    labels = ["/".join(x.split("/")[0:2]) for x in labels]
    axes[2].legend(
        handles, labels, loc="center left", bbox_to_anchor=(-0.1, 0.5), frameon=False
    )

    for ax in axes[0:2]:
        ax.get_legend().remove()
    axes[2].axis("off")

    plt.tight_layout()
    plt.savefig(os.path.join(img_outdir, "mtgemm-cpu-gpu.svg"))
    plt.clf()

    print(f'Total number of CPU datum: {data_frames["cpu"].shape[0]}')
    print(f'Total number of GPU datum: {data_frames["gpu"].shape[0]}')

if __name__ == "__main__":
    main()
