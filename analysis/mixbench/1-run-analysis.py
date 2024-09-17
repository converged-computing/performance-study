#!/usr/bin/env python3

import argparse
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

# header for mixbench-cuda
header = """Experiment ID, Single Precision ops,,,,              Double precision ops,,,,              Half precision ops,,,,                Integer operations,,, 
Compute iters, Flops/byte, ex.time,  GFLOPS, GB/sec, Flops/byte, ex.time,  GFLOPS, GB/sec, Flops/byte, ex.time,  GFLOPS, GB/sec, Iops/byte, ex.time,   GIOPS, GB/sec"""

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


def parse_gpu_devices(item):
    """
    If the run was done without -l (for single lines) we can only
    parse the high level metadata about the GPU. For now, still assemble
    in csv for later parsing.
    """
    csv = []
    metrics = {"total_memory": {}}
    for line in item.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip()
            if key not in metrics:
                metrics[key] = {}
            if value not in metrics[key]:
                metrics[key][value] = 0
            metrics[key][value] += 1
        elif "Total GPU memory" in line:
            parts = line.split(" ")
            total = int(parts[3].replace(",", ""))
            if total not in metrics["total_memory"]:
                metrics["total_memory"][total] = 0
            metrics["total_memory"][total] += 1
            # Just save total for now, free at index 5
        elif line.startswith("         "):
            csv.append(line)
    return metrics, header + "\n".join(csv)


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
    files = ps.find_inputs(indir, "mixbench")
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # For flux we can save jobspecs and other event data
    data = {}
    parsed = {}
    csvs = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:

        # Underscore means skip, also skip configs and runs without efa
        # runs with google and shared memory were actually slower...
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        exp = ps.ExperimentNameParser(filename, indir)

        # Size 2 was typically testing
        if exp.size == 2:
            continue

        # We don't have a good way to compare for cpu, just gpu for now
        if exp.env_type != "gpu":
            continue
        if exp.prefix not in data:
            data[exp.prefix] = []
            parsed[exp.prefix] = {}
            csvs[exp.prefix] = {}
        if exp.env_type not in parsed[exp.prefix]:
            parsed[exp.prefix][exp.env_type] = {}
            csvs[exp.prefix][exp.env_type] = {}
        if exp.size not in parsed[exp.prefix][exp.env_type]:
            parsed[exp.prefix][exp.env_type][exp.size] = []
            csvs[exp.prefix][exp.env_type][exp.size] = []

        # Set the parsing context for the result data frame
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
                try:
                    item, duration, metadata = ps.parse_flux_metadata(item)
                except:
                    print(item)
                    import IPython

                    IPython.embed()
                    sys.exit()
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            else:
                metadata = {}
                item = ps.remove_slurm_duration(item)

            # Total runtime not comparable given different ways we ran.
            # p.add_result("workload_manager_wrapper_seconds", duration, problem_size)
            # Metrics are counts across gpus. csv is the interleaved data with headers
            metrics, csv = parse_gpu_devices(item)
            parsed[exp.prefix][exp.env_type][exp.size].append(metrics)
            csvs[exp.prefix][exp.env_type][exp.size].append(csv)

            # What data looks like
            # https://github.com/ekondis/mixbench

    print("Done parsing mixbench results!")
    # Write output directory for each
    csv_outdir = os.path.join(outdir, "csv")
    if not os.path.exists(csv_outdir):
        os.makedirs(csv_outdir)
    for experiment, env_types in csvs.items():
        for env_type, sizes in env_types.items():
            for size, csv in sizes.items():
                outfile = os.path.join(
                    csv_outdir, experiment.replace(os.sep, "-") + ".csv"
                )
                ps.write_file("\n".join(csv), outfile)
    ps.write_json(parsed, os.path.join(outdir, "mixbench-parsed.json"))
    ps.write_json(data, os.path.join(outdir, "mixbench-flux-events.json"))
    return parsed


def plot_results(results, outdir):
    """
    Plot analysis results
    """
    # TODO plotting
    import IPython

    IPython.embed()
    sys.exit()


if __name__ == "__main__":
    main()
