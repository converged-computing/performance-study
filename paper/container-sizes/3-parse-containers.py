#!/usr/bin/env python3

import argparse
import collections
import json
import os
import re
import sys
from datetime import datetime

import matplotlib.pylab as plt
import pandas
import seaborn as sns

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)
sys.path.insert(0, root)

import performance_study as ps

timestamp_format = "%Y-%m-%dT%H:%M:%SZ"


def get_parser():
    parser = argparse.ArgumentParser(description="Dockerfile Parser")
    parser.add_argument(
        "--data",
        default=os.path.join(here, "data"),
        help="data directory for results",
    )
    return parser


def read_file(filename):
    with open(filename, "r") as fd:
        content = fd.read()
    return content


def read_json(filename):
    return json.loads(read_file(filename))


def write_json(obj, filename):
    with open(filename, "w") as fd:
        fd.write(json.dumps(obj, indent=4))


def main():
    parser = get_parser()
    args, _ = parser.parse_known_args()

    if not os.path.exists(args.data):
        sys.exit(f"{args.data} does not exist.")

    # Output directory for images
    data_dir = os.path.join(args.data, "img")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Read in raw times, which also has cloud, etc.
    times = read_json(os.path.join(args.data, "raw-times.json"))

    # Parse them into data frame too.
    times_df = parse_times(times)
    plot_times(times_df, data_dir)


def parse_time_pulled(time_pulled):
    minutes = 0
    # First check for milliseconds, if reported in ms there aren't seconds or minutes
    if "ms" in time_pulled:
        return float(time_pulled.replace("ms", "", 1)) / 1000
    if "m" in time_pulled:
        minutes, rest = time_pulled.split("m", 1)
        minutes = int(minutes)
        time_pulled = rest
    seconds = float(time_pulled.rstrip("s"))
    return (minutes * 60) + seconds


def parse_times(times):
    """
    Read events and turn into data frame with container pull times
    """
    df = pandas.DataFrame(
        columns=[
            "event",
            "duration",
            "container",
            "cloud",
            "environment",
            "exp_size",
            "exp_type",
            "experiment",
        ]
    )
    idx = 0
    for _, item in times.items():
        # Parse experiment name
        experiment = item["experiment"]
        parts = experiment.split(os.sep)
        cloud = parts.pop(0)
        environment = parts.pop(0)
        exp_type = parts.pop(0)  # gpu vs cpu
        # The only experiment without a stated size is aws eks gpu, size 16
        size = "size16"
        if parts:
            size = parts.pop(0)

        if "broken" in size or "noefa" in size:
            continue
        container = item.get("container")
        if not container and "pulled" in item["events"]:
            container = (
                re.search('["].*["]', item["events"]["pulled"]["message"])
                .group()
                .strip('"')
            )

        # We can do our own calculation based on timestamps here
        # These seem to be better in terms of granularity
        seconds = None
        # We can derive pull plus waiting from the message here
        # This is better data
        if "pulled" in item["events"] and seconds is None:
            message = item["events"]["pulled"]["message"]
            # If it's already pulled, don't count it
            if "already present on machine" in message.lower():
                continue
            time_pulled = re.search("[(].*[)]", message)
            time_pulled = time_pulled.group().split(" ")[0].replace("(", "")
            # parse time pulled
            seconds = parse_time_pulled(time_pulled)

        elif "pulling" in item["events"] and "pulled" in item["events"]:
            start = item["events"]["pulling"]["timestamp"]
            end = item["events"]["pulled"]["timestamp"]
            parsed_end = datetime.strptime(end, timestamp_format)
            parsed_start = datetime.strptime(start, timestamp_format)
            elapsed = parsed_end - parsed_start
            seconds = elapsed.min.seconds + elapsed.seconds

        if seconds is not None:
            df.loc[idx, :] = [
                "pulled",
                seconds,
                container,
                cloud,
                environment,
                size,
                exp_type,
                experiment,
            ]
            idx += 1
    return df


