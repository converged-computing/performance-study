#!/usr/bin/env python3

import argparse
import os
import re
import matplotlib.pylab as plt
import csv
import seaborn as sns
import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
sns.set_theme(style="whitegrid", palette="pastel")


def get_parser():
    parser = argparse.ArgumentParser(
        description="Parse csv files for mixbench",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--root",
        help="root directory with experiments",
        default=os.path.join(here, "data", "csv"),
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
    files = []
    for filename in os.listdir(indir):
        files.append(os.path.join(indir, filename))
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    for metric_type, results in parse_data(indir, outdir, files):
        plot_results(results, metric_type, outdir)


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # It's a LOT of data, so let's save a plot for each
    for metric_type in [
        "single_precision",
        "double_precision",
        "half_precision",
        "integer",
    ]:
        yield parse_metric_type(indir, outdir, files, metric_type)


def parse_metric_type(indir, outdir, files, metric_type):
    """
    Parse a plot a subtype of data
    """
    # For flux we can save jobspecs and other event data
    data = {}

    # It's important to just parse raw data once, and then use intermediate
    total = len(files)
    for i, filename in enumerate(files):
        if not filename.endswith("csv"):
            continue
        print(f"Parsing {filename} {i} of {total}")
        parts = os.path.basename(filename).replace(".csv", "").split("-")
        cloud = parts.pop(0)
        size = parts.pop()
        env_type = parts.pop()
        env = "-".join(parts)
        size = int(size.replace("size", ""))
        prefix = os.path.join(cloud, env, env_type)

        if env_type not in data:
            data[env_type] = {}
        if size not in data[env_type]:
            data[env_type][size] = {}

        # For each file, keep a lookup of vectors based on the index.
        with open(filename, newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=",", quotechar='"')
            for i, row in enumerate(reader):
                if i == 0:
                    continue
                if i == 1:
                    continue
                values = [x.strip() for x in row]
                # The data are interleaved. If values 0 is a string, it's an interleaved header
                # row (and we should skip it). This is the number of the iter - we don't use it.
                try:
                    iters = int(values.pop(0))
                except:
                    continue
                # These are in groups:
                # single_precision_ops
                flops_per_byte_single_precision = float(values.pop(0))
                values.pop(0)
                gflops_single_precision = float(values.pop(0))
                gb_per_sec_single_precision = float(values.pop(0))

                # double_precision_ops
                flops_per_byte_double_precision = float(values.pop(0))
                values.pop(0)
                gflops_double_precision = float(values.pop(0))
                gb_per_second_double_precision = float(values.pop(0))

                # CPU does not have half-precision ops
                if env_type == "gpu":
                    # half_precision_ops
                    flops_per_byte_half_precision = float(values.pop(0))
                    values.pop(0)
                    gflops_half_precision = float(values.pop(0))
                    gb_per_second_half_precision = float(values.pop(0))

                # integer_ops
                iops_per_byte_integer = float(values.pop(0))
                values.pop(0)
                gflops_integer = float(values.pop(0))
                gb_per_second_integer = float(values.pop(0))

                # Save data based on type we are parsing
                if metric_type == "single_precision":
                    if flops_per_byte_single_precision not in data[env_type][size]:
                        data[env_type][size][flops_per_byte_single_precision] = {}
                    if (
                        prefix
                        not in data[env_type][size][flops_per_byte_single_precision]
                    ):
                        data[env_type][size][flops_per_byte_single_precision][
                            prefix
                        ] = []
                    data[env_type][size][flops_per_byte_single_precision][
                        prefix
                    ].append(gflops_single_precision)
                elif metric_type == "double_precision":
                    if flops_per_byte_double_precision not in data[env_type][size]:
                        data[env_type][size][flops_per_byte_double_precision] = {}
                    if (
                        prefix
                        not in data[env_type][size][flops_per_byte_double_precision]
                    ):
                        data[env_type][size][flops_per_byte_double_precision][
                            prefix
                        ] = []
                    data[env_type][size][flops_per_byte_double_precision][
                        prefix
                    ].append(gflops_double_precision)
                elif metric_type == "half_precision" and env_type == "gpu":
                    if flops_per_byte_half_precision not in data[env_type][size]:
                        data[env_type][size][flops_per_byte_half_precision] = {}
                    if (
                        prefix
                        not in data[env_type][size][flops_per_byte_half_precision]
                    ):
                        data[env_type][size][flops_per_byte_half_precision][prefix] = []
                    data[env_type][size][flops_per_byte_half_precision][prefix].append(
                        gflops_half_precision
                    )
                elif metric_type == "integer":
                    if iops_per_byte_integer not in data[env_type][size]:
                        data[env_type][size][iops_per_byte_integer] = {}
                    if prefix not in data[env_type][size][iops_per_byte_integer]:
                        data[env_type][size][iops_per_byte_integer][prefix] = []
                    data[env_type][size][iops_per_byte_integer][prefix].append(
                        gflops_integer
                    )
                elif metric_type == "half_precision" and env_type == "cpu":
                    continue
                else:
                    raise ValueError(f"{metric_type} is an unknown type")

            # What data looks like
            # https://github.com/ekondis/mixbench
    return metric_type, data


def plot_results(results, metric_type, outdir):
    """
    Plot analysis results.
    """
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Within a setup, compare between experiments for GPU and cpu
    for env_type, sizes in results.items():
        size_list = list(sizes.keys())

        # CPU does not have integer precision
        if env_type == "cpu" and metric_type == "half_precision":
            continue

        # This size list (sorted) is the ticks for the plots
        size_list.sort()
        for size in size_list:
            # Each plot is for one size across GFLOPS
            entry = sizes[size]
            vectors = {}
            gflops_values = list(entry.keys())
            for gflops_value in gflops_values:
                for experiment, values in entry[gflops_value].items():
                    if experiment not in vectors:
                        vectors[experiment] = []
                    vectors[experiment].append(values)

            # Make a boxplot for each environment, and space apart so we
            # can then plot them together and they look like they are side by
            # side
            plt.figure(figsize=(20, 6))
            offsets = [-0.75, -0.5, -0.25, 0.25, 0.5, 0.75]
            colors = ["#003f5c", "#58508d", "#bc5090", "#de5a79", "#ff6361", "#ffa600"]
            for experiment, values in vectors.items():
                # TODO figure this out...
                positions = np.array(np.arange(len(values))) * 2.0 + offsets.pop(0)
                plot = plt.boxplot(
                    values,
                    positions=positions,
                    widths=0.3,
                    patch_artist=True,
                    showfliers=False,
                )
                ps.set_group_color_properties(plot, colors.pop(0), experiment)

            # set the x label values, the sizes
            xlabel = "flops/byte"
            if metric_type == "integer":
                xlabel = "iops/byte"

            # set the x label values, the sizes
            plt.xticks(np.arange(0, len(gflops_values) * 2, 2), gflops_values)
            metric = metric_type.replace("_", " ")
            plt.title(f'Mixbench "{metric}" {env_type} size {size}')
            plt.xlabel(xlabel)
            plt.ylabel("Throughput (GLOPS)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(
                os.path.join(
                    img_outdir, f"mixbench-{metric_type}-{env_type}-size-{size}.png"
                )
            )
            plt.close()


if __name__ == "__main__":
    main()
