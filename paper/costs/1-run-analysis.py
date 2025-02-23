#!/usr/bin/env python3

import argparse
import collections
import json
import os
import re
import sys

import matplotlib.pylab as plt
import pandas
import seaborn as sns

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
sys.path.insert(0, root)
import performance_study as ps

sns.set_theme(style="whitegrid", palette="muted")


def get_parser():
    parser = argparse.ArgumentParser(
        description="Run analysis",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--data",
        help="data directory with data files (csv)",
        default=os.path.join(here, "data"),
    )
    parser.add_argument(
        "--out",
        help="directory to save parsed results",
        default=os.path.join(here, "img"),
    )
    return parser


def main():
    """
    Find cost data to parse.
    """
    parser = get_parser()
    args, _ = parser.parse_known_args()

    # Output images and data
    outdir = os.path.abspath(args.out)
    indir = os.path.abspath(args.data)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Just report total cost for each cloud
    read_azure_data(indir)
    read_aws_data(indir)
    read_google_data(indir)

def read_azure_data(indir):
    """
    Read in and parse azure cost data.    
    """
    azure_df = pandas.read_csv(os.path.join(indir, "azure-cost-data-usage.csv"))
    print("Total cost of Azure is %s" % azure_df["LLNL Cost"].sum())
    

def read_aws_data(indir):
    """
    Read in and parse aws cost data.
    """
    # These are all basically the same, you can round them up/down slightly differently.
    aws_df = pandas.read_csv(os.path.join(indir, "aws-cost-data.csv"))
    print(f"line item blended cost {aws_df.line_item_blended_cost.sum()}")
    print(f"line item unblended cost {aws_df.line_item_unblended_cost.sum()}")
    print(f"pricing public on-demand cost {aws_df.pricing_public_on_demand_cost.sum()}")

def read_google_data(indir):
    """
    Read in and parse google cost data.
    """
    google_df = pandas.read_csv(os.path.join(indir, "google-cost-data-2024-08-01-2024-08-31.csv"))
    print(f"Google Cloud Total {google_df['Subtotal ($)'].sum()}")

def parse_matom_steps(item):
    """
    Parse matom steps

    We separated this into a function because cyclecloud submits have
    two problem sizes in one file.
    """
    # Add in Matom steps - what is considered the LAMMPS FOM
    # https://asc.llnl.gov/sites/asc/files/2020-09/CORAL2_Benchmark_Summary_LAMMPS.pdf
    # Not parsed by metrics operator so we find the line here
    line = [x for x in item.split("\n") if "Matom-step/s" in x][0]
    return float(line.split(",")[-1].strip().split(" ")[0])


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ProblemSizeParser("lammps")

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
            if os.path.basename(result).startswith("_") or "missing-sif-log" in result:
                continue
            item = ps.read_file(result)

            # If this is a flux run, we have a jobspec and events here
            duration = None
            if "JOBSPEC" in item:
                item, duration, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)
                problem_size = "64x64x32" if "64x64x32" in item else "64x32x32"
                assert problem_size in item
                p.add_result(
                    "matom_steps_per_second", parse_matom_steps(item), problem_size
                )

            # Slurm has the item output, and then just the start/end of the job
            # IMPORTANT: cyclecloud was run two problem sizes one job!
            elif "on-premises" not in filename:
                metadata = {}
                if item.count("Total wall time") > 1:
                    items = item.split("Total wall time", 1)
                    # Larger problem size is first (slower wall time)
                    problem_size = "64x64x32"
                    assert problem_size in items[0]
                    p.add_result(
                        "matom_steps_per_second",
                        parse_matom_steps(items[0]),
                        problem_size,
                    )
                    # Smaller problem size is second
                    problem_size = "64x32x32"
                    assert problem_size in items[1]
                    p.add_result(
                        "matom_steps_per_second",
                        parse_matom_steps(items[1]),
                        problem_size,
                    )
                else:
                    problem_size = "64x64x32"
                    assert problem_size in item
                    p.add_result(
                        "matom_steps_per_second", parse_matom_steps(item), problem_size
                    )

            # I think we only ran this problem size on premises
            elif "on-premises" in filename:
                metadata = {}
                problem_size = "64x64x32" if "64x64x32" in item else "64x32x32"
                assert problem_size in item
                p.add_result(
                    "matom_steps_per_second", parse_matom_steps(item), problem_size
                )

    print("Done parsing lammps results!")
    p.df.to_csv(os.path.join(outdir, "lammps-reax-results.csv"))
    ps.write_json(data, os.path.join(outdir, "lammps-reax-parsed.json"))
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
    cloud_colors = {}
    for cloud in df.experiment.unique():
        cloud_colors[cloud] = ps.match_color(cloud)

    # Within a setup, compare between experiments for GPU and cpu
    for env in df.env_type.unique():
        subset = df[df.env_type == env]
        for problem_size in subset.problem_size.unique():
            ps_df = subset[subset.problem_size == problem_size]

            # Make a plot for seconds runtime, and each FOM set.
            # We can look at the metric across sizes, colored by experiment
            for metric in ps_df.metric.unique():
                metric_df = ps_df[ps_df.metric == metric]
                title = " ".join([x.capitalize() for x in metric.split("_")])
                if env == "cpu":
                    ps.make_plot(
                        metric_df,
                        title=f"LAMMPS M/Atom Steps per Second {problem_size} ({env.upper()})",
                        ydimension="value",
                        plotname=f"lammps-reax-{metric}-{problem_size}-{env}",
                        xdimension="nodes",
                        palette=cloud_colors,
                        outdir=img_outdir,
                        hue="experiment",
                        xlabel="Nodes",
                        ylabel="Millions of Atom Steps per Second",
                        do_round=False,
                    )
                if env == "gpu":
                    ps.make_plot(
                        metric_df,
                        title=f"LAMMPS M/Atom Steps per Second {problem_size} ({env.upper()})",
                        ydimension="value",
                        plotname=f"lammps-reax-{metric}-{problem_size}-{env}-gpu-count",
                        xdimension="gpu_count",
                        palette=cloud_colors,
                        outdir=img_outdir,
                        hue="experiment",
                        xlabel="GPU Count",
                        ylabel="Millions of Atom Steps per Second",
                        do_round=False,
                    )


if __name__ == "__main__":
    main()
