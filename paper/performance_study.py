#!/usr/bin/env python3

# Shared functions to use across analyses.

import json
import os
import re

from matplotlib.ticker import FormatStrFormatter
import matplotlib.pylab as plt
import pandas
import seaborn as sns

sns.set_theme(style="whitegrid", palette="muted")
sns.set_style("whitegrid", {"legend.frameon": True})


def read_json(filename):
    with open(filename, "r") as fd:
        content = json.loads(fd.read())
    return content


def recursive_find(base, pattern="*.*"):
    """
    Recursively find and yield directories matching a glob pattern.
    """
    for root, dirnames, filenames in os.walk(base):
        for dirname in dirnames:
            if not re.search(pattern, dirname):
                continue
            yield os.path.join(root, dirname)


def recursive_find_files(base, pattern="*.*"):
    """
    Recursively find and yield directories matching a glob pattern.
    """
    for root, _, filenames in os.walk(base):
        for filename in filenames:
            if not re.search(pattern, filename):
                continue
            yield os.path.join(root, filename)


def find_inputs(input_dir, pattern="*.*", include_on_premises=False):
    """
    Find inputs (times results files)
    """
    files = []
    for filename in recursive_find(input_dir, pattern):
        # We only have data for small
        if not include_on_premises and "on-premises" in filename:
            continue
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


class ExperimentNameParser:
    """
    Shared parser to convert directory path into components.
    """

    def __init__(self, filename, indir):
        self.filename = filename
        self.indir = indir
        self.parse()

    def show(self):
        print(self.cloud, self.env, self.env_type, self.size)

    def parse(self):
        parts = self.filename.replace(self.indir + os.sep, "").split(os.sep)
        # These are consistent across studies
        self.cloud = parts.pop(0)
        self.env = parts.pop(0)
        self.env_type = parts.pop(0)
        size = parts.pop(0)

        # Experiment is the plot label
        self.experiment = os.path.join(self.cloud, self.env, self.env_type)

        # Prefix is an identifier for parsed flux metadata, jobspec and events
        self.prefix = os.path.join(self.experiment, size)

        # If these are in the size, they are additional identifiers to indicate the
        # environment type. Add to it instead of the size. I could skip some of these
        # but I want to see the differences.
        if "-" in size:
            size, _ = size.split("-", 1)
        self.size = int(size.replace("size", ""))


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
                "gpu_count",
            ]
        )

    def set_context(self, cloud, env, env_type, size, qualifier=None, gpu_count=0):
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
        self.gpu_count = gpu_count

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
            self.gpu_count,
        ]
        self.idx += 1


class ProblemSizeParser(ResultParser):
    """
    Extended ResultParser that includes a problem size.
    """

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
                "gpu_count",
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
            self.gpu_count,
        ]
        self.idx += 1


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


def remove_slurm_duration(item):
    """
    Remove the start and end time from the slurm output.
    """
    keepers = [x for x in item.split("\n") if not re.search("^(Start|End) time", x)]
    return "\n".join(keepers)


def skip_result(dirname, filename):
    """
    Return true if we should skip the result path.
    """
    # I don't know if these are results or testing, skipping for now
    # They are from aws parallel-cluster CPU
    if os.path.join("experiment", "data") in filename:
        return True

    if "compute-toolkit" in filename:
        return True
    # These are OK
    if "aks/cpu/size" in filename and "kripke" in filename:
        return False

    # These were redone with a placement group
    if (
        "aks/cpu/size" in filename
        and "placement" not in filename
        and "256" not in filename
        and "128" not in filename
    ):
        return True

    return (
        dirname.startswith("_")
        or "configs" in filename
        or "no-add" in filename
        or "noefa" in filename
        or "attempt-1" in filename
        or "no-placement" in filename
        or "shared-memory" in filename
    )


