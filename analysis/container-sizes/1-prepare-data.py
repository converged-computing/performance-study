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
    for filename in recursive_find(input_dir, pattern="events-"):
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


def parse_data(indir, outdir, files):

    # Assemble results across filenames - we will have mixing
    lookup = {}
    for filename in files:
        events = read_file(filename)
        sections = [x.strip() for x in events.split("\n") if x.strip()]

        # All unique events (reasons)
        # {'created',
        # 'killing',
        # 'noderegistrationcheckerdidnotrunchecks',
        # 'pulled',
        # 'pulling',
        # 'scalingreplicaset',
        # 'scheduled',
        # 'started',
        # 'successfulcreate'}

        # For each file, create lookup with container uid
        experiment = filename.replace(indir + os.sep, "").split(os.sep + "times")[0]
        for section in sections:
            try:
                section = json.loads(section)
            except:
                print(f"Skipping non json {section}")
                continue

            # Discarded events
            if "reason" not in section:
                continue
            uid = experiment + "-" + section["metadata"]["name"].rsplit(".", 1)[0]
            if uid not in lookup:
                lookup[uid] = {"experiment": experiment, "events": {}}
            reason = section["reason"].lower()

            # Use event time and fall back to first time
            timestamp = section.get("eventTime") or section["firstTimestamp"]
            # Get the container URI from pulling
            if reason == "pulling":
                lookup[uid]["container"] = (
                    section["message"].rsplit(" ", 1)[-1].strip('"')
                )
            instance = section["reportingInstance"]
            lookup[uid]["events"][reason] = {
                "timestamp": timestamp,
                "instance": instance,
            }

            # If pulled, there is extra metadata about what it calculated
            if reason == "pulled":
                lookup[uid]["events"][reason]["message"] = section["message"]

    # This is the primary raw data we are interested in.
    raw_times_file = os.path.join(outdir, "raw-times.json")
    print(f"Saving raw container times to {raw_times_file}")
    write_json(lookup, raw_times_file)

    # Get unique containers to save
    containers = {x.get("container") for _, x in lookup.items() if x.get("container")}
    # This gives us unique containers
    containers_file = os.path.join(outdir, "unique-containers.json")
    print(f"Saving list of unique containers to {containers_file}")
    write_json(list(containers), containers_file)


if __name__ == "__main__":
    main()
