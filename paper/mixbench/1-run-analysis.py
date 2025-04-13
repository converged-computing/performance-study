#!/usr/bin/env python3

import argparse
import collections
import os
import re
import sys
import pandas

import seaborn as sns

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="pastel")

# header for mixbench-cuda
gpu_header = """Experiment ID, Single Precision ops,,,,              Double precision ops,,,,              Half precision ops,,,,                Integer operations,,, 
Compute iters, Flops/byte, ex.time,  GFLOPS, GB/sec, Flops/byte, ex.time,  GFLOPS, GB/sec, Flops/byte, ex.time,  GFLOPS, GB/sec, Iops/byte, ex.time,   GIOPS, GB/sec
"""

cpu_header = """Experiment ID, Single Precision ops,,,,              Double precision ops,,,,              Integer operations,,, 
Compute iters, Flops/byte, ex.time,  GFLOPS, GB/sec, Flops/byte, ex.time,  GFLOPS, GB/sec, Iops/byte, ex.time,   GIOPS, GB/sec
"""


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


def parse_metric(line):
    """
    Extract a key/value pair from a line,
    accounting for specific units
    """
    parts = line.split(":", 1)
    key = parts[0].strip()
    value = parts[1].strip()
    parse_int = [
        "total_memory",
        "WarpSize",
        "Elements per thread",
        "Thread fusion degree",
    ]
    parse_float = ["CUDA driver version", "Compute Capability"]
    spaced_unit = [
        "GPU clock rate",
        "Memory clock rate",
        "Memory bus width",
        "L2 cache size",
        "Total global mem",
        "Memory bandwidth",
    ]
    spaced_unit_float = [
        "Memory bandwidth",
    ]
    if key in parse_int:
        return key, int(value)
    elif key in parse_float:
        return key, float(value)
    elif key == "Total SPs":
        value = value.split(" ")[0]
        return key, float(value)
    elif key == "Compute throughput":
        value = value.split(" ")[0]
        key += "_gflops"
        return key, float(value)
    elif "Buffer size" in key:
        key = "buffer_size_mb"
        value = int(value.replace("MB", ""))
        return key, value
    elif key in spaced_unit:
        value, unit = value.split(" ")
        value = value.strip()
        unit = unit.strip()
        if "/" in unit:
            unit = unit.replace("/", "_per_")
        if key in spaced_unit_float:
            value = float(value)
        else:
            value = int(value)
        return key + "_" + unit, value
    return key, value


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
            key, value = parse_metric(line)
            key = key.lower().replace(" ", "_")
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
    return metrics, gpu_header + "\n".join(csv)


