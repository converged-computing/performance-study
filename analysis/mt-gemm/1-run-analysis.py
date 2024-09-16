#!/usr/bin/env python3

import argparse
import collections
import os
import re
import sys

import seaborn as sns

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
    files = ps.find_inputs(indir, "mt-gemm")
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


def parse_cpu_gemm(item):
    """
    Parse CPU gemm

    Performance= 370.99 GFlop/s, Time= 5.391 msec, Size= 2000000000 Ops\n'
    """
    metrics = {}
    for line in item.strip().split(","):
        if "Performance" in line:
            parts = [x for x in line.split(" ") if x]
            metrics["performance_gflops_per_second"] = float(parts[1])
        elif "Time" in line:
            if "msec" not in line:
                raise ValueError(f"All times are expected to be in msec. Found {line}")
            parts = [x for x in line.split(" ") if x]
            metrics["time_msecs"] = float(parts[1])
        elif "Size" in line:
            parts = [x for x in line.split(" ") if x]
            metrics["size_ops"] = float(parts[1])
    return metrics


def parse_gpu_gemm(item):
    """
    Parse GPU gemm
    """
    metrics = {}
    for line in item.split("\n"):
        if "Matrix size input" in line:
            metrics["matrix_size_input"] = float(line.split(":")[-1].strip())
        elif line.startswith("Alpha"):
            metrics["alpha"] = float(line.split("=")[-1].strip())
        elif line.startswith("Beta"):
            metrics["beta"] = float(line.split("=")[-1].strip())
        elif "Final Sum" in line:
            metrics["final_sum"] = float(line.split(":")[-1].strip())
        elif "Memory for Matrices" in line:
            memory = line.split(":")[-1].strip().replace("MB", "").strip()
            metrics["memory_for_matrices_mb"] = float(memory)
        elif "Multiply time" in line:
            seconds = line.split(":")[-1].strip().replace("seconds", "").strip()
            metrics["multiply_time_seconds"] = float(seconds)
        elif "GFLOP/s" in line:
            seconds = line.split(":")[-1].strip().replace("GF/s", "").strip()
            metrics["gflops_per_second_rate"] = float(seconds)
    return metrics


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ResultParser("mt-gemm")

    # For flux we can save jobspecs and other event data
    data = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:

        # Underscore means skip, also skip configs and runs without efa
        # runs with google and shared memory were actually slower...
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        # For GKE size 32 I ran both the 1k and 9k sizes. 9k seemed to work here,
        # but would not work anywhere else, so we can't use it.
        if "mt-gemm-9k" in filename:
            continue

        exp = ps.ExperimentNameParser(filename, indir)
        if exp.prefix not in data:
            data[exp.prefix] = []

        # Size 2 was typically testing
        if exp.size == 2:
            continue

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size)
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

            # If this is a flux run, we have a jobspec and events here
            if "JOBSPEC" in item:
                item, duration, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            else:
                metadata = {}
                duration = ps.parse_slurm_duration(item)
                item = ps.remove_slurm_duration(item)

            # Add the duration in seconds
            # Note - different output for GPU vs. CPU!
            if exp.env_type == "gpu":
                metrics = parse_gpu_gemm(item)
            else:
                metrics = parse_cpu_gemm(item)
            p.add_result("workload_manager_wrapper_seconds", duration)
            for metric, value in metrics.items():
                p.add_result(metric, value)

    print("Done parsing mt-gemm results!")
    p.df.to_csv(os.path.join(outdir, "mt-gemm-results.csv"))
    ps.write_json(data, os.path.join(outdir, "mt-gemm-parsed.json"))
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

        # Make a plot for each metric
        for metric in subset.metric.unique():
            metric_df = subset[subset.metric == metric]

            colors = sns.color_palette("hls", 16)
            hexcolors = colors.as_hex()
            types = list(metric_df.experiment.unique())
            palette = collections.OrderedDict()
            for t in types:
                palette[t] = hexcolors.pop(0)
            title = " ".join([x.capitalize() for x in metric.split("_")])

            ps.make_plot(
                metric_df,
                title=f"MT-GEMM Metric {title} for {env.upper()}",
                ydimension="value",
                plotname=f"mt-gemm-{metric}-{env}",
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
