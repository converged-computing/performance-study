#!/usr/bin/env python3

import argparse
import collections
import json
import os
import re

import matplotlib.pylab as plt
import pandas
import seaborn as sns

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(os.path.dirname(here))

sns.set_theme(style="whitegrid", palette="pastel")

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


def recursive_find(base, pattern="*.*"):
    """
    Recursively find and yield directories matching a glob pattern.
    """
    for root, dirnames, filenames in os.walk(base):
        for dirname in dirnames:
            if not re.search(pattern, dirname):
                continue
            yield os.path.join(root, dirname)


def find_inputs(input_dir, pattern="*.*"):
    """
    Find inputs (times results files)
    """
    files = []
    for filename in recursive_find(input_dir, pattern):
        # We only have data for small
        files.append(filename)
    return files


def get_outfiles(base, pattern="[.]out"):
    """
    Recursively find and yield directories matching a glob pattern.
    """
    for root, _, filenames in os.walk(base):
        for filename in filenames:
            if not re.search(pattern, filename):
                continue
            yield os.path.join(root, filename)


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

    # Find input files (skip anything with test)
    files = find_inputs(indir, "amg2023")
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


def read_file(filename):
    with open(filename, "r") as fd:
        content = fd.read()
    return content


def write_json(obj, filename):
    with open(filename, "w") as fd:
        fd.write(json.dumps(obj, indent=4))


def write_file(text, filename):
    with open(filename, "w") as fd:
        fd.write(text)


class ResultParser:
    """
    Helper class to parse results into a data frame.
    """

    def __init__(self, app):
        self.init_df()
        self.idx = 0
        self.app = app

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
                "metric",
                "value",
            ]
        )

    def set_context(self, cloud, env, env_type, size, qualifier=None):
        """
        Set the context for the next stream of results.

        These are just fields to add to the data frame.
        """
        self.cloud = cloud
        self.env = env
        self.env_type = env_type
        self.size = size
        # Extra metadata to add to experiment name
        self.qualifier = qualifier

    def add_result(self, metric, value):
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
            metric,
            value,
        ]
        self.idx += 1


def get_fom_line(item, name):
    """
    Get a figure of merit based on the name
    """
    line = [x for x in item.split("\n") if name in x][0]
    return float(line.rsplit(" ", 1)[-1])


def parse_flux_metadata(item):
    """
    Jobs run with flux have a jobspec and event metadata at the end
    """
    item, metadata = item.split("START OF JOBSPEC")
    metadata, events = metadata.split("START OF EVENTLOG")
    jobspec = json.loads(metadata)
    events = [json.loads(x) for x in events.split("\n") if x]

    # QUESTION: is this the correct event, shell.start? I chose over init
    # Note that I assume we want to start at init and done.
    # This unit is in seconds
    start = [x for x in events if x["name"] == "shell.start"][0]["timestamp"]
    done = [x for x in events if x["name"] == "done"][0]["timestamp"]
    duration = done - start
    metadata = {"jobspec": jobspec, "events": events}
    return item, duration, metadata


