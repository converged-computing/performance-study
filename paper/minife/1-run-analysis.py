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

sns.set_theme(style="dark", palette="muted")

# These are files I found erroneous - no result, or incomplete result
errors = [
    # Partial result with no end time (and no final value)
    "azure/cyclecloud/cpu/size256/results/minife/minife-256n-4859-iter-3.out",
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
    args.on_premises = True
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories
    files = ps.find_inputs(indir, "minife", args.on_premises)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    df = parse_data(indir, outdir, files)
    plot_results(df, outdir)


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # metrics here will be wall time and wrapped time
    p = ps.ProblemSizeParser("minife")

    # For flux we can save jobspecs and other event data
    data = {}

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
        # results = list(ps.get_outfiles(filename))

        # The FOMs are in these yaml files
        # We mostly care about the foms, the output (terminal) isn't as relevant.
        result_foms = list(ps.get_outfiles(filename, pattern="[.]yaml"))

        for result in result_foms:
            if errors and re.search(error_regex, result):
                print(f"Skipping {result} due to known missing result or error.")
                continue

            # miniFE writes results to a YAML file which should be saved for reporting
            # the figure of merit (FOM). From the YAML files, report "Total CG Mflops" as the FOM for miniFE.
            item = ps.read_yaml(result)

            # Just parse smaller problem size
            dims = item["Global Run Parameters"]["dimensions"]
            if dims["nx"] != 230:
                continue

            problem_size = "230nx-ny-nz"
            fom = item["CG solve"]["Total"]["Total CG Mflops"]
            p.add_result("total_cg_mflops", fom, problem_size)

    print("Done parsing minife results!")
    p.df.to_csv(os.path.join(outdir, "minife-results.csv"))
    ps.write_json(data, os.path.join(outdir, "minife-parsed.json"))
    return p.df


def plot_results(df, outdir):
    """
    Plot analysis results
    """
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Within a setup, compare between experiments for GPU and cpu
    for env in df.env_type.unique():
        subset = df[df.env_type == env]
        for problem_size in subset.problem_size.unique():
            ps_df = subset[subset.problem_size == problem_size]

            # Make a plot for each metric
            for metric in ps_df.metric.unique():
                metric_df = ps_df[ps_df.metric == metric]
                colors = sns.color_palette("muted", len(metric_df.experiment.unique()))
                hexcolors = colors.as_hex()
                types = list(metric_df.experiment.unique())
                palette = collections.OrderedDict()
                for t in types:
                    palette[t] = hexcolors.pop(0)
                title = " ".join([x.capitalize() for x in metric.split("_")])

                if env == "cpu":
                    ps.make_plot(
                        metric_df,
                        title=f"MiniFE Total CG Mflops {problem_size} for {env.upper()}",
                        ydimension="value",
                        plotname=f"minife-{metric}-{problem_size}-{env}",
                        xdimension="nodes",
                        palette=palette,
                        outdir=img_outdir,
                        hue="experiment",
                        xlabel="Nodes",
                        ylabel=title,
                        do_round=True,
                        log_scale=True,
                    )
                else:
                    ps.make_plot(
                        metric_df,
                        title=f"MiniFE Total CG Mflops {problem_size} for {env.upper()}",
                        ydimension="value",
                        plotname=f"minife-{metric}-{problem_size}-{env}",
                        xdimension="gpu_count",
                        palette=palette,
                        outdir=img_outdir,
                        hue="experiment",
                        xlabel="GPU Count",
                        ylabel=title,
                        do_round=True,
                        log_scale=True,
                    )


if __name__ == "__main__":
    main()
