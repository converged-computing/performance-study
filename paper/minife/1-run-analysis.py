#!/usr/bin/env python3

import argparse
import collections
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

sns.set_theme(style="whitegrid", palette="muted")

# These are files I found erroneous - no result, or incomplete result
errors = [
    # Partial result with no end time (and no final value)
    "azure/cyclecloud/cpu/size256/results/minife/minife-256n-4859-iter-3.out",
]
error_regex = "(%s)" % "|".join(errors)


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
        "--non-anon",
        help="Generate non-anon",
        action="store_true",
        default=False,
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

    # Find input directories
    files = ps.find_inputs(indir, "minife", args.on_premises)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir, args.non_anon)


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ProblemSizeParser("minife")

    # For flux we can save jobspecs and other event data
    data = {}

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

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size, gpu_count=number_gpus)
        exp.show()

        # Now we can read each result file to get metrics.
        # results = list(ps.get_outfiles(filename))

        # The FOMs are in these yaml files
        # We mostly care about the foms, the output (terminal) isn't as relevant.
        result_foms = list(ps.get_outfiles(filename, pattern="[.]yaml"))

        for result in result_foms:
            if errors and re.search(error_regex, result):
                print(f"Skipping {result} due to known missing result or error.")
                continue

            # miniFE writes results to a YAML file which should be saved for reporting
            # the figure of merit (FOM). From the YAML files, report "Total CG Mflops" as the FOM for miniFE.
            item = ps.read_yaml(result)

            # Just parse smaller problem size
            dims = item["Global Run Parameters"]["dimensions"]
            if dims["nx"] != 230:
                continue

            problem_size = "230nx-ny-nz"
            fom = item["CG solve"]["Total"]["Total CG Mflops"]
            p.add_result("total_cg_mflops", fom, problem_size)
            p.add_result("duration", item['Total Program Time'], problem_size)

    print("Done parsing minife results!")
    p.df.to_csv(os.path.join(outdir, "minife-results.csv"))
    ps.write_json(data, os.path.join(outdir, "minife-parsed.json"))
    return p.df


def plot_results(df, outdir, non_anon=False):
    """
    Plot analysis results
    """
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

    ps.print_experiment_cost(df, outdir)

    # We are going to put the plots together, and the colors need to match!
    cloud_colors = {}
    for cloud in df.experiment.unique():
        cloud_colors[cloud] = ps.match_color(cloud)

    # Within a setup, compare between experiments for GPU and cpu
    data_frames = {}
    for env in df.env_type.unique():
        subset = df[df.env_type == env]
        for problem_size in subset.problem_size.unique():
            if "230" not in problem_size:
                continue
            ps_df = subset[subset.problem_size == problem_size]

            # Make a plot for each metric
            for metric in ps_df.metric.unique():
                if "mflops" not in metric.lower():
                    continue
                metric_df = ps_df[ps_df.metric == metric]
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
            "azure/aks/cpu",
            "google/gke/cpu",
            "azure/cyclecloud/cpu",
            "aws/parallel-cluster/cpu",
            "google/compute-engine/cpu",
            "aws/eks/cpu",
            #            "on-premises/a/cpu",
        ],
        err_kws={"color": "darkred"},
        palette=cloud_colors,
        order=[32, 64, 128, 256],
    )
    axes[0].set_title("MiniFE Total CG Mflops for CPU", fontsize=14)
    axes[0].set_ylabel("Total CG Mflops", fontsize=14)
    axes[0].set_xlabel("Nodes", fontsize=14)

    print(data_frames["gpu"].experiment.unique())
    sns.barplot(
        data_frames["gpu"],
        ax=axes[1],
        x="gpu_count",
        y="value",
        hue="experiment",
        hue_order=[
            "azure/cyclecloud/gpu",
            #            "on-premises/b/gpu",
            "google/compute-engine/gpu",
            "google/gke/gpu",
            "azure/aks/gpu",
            "aws/eks/gpu",
        ],
        palette=cloud_colors,
        err_kws={"color": "darkred"},
        order=[32, 64, 128, 256],
    )
    axes[1].set_title("MiniFE Total CG Mflops for GPU", fontsize=14)
    axes[1].set_xlabel("GPU Count", fontsize=14)
    axes[1].set_ylabel("")

    handles, labels = axes[1].get_legend_handles_labels()
    labels = ["/".join(x.split("/")[0:2]) for x in labels]
    axes[2].legend(
        handles, labels, loc="center left", bbox_to_anchor=(-0.1, 0.5), frameon=False
    )
    for ax in axes[0:2]:
        ax.get_legend().remove()
    axes[2].axis("off")

    plt.tight_layout()
    plt.savefig(os.path.join(img_outdir, "minife-cpu-gpu.svg"))
    plt.clf()
    print(f'Total number of CPU datum: {data_frames["cpu"].shape[0]}')
    print(f'Total number of GPU datum: {data_frames["gpu"].shape[0]}')


if __name__ == "__main__":
    main()
