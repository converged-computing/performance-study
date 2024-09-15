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

    # Find input directories (anything with lammps-reax)
    # lammps directories are usually snap
    files = ps.find_inputs(indir, "lammps-reax")
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


class LAMMPSParser(ps.ResultParser):
    def init_df(self):
        """
        Initialize an empty data frame for the application
        """
        self.df = pandas.DataFrame(
            columns=[
                "experiment",
                "cloud",
                "env",
                "env_type",
                "nodes",
                "application",
                "problem_size",
                "metric",
                "value",
            ]
        )

    def add_result(self, metric, value, problem_size):
        """
        Add a result to the table
        """
        # Unique identifier for the experiment plot
        # is everything except for size
        experiment = os.path.join(self.cloud, self.env, self.env_type)
        if self.qualifier is not None:
            experiment = os.path.join(experiment, self.qualifier)
        self.df.loc[self.idx, :] = [
            experiment,
            self.cloud,
            self.env,
            self.env_type,
            self.size,
            self.app,
            problem_size,
            metric,
            value,
        ]
        self.idx += 1


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = LAMMPSParser("lammps")

    # For flux we can save jobspecs and other event data
    data = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:

        # Underscore means skip, also skip configs and runs without efa
        # runs with google and shared memory were actually slower...
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        # All of these are consistent across studies
        parts = filename.replace(indir + os.sep, "").split(os.sep)

        # These are consistent across studies
        cloud = parts.pop(0)
        env = parts.pop(0)
        env_type = parts.pop(0)
        size = parts.pop(0)

        # Prefix is an identifier for parsed flux metadata, jobspec and events
        prefix = os.path.join(cloud, env, env_type, size)
        if prefix not in data:
            data[prefix] = []

        # I don't know if these are results or testing, skipping for now
        # They are from aws parallel-cluster CPU
        if os.path.join("experiment", "data") in filename:
            continue

        # If these are in the size, they are additional identifiers to indicate the
        # environment type. Add to it instead of the size. I could skip some of these
        # but I want to see the differences.
        if "-" in size:
            print(filename)
            size, _ = size.split("-", 1)
        size = int(size.replace("size", ""))

        # Size 2 was typically testing
        if size == 2:
            continue

        # Set the parsing context for the result data frame
        p.set_context(cloud, env, env_type, size)
        print(cloud, env, env_type, size)

        # Now we can read each AMG result file and get the FOM.
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
            if "JOBSPEC" in item:
                item, duration, metadata = ps.parse_flux_metadata(item)
                data[prefix].append(metadata)
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
            else:
                # We assume all other sizes were 256 256 128
                # TODO check this is true
                metadata = {}
                problem_size = "64x64x32"
                duration = ps.parse_slurm_duration(item)

            # Add the duration in seconds
            p.add_result("seconds", duration, problem_size)

            # We want this to fail if there is an issue!
            lammps_result = parse_lammps(item)
            wall_time = lammps_result["total_wall_time_seconds"]
            metadata["lammps"] = lammps_result
            p.add_result("wall_time", wall_time, problem_size)
            p.add_result("ranks", metadata["lammps"]["ranks"], problem_size)

            # Calculate the hookup time - wrapper time minus wall time
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
                colors = sns.color_palette("hls", 16)
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


if __name__ == "__main__":
    main()