def parse_slurm_duration(item):
    """
    Get the start and end time from the slurm output.

    We want this to throwup if it is missing from the output.
    """
    start = int(
        [x for x in item.split("\n") if "Start time" in x][0].rsplit(" ", 1)[-1]
    )
    done = int([x for x in item.split("\n") if "End time" in x][0].rsplit(" ", 1)[-1])
    return done - start


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be figures of merit, and seconds runtime
    p = ResultParser("amg2023")

    # For flux we can save jobspecs and other event data
    data = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:

        # Underscore means skip, also skip configs and runs without efa
        # runs with google and shared memory were actually slower...
        dirname = os.path.basename(filename)
        if (
            dirname.startswith("_")
            or "configs" in filename
            or "no-add" in filename
            or "noefa" in filename
            or "shared-memory" in filename
        ):
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

        # TODO we should check to make sure problem decompositions are the same.
        # If the cloud is google, gke, gpu size 8, we want final/amg2023-large
        # there is another attempt-1 and the wrong decomposition (amg2023-large-8-4-2)
        # that we can skip.
        if cloud == "google" and env == "gke" and env_type == "gpu":
            # amg was run at different sizes and decompositions. amg2023-large is the correct one
            if "amg2023" in filename and not filename.endswith(
                os.path.join("final", "amg2023-large")
            ):
                print(f"Skipping {filename}, not correct result to use.")
                continue

            # attempt-1 needed a redo, so don't use it
            if "final" not in filename:
                print(f"Skipping {filename}, not correct result to use.")
                continue

        # I don't know if these are results or testing, skipping for now
        # They are from aws parallel-cluster CPU
        if os.path.join("experiment", "data") in filename:
            continue

        # These were redone with a placement group
        if "aks/cpu/size" in filename and "placement" not in filename:
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
        results = list(get_outfiles(filename))
        for result in results:

            # Skip over found erroneous results
            if re.search(error_regex, result):
                print(f"Skipping {result} due to known missing result or error.")
                continue

            # Basename that start with underscore are test or otherwise should not be included
            if os.path.basename(result).startswith("_"):
                continue
            item = read_file(result)

            # If this is a flux run, we have a jobspec and events here
            if "JOBSPEC" in item:
                item, duration, metadata = parse_flux_metadata(item)
                data[prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            else:
                duration = parse_slurm_duration(item)

            # Add the duration in seconds
            p.add_result("seconds", duration)

            # Parse the FOM from the item - I see three.
            # This needs to throw an error if we can't find it - indicates the result file is wonky
            # Figure of Merit (FOM): nnz_AP / (Setup Phase Time + 3 * Solve Phase Time) 1.148604e+09
            fom_overall = get_fom_line(item, "Figure of Merit (FOM)")
            p.add_result("fom_overall", fom_overall)

            # FOM_Solve: nnz_AP * iterations / Solve Phase Time: 4.546804e+09
            fom_solve = get_fom_line(item, "FOM_Solve")
            p.add_result("fom_solve", fom_solve)

            # FOM_Setup: nnz_AP / Setup Phase Time: 4.743429e+09
            fom_setup = get_fom_line(item, "FOM_Setup")
            p.add_result("fom_setup", fom_setup)

    print("Done parsing amg2023 results!")

    # Save stuff to file first
    p.df.to_csv(os.path.join(outdir, "amg2023-results.csv"))
    write_json(data, os.path.join(outdir, "flux-jobspec-and-events.json"))
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

        # Make a plot for seconds runtime, and each FOM set.
        # We can look at the metric across sizes, colored by experiment
        for metric in subset.metric.unique():
            metric_df = subset[subset.metric == metric]

            # Note that some of these will be eventually removed / filtered
            colors = sns.color_palette("hls", 16)
            hexcolors = colors.as_hex()
            types = list(metric_df.experiment.unique())
            palette = collections.OrderedDict()
            for t in types:
                palette[t] = hexcolors.pop(0)

            log_scale = False if metric == "seconds" else True
            title = " ".join([x.capitalize() for x in metric.split("_")])

            # Make sure fom is always capitalized
            title = title.replace("Fom", "FOM")
            make_plot(
                metric_df,
                title=f"AMG2023 Metric {title} for {env.upper()}",
                ydimension="value",
                plotname=f"amg2023-{metric}-{env}",
                xdimension="nodes",
                palette=palette,
                outdir=img_outdir,
                hue="experiment",
                xlabel="Nodes",
                ylabel=title,
                log_scale=log_scale,
            )


def make_plot(
    df,
    title,
    ydimension,
    xdimension,
    xlabel,
    ylabel,
    palette=None,
    ext="png",
    plotname="lammps",
    hue=None,
    outdir="img",
    log_scale=False,
):
    """
    Helper function to make common plots.
    """
    ext = ext.strip(".")
    plt.figure(figsize=(12, 6))
    sns.set_style("dark")
    ax = sns.boxplot(
        x=xdimension,
        y=ydimension,
        hue=hue,
        data=df,
        # gap=.1,
        linewidth=0.8,
        palette=palette,
        whis=[5, 95],
        # dodge=False,
    )

    plt.title(title)
    print(log_scale)
    ax.set_xlabel(xlabel, fontsize=16)
    ax.set_ylabel(ylabel, fontsize=16)
    ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
    ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    # plt.xticks(rotation=90)
    if log_scale is True:
        plt.gca().yaxis.set_major_formatter(
            plt.ScalarFormatter(useOffset=True, useMathText=True)
        )

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{plotname}.{ext}"))
    plt.clf()


if __name__ == "__main__":
    main()