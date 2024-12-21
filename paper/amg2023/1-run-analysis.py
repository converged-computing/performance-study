#!/usr/bin/env python3

import argparse
import collections
import json
import os
import sys
import re

import matplotlib.pylab as plt
import pandas
import seaborn as sns

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="muted")

# These are files I found erroneous - no result, or incomplete result
# Details included with each, and more exploration is likely needed to quantify
# error types
errors = [
    # These are start/end time wrapping a ton of UCX errors
    "azure/cyclecloud/cpu/size256/results/amg2023/amg-256n-4799-iter-1.out",
    # This partially ran, but didn't get to any FOM.
    # UCX  ERROR shm_open(file_name=/ucx_shm_posix_2e841ba5 flags=0x0) failed: No such file or directory
    "azure/cyclecloud/cpu/size256/results/amg2023/amg-256n-4794-iter-1.out",
    # This partially ran (has FOM_Setup) but was killed.
    # 9 total processes killed (some possibly by mpirun during cleanup)
    "azure/cyclecloud/cpu/size256/results/amg2023/amg-256n-4801-iter-1-ucxall.out",
    # This just has a start time (and nothing else)
    "azure/cyclecloud/cpu/size256/results/amg2023/amg-256n-4797-iter-4.out",
    # This has a start time and partial run, but never any FOM
    # The error file has driver loading errors, then CANCELLED by slurm
    "azure/cyclecloud/gpu/size4/results/amg2023/amg-4n-10-iter-3.out",
    # This is a GPU run that partially ran - no FOMs, but has start and end time
    # The error file is a stream of not being able to load object files
    "azure/cyclecloud/gpu/size32/results/amg2023/amg-32n-504-iter-5.out",
    "azure/cyclecloud/gpu/size32/results/amg2023/amg-32n-503-iter-4.out",
    # This partially ran but was killed. Error file hypre throwup (Segmentation fault)
    "azure/cyclecloud/gpu/size32/results/amg2023/amg-32n-502-iter-3.out",
    # Incomplete result
    "on-premises/dane/cpu/size256/amg2023/amg2023-256-4threads-1020030-iter-1-256n.out",
    "on-premises/dane/cpu/size256/amg2023/amg2023-256-4threads-1020031-iter-2-256n.out",
    "on-premises/dane/cpu/size256/amg2023/amg2023-256-4threads-1020032-iter-3-256n.out",
    "on-premises/lassen/gpu/size64/amg2023/6169223-iter-1-64n.out",
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
    
    # We absolutely want on premises results here
    args.on_premises = True
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input files (skip anything with test)
    files = ps.find_inputs(indir, "amg2023", args.on_premises)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


def get_fom_line(item, name):
    """
    Get a figure of merit based on the name
    """
    line = [x for x in item.split("\n") if name in x][0]
    return float(line.rsplit(" ", 1)[-1])


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be figures of merit, and seconds runtime
    p = ps.ResultParser("amg2023")

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

        # TODO we should check to make sure problem decompositions are the same.
        # If the cloud is google, gke, gpu size 8, we want final/amg2023-large
        # there is another attempt-1 and the wrong decomposition (amg2023-large-8-4-2)
        # that we can skip.
        if exp.cloud == "google" and exp.env == "gke" and exp.env_type == "gpu":
            # amg was run at different sizes and decompositions. amg2023-large is the correct one
            if "amg2023-large" not in filename:
                print(f"Skipping {filename}, not correct result to use.")
                continue

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size, gpu_count=number_gpus)
        exp.show()

        # Now we can read each AMG result file and get the FOM.
        results = list(ps.get_outfiles(filename))
        for result in results:
            # Skip over found erroneous results
            if re.search(error_regex, result):
                print(f"Skipping {result} due to known missing result or error.")
                continue

            # Basename that start with underscore are test or otherwise should not be included
            if os.path.basename(result).startswith("_"):
                continue
            item = ps.read_file(result)

            # If this is a flux run, we have a jobspec and events here
            duration = None
            if "JOBSPEC" in item:
                item, duration, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            elif "on-premises" not in filename:
                duration = ps.parse_slurm_duration(item)

            # Parse the FOM from the item - I see three.
            # This needs to throw an error if we can't find it - indicates the result file is wonky
            # Figure of Merit (FOM): nnz_AP / (Setup Phase Time + 3 * Solve Phase Time) 1.148604e+09
            fom_overall = get_fom_line(item, "Figure of Merit (FOM)")
            p.add_result("fom_overall", fom_overall)

    print("Done parsing amg2023 results!")

    # Save stuff to file first
    p.df.to_csv(os.path.join(outdir, "amg2023-results.csv"))
    ps.write_json(data, os.path.join(outdir, "flux-jobspec-and-events.json"))
    return p.df


def plot_results(df, outdir):
    """
    Plot analysis results
    """
    # Let's get some shoes! Err, plots.
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Within a setup, compare between experiments for GPU and cpu
    for env in df.env_type.unique():
        subset = df[df.env_type == env]

        # x axis is by gpu count for gpus
        x_by = "nodes"
        x_label = "Nodes"
        if env == "gpu":
            x_by = "gpu_count"
            x_label = "Number of GPU"

        # Make a plot for seconds runtime, and each FOM set.
        # We can look at the metric across sizes, colored by experiment
        for metric in subset.metric.unique():
            metric_df = subset[subset.metric == metric]

            # Note that some of these will be eventually removed / filtered
            colors = sns.color_palette("muted", len(metric_df.experiment.unique()))
            hexcolors = colors.as_hex()
            types = list(metric_df.experiment.unique())
            palette = collections.OrderedDict()
            for t in types:
                palette[t] = hexcolors.pop(0)

            log_scale = False if metric == "seconds" else True
            title = " ".join([x.capitalize() for x in metric.split("_")])

            # Make sure fom is always capitalized
            title = title.replace("Fom", "FOM")
            ps.make_plot(
                metric_df,
                title=f"AMG2023 {title} ({env.upper()})",
                ydimension="value",
                plotname=f"amg2023-{metric}-{env}",
                xdimension=x_by,
                palette=palette,
                outdir=img_outdir,
                hue="experiment",
                xlabel=x_label,
                ylabel=title,
                log_scale=log_scale,
            )


if __name__ == "__main__":
    main()
