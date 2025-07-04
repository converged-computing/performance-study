#!/usr/bin/env python3

import pandas
import argparse
import os
import re
import sys

import matplotlib.pylab as plt
import seaborn as sns

here = os.path.dirname(os.path.abspath(__file__))
analysis_root = os.path.dirname(here)
root = os.path.dirname(analysis_root)
sys.path.insert(0, analysis_root)

import performance_study as ps

sns.set_theme(style="whitegrid", palette="muted")

# These are files I found erroneous - no result, or incomplete result
errors = [
    # Only start time, module load error, and Mounting with FUSE
    "azure/cyclecloud/cpu/size32/results/lammps-reax/lammps-32n-223-iter-5.out",
    # Only start time, error shows loading module and then CANCELLED
    "azure/cyclecloud/cpu/size128/results/lammps-reax/lammps-128n-85-iter-1.out",
    "azure/cyclecloud/cpu/size128/results/lammps-reax/lammps-128n-96-iter-1.out",
    # CANCELLED, empty log except for start timestamp
    "azure/cyclecloud/cpu/size128/results/lammps-reax/lammps-128n-91-iter-2.out",
    # Huge stream of UCX errors, not available or found, no lammps output
    "azure/cyclecloud/cpu/size256/results/lammps-reax/lammps-256n-4826-iter-5.out",
    "azure/cyclecloud/cpu/size256/results/lammps-reax/lammps-256n-4829-iter-3.out",
    "on-premises/lassen/gpu/size8/lammps-reax/6348824-iter-1-8n-gpuon.out",
]
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
        "--non-anon",
        help="Generate non-anon",
        action="store_true",
        default=False,
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

    # We absolutely want on premises results here
    args.on_premises = True

    # Output images and data
    outdir = os.path.abspath(args.out)
    indir = os.path.abspath(args.root)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories (anything with lammps-reax)
    # lammps directories are usually snap
    files = ps.find_inputs(indir, "lammps-reax", args.on_premises)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir, args.non_anon)


