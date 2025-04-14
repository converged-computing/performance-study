#!/usr/bin/env python3

import argparse
import collections
import os
import re
import sys

import seaborn as sns

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="muted")

# These are files I found erroneous - no result, or incomplete result
errors = [
    # Only a start time and in error file, mount with fuse, then CANCELLED
    "azure/cyclecloud/cpu/size32/results/kripke/kripke-32n-173-iter-5.out",
]
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

    # We absolutely want on premises results here
    args.on_premises = True

    # Find input directories
    files = ps.find_inputs(indir, "kripke", args.on_premises)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir, args.non_anon)


def parse_kripke_foms(item):
    """
    Figures of Merit
    ================

      Throughput:         2.683674e+10 [unknowns/(second/iteration)]
      Grind time :        3.726235e-11 [(seconds/iteration)/unknowns]
      Sweep efficiency :  17.43900 [100.0 * SweepSubdomain time / SweepSolver time]
      Number of unknowns: 4932501504
    """
    metrics = {}
    for line in item.split("\n"):
        if "Grind time" in line:
            parts = [x for x in line.replace(":", "").split(" ") if x]
            metrics["grind_time_seconds"] = float(parts[2])
    return metrics


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ResultParser("kripke")

    # For flux we can save jobspecs and other event data
    data = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:
        # Underscore means skip, also skip configs and runs without efa
        # runs with google and shared memory were actually slower...
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        # Note that aws eks has kripke-8gpu directories, that just
        # distinguishes when we ran a first set of runs just with 8 and
        # then had the larger cluster working. Both data are good.
        # All of these are consistent across studies
        exp = ps.ExperimentNameParser(filename, indir)
        if exp.prefix not in data:
            data[exp.prefix] = []

        # Size 2 was typically testing, and we are only processing GPU
        if exp.size == 2 or exp.env_type == "gpu":
            continue

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size)
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
            if "JOBSPEC" in item:
                item, _, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            else:
                metadata = {}
                item = ps.remove_slurm_duration(item)

            metrics = parse_kripke_foms(item)
            for metric, value in metrics.items():
                p.add_result(metric, value)

    print("Done parsing kripke results!")
    p.df.to_csv(os.path.join(outdir, "kripke-cpu-grind-time-results.csv"))
    ps.write_json(data, os.path.join(outdir, "kripke-cpu-grind-time-parsed.json"))
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

    # We are going to put the plots together, and the colors need to match!
    cloud_colors = {}
    for cloud in df.experiment.unique():
        cloud_colors[cloud] = ps.match_color(cloud)

    # Within a setup, compare between experiments for GPU and cpu
    for env in df.env_type.unique():
        if env != "cpu":
            continue
        subset = df[df.env_type == env]

        # Make a plot for each metric
        for metric in subset.metric.unique():
            metric_df = subset[subset.metric == metric]
            title = " ".join([x.capitalize() for x in metric.split("_")])
            if "grind" not in metric.lower():
                continue

            # Note that the Y label is hard coded because we just have one metric
            ps.make_plot(
                metric_df,
                title=f"Kripke {title} ({env.upper()})",
                ydimension="value",
                plotname=f"kripke-grind-time-{env}",
                xdimension="nodes",
                palette=cloud_colors,
                outdir=img_outdir,
                hue="experiment",
                xlabel="Nodes",
                hue_order=[
                    "on-premises/a/cpu",
                    "aws/parallel-cluster/cpu",
                    "aws/eks/cpu",
                    "azure/cyclecloud/cpu",
                    "google/compute-engine/cpu",
                    "azure/aks/cpu",
                    "google/gke/cpu",
                ],
                order=[32, 64, 128, 256],
                ylabel="Grind Time (Seconds)",
                do_round=False,
                log_scale=True,
                height=3.8,
                width=10,
            )

        print(f"Total number of CPU datum: {metric_df.shape[0]}")


if __name__ == "__main__":
    main()
