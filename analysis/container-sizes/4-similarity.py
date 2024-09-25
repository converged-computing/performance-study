#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
import hashlib

import matplotlib.pylab as plt
import pandas
import seaborn as sns

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)


def get_parser():
    parser = argparse.ArgumentParser(description="Dockerfile Parser")
    parser.add_argument(
        "--data",
        default=os.path.join(here, "data"),
        help="data directory for results",
    )
    return parser


def read_file(filename):
    with open(filename, "r") as fd:
        content = fd.read()
    return content


def read_json(filename):
    return json.loads(read_file(filename))


def write_json(obj, filename):
    with open(filename, "w") as fd:
        fd.write(json.dumps(obj, indent=4))


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
    Find inputs (results files)
    """
    files = []
    for filename in recursive_find(input_dir, pattern="manifests-config-layers.json"):
        # We only have data for small
        files.append(filename)
    return files


def main():
    parser = get_parser()
    args, _ = parser.parse_known_args()

    if not os.path.exists(args.data):
        sys.exit(f"{args.data} does not exist.")

    # Output directory for images
    data_dir = os.path.join(args.data, "similarity")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Read in manifests
    files = find_inputs(args.data)

    # Filter down to those in our study
    files = [x for x in files if "ghcr.io/converged-computing" in x]
    df = parse_manifests(files)
    df.to_csv(os.path.join(data_dir, "layer-sizes.csv"))

    # Make some plots of sizes and similarity
    plot_layers(df, data_dir)

    # Finally, similarity based on image configs
    plot_config_similarity(files, data_dir)


def plot_config_similarity(files, outdir):
    # This is a content digest we will calculate
    df = pandas.DataFrame(
        columns=[
            "uri",
            "full_uri",
            "digest",
        ]
    )
    idx = 0

    for filename in files:
        print(f"Parsing filename {filename}")
        parsed = (
            os.path.relpath(filename, root).split("containers", 1)[-1].strip(os.sep)
        )
        uri, _ = parsed.rsplit(os.sep, 1)
        item = read_json(filename)

        # Have each group of tags as a transaction
        for tag, cfg in item["configs"].items():
            for layer in cfg["history"]:
                hasher = hashlib.sha256()
                full_uri = f"{uri}:{tag}"
                if "created_by" not in layer:
                    continue
                content = layer["created_by"].replace(" ", "").lower()
                hasher.update(bytes(content.encode("utf-8")))
                digest = hasher.hexdigest()
                df.loc[idx, :] = [
                    uri,
                    full_uri,
                    digest,
                ]
                idx += 1

    calculate_similarity(df, outdir, "container-layer-content-similarity")


def calculate_similarity(df, outdir, outfile):
    """
    Calculate pairwaise similarity of containers and save to file
    """
    # Now calculate similiarty
    sims = pandas.DataFrame(
        index=df.full_uri.unique().tolist(), columns=df.full_uri.unique().tolist()
    )

    # This is similarity based on EXACT layer digests
    total = len(sims.index)
    for i, a in enumerate(sims.index):
        print(f"Calculating for {a}, {i} of {total}")
        for b in sims.index:
            if a == b:
                sims.loc[a, b] = 1
                continue
            # Otherwise, we want to know the number of digests they share
            # Let's calculate jacaard similarity:
            # intersection(a,b) / union(a,b)
            layers_a = set(df[df.full_uri == a].digest.tolist())
            layers_b = set(df[df.full_uri == b].digest.tolist())
            score = len(layers_a.intersection(layers_b)) / len(layers_a.union(layers_b))
            sims.loc[a, b] = score

    sims.to_csv(os.path.join(outdir, f"{outfile}-similarity.csv"))

    # Update sims index and columns to make them shorter (they will render on the plot)
    names = [x.replace('ghcr.io/converged-computing/', '').replace('metric-', '') for x in sims.index.tolist()]
    # Also remove hash
    names = [x.split('@', 1)[0] for x in names]
    sims.index = names
    sims.columns = names

    # Now plot it! Remove containers so we just have tags left
    plt.figure(figsize=(36, 36))
    sims = sims.astype(float)
    m = sns.heatmap(sims, annot=True, cmap="BrBG", mask=(sims == 0.0))
    m.set_facecolor("black")
    plt.title("Container similarity by digest")
    plt.savefig(os.path.join(outdir, f"{outfile}.png"))
    plt.savefig(os.path.join(outdir, f"{outfile}.svg"))
    plt.clf()

    m = sns.clustermap(sims, annot=False, cmap="BrBG")
    plt.title("Container similarity by content of digest")
    plt.savefig(os.path.join(outdir, f"cluster-{outfile}.png"))
    plt.savefig(os.path.join(outdir, f"cluster-{outfile}.svg"))
    plt.clf()

    # Get a gist of the groups
    new_order = m.dendrogram_row.reordered_ind
    new_rows = sims.index[new_order].tolist()
    new_order = m.dendrogram_col.reordered_ind
    new_cols = sims.index[new_order].tolist()
    write_json(
        {"rows": new_rows, "cols": new_cols},
        os.path.join(outdir, f"cluster-{outfile}-labels.json"),
    )


def plot_layers(df, outdir):
    """
    Plot a histogram of layers
    """
    # Summary of space. How many layers?
    # df.shape
    # (2386, 6)
    # How many unique container URIs?
    # len(df.uri.unique())
    # 20
    # How many including tags?
    # len(df.full_uri.unique())
    # 80
    # len(df.digest.unique())
    # 633
    # Filter out empty layers and small layers (WORKDIR, etc)
    # This value is arbitrary, over 1MB
    subset = df[df.layer_size > 1000000]
    values = subset.layer_size.values
    ax = sns.histplot(values)
    plt.title("Sizes of 633 unique layers across 2386 layers and 80 application builds")
    ax.set_xlabel("Size (bytes)", fontsize=16)
    plt.savefig(os.path.join(outdir, "layer-size-histogram.png"))
    plt.clf()

    # Now calculate similiarty
    calculate_similarity(df, outdir, "container-similarity")


def parse_manifests(files):
    """
    Given a listing of files, parse into results data framed
    """
    # fields are consistent
    df = pandas.DataFrame(
        columns=[
            "uri",
            "full_uri",
            "layer_size",
            "digest",
            "media_type",
            "schema_version",
        ]
    )
    idx = 0

    # manifests has the following:
    # shared digests across images
    # distribution of sizes in different contexts
    # distribution of platforms / arch
    seen = set()
    for filename in files:
        if filename in seen:
            continue
        print(f"Parsing filename {filename}")
        parsed = (
            os.path.relpath(filename, root).split("containers", 1)[-1].strip(os.sep)
        )
        uri, _ = parsed.rsplit(os.sep, 1)
        item = read_json(filename)

        # Have each group of tags as a transaction
        for tag, manifest in item["manifests"].items():
            created_at = item["configs"][tag]["created"].rsplit("T")[0]
            created_at = f"{created_at} 00:00:00"

            full_uri = f"{uri}:{tag}"
            if "layers" not in manifest:
                print(f"Missing layers for {uri}")
                continue

            for i, layer in enumerate(manifest["layers"]):
                digest = layer["digest"]
                size = layer["size"]
                mt = layer["mediaType"]
                sv = manifest["schemaVersion"]
                df.loc[idx, :] = [
                    uri,
                    full_uri,
                    size,
                    digest,
                    mt,
                    sv,
                ]
                idx += 1

        seen.add(filename)

    return df


if __name__ == "__main__":
    main()
