#!/usr/bin/env python3

import argparse
import os
import re
import sys
import seaborn as sns
import numpy as np
import matplotlib.pylab as plt

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="pastel")

# Break into which had single vs. all nodes (or both)
# I'm not currently using these, but put them here if needed.
all_nodes = [
    "aws/eks/gpu",
    "azure/aks/gpu",
    "azure/cyclecloud/gpu",
    "google/compute-engine/gpu",
    "google/gke/gpu",
]
single_nodes = [
    "aws/eks/gpu",
    "aws/eks/gpu",
    "aws/parallel-cluster",
    "azure/aks/cpu",
    "azure/cyclecloud/cpu",
    "google/compute-engine/cpu",
    "google/gke/cpu",
]

single_node_regex = "(%s)" % "|".join(single_nodes)
all_node_regex = "(%s)" % "|".join(all_nodes)

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

    # Find input directories
    files = ps.find_inputs(indir, "stream")
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


def parse_item(item):
    """
    Parse individual results from an item.
    Each (I think) is a node or core, and it's OK we ran these
    a little differently. A complete result has these four fields
    I think, and we can use the "best rate" MB/s as the metric we
    care about:

    -------------------------------------------------------------
    Function    Best Rate MB/s  Avg time     Min time     Max time
    Copy:           11271.6     0.028207     0.014195     0.031694
    Scale:           5904.2     0.042100     0.027099     0.046774
    Add:             8845.0     0.056286     0.027134     0.066129
    Triad:           9128.6     0.056622     0.026291     0.067381
    """
    # Note that these are interleaved, so we can't always associate them
    # together as a group.
    metrics = []
    lines = item.split("\n")
    for line in lines:
        if re.search("(Copy|Scale|Add|Triad):", line):
            values = [x for x in line.split(" ") if x.strip()]
            value = float(values[1])
            label = values[0].replace(":", "").strip()
            metrics.append({"label": label, "value": value})

    return metrics


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ResultParser("stream")

    # For flux we can save jobspecs and other event data
    data = {}

    # Since the data is huge, saving to dfs as we go is really slow
    items = {}

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

            # Let's skip adding this - the runs might not be comparable.
            # p.add_result("workload_manager_wrapper_seconds", duration)

            # For now, let's assume that the benchmark runs across
            # cores, regardless of how many we chose. Each is a valid
            # sample for the cloud / environment. Note that these should
            # be labeled "best_rate_X_mb_per_second"
            for result in parse_item(item):
                label = result["label"]
                if label not in items:
                    items[label] = {}
                if exp.env_type not in items[label]:
                    items[label][exp.env_type] = {}
                if exp.size not in items[label][exp.env_type]:
                    items[label][exp.env_type][exp.size] = {}
                if exp.prefix not in items[label][exp.env_type][exp.size]:
                    items[label][exp.env_type][exp.size][exp.prefix] = []

                # label -> env -> size -> experiment -> lists of values
                items[label][exp.env_type][exp.size][exp.prefix].append(result["value"])

    print("Done parsing stream results!")
    ps.write_json(items, os.path.join(outdir, "stream-results.json"))
    ps.write_json(data, os.path.join(outdir, "stream-parsed.json"))
    return items



def plot_results(results, outdir):
    """
    Plot analysis results
    """
    # Pandas is too slow here, so we will assemble vectors for each thing
    # across the environments. It's harder, but I hope will work.
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Within a setup, compare between experiments for GPU and cpu
    for label, env_types in results.items():
        for env_type, sizes in env_types.items():
            size_list = list(sizes.keys())

            # This size list (sorted) is the ticks for the plots
            size_list.sort()

            # Create a vector for each environment, with each entry (list)
            # a size from least to greatest.
            vectors = {}

            for size in size_list:
                for cloud_env, values in sizes[size].items():
                    # Truncate the size - we just need <cloud>/<env>/<env_type>
                    experiment = os.path.dirname(cloud_env)
                    if experiment not in vectors:
                        vectors[experiment] = []
                    # This would be, for example, all the values for
                    # a specific environment and size. Then the
                    # next append will be the next size
                    vectors[experiment].append(values)

            # Make a boxplot for each environment, and space apart so we
            # can then plot them together and they look like they are side by
            # side
            plt.figure(figsize=(10, 6))

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
            plt.xticks(np.arange(0, len(size_list) * 2, 2), size_list)
            plt.title(f'Stream Best Rate "{label}" MB/s {env_type}')
            plt.savefig(
                os.path.join(
                    img_outdir, f"best-rate-{label}-{env_type}-mb-per-second.png"
                )
            )
            plt.close()


if __name__ == "__main__":
    main()
