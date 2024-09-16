#!/usr/bin/env python3

import argparse
import os
import re
import sys

import matplotlib.pylab as plt
import pandas
import seaborn as sns
from metricsoperator.metrics.network.osu_benchmark import parse_multi_section

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="pastel")

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
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories (anything with lammps-reax)
    # lammps directories are usually snap
    files = ps.find_inputs(indir, "osu")
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

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size)

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
                    # These are only present for cyclecloud
                    if "osu-dd" in result:
                        command = f"{command}_dd"
                    elif "osu-hh" in result:
                        command = f"{command}_hh"
                    matrix = parse_multi_section([command] + section)
                    matrix["context"] = [cloud, env, env_type, size]
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
                matrix["context"] = [cloud, env, env_type, size]
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

    # Create a data frame for each result type
    dfs = {}
    idxs = {}
    # lookup for x and y values for each
    lookup = {}
    for entry in results:
        # The source of truth is the command
        command = entry["command"]
        title = command
        # We don't want these put into separate data frames
        if re.search("_(dd|hh)", title):
            title = title.rsplit("_", 1)[0]
        if title not in dfs:
            columns = get_columns(title) + [
                "experiment",
                "cloud",
                "env",
                "env_type",
                "nodes",
            ]
            dfs[title] = pandas.DataFrame(columns=columns)
            idxs[title] = 0
            lookup[title] = {"x": columns[0], "y": columns[1]}
        # Add command to experiment id since it includes unique command
        experiment = os.sep.join(entry["context"][:-1] + [command])
        for datum in entry["matrix"]:
            dfs[title].loc[idxs[title], :] = datum + [experiment] + entry["context"]
            idxs[title] += 1

    # Save each completed data frame to file and plot!
    for slug, df in dfs.items():
        print(f"Preparing plot for {slug}")

        # Save entire (unsplit) data frame to file
        df.to_csv(os.path.join(outdir, f"{slug}-dataframe.csv"))

        # Separate x and y - latency (y) is a function of size (x)
        x = lookup[slug]["x"]
        y = lookup[slug]["y"]

        # Within a setup, compare between experiments for GPU and cpu
        for env in df.env_type.unique():
            subset = df[df.env_type == env]

            # Make each figure a little bigger
            plt.figure(figsize=(10, 6))

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
            plt.title(slug + " " + env.upper())
            x_label = x.replace("_", " ")
            y_label = y.replace("_", " ")
            ax.set_xlabel(x_label + " (logscale)", fontsize=16)
            ax.set_ylabel(y_label + " (logscale)", fontsize=16)
            ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
            ax.set_yticklabels(ax.get_yticks(), fontsize=14)
            plt.xscale("log")
            plt.yscale("log")
            plt.tight_layout()
            plt.savefig(os.path.join(img_outdir, f"{slug}_{env}.png"))
            plt.clf()
            plt.close()


if __name__ == "__main__":
    main()
