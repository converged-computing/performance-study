#!/usr/bin/env python3

import argparse
import collections
import json
import os
import re
import sys

from metricsoperator.metrics.app.lammps import parse_lammps
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
    plot_results(df, outdir)


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


def plot_results(df, outdir):
    """
    Plot analysis results
    """
    # Let's get some shoes! Err, plots.
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # We are going to put the plots together, and the colors need to match!
    cloud_colors = ps.get_cloud_colors(df.experiment.unique())

    for env in df.env_type.unique():
        subset = df[df.env_type == env]
        # Make a plot for seconds runtime, and each FOM set.
        # We can look at the metric across sizes, colored by experiment
        for metric in subset.metric.unique():
            metric_df = subset[subset.metric == metric]
            print(metric_df.groupby(['env_type', 'env', 'cloud', 'experiment']).value.mean())
            print(metric_df.groupby(['env_type', 'env', 'cloud', 'experiment']).value.std())
            title = " ".join([x.capitalize() for x in metric.split("_")])
            if env == "cpu":
                ps.make_plot(
                    metric_df,
                    title=f"Laghos Major Kernels Total Rate ({env.upper()})",
                    ydimension="value",
                    plotname=f"laghos-{metric}-{env}",
                    xdimension="nodes",
                    palette=cloud_colors,
                    outdir=img_outdir,
                    hue="experiment",
                    xlabel="Nodes",
                    ylabel="megadofs x time steps / second",
                    do_round=False,
                    #legend_pos="center right",
                    width=5,
                    height=6.5,
                )

            # Note that we couldn't build the laghos GPU container


if __name__ == "__main__":
    main()
