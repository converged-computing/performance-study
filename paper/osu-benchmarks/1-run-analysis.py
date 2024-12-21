#!/usr/bin/env python3

import argparse
import os
import re
import sys

import plotly.graph_objects as go
import matplotlib.pylab as plt
import pandas
import seaborn as sns
from metricsoperator.metrics.network.osu_benchmark import parse_multi_section

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="dark", palette="muted")

import numpy as np
from mpl_toolkits.mplot3d import Axes3D

# These are files I found erroneous - no result, or incomplete result
errors = []
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

    # If flag is added, also parse on premises data
    args.on_premises = True
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories
    files = ps.find_inputs(indir, "osu", args.on_premises)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    parsed = parse_data(indir, outdir, files)
    plot_results(parsed, outdir)


def split_combined_file(item, host_prefix="flux-sample"):
    """
    split combinations of OSU
    """
    # Remove lines with flux sample prints.
    # We could use this somewhere to derive pairs, but it's too hard
    # a parse for this first level analysis
    lines = [x for x in item.split("\n") if host_prefix not in x]

    # Each section has a last entry for size 4194304
    sections = []
    section = []
    last_line = None
    while lines:
        line = lines.pop(0)
        if not line.strip():
            continue

        # Get rid of these labels, not helpful
        if "Allreduce iteration" in line:
            continue
        # This is the start of an error and we need to stop parsing
        if "failed" in line:
            break
        section.append(line)

        # This is cyclecloud - ends with 1048576 or 4096 or 262144
        # These are likely incomplete runs
        if (
            line.startswith("#")
            and last_line
            and re.search("(1048576|4096|262144)", last_line)
        ):
            section.pop()
            sections.append(section)
            section = [line]

        # Reset when we get to the end
        if re.search("4194304", line) and section:
            sections.append(section)
            section = []
        last_line = line

    # Last hanging section, often has partial data
    if section:
        sections.append(section)
    return sections


def remove_cuda_line(item):
    """
    Remove the cuda metadata line for now.

    Ideally we should use it to validate, but we also know from
    commands what we ran and can come back to this.
    """
    idx = None
    for i, line in enumerate(item):
        if "Send Buffer" in line:
            idx = i
    if idx is not None:
        item.pop(idx)


def find_osu_command(metadata):
    """
    Find the osu command, meaning the line with the osu executable. This
    can be confused with the singularity container, etc.
    """
    command = metadata["jobspec"]["tasks"][0]["command"]
    for line in command:
        # Be pedantic
        if re.search("(osu_latency|osu_bw|osu_allreduce)$", line):
            return os.path.basename(line)
    raise ValueError(f"Cannot find osu command in {command}")


def clean_cyclecloud(item):
    """
    CycleCloud is different because it has:

    1. Loading messages for modules
    2. time wrappers
    3. Iterations counts
    """
    lines = [x for x in item.split("\n") if not re.search("(Loading|hpcx)", x)]
    # Time wrappers show up sometimes
    lines = [x for x in lines if not re.search("^(real|user|sys) ", x)]
    return "\n".join(lines)