def parse_cpu_lines(item):
    """
    CPU just has the csv output, no GPU devices
    """
    csv = []
    metrics = {}
    for line in item.split("\n"):
        if not line.strip():
            continue
        if "Working memory size" in line:
            metrics["working_memory_size_mb"] = int(
                line.split(":", 1)[-1].replace("MB", "")
            )
        elif "Total threads" in line:
            metrics["total_threads"] = int(line.split(":", 1)[-1])
        # These are lines to ignore, headers to ignore, errors for a single run
        elif re.search("^(---|Use|flux-job|mixbench-cpu|Experiment|Compute)", line):
            continue
        elif line.startswith("         "):
            csv.append(line)
        else:
            raise ValueError(f"Unexpected line in csv data: {line}")

    return metrics, cpu_header + "\n".join(csv)


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
    args.on_premises = True

    # Find input directories
    files = ps.find_inputs(indir, "mixbench", args.on_premises)
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
    result_counts = set()

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
        if exp.prefix not in data:
            data[exp.prefix] = []
            parsed[exp.prefix] = {}
            csvs[exp.prefix] = {}
        if exp.env_type not in parsed[exp.prefix]:
            parsed[exp.prefix][exp.env_type] = {}
            csvs[exp.prefix][exp.env_type] = {}
        if exp.size not in parsed[exp.prefix][exp.env_type]:
            parsed[exp.prefix][exp.env_type][exp.size] = {}
            csvs[exp.prefix][exp.env_type][exp.size] = []

        # Kind of redundant, but works to parse.
        if exp.prefix not in parsed[exp.prefix][exp.env_type][exp.size]:
            parsed[exp.prefix][exp.env_type][exp.size][exp.prefix] = []

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

            result_counts.add(result)
            item = ps.read_file(result)
            # If this is a flux run, we have a jobspec and events here
            if "JOBSPEC" in item:
                item, duration, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            else:
                metadata = {}
                item = ps.remove_slurm_duration(item)

            # These are cancelled
            if "job.exception type=cancel" in item:
                continue
            # Total runtime not comparable given different ways we ran.
            # p.add_result("workload_manager_wrapper_seconds", duration, problem_size)
            # Metrics are counts across gpus. csv is the interleaved data with headers
            if exp.env_type == "gpu":
                metrics, csv = parse_gpu_devices(item)
            else:
                metrics, csv = parse_cpu_lines(item)
            csvs[exp.prefix][exp.env_type][exp.size].append(csv)
            parsed[exp.prefix][exp.env_type][exp.size][exp.prefix].append(metrics)

            # Sanity check that all GPU are the same
            if exp.env_type == "gpu":
                for metric, value in metrics.items():
                    if len(value) > 1:
                        print(
                            f"WARNING {exp.prefix} has GPUs that are different for {metric}: {value}"
                        )

            # What data looks like
            # https://github.com/ekondis/mixbench

    print(f"Done parsing mixbench {len(result_counts)} results!")
    # Write output directory for each
    csv_outdir = os.path.join(outdir, "csv")
    if not os.path.exists(csv_outdir):
        os.makedirs(csv_outdir)
    for experiment, env_types in csvs.items():
        for env_type, sizes in env_types.items():
            for size, csv in sizes.items():
                experiment = experiment.replace("-placement", "").replace(os.sep, "-")
                outfile = os.path.join(csv_outdir, experiment + ".csv")
                ps.write_file("\n".join(csv), outfile)
    ps.write_json(parsed, os.path.join(outdir, "mixbench-parsed.json"))
    ps.write_json(data, os.path.join(outdir, "mixbench-flux-events.json"))
    return parsed


def plot_results(results, outdir):
    """
    Plot analysis results. We are only going to look at breakdown
    of attributes for each. This is just for GPU for now.
    """
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Create a data frame with everything flattened
    df = pandas.DataFrame(
        columns=["experiment", "env_type", "nodes", "metric", "value", "percentage"]
    )
    idx = 0

    # Within a setup, compare between experiments for GPU and cpu
    for label, env_types in results.items():
        for env_type, sizes in env_types.items():
            if env_type != "gpu":
                continue
            size_list = list(sizes.keys())

            # This size list (sorted) is the ticks for the plots
            size_list.sort()

            for size in size_list:
                for cloud_env, values in sizes[size].items():
                    # Truncate the size - we just need <cloud>/<env>/<env_type>
                    experiment = os.path.dirname(cloud_env)

                    # This isn't perfect, but calculate percentages
                    totals = {}
                    counts = {}
                    for entry in values:
                        for k, vals in entry.items():
                            if k not in totals:
                                totals[k] = {}
                                counts[k] = 0
                            for v in vals:
                                if v not in totals[k]:
                                    totals[k][v] = 0
                                totals[k][v] += vals[v]
                                counts[k] += vals[v]

                    # Add summary counts to data frame
                    for key, values in totals.items():
                        for k, count in values.items():
                            percentage = count / counts[key]
                            df.loc[idx, :] = [
                                experiment,
                                env_type,
                                size,
                                key,
                                k,
                                percentage,
                            ]
                            idx += 1

    df.to_csv(os.path.join(outdir, "mixbench-data-frame.csv"))

    # This is all GPU for now, but might as well be pedantic
    for env in df.env_type.unique():
        subset = df[df.env_type == env]

        # Make a plot for each metric - percentage of gpu that have a feature
        for metric in subset.metric.unique():
            metric_df = subset[subset.metric == metric]
            if len(metric_df.value.unique()) == 1:
                print(
                    f"{env_type} for {metric} are all the same, {metric_df.value.unique()}"
                )
            else:
                print(f"{env_type} for {metric} have differences, {metric_df}")
                if env_type == "gpu" and "ecc" in metric.lower():
                    print(
                        f"ECC has {metric_df.nodes.sum()} nodes that we get data from."
                    )


if __name__ == "__main__":
    main()
