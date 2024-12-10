#!/usr/bin/env python3

import argparse
import imageio
import imageio.v3 as iio
import os
import sys

import pandas as pd
import networkx as nx
from itertools import combinations
import numpy as np
import matplotlib.pyplot as plt

import seaborn as sns

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="pastel")

# This file is empty
skip_files = [
    "/home/vanessa/Desktop/Code/performance-study/experiments/aws/parallel-cluster/cpu/size64/results/quicksilver/topology-size-64-quicksilver.json"
]

# Keep track of instance overlap
overlaps = {}


def plot_topology(filename, exp, outdir):
    """
    Helper function to plot a topology file.
    """
    global overlaps
    aws_top = ps.read_json(filename)

    g = nx.Graph()
    inst_names = set()
    for i in aws_top["Instances"]:
        # Add edge between last level switch and middle
        g.add_edge(i["NetworkNodes"][2], i["NetworkNodes"][1])
        # Add edge between middle and top level
        g.add_edge(i["NetworkNodes"][1], i["NetworkNodes"][0])
        # Add edge between instance and last level switch
        g.add_edge(i["InstanceId"], i["NetworkNodes"][2])
        # Add instance name to our known set
        inst_names.add(i["InstanceId"])

    # index lookup, make arbitrary number
    name_idx = {}
    for i, inst in enumerate(inst_names):
        name_idx[inst] = i

    # Keep count for instances we've seen more than once
    for name in inst_names:
        if name not in overlaps:
            overlaps[name] = 0
        overlaps[name] += 1

    hops = np.zeros((len(inst_names), len(inst_names)), dtype=np.int32)

    # Compute number of hops via shortest path
    for c in combinations(name_idx, 2):
        # Don't count source vertex
        dist = len(nx.shortest_path(g, c[0], c[1])) - 1
        hops[name_idx[c[0]]][name_idx[c[1]]] = dist
        # symmetric adjacency matrix
        hops[name_idx[c[1]]][name_idx[c[0]]] = dist

    # image directory should already be created in calling function
    img_outdir = os.path.join(outdir, "img")

    # Filename (uid) for experiment - must include filename (for app) plus exp uid
    # Since we ran studies multiple times, we might have multiple of the same environment, etc.
    counter = 0
    exp_uid = exp.prefix.replace(os.sep, "-")
    uid = os.path.basename(filename).replace(".json", "")

    while True:
        # We want the title to have the identifier for the animation
        title = f"{uid}-{exp_uid}-{counter}"
        data_path = os.path.join(outdir, f"{uid}-{exp_uid}-{counter}-hops.csv")
        plot_path = os.path.join(img_outdir, f"{uid}-{exp_uid}-{counter}-hops.png")
        if os.path.exists(data_path) or os.path.exists(plot_path):
            counter += 1
            continue
        break

    df = pd.DataFrame(hops, index=name_idx, columns=name_idx)
    plt.figure(figsize=(20, 18))
    sns.heatmap(df, mask=(df == 0.0), cmap="crest", annot=hops)

    # Save all the things!
    plt.title(title, fontsize=16)
    plt.savefig(plot_path)
    df.to_csv(data_path)
    plt.close()

    # Count unique hops across data frame
    unique_hops = {}
    for count in df.stack().unique():
        if count == 0:
            continue
        unique_hops[int(count)] = float(df.apply(pd.value_counts).loc[count].sum())

    # Return plot path - we want to combine together to form an animation
    return plot_path, unique_hops


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

    # Find input directories
    files = ps.recursive_find_files(indir, "topology")

    # Only get json files
    files = [x for x in files if x.endswith("json")]
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    # This is commented out because you need to remove the data and images
    # if you want to regenerate it!
    # parse_data(indir, outdir, files)


def make_animation(images, outfile):
    """
    Make a gif with imageio! Damn this was easy.
    """
    frames = []
    for filename in images:
        image = imageio.imread(filename)
        frames.append(image)
    # One frame per second - duration doesn't do it
    iio.imwrite(outfile, frames, fps=1, loop=0)


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    global overlaps
    # Keep file timestamps if we want them
    data = {}

    # Also organize based on eks / parallel cluster and size
    by_env = {}

    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # We have two types of data:
    # eks, which is for an entire cluster and one size
    # parallel-cluster, which has instances changing and thus might have different topology.
    # I'm going to start by assessing instance overlap, and then (if there is overlap)
    # we can try to look at change in hops over time.

    # Keep a lookup of the filename creation times
    creation_times = {}

    total = len(files)
    for i, filename in enumerate(files):
        if filename in skip_files:
            continue
        print(f"{i} of {total}: {filename}")
        try:
            exp = ps.ExperimentNameParser(filename, indir)
        except:
            # One badly named file missing size directory (because we ran eks gpu in one shot)
            # /home/vanessa/Desktop/Code/performance-study/experiments/aws/eks/gpu/topology-16.json
            pretend_filename = filename.replace("gpu/", "gpu/size16/")
            exp = ps.ExperimentNameParser(pretend_filename, indir)

        # Size 2 was typically testing
        if exp.size == 2:
            continue

        environ = f"{exp.env_type}-{exp.env}"
        if environ not in by_env:
            by_env[environ] = {}

        # Keep track of counts of hops for each
        if exp.size not in data:
            data[exp.size] = {}

        if exp.size not in by_env[environ]:
            by_env[environ][exp.size] = {}

        # Read in the data and generate the plot file!
        plot_file, unique_hops = plot_topology(filename, exp, outdir)

        # Get the relative path
        relpath = os.path.relpath(plot_file, outdir)
        creation_times[relpath] = os.stat(filename).st_ctime
        data[exp.size][relpath] = unique_hops
        by_env[environ][exp.size][relpath] = unique_hops

    # Save overlaps by value (count we see)
    overlaps = {k: v for k, v in sorted(overlaps.items(), key=lambda item: item[1])}

    # Save unique hops, timestamps, etc to file
    ps.write_json(by_env, os.path.join(outdir, "hop-counts-by-env_size.json"))
    ps.write_json(data, os.path.join(outdir, "hop-counts-by-size.json"))
    ps.write_json(creation_times, os.path.join(outdir, "creation_times.json"))
    ps.write_json(
        overlaps, os.path.join(outdir, "instance-uid-overlap-across-studies.json")
    )

    gif_outdir = os.path.join(outdir, "gif")
    if not os.path.exists(gif_outdir):
        os.makedirs(gif_outdir)

    # Make animation for each environment and size
    for env_name, items in by_env.items():
        for size, names in items.items():
            names = list(names)
            count = len(names)
            names = [f"data/{x}" for x in names]
            outfile = f"{env_name}-size-{size}-count-{count}.gif"
            make_animation(names, os.path.join(gif_outdir, outfile))


if __name__ == "__main__":
    main()
