#!/usr/bin/env python3

# Shared functions to use across analyses.

import json
import os
import re

from matplotlib.ticker import FormatStrFormatter
import matplotlib.pylab as plt
import pandas
import seaborn as sns
import yaml

sns.set_theme(style="whitegrid", palette="muted")
sns.set_style("whitegrid", {"legend.frameon": True})

# Manually created color palette
cloud_prefixes = [
    "azure/aks",
    "aws/eks",
    "google/gke",
    "google/compute-engine",
    "aws/parallel-cluster",
    "on-premises/dane",
    "azure/cyclecloud",
    "on-premises/lassen",
]

cloud_prefixes.sort()

# colors = sns.color_palette("muted", len(cloud_prefixes))
# hexcolors = colors.as_hex()
# colors = {}
# for cloud in cloud_prefixes:
#    colors[cloud] = hexcolors.pop(0)
colors = {
    "azure/aks": "#004589",
    "aws/parallel-cluster": "#FF9900",
    "aws/eks": "#CC5500",
    "google/gke": "#FBBC04",
    "google/compute-engine": "#EA4335",
    "on-premises/a": "gray",
    "on-premises/dane": "gray",
    "azure/cyclecloud": "#0080ff",
    "on-premises/lassen": "gray",
    "on-premises/b": "gray",
}


def match_color(cloud):
    """
    Match the color for an environment
    """
    if "lassen" in cloud:
        cloud = "on-premises/b"
    if "dane" in cloud:
        cloud = "on-premises/a"
    # We assume the environ name (e.g., azure/aks) is shorter than
    # the one provided (e.g., azure/aks/cpu)
    for environ, color in colors.items():
        if environ in cloud:
            return color
    raise ValueError(f"Did not find color for {cloud}")


def read_yaml(filename):
    with open(filename, "r") as fd:
        content = yaml.safe_load(fd)
    return content


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


def print_experiment_cost(
    df, outdir, duration_field="duration", problem_size="", iterations=5
):
    """
    Based on costs of instances, calculate the cost for runs
    """
    # Lookup for prices.
    # This is not saying on-premises costs nothing, but rather that
    # we cannot share / disclose (and we aren't entirely sure)
    instance_costs = {
        "google/gke/cpu": 5.06,
        "google/gke/gpu": 23.36,
        "google/compute-engine/cpu": 5.06,
        "google/compute-engine/gpu": 23.36,
        "aws/eks/cpu": 2.88,
        "aws/eks/gpu": 34.33,
        "on-premises/a/cpu": None,
        "on-premises/b/gpu": None,
        "on-premises/dane/cpu": None,
        "on-premises/lassen/gpu": None,
        "aws/parallel-cluster/cpu": 2.88,
        "azure/cyclecloud/cpu": 3.60,
        "azure/cyclecloud/gpu": 22.03,
        "azure/aks/cpu": 3.60,
        "azure/aks/gpu": 22.03,
    }

    cost_df = pandas.DataFrame(columns=["experiment", "cost", "size", "duration"])
    idx = 0

    # aren't calculating on prem costs because we can't
    for size in df.nodes.unique():
        subset = df[(df.metric == "duration") & (df.nodes == size)]
        subset["cost_per_hour"] = [instance_costs[x] for x in subset.experiment.values]

        # This converts seconds to hours
        hourly_cost_node = (subset["value"] / 60 / 60) * subset["cost_per_hour"]

        # Multiply by number of nodes.
        # row.value is duration in seconds
        subset["cost"] = hourly_cost_node * size
        for idx, row in subset.iterrows():
            cost_df.loc[idx, :] = [row.experiment, row.cost, row.nodes, row.value]
            idx += 1

    cost_comparison_df = pandas.DataFrame(
        columns=["experiment", "size", "iterations", "cost", "duration"]
    )
    cost_idx = 0

    # Also build a data frame that calculates based on 5 iterations, and if
    # we have less than 5, we use median value.
    for experiment in cost_df.experiment.unique():
        # We don't have on premises costs
        if "on-premises" in experiment:
            continue
        subset = cost_df[cost_df.experiment == experiment]
        for size in subset["size"].unique():
            size_subset = subset[subset["size"] == size]
            # Case 1: zero entries, we can't count really
            if size_subset.shape[0] == 0:
                cost_comparison_df.loc[cost_idx, :] = [
                    experiment,
                    size,
                    iterations,
                    None,
                    None,
                ]
                cost_idx += 1
                continue
            elif size_subset.shape[0] < iterations:
                median = size_subset.cost.median()
                duration = size_subset.duration.median()
                for _ in range(0, iterations - size_subset.shape[0]):
                    cost_df.loc[idx, :] = [experiment, median, size, duration]
                    idx += 1
            elif size_subset.shape[0] > 5:
                size_subset = size_subset.loc[size_subset.index[0:5], :]
            # Other case is we have exactly 5.
            # Finally, add the values
            cost_comparison_df.loc[cost_idx, :] = [
                experiment,
                size,
                iterations,
                size_subset.cost.sum(),
                size_subset.duration.sum(),
            ]
            cost_idx += 1

    # Add median and std of duration to each        
    # print(cost_df.groupby(['experiment']).cost.sum().sort_values())
    print("Experiment costs - missing runs (cost by size)")
    print(
        cost_comparison_df.groupby(["experiment", "size", "iterations", "duration"])
        .cost.sum()
        .sort_values()
    )
    cost_df.to_csv(os.path.join(outdir, f"cost-by-environment{problem_size}.csv"))
    cost_comparison_df.to_csv(
        os.path.join(outdir, f"cost-by-environment-5-iterations{problem_size}.csv")
    )


