#!/usr/bin/env python3

# Shared functions to use across analyses.

import json
import os
import re

from matplotlib.ticker import FormatStrFormatter
import matplotlib.pylab as plt
import pandas
import seaborn as sns

sns.set_theme(style="whitegrid", palette="pastel")


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

    # These are OK
    if "aks/cpu/size" in filename and "kripke" in filename:
        return False

    # These were redone with a placement group
    if "aks/cpu/size" in filename and "placement" not in filename and "256" not in filename and "128" not in filename:
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

    if do_round is True:
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{plotname}.{ext}"))
    plt.clf()
