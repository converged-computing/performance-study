#!/usr/bin/env python3

import argparse
import collections
import os
import re
import sys

import seaborn as sns
import matplotlib.pylab as plt
import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="pastel")


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
    files = ps.find_inputs(indir, "magma")
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to files (json has parsed, and df csv has just duration / wrapper)
    df, results = parse_data(indir, outdir, files)
    plot_results(results, df, outdir)


def parse_magma(item, filename, exp):
    """
    Parse rows of results from magma
    """
    results = []
    for line in item.split("\n"):
        # Use the empty cpu metadata as a marker of a result line
        if "(  ---  )" not in line:
            continue
        # % BatchCount     M     N     K   MAGMA Gflop/s (ms)   CPU Gflop/s (ms)   MAGMA error
        # 300    32    32    31      0.53 (   5.11)     ---   (  ---  )     ---
        parts = [x for x in re.sub("([(]|[)])", "", line).split(" ") if x]
        if parts[0] != "300":
            raise ValueError(f"Found unexpected batch count {parts[0]}, should be 300.")
        problem_size = f"{parts[1]}x{parts[2]}x{parts[3]}"
        results.append(
            {
                "problem_size": problem_size,
                "gflops_per_second": float(parts[4]),
                "ms": float(parts[5]),
                "exp": exp.prefix,
                "size": exp.size,
            }
        )
    print(f"File {filename} has {len(results)} results.")
    return results


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ProblemSizeParser("magma")

    # For flux we can save jobspecs and other event data
    data = {}

    # This data is HUGE so we will organize by environment, size, then metric
    results = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:
        # Underscore means skip, also skip configs and runs without efa
        # runs with google and shared memory were actually slower...
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        # Note that aws eks has kripke-8gpu directories, that just
        # distinguishes when we ran a first set of runs just with 8 and
        # then had the larger cluster working. Both data are good.
        # All of these are consistent across studies
        exp = ps.ExperimentNameParser(filename, indir)
        if exp.prefix not in data:
            data[exp.prefix] = []

        # Size 2 was typically testing
        if exp.size == 2:
            continue
        if exp.size not in results:
            results[exp.size] = {}

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size)
        exp.show()

        # Now we can read each result file to get metrics.
        result_files = list(ps.get_outfiles(filename))
        for result in result_files:
            # Basename that start with underscore are test or otherwise should not be included
            if os.path.basename(result).startswith("_"):
                continue

            # If we are running in an environment that had two jobs, check for result file name.
            # the vbatched one is what we want!
            if (
                "eks/gpu" in result
                or "aks/gpu" in result
                or "gke/gpu" in result
                or "compute-engine/gpu" in result
            ):
                if "vbatched" not in result:
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

            for r in parse_magma(item, result, exp):
                if r["problem_size"] not in results[r["size"]]:
                    results[r["size"]][r["problem_size"]] = {}
                if r["exp"] not in results[r["size"]][r["problem_size"]]:
                    results[r["size"]][r["problem_size"]][r["exp"]] = {
                        "gflops_per_second": [],
                        "ms": [],
                    }
                results[r["size"]][r["problem_size"]][r["exp"]][
                    "gflops_per_second"
                ].append(r["gflops_per_second"])
                results[r["size"]][r["problem_size"]][r["exp"]]["ms"].append(r["ms"])
            p.add_result("workload_manager_wrapper_seconds", duration, "all")

    print("Done parsing magma results!")
    # This just has the magma durations
    p.df.to_csv(os.path.join(outdir, "magma-durations.csv"))
    ps.write_json(data, os.path.join(outdir, "magma-parsed.json"))
    ps.write_json(results, os.path.join(outdir, "magma-data-parsed.json"))
    return p.df, results


def plot_results(results, df, outdir):
    """
    Plot analysis results
    """
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Within a setup, compare between experiments for GPU and cpu
    for nodes, problem_sizes in results.items():
        size_list = list(problem_sizes.keys())

        # Parse gflops/s and ms at the same time
        vectors = {}
        ms_vectors = {}

        # For each size, we want a plot that has problem sizes on x, and the metric on y
        # We are going to hue (color) by the full environment prefix.
        # We need size -> experiment ->
        for size in size_list:
            for cloud_env, metrics in problem_sizes[size].items():
                # Truncate the size - we just need <cloud>/<env>/<env_type>
                experiment = os.path.dirname(cloud_env)
                if experiment not in vectors:
                    vectors[experiment] = []
                if experiment not in ms_vectors:
                    ms_vectors[experiment] = []
                vectors[experiment].append(metrics["gflops_per_second"])
                ms_vectors[experiment].append(metrics["ms"])

        # Make a boxplot for each environment, so this is problem size across x
        # and metric on y, colored by cloud environment
        plt.figure(figsize=(10, 6))

        # Make better colors!
        palette = sns.color_palette("hls", 6)
        colors = palette.as_hex()
        offsets = [-0.75, -0.5, -0.25, 0.25, 0.5, 0.75]
        for experiment, values in vectors.items():
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
        plt.xticks(
            np.arange(0, len(size_list) * 2, 2), size_list, rotation=45, fontsize=6
        )
        plt.title(f"Magma Gflop/s Size {nodes}")
        plt.tight_layout()
        plt.savefig(
            os.path.join(img_outdir, f"magma-gflop-per-second-size-{nodes}.png")
        )
        plt.close()

        # Make a boxplot for each environment, so this is problem size across x
        # and metric on y, colored by cloud environment
        plt.figure(figsize=(10, 6))

        offsets = [-0.75, -0.5, -0.25, 0.25, 0.5, 0.75]
        palette = sns.color_palette("hls", 6)
        colors = palette.as_hex()
        for experiment, values in ms_vectors.items():
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
        plt.xticks(
            np.arange(0, len(size_list) * 2, 2), size_list, rotation=45, fontsize=6
        )
        plt.title(f"Magma Milliseconds Size {nodes}")
        plt.tight_layout()
        plt.savefig(os.path.join(img_outdir, f"magma-milliseconds-size-{nodes}.png"))
        plt.close()


if __name__ == "__main__":
    main()