def convert_walltime_to_seconds(walltime):
    """
    This is from flux and the function could be shared
    """
    # An integer or float was provided
    if isinstance(walltime, int) or isinstance(walltime, float):
        return int(float(walltime) * 60.0)

    # A string was provided that will convert to numeric
    elif isinstance(walltime, str) and walltime.isnumeric():
        return int(float(walltime) * 60.0)

    # A string was provided that needs to be parsed
    elif ":" in walltime:
        seconds = 0.0
        for i, value in enumerate(walltime.split(":")[::-1]):
            seconds += float(value) * (60.0**i)
        return seconds

    # Don't set a wall time
    elif not walltime or (isinstance(walltime, str) and walltime == "inf"):
        return 0

    # If we get here, we have an error
    msg = (
        f"Walltime value '{walltime}' is not an integer or colon-" f"separated string."
    )
    raise ValueError(msg)


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
    order=None,
    log_scale=False,
    do_round=False,
    no_legend=False,
    hue_order=None,
    bottom_legend=False,
    round_by=3,
    width=12,
    height=6,
):
    """
    Helper function to make common plots.

    This is largely not used. I was too worried to have the generalized function
    not work for a specific plot so I just redid them all manually. Ug.

    Speedup: typically we do it in a way that takes into account serial/parallel.
    Speedup definition - normalize by performance at smallest size tested.
      This means taking each value and dividing by result at smallest test size (relative speed up)
      to see if conveys information better.
    """
    # Replace the initial value of interest with the speedup (this gets thrown away after plot)
    plt.figure(figsize=(width, height))
    sns.set_style("whitegrid")
    ax = sns.barplot(
        df,
        x=xdimension,
        y=ydimension,
        hue=hue,
        hue_order=hue_order,
        palette=palette,
        order=order,
        err_kws={"color": "darkred"},
    )
    plt.title(title, fontsize=14)
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    if log_scale is True:
        plt.gca().yaxis.set_major_formatter(
            plt.ScalarFormatter(useOffset=True, useMathText=True)
        )

    if do_round is True:
        ax.yaxis.set_major_formatter(FormatStrFormatter(f"%.{round_by}f"))
    if bottom_legend:
        # Get the current x-axis label
        xlabel = ax.get_xlabel()
        x_min, x_max = ax.get_xlim()
        x_pos = x_min + 0.2
        # Remove the default x-axis label
        ax.set_xlabel("")
        # Add the new x-axis label at the desired position
        ax.text(x_pos, ax.get_ylim()[0] - 30, xlabel, ha="left", va="top")
        plt.legend(loc="lower center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    elif no_legend:
        plt.legend().remove()
    else:
        plt.legend(facecolor="white")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{plotname}-speedup-scaled.svg"))
    plt.clf()
