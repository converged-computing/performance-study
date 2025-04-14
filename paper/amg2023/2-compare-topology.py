#!/usr/bin/env python3

# Compare processor topology between google and compute engine

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
    p = ps.ProblemSizeParser("amg2023")

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

        if exp.cloud != "google":
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

        if "amg2023-large" not in filename:
            print(f"Skipping {filename}, not correct result to use.")
            continue

        # Now we can read each AMG result file and get the FOM.
        results = list(ps.get_outfiles(filename))
        for result in results:

            item = ps.read_file(result)

            # All of Google runs use flux
            item, duration, metadata = ps.parse_flux_metadata(item)
            data[exp.prefix].append(metadata)

            pline = (
                " ".join(metadata["jobspec"]["tasks"][0]["command"])
                .split("-P")[-1]
                .split("-problem")[0]
                .split(" ")
            )
            pline = " ".join([x for x in pline if x.strip()])
            fom_overall = get_fom_line(item, "Figure of Merit (FOM)")
            p.add_result("fom_overall", fom_overall, pline)

    print("Done parsing amg2023 results!")

    # Save stuff to file first
    p.df.to_csv(os.path.join(outdir, "amg2023-results.csv"))
    ps.write_json(data, os.path.join(outdir, "flux-jobspec-and-events.json"))
    return p.df


def plot_results(df, outdir):
    """
    Plot analysis results
    """
    import IPython

    IPython.embed()
    sys.exit()
    # Let's get some shoes! Err, plots.
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # We are going to put the plots together, and the colors need to match!
    cloud_colors = {}
    for cloud in df.experiment.unique():
        cloud_colors[cloud] = ps.match_color(cloud)

    # Within a setup, compare between experiments for GPU and cpu
    for env in df.env_type.unique():
        subset = df[df.env_type == env]

        # x axis is by gpu count for gpus
        x_by = "nodes"
        x_label = "Nodes"
        if env == "gpu":
            x_by = "gpu_count"
            x_label = "Number of GPU"

        for experiment in subset.experiment.unique():
            exp_df = subset[subset.experiment == experiment]
            for metric in exp_df.metric.unique():
                metric_df = exp_df[exp_df.metric == metric]
                title = " ".join([x.capitalize() for x in metric.split("_")])

            # Make sure fom is always capitalized
            title = title.replace("Fom", "FOM")
            ps.make_plot(
                metric_df,
                title=f"AMG2023 {title} ({env.upper()})",
                ydimension="value",
                plotname=f"amg2023-{metric}-{env}",
                xdimension=x_by,
                palette=cloud_colors,
                outdir=img_outdir,
                hue="experiment",
                xlabel=x_label,
                ylabel=title,
                log_scale=log_scale,
            )


if __name__ == "__main__":
    main()