def set_group_color_properties(plot_name, color_code, label):
    # https://www.geeksforgeeks.org/how-to-create-boxplots-by-group-in-matplotlib/
    for k, v in plot_name.items():
        plt.setp(plot_name.get(k), color=color_code)

    # use plot function to draw a small line to name the legend.
    plt.plot([], c=color_code, label=label)
    plt.legend()


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
    do_round=False,
    round_by=3,
):
    """
    Helper function to make common plots.

    This also adds the normalized version

    Speedup: typically we do it in a way that takes into account serial/parallel.
    Speedup definition - normalize by performance at smallest size tested.
      This means taking each value and dividing by result at smallest test size (relative speed up)
      to see if conveys information better.
    """
    ext = ext.strip(".")
    plt.figure(figsize=(7, 6))
    sns.set_style("dark")
    ax = sns.stripplot(
        x=xdimension,
        y=ydimension,
        hue=hue,
        data=df,
        palette=palette,
    )

    plt.title(title)
    ax.set_xlabel(xlabel, fontsize=16)
    ax.set_ylabel(ylabel, fontsize=16)
    if log_scale is True:
        plt.gca().yaxis.set_major_formatter(
            plt.ScalarFormatter(useOffset=True, useMathText=True)
        )

    if do_round is True:
        ax.yaxis.set_major_formatter(FormatStrFormatter(f"%.{round_by}f"))
    plt.legend(facecolor="white")

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{plotname}.{ext}"))
    plt.clf()

    # If we have more than one node size, normalize by smallest
    if len(df.experiment.unique()) <= 1:
        return

    # We will assemble a column of speedups.
    #  1. Take smallest size for the experiment environment
    #  2. Calculate median metric for that size
    #  3. Calculate how many times that size goes into larger sizes (e.g., 32 goes into 64 twice)
    #  4. Multiply the median metric by that multiplier to get expected speedup
    # First, normalize the index so we can reliably reference it later
    df.index = list(range(0, df.shape[0]))
    df.loc[:, "speedup"] = [None] * df.shape[0]

    # We have to do by each experiment separately, because they don't all have the smallest size...
    # We can reassemble after with the indices
    for experiment in df.experiment.unique():
        # Subset of data frame just for that cloud and environment
        subset = df[df.experiment == experiment]

        # The smallest size (important, not all cloud/environments have the very smallest)
        # And get multiplier for all sizes based on the smallest. "column" would be a column
        # of multipliers, one specific to each row (that has a size)
        smallest = sorted(subset[xdimension].unique())[0]
        multipliers = {x: x / smallest for x in subset[xdimension].unique()}
        original_values = subset[ydimension].values

        # xdimension here is usually nodes or gpu_count
        column = [multipliers[x] for x in subset[xdimension].values]

        # Get the median for the smallest sizes, organized by experiment
        medians = (
            subset[subset[xdimension] == smallest]
            .groupby("experiment")[ydimension]
            .median()
        )
        medians = medians.to_dict()
        experiments = list(subset.experiment.values)

        # And we want to divide each experiment by its median at the smallest size
        speedup = []
        for i, experiment in enumerate(experiments):
            multiplier = column[i]
            original_value = original_values[i]
            # divide by the median of the smallest size, not the multiplier
            speedup.append(original_value / medians[experiment])

        # Fill the speedup in back at the experiment indices
        df.loc[subset.index, "speedup"] = speedup

    # Replace the initial value of interest with the speedup (this gets thrown away after plot)
    df[ydimension] = df["speedup"]
    plt.figure(figsize=(7, 6))
    sns.set_style("dark")
    ax = sns.stripplot(
        x=xdimension,
        y=ydimension,
        hue=hue,
        data=df,
        palette=palette,
    )

    plt.title(title + " Speedup")
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel + " (Speedup)", fontsize=14)
    if log_scale is True:
        plt.gca().yaxis.set_major_formatter(
            plt.ScalarFormatter(useOffset=True, useMathText=True)
        )

    if do_round is True:
        ax.yaxis.set_major_formatter(FormatStrFormatter(f"%.{round_by}f"))
    plt.legend(facecolor="white")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{plotname}-speedup-scaled.{ext}"))
    plt.clf()
