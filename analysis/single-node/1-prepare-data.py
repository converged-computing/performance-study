#!/usr/bin/env python3

import argparse
import json
import os
import re

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(os.path.dirname(here))


def get_parser():
    parser = argparse.ArgumentParser(
        description="Parse container events",
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


def recursive_find(base, pattern="*.*"):
    """
    Recursively find and yield files matching a glob pattern.
    """
    for root, _, filenames in os.walk(base):
        for filename in filenames:
            if not re.search(pattern, filename):
                continue
            yield os.path.join(root, filename)


def find_inputs(input_dir):
    """
    Find inputs (times results files)
    """
    files = []
    for filename in recursive_find(input_dir, pattern="single-node.+[.out]"):
        # We only have data for small
        files.append(filename)
    return files


def main():
    """
    Find times/events* files to parse.
    """
    parser = get_parser()
    args, _ = parser.parse_known_args()

    # Output images and data
    outdir = os.path.abspath(args.out)
    indir = os.path.abspath(args.root)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input files (skip anything with test)
    files = find_inputs(indir)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # Saves raw data to file
    parse_data(indir, outdir, files)


def read_file(filename):
    with open(filename, "r") as fd:
        content = fd.read()
    return content


def write_json(obj, filename):
    with open(filename, "w") as fd:
        fd.write(json.dumps(obj, indent=4))


def write_file(text, filename):
    with open(filename, "w") as fd:
        fd.write(text)


def parse_data(indir, outdir, files):
    """
    Parse filepaths for environment, etc., and results files for data.
    """
    # We will keep a counter for different environments
    counter = {}

    # It's important to just parse raw data once, and then use intermediate
    for filename in files:
        item = read_file(filename)

        # For flux runs, we don't care about the jobspec here.
        item = item.split("START OF JOBSPEC")[0]

        # Break into sections - dividers are ======
        sections = {}
        lines = item.split("\n")
        section = []
        section_name = None
        while lines:
            line = lines.pop(0)

            # First section is always hostname
            if "hostname" in line:
                section_name = "hostname"

            elif "======" in line and section:
                sections[section_name] = section
                section_name = " ".join(line.split(" ")[1:])
                section = []
            else:
                section.append(line)

        if re.search("(attempt|broken|configs|times)", filename):
            continue

        # All of these are consistent across studies
        parts = filename.replace(indir + os.sep, "").split(os.sep)
        cloud = parts.pop(0)
        env = parts.pop(0)
        env_type = parts.pop(0)
        size = parts.pop(0)

        # We can use the node data for shared memory, no efa runs too, still valuable
        size = re.sub("-(shared-memory|noefa|placement)", "", size)
        size = int(size.replace("size", ""))

        print(cloud, env, env_type, size)
        if cloud not in counter:
            counter[cloud] = {}
        if env not in counter[cloud]:
            counter[cloud][env] = {}
        if env_type not in counter[cloud][env]:
            counter[cloud][env][env_type] = {}
        if size not in counter[cloud][env][env_type]:
            counter[cloud][env][env_type][size] = 0

        # The counter is the identifier
        count = counter[cloud][env][env_type][size]
        counter[cloud][env][env_type][size] += 1

        # Derive path based on cloud, environment, and size
        item_outdir = os.path.join(
            outdir, cloud, env, env_type, str(size), f"node-{count}", "raw"
        )
        if not os.path.exists(item_outdir):
            os.makedirs(item_outdir)

        for key, value in sections.items():
            save_file = (
                re.sub("(--|[>]|=)", "", key)
                .replace(" ", "-")
                .replace(os.sep, "-")
                .replace("--", "-")
            )
            if "machine" in key:
                save_file = key.split(" ")[-1]
            save_file = os.path.join(item_outdir, save_file)
            write_file("\n".join(value), save_file)


if __name__ == "__main__":
    main()