def split_combined_file_on_premises(item, host_prefix):
    """
    split combinations of OSU
    """
    # Job info
    skip_regex = "(PST|PDT|JobID|Hosts)"
    lines = [
        x
        for x in item.split("\n")
        if x and host_prefix not in x and not re.search(skip_regex, x)
    ]

    # Each section has a last entry for size 4194304
    sections = []
    section = []
    last_line = None
    while lines:
        line = lines.pop(0)
        if not line.strip():
            continue

        # Get rid of these labels, not helpful
        if "Allreduce iteration" in line:
            continue
        # This is the start of an error and we need to stop parsing
        if "failed" in line:
            break
        section.append(line)

        if (
            line.startswith("#")
            and last_line
            and re.search("(1048576|4096|262144)", last_line)
        ):
            section.pop()
            sections.append(section)
            section = [line]

        # Reset when we get to the end (largest size)
        if re.search("4194304", line) and section:
            sections.append(section)
            section = []
        last_line = line

    # Last hanging section, often has partial data
    if section:
        sections.append(section)
    return sections


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # For flux we can save jobspecs and other event data
    data = {}
    parsed = []

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

        # Cyclecloud GPU had multiple types, osu-dd and osu-hh
        # For Google Cloud GPU on GKE the point to point benchmarks
        # were run without GPU - never worked
        exp.show()

        # Now we can read each result file to get metrics.
        results = list(ps.get_outfiles(filename))
        for result in results:
            # Skip over found erroneous results
            if errors and re.search(error_regex, result):
                print(f"Skipping {result} due to known missing result or error.")
                continue

            # Basename that start with underscore are test or otherwise should not be included
            if os.path.basename(result).startswith("_"):
                continue
            item = ps.read_file(result)

            # On premises results have a totally different format
            if "on-premises" in filename:
                item = item.split(
                    "------------------------------------------------------------", 1
                )[0]

                # These are combined files with OSU that have all the results in one file
                cluster_name = "lassen" if "lassen" in filename else "dane"
                for section in split_combined_file_on_premises(item, cluster_name):
                    if "lassen" in filename:
                        remove_cuda_line(section)
                    command = "osu_latency"
                    if "Bandwidth" in "\n".join(section):
                        command = "osu_bw"
                    elif "Allreduce" in "\n".join(section):
                        command = "osu_allreduce"
                    matrix = parse_multi_section([command] + section)
                    matrix["context"] = [exp.cloud, exp.env, exp.env_type, exp.size]
                    parsed.append(matrix)
                continue

            # compute engine GPU had smcuda bugs for our first try, and we ran anyway with DD/HH
            # these were ultimately fixed, and we want to skip these runs in osu. The fixed
            # runs are in osu-allreduce in the same results directory. I verified that smcuda
            # does not appear anywhere else in this directory.
            if "compute-engine/gpu" in result and "smcuda" in item:
                continue

            # gke gpu had a string of warnings we need to parse out before the result
            # This finds the index of the header and then parses out the warning
            line = [
                x for x in item.split("\n") if re.search("(Allreduce|Send Buffer)", x)
            ]
            if re.search("(gke/gpu|compute-engine|eks/gpu)", result) and line:
                item = item.split("\n")
                idx = item.index(line[-1])
                item = item[idx:]
                item = "\n".join(item)

            # These are combined files with OSU that have all the
            # results in one file, parse it differently. No flux metadata here.
            host_prefix = "flux-sample"
            if re.search("(combinations-|parallel-cluster|cyclecloud)", result):
                # I don't know what to do with start/end (duration) for
                # all runs - we can't say anything about a specific run.
                # So here we are removing it for those that used slurm
                item = ps.remove_slurm_duration(item)
                if "parallel-cluster" in result:
                    host_prefix = "queue1-"
                elif "cyclecloud" in result:
                    host_prefix = "cluster-" if "cpu" in result else "ccloud-"
                    # CycleCloud has loading messages interleaved and times
                    item = clean_cyclecloud(item)

                for section in split_combined_file(item, host_prefix):
                    remove_cuda_line(section)
                    # This was an empty line for cyclecloud
                    if not section:
                        continue
                    # This is another parsing issue with cyclecloud - we
                    # get a bunch of allreduce in one result.
                    # This is harder because we don't have flux metadata
                    # with the command in a combined file. But we know the combinations
                    # file is a pairing of bandwidth and latency
                    command = "osu_latency"
                    if "Bandwidth" in "\n".join(section):
                        command = "osu_bw"
                    elif "Allreduce" in "\n".join(section):
                        command = "osu_allreduce"

                    # Special cases - directories to indicate command
                    # These are only present for cyclecloud. Note
                    # that we are not using osu-dd (device to device)
                    # as that result is only possible on cycle cloud
                    # with GPU Direct RDMA
                    if "osu-dd" in result:
                        continue
                    # We assume osu-hh is the same as regular osu without it
                    matrix = parse_multi_section([command] + section)
                    matrix["context"] = [exp.cloud, exp.env, exp.env_type, exp.size]
                    parsed.append(matrix)

            # If this is a flux run, we have a jobspec and events here
            # We can get the type of command from this.
            elif "JOBSPEC" in item:
                item, duration, metadata = ps.parse_flux_metadata(item)

                # The osu parser expects cleaned, as lines
                item = item.strip().split("\n")
                data[exp.prefix].append(metadata)

                # If we have cuda, the first line will be a send buffer message
                remove_cuda_line(item)

                # osu_latency, osu_bw, osu_allreduce
                command = find_osu_command(metadata)

                # The command above is included in this parsed metadata, which is used to
                # derive the organization of the data frames in plot_results
                # Note that header would be consistent to provide a title,
                # but not here because of the cuda line. So we are just
                # going to use the command.
                matrix = parse_multi_section([command] + item)
                matrix["context"] = [exp.cloud, exp.env, exp.env_type, exp.size]
                parsed.append(matrix)

            # Slurm has the item output, and then just the start/end of the job
            else:
                raise ValueError(f"Unexpected result to parse: {item}")

    print("Done parsing OSU results!")
    ps.write_json(parsed, os.path.join(outdir, "osu-parsed.json"))
    ps.write_json(data, os.path.join(outdir, "flux-jobspec-events.json"))
    return parsed