def parse_matom_steps(item):
    """
    Parse matom steps

    We separated this into a function because cyclecloud submits have
    two problem sizes in one file.
    """
    # Add in Matom steps - what is considered the LAMMPS FOM
    # https://asc.llnl.gov/sites/asc/files/2020-09/CORAL2_Benchmark_Summary_LAMMPS.pdf
    # Not parsed by metrics operator so we find the line here
    line = [x for x in item.split("\n") if "Matom-step/s" in x][0]
    return float(line.split(",")[-1].strip().split(" ")[0])


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ProblemSizeParser("lammps")

    # For flux we can save jobspecs and other event data
    data = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:
        dirname = os.path.basename(filename)
        if ps.skip_result(dirname, filename):
            continue

        # I don't know if these are results or testing, skipping for now
        # They are from aws parallel-cluster CPU
        if os.path.join("experiment", "data") in filename:
            continue

        exp = ps.ExperimentNameParser(filename, indir)
        if exp.prefix not in data:
            data[exp.prefix] = []

        # Size 2 was typically testing
        if exp.size == 2:
            continue

        # Calculate number of gpus from nodes
        number_gpus = 0
        if exp.env_type == "gpu":
            number_gpus = (
                (exp.size * 4) if "on-premises" in filename else (exp.size * 8)
            )

        # Set the parsing context for the result data frame
        p.set_context(exp.cloud, exp.env, exp.env_type, exp.size, gpu_count=number_gpus)
        exp.show()

        # Now we can read each result file to get metrics.
        results = list(ps.get_outfiles(filename))
        for result in results:
            # Skip over found erroneous results
            if errors and re.search(error_regex, result):
                print(f"Skipping {result} due to known missing result or error.")
                continue

            # Basename that start with underscore are test or otherwise should not be included
            if os.path.basename(result).startswith("_") or "missing-sif-log" in result:
                continue
            item = ps.read_file(result)

            # If this is a flux run, we have a jobspec and events here
            if "JOBSPEC" in item:
                item, duration, metadata = ps.parse_flux_metadata(item)
                data[exp.prefix].append(metadata)
                problem_size = "64x64x32" if "64x64x32" in item else "64x32x32"
                assert problem_size in item
                p.add_result(
                    "matom_steps_per_second", parse_matom_steps(item), problem_size
                )
                p.add_result("duration", duration, problem_size)

            # Slurm has the item output, and then just the start/end of the job
            # IMPORTANT: cyclecloud was run two problem sizes one job!
            elif "on-premises" not in filename:
                metadata = {}
                # Wall times are here
                durations = [
                    ps.convert_walltime_to_seconds(x.rsplit(" ", 1)[-1])
                    for x in item.split("\n")
                    if "Total wall time" in x
                ]
                if item.count("Total wall time") > 1:
                    items = item.split("Total wall time", 1)
                    # Larger problem size is first (slower wall time)
                    problem_size = "64x64x32"
                    assert problem_size in items[0]
                    p.add_result(
                        "matom_steps_per_second",
                        parse_matom_steps(items[0]),
                        problem_size,
                    )
                    p.add_result("duration", durations[0], problem_size)
                    # Smaller problem size is second
                    problem_size = "64x32x32"
                    assert problem_size in items[1]
                    p.add_result(
                        "matom_steps_per_second",
                        parse_matom_steps(items[1]),
                        problem_size,
                    )
                    p.add_result("duration", durations[1], problem_size)
                else:
                    problem_size = "64x64x32"
                    assert problem_size in item
                    p.add_result(
                        "matom_steps_per_second", parse_matom_steps(item), problem_size
                    )
                    durations = [
                        ps.convert_walltime_to_seconds(x.rsplit(" ", 1)[-1])
                        for x in item.split("\n")
                        if "Total wall time" in x
                    ]
                    p.add_result("duration", durations[0], problem_size)

            # I think we only ran this problem size on premises
            elif "on-premises" in filename:
                metadata = {}
                problem_size = "64x64x32" if "64x64x32" in item else "64x32x32"
                durations = [
                    ps.convert_walltime_to_seconds(x.rsplit(" ", 1)[-1])
                    for x in item.split("\n")
                    if "Total wall time" in x
                ]
                assert problem_size in item
                p.add_result(
                    "matom_steps_per_second", parse_matom_steps(item), problem_size
                )
                p.add_result("duration", durations[0], problem_size)

    print("Done parsing lammps results!")
    p.df.to_csv(os.path.join(outdir, "lammps-reax-results.csv"))
    ps.write_json(data, os.path.join(outdir, "lammps-reax-parsed.json"))
    return p.df