def plot_times(df, outdir):
    """
    Plot containers, generating images in the output directory.
    """
    plot_containers(df, outdir)

    # Show total pulling time across sizes, so we can estimate cost
    for cloud in df.cloud.unique():
        subset = df[df.cloud == cloud]
        for environment in subset.environment.unique():
            subset = subset[subset.environment == environment]
            for typ in subset.exp_type.unique():
                typset = subset[subset.exp_type == typ]
                total_duration = typset.duration.sum()
                print(
                    f"Cloud {cloud} for {environment} {typ}: {total_duration} seconds"
                )

    # Save unique containers for each
    uniques = {}
    # Filter to different apps.
    for app in [
        "amg",
        "kripke",
        "lammps",
        "single-node",
        "minife",
        "mixbench",
        "gem",
        "osu",
        "magma",
        "stream",
        "quicksilver",
        "multi-gpu-models",
        "laghos",
    ]:
        app_outdir = os.path.join(outdir, app)
        if not os.path.exists(app_outdir):
            os.makedirs(app_outdir)
        app_containers = [x for x in df.container if app in x]
        app_df = df[df.container.isin(app_containers)]
        app_df.to_csv(os.path.join(outdir, f"{app}-pull-times.csv"))
        plot_containers(
            app_df,
            app_outdir,
            save_prefix=f"pull_times_{app}",
            # I'm not filtering out any yet because I want to see everything
            filter_below=None,
            suffix=f"({app})",
        )
        uniques[app] = list(app_df.container.unique())

    # Report unique containers for each
    print()
    for app, containers in uniques.items():
        print(f"{app} has {len(containers)} containers")
        for container in containers:
            print(f" {container}")


def plot_containers(df, outdir, save_prefix=None, filter_below=None, suffix=None):
    """
    Given an output directory, plot image to show pull times.
    """
    save_prefix = save_prefix or "pull_times_experiment_type"

    # Assume containers need at least 20 seconds to pull
    if filter_below is not None:
        df = df[df.duration > filter_below]

    # Let's just plot CPU since we have partial GPU for aws
    subset = df[df.exp_type == "cpu"]
    sizes = [
        int(x.replace("-placement", "").replace("-shared-memory", "").split("size")[-1])
        for x in subset.exp_size
    ]
    subset.loc[:, "experiment_size"] = sizes

    # Break into our experiment containers vs others
    container_types = []
    for x in subset.container.tolist():
        if "converged-computing" in x:
            container_types.append("experiment-container")
        else:
            container_types.append("kubernetes-container")

    # Let's first plot pull times by experiment
    cloud_colors = {}
    for cloud in df.experiment.unique():
        cloud_colors[cloud] = ps.match_color(cloud)

    # Ensure we have the color for just the cloud
    # E.g., an experiment azure/aks needs just the lookup of azure for the plot palette
    updates = {}
    for cloud, color in cloud_colors.items():
        cloud = cloud.split("/", 1)[0]
        updates[cloud] = color
    cloud_colors.update(updates)

    subset.loc[:, "container_type"] = container_types
    subset = subset[subset.container_type == "experiment-container"]
    make_plot(
        subset,
        title="Pull times for CPU Containers Across Cluster Sizes",
        ydimension="duration",
        xdimension="experiment_size",
        outdir=outdir,
        ext="png",
        plotname=f"{save_prefix}_all_clouds_cpu",
        hue="cloud",
        palette=cloud_colors,
        plot_type="bar",
        xlabel="Size (Nodes)",
        ylabel="Pull time (seconds)",
        dodge=True,
        width=12,
        height=6,
    )


def make_plot(
    df,
    title,
    ydimension,
    xdimension,
    xlabel,
    ylabel,
    palette=None,
    ext="pdf",
    plotname="lammps",
    plot_type="violin",
    hue=None,
    outdir="img",
    dodge=False,
    width=12,
    height=8,
):
    """
    Helper function to make common plots.
    """
    plotfunc = sns.boxplot
    if plot_type == "violin":
        plotfunc = sns.violinplot

    ext = ext.strip(".")
    plt.figure(figsize=(width, height))
    sns.set_style("whitegrid")
    if plot_type == "violin":
        ax = plotfunc(
            x=xdimension, y=ydimension, hue=hue, data=df, linewidth=0.8, palette=palette
        )
    else:
        ax = plotfunc(
            x=xdimension,
            y=ydimension,
            hue=hue,
            data=df,
            linewidth=0.8,
            palette=palette,
            whis=[5, 95],
            dodge=dodge,
        )

    plt.title(title, fontsize=16)
    ax.set_xlabel(xlabel, fontsize=16)
    ax.set_ylabel(ylabel, fontsize=16)
    ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=16)
    ax.set_yticklabels(ax.get_yticks(), fontsize=16)
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{plotname}.{ext}"))
    plt.clf()


if __name__ == "__main__":
    main()