def get_columns(command):
    """
    Get columns for data frame depending on command
    """
    # Size       Avg Latency(us)
    if "allreduce" in command:
        return ["size", "avg_latency_us"]
    # Size          Latency (us)
    elif "latency" in command:
        return ["size", "latency_us"]
    # Size      Bandwidth (MB/s)
    return ["size", "bandwidth_mb_s"]


def plot_results(results, outdir):
    """
    Plot result images to file
    """
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Create a data frame for each result type, also lookup by size
    # For osu latency we will combine into one size (2 nodes)
    # Keep gpu and cpu results separate to be conservative
    dfs_cpu = {}
    idxs_cpu = {}
    dfs_gpu = {}
    idxs_gpu = {}

    # lookup for x and y values for each
    lookup_cpu = {}
    lookup_gpu = {}
    for entry in results:
        # The source of truth is the command
        command = entry["command"]
        is_gpu = entry["context"][2] == "gpu"

        title = command
        if is_gpu and title not in dfs_gpu:
            dfs_gpu[title] = {}
            idxs_gpu[title] = {}
            lookup_gpu[title] = {}
        elif title not in dfs_cpu:
            dfs_cpu[title] = {}
            idxs_cpu[title] = {}
            lookup_cpu[title] = {}

        size = entry["context"][-1]

        # Calculate number of gpus from nodes
        number_gpus = 0
        if is_gpu:
            number_gpus = (
                (size * 4) if "on-premises" in entry["context"][0] else (size * 8)
            )

        columns = get_columns(title) + [
            "experiment",
            "cloud",
            "env",
            "env_type",
            "nodes",
            "gpu_count",
        ]

        dimension = number_gpus if is_gpu else size
        experiment = os.sep.join(entry["context"][:-1] + [command])

        if is_gpu and number_gpus not in dfs_gpu[title]:
            dfs_gpu[title][number_gpus] = pandas.DataFrame(columns=columns)
            idxs_gpu[title][number_gpus] = 0
            lookup_gpu[title][number_gpus] = {"x": columns[0], "y": columns[1]}

        elif not is_gpu and size not in dfs_cpu[title]:
            dfs_cpu[title][size] = pandas.DataFrame(columns=columns)
            idxs_cpu[title][size] = 0
            lookup_cpu[title][size] = {"x": columns[0], "y": columns[1]}

        # Add command to experiment id since it includes unique command
        if is_gpu:
            for datum in entry["matrix"]:
                dfs_gpu[title][number_gpus].loc[idxs_gpu[title][number_gpus], :] = (
                    datum + [experiment] + entry["context"] + [number_gpus]
                )
                idxs_gpu[title][number_gpus] += 1
        else:
            for datum in entry["matrix"]:
                dfs_cpu[title][size].loc[idxs_cpu[title][size], :] = (
                    datum + [experiment] + entry["context"] + [number_gpus]
                )
                idxs_cpu[title][size] += 1

    # Make an output directory for plots by size
    plots_by_size = os.path.join(img_outdir, "by_size")
    if not os.path.exists(plots_by_size):
        os.makedirs(plots_by_size)

    # Save each completed data frame to file and plot!
    for slug, sizes in dfs_cpu.items():
        for size, subset in sizes.items():
            print(f"Preparing plot for {slug} size {size}")

            # Save entire (unsplit) data frame to file
            subset.to_csv(os.path.join(outdir, f"{slug}-{size}-cpu-dataframe.csv"))

            # Separate x and y - latency (y) is a function of size (x)
            xlabel = "Message size in bytes"
            x = lookup_cpu[slug][size]["x"]
            y = lookup_cpu[slug][size]["y"]

            # Make each figure a little bigger
            plt.figure(figsize=(8, 6))

            # for sty in plt.style.available:
            ax = sns.lineplot(
                data=subset,
                hue="experiment",
                x=x,
                y=y,
                markers=True,
                dashes=True,
                errorbar=("ci", 95),
            )
            plt.title(slug + " CPU " + str(size) + " Nodes")
            y_label = y.replace("_", " ")
            ax.set_xlabel(xlabel + " (logscale)", fontsize=16)
            ax.set_ylabel(y_label + " (logscale)", fontsize=16)
            ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
            ax.set_yticklabels(ax.get_yticks(), fontsize=14)
            plt.xscale("log")
            plt.yscale("log")
            plt.legend(facecolor="white")
            plt.tight_layout()
            plt.savefig(os.path.join(plots_by_size, f"{slug}_size-{size}_cpu.png"))
            plt.clf()
            plt.close()

    # Save each completed data frame to file and plot!
    for slug, sizes in dfs_gpu.items():
        for size, subset in sizes.items():
            print(f"Preparing plot for {slug} size {size}")

            # Save entire (unsplit) data frame to file
            subset.to_csv(os.path.join(outdir, f"{slug}-{size}-gpu-dataframe.csv"))

            # Separate x and y - latency (y) is a function of size (x)
            xlabel = "Message size in bytes"
            x = lookup_gpu[slug][size]["x"]
            y = lookup_gpu[slug][size]["y"]

            # Make each figure a little bigger
            plt.figure(figsize=(8, 6))

            # for sty in plt.style.available:
            ax = sns.lineplot(
                data=subset,
                hue="experiment",
                x=x,
                y=y,
                markers=True,
                dashes=True,
                errorbar=("ci", 95),
            )
            plt.title(slug + " " + str(size) + " GPUs")
            y_label = y.replace("_", " ")
            ax.set_xlabel(xlabel + " (logscale)", fontsize=16)
            ax.set_ylabel(y_label + " (logscale)", fontsize=16)
            ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
            ax.set_yticklabels(ax.get_yticks(), fontsize=14)
            plt.xscale("log")
            plt.yscale("log")
            plt.legend(facecolor="white")
            plt.tight_layout()
            plt.savefig(os.path.join(plots_by_size, f"{slug}_size-{size}_gpu.png"))
            plt.clf()
            plt.close()

    # As we go through sizes, for all reduce and bw collect data in rows for surface plot
    # We can't keep all the values, so we will calculate the medium, and then top / lower quartile
    #   X dimension: will be message sizes (logscale)
    #   Y dimension: will be latency (also logscale)
    #   Z dimension: goes across the number of nodes
    surfaces = {}
    for slug, sizes in dfs_cpu.items():
        for size, subset in sizes.items():
            if "latency_us" in subset:
                continue

            # X dimension: will be message sizes (logscale)
            # Y dimension: will be latency (also logscale)
            # We probably need this in log scale
            dimension = "avg_latency_us"
            if "avg_latency_us" not in subset:
                dimension = "bandwidth_mb_s"
            bytes_sizes = subset["size"].unique().tolist()
            values = np.log(subset[dimension].tolist())
            y = np.linspace(values.min(), values.max(), len(bytes_sizes))

            # We need to do this for each environment since we are using matlab
            for experiment in subset.experiment.unique():
                # lower and upper will be used to calculate some kind of error bars
                exp_df = subset[subset.experiment == experiment]

                # Median, and upper and lower bounds (25th/75th quantile) for surface plot
                exp_df[dimension] = exp_df[dimension].astype(float)

                # Note that these currently aren't used
                # lower = exp_df.groupby("size")[dimension].quantile(0.25)
                # upper = exp_df.groupby("size")[dimension].quantile(0.75)
                if "aws" in experiment:
                    slug = "aws"
                elif "google" in experiment:
                    slug = "gcp"
                else:
                    slug = "azure"

                # Median we will save as the row for the experiment size
                median = exp_df.groupby("size")[dimension].median()
                if experiment not in surfaces:
                    surfaces[experiment] = {
                        "x": np.log(bytes_sizes),
                        "y": y,
                        "slug": slug,
                        "z": [],
                        "y_labels": [],
                        "title": dimension,
                    }
                # This is the data going backward - the medians across sizes
                surfaces[experiment]["z"].append(np.log(median.values))
                surfaces[experiment]["y_labels"].append(size)

    # Generate a surface plot for each
    # Path for html needs to be relative
    relpath = os.path.relpath(img_outdir, here)
    html_path = os.path.join(relpath, "web")
    if not os.path.exists(html_path):
        os.makedirs(html_path)
    for experiment, meta in surfaces.items():
        x_bytes = meta["x"]
        slug = meta["slug"]
        cloud = "-".join(experiment.split(os.sep)[0:2])
        label = os.sep.join(experiment.split(os.sep, 2)[0:2])
        y_labels = meta["y_labels"]
        z_nodes = meta["z"]
        if slug == "aws":
            color = "YlOrBr"
        elif slug == "azure":
            color = "PuBu"
        else:
            color = "RdYlBu"
        trace = go.Surface(
            x=x_bytes,
            y=y_labels,
            z=z_nodes,
            colorscale=color,
            cauto=False,
            showscale=False,
        )
        data = [trace]
        fig = go.Figure(data=data)
        if meta["title"] == "bandwidth_mb_s":
            fig.update_scenes(
                xaxis_title_text="Message Size in Bytes (logscale)",
                yaxis_title_text="Nodes",
                zaxis_title_text="Bandwidth Average Latency MB/s (logscale)",
                xaxis_autorange="reversed",
            )
            fig.update_layout(
                width=1000,
                height=1000,
                # margin=dict(l=0, r=0, t=0, b=0),
                title=f"OSU Bandwidth (CPU) for {label}",
                scene_camera={
                    "eye": {"x": 0.0, "y": 2.0, "z": 0.75},
                    "up": {"x": 0, "y": 0, "z": 0},
                    "center": {"x": 0, "y": 0, "z": 0},
                },
            )
            fig.write_image(
                os.path.join(img_outdir, f"{cloud}-bandwidth-surface-plot.png")
            )
            fig.write_html(
                os.path.join(html_path, f"{cloud}-bandwidth-surface-plot.html")
            )

        elif meta["title"] == "avg_latency_us":
            fig.update_scenes(
                xaxis_title_text="Message Size in Bytes (logscale)",
                yaxis_title_text="Nodes",
                zaxis_title_text="Average Latency MB/s (logscale)",
                xaxis_autorange="reversed",
            )
            fig.update_layout(
                width=1000,
                height=1000,
                # margin=dict(l=0, r=0, t=0, b=0),
                title=f"OSU All Reduce (CPU) for {label}",
                scene_camera={
                    "eye": {"x": 0.0, "y": 2.0, "z": 0.75},
                    "up": {"x": 0, "y": 0, "z": 0},
                    "center": {"x": 0, "y": 0, "z": 0},
                },
            )
            fig.write_image(
                os.path.join(img_outdir, f"{cloud}-allreduce-surface-plot.png")
            )
            fig.write_html(
                os.path.join(html_path, f"{cloud}-allreduce-surface-plot.html")
            )

        else:
            fig.update_scenes(
                xaxis_title_text="Message Size in Bytes (logscale)",
                yaxis_title_text="Nodes",
                zaxis_title_text="Average Latency MB/s (logscale)",
                xaxis_autorange="reversed",
            )
            fig.update_layout(
                width=1000,
                height=1000,
                # margin=dict(l=0, r=0, t=0, b=0),
                title=f"OSU Latency (CPU) for {label}",
                scene_camera={
                    "eye": {"x": 0.0, "y": 2.0, "z": 0.75},
                    "up": {"x": 0, "y": 0, "z": 0},
                    "center": {"x": 0, "y": 0, "z": 0},
                },
            )
            fig.write_image(
                os.path.join(img_outdir, f"{cloud}-latency-surface-plot.png")
            )
            fig.write_html(
                os.path.join(html_path, f"{cloud}-latency-surface-plot.html")
            )

    # fig.show()
    return

    start_index = 0
    z_nodes = None
    for experiment, meta in surfaces.items():
        if meta["title"] == "bandwidth_mb_s":
            x_bytes = meta["x"]
            y_latency = meta["y"]
            if z_nodes is None:
                z_nodes = np.zeros((len(x_bytes), len(y_latency)))
            for row in meta["z"]:
                try:
                    z_nodes[start_index, :] = row
                except:
                    pass
                start_index += 1

    z_nodes = np.array(z_nodes)
    X, Y = np.meshgrid(x_bytes, y_latency)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.set_title("Bandwidth MB/s")
    surf = ax.plot_surface(X, Y, z_nodes, cmap="viridis")
    ax.set_zlabel("Avg Latency in ms (logscale)", fontsize=10)
    ax.set_xlabel("Message Size in bytes (logscale)", fontsize=10)
    ax.set_ylabel("Nodes")
    plt.savefig(os.path.join(img_outdir, f"osu_bw_surface-cpu.png"))
    plt.clf()
    plt.close()

    # Generate a surface plot for each
    start_index = 0
    fig = plt.figure()
    ax = None
    colors = sns.color_palette("muted", 8)
    hexcolors = colors.as_hex()
    for experiment, meta in surfaces.items():
        if meta["title"] == "bandwidth_mb_s":
            x_bytes = meta["x"]
            y_latency = meta["y"]
            z_nodes = np.zeros((len(x_bytes), len(y_latency)))
            for row in meta["z"]:
                try:
                    z_nodes[start_index, :] = row
                except:
                    pass
                start_index += 1
            z_nodes = np.array(z_nodes)
            X, Y = np.meshgrid(x_bytes, y_latency)
            if ax is None:
                ax = fig.add_subplot(111, projection="3d")
            surf = ax.plot_surface(X, Y, z_nodes, facecolor=colors.pop(0))

    ax.set_title("Bandwidth MB/s")
    ax.set_zlabel("Avg Latency in ms (logscale)", fontsize=10)
    ax.set_xlabel("Message Size in bytes (logscale)", fontsize=10)
    ax.set_ylabel("Nodes")
    plt.savefig(os.path.join(img_outdir, f"osu_bw_surface_colored-cpu.png"))
    plt.clf()
    plt.close()

    start_index = 0
    z_nodes = None
    for experiment, meta in surfaces.items():
        if meta["title"] == "avg_latency_us":
            x_bytes = meta["x"]
            y_latency = meta["y"]
            if z_nodes is None:
                z_nodes = np.zeros((len(x_bytes), len(y_latency)))
            for row in meta["z"]:
                try:
                    z_nodes[start_index, :] = row
                except:
                    break
                start_index += 1

    z_nodes = np.array(z_nodes)
    X, Y = np.meshgrid(x_bytes, y_latency)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.set_title("OSU All_Reduce")
    surf = ax.plot_surface(X, Y, z_nodes, cmap="viridis")
    ax.set_zlabel("Avg Latency in ms (logscale)", fontsize=10)
    ax.set_xlabel("Message Size in bytes (logscale)", fontsize=10)
    ax.set_ylabel("Nodes")
    plt.savefig(os.path.join(img_outdir, f"osu_allreduce_surface-cpu.png"))
    plt.clf()
    plt.close()

    # Generate a surface plot for each
    start_index = 0
    fig = plt.figure()
    ax = None
    colors = sns.color_palette("muted", 8)
    hexcolors = colors.as_hex()
    for experiment, meta in surfaces.items():
        if meta["title"] == "avg_latency_us":
            x_bytes = meta["x"]
            y_latency = meta["y"]
            z_nodes = np.zeros((len(x_bytes), len(y_latency)))

            # This is like this because we need N sizes X environments,
            # and there isn't enough space in the z dimension
            for row in meta["z"]:
                try:
                    z_nodes[start_index, :] = row
                except:
                    break
                start_index += 1
            z_nodes = np.array(z_nodes)
            X, Y = np.meshgrid(x_bytes, y_latency)
            if ax is None:
                ax = fig.add_subplot(111, projection="3d")
            surf = ax.plot_surface(X, Y, z_nodes, facecolor=colors.pop(0))
    ax.set_title("OSU AllReduce")
    ax.set_zlabel("Avg Latency in ms (logscale)", fontsize=10)
    ax.set_xlabel("Message Size in bytes (logscale)", fontsize=10)
    ax.set_ylabel("Nodes")
    plt.savefig(os.path.join(img_outdir, f"osu_allreduce_surface_colored-cpu.png"))
    plt.clf()
    plt.close()


if __name__ == "__main__":
    main()