def plot_results(df, outdir, non_anon=False):
    """
    Plot analysis results
    """
    # Let's get some shoes! Err, plots.
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Calculate cost for running lammps!
    print('Costs for 64x64x32')
    ps.print_experiment_cost(df[df.problem_size == "64x64x32"], outdir, '-64-64-32')
    # This first df doesn't account for 5 iteratinos (could have more or less)
    # on-premises/dane/cpu                  0
    # azure/cyclecloud/gpu          52.774089
    # aws/eks/gpu                   60.077584
    # azure/aks/gpu                 60.276223
    # google/gke/gpu                71.926594
    # google/compute-engine/gpu     74.441981
    # aws/parallel-cluster/cpu         93.312
    # aws/eks/cpu                  307.597583
    # azure/cyclecloud/cpu            348.832
    # google/compute-engine/cpu    457.718113
    # google/gke/cpu               898.050777
    # azure/aks/cpu                975.219782

    # Experiment costs - not missing runs (cost sum across sizes)
    # experiment
    # on-premises/dane/cpu                  0
    # experiment                    cost
    # azure/cyclecloud/gpu          52.774089
    # aws/eks/gpu                   60.077584
    # azure/aks/gpu                 60.276223
    # google/gke/gpu                71.926594
    # google/compute-engine/gpu     74.441981
    # aws/parallel-cluster/cpu         93.312
    # azure/cyclecloud/cpu            236.576
    # aws/eks/cpu                  266.731258
    # azure/aks/cpu                358.192452
    # google/compute-engine/cpu    396.780725
    # google/gke/cpu               487.407771

    print('Costs for 64x32x32')
    ps.print_experiment_cost(df[df.problem_size == "64x32x32"], outdir, '-64-32-32')

    # For anonymization
    if not non_anon:
        df["experiment"] = df["experiment"].str.replace(
            "on-premises/lassen", "on-premises/b"
        )
        df["experiment"] = df["experiment"].str.replace(
            "on-premises/dane", "on-premises/a"
        )

    # We are going to put the plots together, and the colors need to match!
    cloud_colors = {}
    for cloud in df.experiment.unique():
        cloud_colors[cloud] = ps.match_color(cloud)

    # Within a setup, compare between experiments for GPU and cpu
    data_frames = {}
    for env in df.env_type.unique():
        subset = df[df.env_type == env]
        for problem_size in subset.problem_size.unique():
            if env == "gpu" and problem_size == "64x64x32":
                continue
            ps_df = subset[subset.problem_size == problem_size]

            # Make a plot for seconds runtime, and each FOM set.
            # We can look at the metric across sizes, colored by experiment
            for metric in ps_df.metric.unique():
                if "matom" not in metric:
                    continue
                metric_df = ps_df[ps_df.metric == metric]
                data_frames[env] = [metric_df, problem_size]

    fig = plt.figure(figsize=(18, 3.3))
    gs = plt.GridSpec(1, 3, width_ratios=[2, 2, 1])
    axes = []
    cpu_ax = fig.add_subplot(gs[0, 0])
    axes.append(cpu_ax)
    axes.append(fig.add_subplot(gs[0, 1], sharey=cpu_ax))
    axes.append(fig.add_subplot(gs[0, 2]))

    # fig, axes = plt.subplots(1, 2, sharey=True, figsize=(18, 3.3))
    sns.set_style("whitegrid")
    sns.barplot(
        data_frames["cpu"][0],
        ax=axes[0],
        x="nodes",
        y="value",
        hue="experiment",
        hue_order=[
            "google/gke/cpu",
            "azure/aks/cpu",
            "google/compute-engine/cpu",
            "azure/cyclecloud/cpu",
            "aws/eks/cpu",
            "aws/parallel-cluster/cpu",
            "on-premises/a/cpu",
        ],
        err_kws={"color": "darkred"},
        palette=cloud_colors,
        order=[32, 64, 128, 256],
    )
    axes[0].set_title("LAMMPS M/Atom Steps per Second (CPU)", fontsize=14)
    problem_size = data_frames["cpu"][1]
    axes[0].set_ylabel("M/Atom Steps Per Second", fontsize=14)
    axes[0].set_xlabel("Nodes", fontsize=14)

    sns.barplot(
        data_frames["gpu"][0],
        ax=axes[1],
        x="gpu_count",
        y="value",
        hue="experiment",
        hue_order=[
            "google/compute-engine/gpu",
            "google/gke/gpu",
            "aws/eks/gpu",
            "azure/aks/gpu",
            "azure/cyclecloud/gpu",
            "on-premises/b/gpu",
        ],
        err_kws={"color": "darkred"},
        palette=cloud_colors,
        order=[32, 64, 128, 256],
    )
    axes[1].set_title("LAMMPS M/Atom Steps per Second (GPU)", fontsize=14)
    axes[1].set_xlabel("GPU Count", fontsize=14)
    axes[1].set_ylabel("")

    handles, labels = axes[1].get_legend_handles_labels()
    labels = ["/".join(x.split("/")[0:2]) for x in labels]
    axes[2].legend(
        handles, labels, loc="center left", bbox_to_anchor=(-0.1, 0.5), frameon=False
    )
    for ax in axes[0:2]:
        ax.get_legend().remove()
    axes[2].axis("off")

    plt.tight_layout()
    plt.savefig(os.path.join(img_outdir, "lammps-matom-steps-cpu-gpu.svg"))
    plt.clf()
    print(f'Total number of CPU datum: {data_frames["cpu"][0].shape[0]}')
    print(f'Total number of GPU datum: {data_frames["gpu"][0].shape[0]}')


if __name__ == "__main__":
    main()
