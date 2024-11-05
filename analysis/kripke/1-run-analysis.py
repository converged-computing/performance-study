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

sns.set_theme(style="whitegrid", palette="pastel")

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
    files = ps.find_inputs(indir, "kripke")
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


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
        if "Throughput" in line:
            parts = [x for x in line.split(" ") if x]
            metrics["throughput_unknowns_over_second_per_iteration"] = float(parts[1])
        elif "Grind time" in line:
            parts = [x for x in line.replace(":", "").split(" ") if x]
            metrics["grind_time_seconds_per_iteration_over_unknowns"] = float(parts[2])
        elif "Sweep efficiency" in line:
            parts = [x for x in line.replace(":", "").split(" ") if x]
            metrics["sweep_efficiency"] = float(parts[2])
        elif "Number of unknowns" in line:
            parts = [x for x in line.split(" ") if x]
            metrics["number_of_unknowns"] = float(parts[-1])
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

        # Size 2 was typically testing
        if exp.size == 2:
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
                item, duration, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            else:
                metadata = {}
                duration = ps.parse_slurm_duration(item)
                item = ps.remove_slurm_duration(item)

            metrics = parse_kripke_foms(item)
            for metric, value in metrics.items():
                p.add_result(metric, value)

            # If we don't have metrics, don't consider the runtime duration
            # CycleCloud GPU size 4 doesn't have any successful runs
            if not metrics:
                continue
            p.add_result("workload_manager_wrapper_seconds", duration)

    print("Done parsing kripke results!")
    p.df.to_csv(os.path.join(outdir, "kripke-results.csv"))
    ps.write_json(data, os.path.join(outdir, "kripke-parsed.json"))
    return p.df


def plot_results(df, outdir):
    """
    Plot analysis results
    """
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Scientific Notation for prettier plot
    log_scale_set = [
        "number_unknowns",
        "throughput_unknowns_over_second_per_iteration",
        "grind_time_seconds_per_iteration_over_unknowns",
    ]
    # Within a setup, compare between experiments for GPU and cpu
    for env in df.env_type.unique():
        subset = df[df.env_type == env]

        # Make a plot for each metric
        for metric in subset.metric.unique():
            metric_df = subset[subset.metric == metric]

            colors = sns.color_palette("hls", len(metric_df.experiment.unique()))
            hexcolors = colors.as_hex()
            types = list(metric_df.experiment.unique())
            palette = collections.OrderedDict()
            for t in types:
                palette[t] = hexcolors.pop(0)
            title = " ".join([x.capitalize() for x in metric.split("_")])

            log_scale = True if metric in log_scale_set else False
            ps.make_plot(
                metric_df,
                title=f"Kripke Metric {title} for {env.upper()}",
                ydimension="value",
                plotname=f"kripke-{metric}-{env}",
                xdimension="nodes",
                palette=palette,
                outdir=img_outdir,
                hue="experiment",
                xlabel="Nodes",
                ylabel=title,
                do_round=False,
                log_scale=log_scale,
            )


if __name__ == "__main__":
    main()
