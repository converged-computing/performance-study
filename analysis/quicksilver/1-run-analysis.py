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
errors = [
    # Stopped at 15 min, only reached step 15
    "google/gke/cpu/size256/results/quicksilver-3-threads/quicksilver-256-iter-1-791918149632.out",
    # Stopped at step 10, no ending timestamp
    "azure/cyclecloud/gpu/size32/results/quicksilver/quicksilver-32n-517-iter-2.out",
    # Stopped at step 3 ERROR
    "azure/cyclecloud/gpu/size32/results/quicksilver/quicksilver-32n-516-iter-1.out",
    # Stopped at step 76
    "azure/cyclecloud/gpu/size8/results/quicksilver/quicksilver-8n-197-iter-1.out",
    "azure/cyclecloud/gpu/size16/results/quicksilver/quicksilver-16n-305-iter-1.out",
    # Stopped at step 75
    "azure/cyclecloud/gpu/size8/results/quicksilver/quicksilver-8n-207-iter-1-ucxall.out",
    # Stopped at step 79
    "azure/cyclecloud/gpu/size4/results/quicksilver/quicksilver-4n-89-iter-1.out",
    # Stopped at step 40
    "azure/cyclecloud/gpu/size16/results/quicksilver/quicksilver-16n-306-iter-2.out",
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
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input directories
    files = ps.find_inputs(indir, "quicksilver")
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
    p = ps.ResultParser("quicksilver")

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
                try:
                    item, duration, metadata = ps.parse_flux_metadata(item)
                except:
                    print(item)
                    print(result)
                    import IPython

                    IPython.embed()
                    sys.exit()
                data[exp.prefix].append(metadata)

            # Slurm has the item output, and then just the start/end of the job
            else:
                metadata = {}
                try:
                    duration = ps.parse_slurm_duration(item)
                except:
                    print(item)
                    print(result)
                    import IPython

                    IPython.embed()
                    sys.exit()
                item = ps.remove_slurm_duration(item)

            # Let's just parse figure of merit for now
            # Figure Of Merit              9.519e+08 [Num Segments / Cycle Tracking Time]
            fom = [x for x in item.split("\n") if x.startswith("Figure Of Merit")]
            if not fom:
                print(
                    f"Filename {result} is missing a figure of merit - likely did not finish."
                )
                continue
            fom = float([x for x in fom[0].split(" ") if x][3])
            p.add_result("num_segments_over_cycle_tracking_time", fom)
            p.add_result("workload_manager_wrapper_seconds", duration)

    print("Done parsing quicksilver results!")
    p.df.to_csv(os.path.join(outdir, "quicksilver-results.csv"))
    ps.write_json(data, os.path.join(outdir, "quicksilver-parsed.json"))
    return p.df


def plot_results(df, outdir):
    """
    Plot analysis results
    """
    # Make an image outdir
    img_outdir = os.path.join(outdir, "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Scientific Notation for prettier plot
    log_scale_set = []
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

            log_scale = True if metric in log_scale_set else False
            ps.make_plot(
                metric_df,
                title=f"Quicksilver Metric {title} for {env.upper()}",
                ydimension="value",
                plotname=f"quicksilver-{metric}-{env}",
                xdimension="nodes",
                palette=palette,
                outdir=img_outdir,
                hue="experiment",
                xlabel="Nodes",
                ylabel=title,
                do_round=False,
                log_scale=log_scale,
            )


if __name__ == "__main__":
    main()
