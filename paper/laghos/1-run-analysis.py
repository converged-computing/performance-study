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

sns.set_theme(style="whitegrid", palette="muted")

# These are files I found erroneous - no result, or incomplete result
errors = [
    # No results (or run at all)
    "azure/cyclecloud/cpu/size32/results/laghos/laghos-32n-174-iter-1.out",
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

    # We absolutely want on premises results here
    args.on_premises = True

    # Output images and data
    outdir = os.path.abspath(args.out)
    indir = os.path.abspath(args.root)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories (anything with lammps-reax)
    # lammps directories are usually snap
    files = ps.find_inputs(indir, "laghos", args.on_premises)
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
    p = ps.ResultParser("laghos")

    # For flux we can save jobspecs and other event data
    data = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        # I don't know if these are results or testing, skipping for now
        # They are from aws parallel-cluster CPU
        if os.path.join("experiment", "data") in filename:
            continue

        exp = ps.ExperimentNameParser(filename, indir)
        if exp.prefix not in data:
            data[exp.prefix] = []

        # Size 2 was typically testing, and others were erroneous across setups
        if exp.size not in [32, 64]:
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

            item = ps.read_file(result)

            # If this is a flux run, we have a jobspec and events here
            duration = None
            if "JOBSPEC" in item:
                item, duration, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)
                p.add_result("duration", duration)
            else:
                try:
                    duration = ps.parse_slurm_duration(item)
                except:
                    print(f"{filename} does not have a wrapped duration.")

            # Major kernels total rate (megadofs x time steps / second): 2210.6651277298
            total_rate = [
                x for x in item.split("\n") if "Major kernels total rate" in x
            ]
            if not total_rate:
                print(f"{result} does not have a total rate")
                continue
            total_rate = total_rate[0]
            total_rate = float(total_rate.split(" ")[-1])
            p.add_result("total_rate", total_rate)

    print("Done parsing laghos results!")
    p.df.to_csv(os.path.join(outdir, "laghos-results.csv"))
    ps.write_json(data, os.path.join(outdir, "laghos-parsed.json"))
    return p.df


def plot_results(df, outdir, non_anon=True):
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
    # cloud_colors = ps.get_cloud_colors(df.experiment.unique())

    data_frames = {}
    for env in df.env_type.unique():
        # We could not build the gpu container
        if env == "gpu":
            continue
        subset = df[df.env_type == env]
        # Make a plot for seconds runtime, and each FOM set.
        # We can look at the metric across sizes, colored by experiment
        for metric in subset.metric.unique():
            # We are only plotting total rate
            if "total_rate" not in metric:
                continue
            metric_df = subset[subset.metric == metric]
            data_frames[env] = metric_df
            print(
                metric_df.groupby(
                    ["env_type", "env", "cloud", "experiment"]
                ).value.mean()
            )
            print(
                metric_df.groupby(
                    ["env_type", "env", "cloud", "experiment"]
                ).value.std()
            )
            title = " ".join([x.capitalize() for x in metric.split("_")])
            print(title)

    # We are going to put the plots together, and the colors need to match!
    cloud_colors = {}
    for cloud in df.experiment.unique():
        cloud_colors[cloud] = ps.match_color(cloud)

    fig, axes = plt.subplots(1, 1, sharey=True, figsize=(8, 6))
    sns.set_style("whitegrid")
    sns.barplot(
        data_frames["cpu"],
        ax=axes,
        x="nodes",
        y="value",
        hue="experiment",
        hue_order=[
            "google/gke/cpu",
            "azure/cyclecloud/cpu",
            "aws/eks/cpu",
            "google/compute-engine/cpu",
            "aws/parallel-cluster/cpu",
            "on-premises/a/cpu",
        ],
        palette=cloud_colors,
        order=[32, 64],
    )
    axes.set_title("Laghos Major Kernels Total Rate (CPU)", fontsize=14)
    axes.set_ylabel("Megadofs By Timesteps / Second", fontsize=14)
    axes.set_xlabel("Nodes", fontsize=14)

    # Remove legend title, don't need it
    handles, labels = axes.get_legend_handles_labels()
    axes.legend(handles=handles, labels=labels)

    plt.tight_layout()
    plt.savefig(os.path.join(img_outdir, "laghos-major-kernels-total-rate-cpu.svg"))
    plt.clf()


if __name__ == "__main__":
    main()
