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

sns.set_theme(style="whitegrid", palette="pastel")

# These are files I found erroneous - no result, or incomplete result
errors = [
    # Only start time, module load error, and Mounting with FUSE
    "azure/cyclecloud/cpu/size32/results/lammps-reax/lammps-32n-223-iter-5.out",
    # Only start time, error shows loading module and then CANCELLED
    "azure/cyclecloud/cpu/size128/results/lammps-reax/lammps-128n-85-iter-1.out",
    "azure/cyclecloud/cpu/size128/results/lammps-reax/lammps-128n-96-iter-1.out",
    # CANCELLED, empty log except for start timestamp
    "azure/cyclecloud/cpu/size128/results/lammps-reax/lammps-128n-91-iter-2.out",
    # Huge stream of UCX errors, not available or found, no lammps output
    "azure/cyclecloud/cpu/size256/results/lammps-reax/lammps-256n-4826-iter-5.out",
    "azure/cyclecloud/cpu/size256/results/lammps-reax/lammps-256n-4829-iter-3.out",
    "on-premises/lassen/gpu/size8/lammps-reax/6348824-iter-1-8n-gpuon.out",
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
    parser.add_argument(
        "--on-premises",
        help="save results that also parse on-premises data.",
        default=False,
        action="store_true",
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
    if args.on_premises:
        outdir = os.path.join(outdir, "on-premises")
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories (anything with lammps-reax)
    # lammps directories are usually snap
    files = ps.find_inputs(indir, "lammps-reax", args.on_premises)
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
                problem_size = metadata["jobspec"]["tasks"][0]["command"]

                # Kind of janky, but looks ok!
                problem_size = (
                    " ".join(problem_size)
                    .split(" x ")[-1]
                    .split("-in")[0]
                    .strip()
                    .replace(" -v ", "x")
                    .replace("y ", "")
                    .replace("z ", "")
                )

            # Slurm has the item output, and then just the start/end of the job
            elif "on-premises" not in filename:
                # We assume all other sizes were 256 256 128
                # TODO check this is true
                metadata = {}
                problem_size = "64x64x32"
                duration = ps.parse_slurm_duration(item)

            elif "on-premises" in filename:
                print(filename)
                metadata = {}
                problem_size = "64x64x32"

            # Add the duration in seconds
            if duration is not None:
                p.add_result("workload_manager_wrapper_seconds", duration, problem_size)

            # We want this to fail if there is an issue!
            lammps_result = parse_lammps(item)

            # Add in Matom steps - what is considered the LAMMPS FOM
            # https://asc.llnl.gov/sites/asc/files/2020-09/CORAL2_Benchmark_Summary_LAMMPS.pdf
            # Not parsed by metrics operator so we find the line here
            line = [x for x in item.split("\n") if "Matom-step/s" in x][0]
            matom_steps_per_second = float(line.split(",")[-1].strip().split(" ")[0])
            p.add_result("matom_steps_per_second", matom_steps_per_second, problem_size)

            wall_time = lammps_result["total_wall_time_seconds"]
            metadata["lammps"] = lammps_result
            p.add_result("wall_time", wall_time, problem_size)
            p.add_result("ranks", metadata["lammps"]["ranks"], problem_size)

            # Calculate the hookup time - wrapper time minus wall time
            if duration is not None:
                hookup_time = duration - wall_time
                p.add_result("hookup_time", hookup_time, problem_size)

            # CPU utilization
            line = [x for x in item.split("\n") if "CPU use" in x][0]
            cpu_util = float(line.split(" ")[0].replace("%", ""))
            p.add_result("cpu_utilization", cpu_util, problem_size)

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

    # Within a setup, compare between experiments for GPU and cpu
    for env in df.env_type.unique():
        subset = df[df.env_type == env]
        for problem_size in subset.problem_size.unique():
            ps_df = subset[subset.problem_size == problem_size]

            # Make a plot for seconds runtime, and each FOM set.
            # We can look at the metric across sizes, colored by experiment
            for metric in ps_df.metric.unique():
                if metric == "ranks":
                    continue
                metric_df = ps_df[ps_df.metric == metric]

                # Note that some of these will be eventually removed / filtered
                colors = sns.color_palette("hls", len(metric_df.experiment.unique()))

                hexcolors = colors.as_hex()
                types = list(metric_df.experiment.unique())
                palette = collections.OrderedDict()
                for t in types:
                    palette[t] = hexcolors.pop(0)
                title = " ".join([x.capitalize() for x in metric.split("_")])

                ps.make_plot(
                    metric_df,
                    title=f"LAMMPS Metric {title} {problem_size} for {env.upper()}",
                    ydimension="value",
                    plotname=f"lammps-reax-{metric}-{problem_size}-{env}",
                    xdimension="nodes",
                    palette=palette,
                    outdir=img_outdir,
                    hue="experiment",
                    xlabel="Nodes",
                    ylabel=title,
                    do_round=True,
                )
                if env == "gpu":
                    ps.make_plot(
                        metric_df,
                        title=f"LAMMPS Metric {title} {problem_size} for {env.upper()}",
                        ydimension="value",
                        plotname=f"lammps-reax-{metric}-{problem_size}-{env}-gpu-count",
                        xdimension="gpu_count",
                        palette=palette,
                        outdir=img_outdir,
                        hue="experiment",
                        xlabel="GPU Count",
                        ylabel=title,
                        do_round=True,
                    )


if __name__ == "__main__":
    main()
