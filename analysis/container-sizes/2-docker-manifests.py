#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime

import pandas
import requests

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)

timestamp_format = "%Y-%m-%dT%H:%M:%SZ"


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


def main():
    parser = get_parser()
    args, _ = parser.parse_known_args()

    # Data with containers listing
    containers = os.path.join(args.data, "unique-containers.json")
    all_containers = os.path.join(args.data, "all-containers.json")
    if not os.path.exists(containers):
        sys.exit(f"Raw containers {containers} does not exist.")

    containers = read_json(containers)

    # Also add in "all containers" set that includes those that were just pulled with singularity
    # (eg., compute engine CPU used rocky bases)
    all_containers = set(read_json(all_containers))

    # There are 90 in all containers, including those not in kubernetes events
    # There are 80 application containers in containers, those we have k8s events for
    # This does not include the flux-view
    # Let's get metadata for the union set
    containers = list(set(all_containers).union(set(containers)))

    # Output directory for containers
    data_dir = os.path.join(args.data, "containers")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # For each dockerfile FROM, we want to get:
    # 1. tags over time
    # 2. for each tag:
    # 3.   total size (summed from manifest)
    # 4.   number of layers (manifest)
    # 5.   size of each layer
    # The config has timestamps for creation of layers
    misses = set()

    # Generate unique list of uris and tags (most containers have multiple tags)
    lookup = {}
    for uri in containers:
        uri, tag = uri.split(":", 1)
        if uri not in lookup:
            lookup[uri] = set()
        lookup[uri].add(tag)

    # Save list of output files
    output_files = []
    for uri, tags in lookup.items():
        image_outdir = os.path.join(data_dir, uri)
        output_file = os.path.join(image_outdir, "manifests-config-layers.json")
        output_files.append(output_file)
        # if os.path.exists(output_file):
        #    print(f"Skipping {output_file}, already exists.")
        #    continue
        if not os.path.exists(image_outdir):
            os.makedirs(image_outdir)

        try:
            print(f"Looking for tags {tags} for {uri}")
            parse_image(uri, image_outdir, list(tags))
        except Exception as exc:
            print(f"Issue parsing image {uri}: {exc}")
            misses.add(uri)
            if os.path.exists(image_outdir) and not os.path.exists(output_file):
                shutil.rmtree(image_outdir)

    # At time of study, no misses
    if misses:
        print(misses)

    # Parse manifests to get layer metadata
    df = parse_manifests(output_files)
    df.to_csv(os.path.join(data_dir, "container-layers-csv"))


def parse_time_pulled(time_pulled):
    minutes = 0
    # First check for milliseconds, if reported in ms there aren't seconds or minutes
    if "ms" in time_pulled:
        return float(time_pulled.replace("ms", "", 1)) / 1000
    if "m" in time_pulled:
        minutes, rest = time_pulled.split("m", 1)
        minutes = int(minutes)
        time_pulled = rest
    seconds = float(time_pulled.rstrip("s"))
    return (minutes * 60) + seconds


def parse_times(times):
    """
    Read events and turn into data frame with container pull times
    """
    df = pandas.DataFrame(
        columns=[
            "event",
            "duration",
            "container",
            "cloud",
            "environment",
            "exp_size",
            "exp_type",
            "experiment",
        ]
    )
    idx = 0
    for _, item in times.items():
        # Parse experiment name
        experiment = item["experiment"]
        parts = experiment.split(os.sep)
        cloud = parts.pop(0)
        environment = parts.pop(0)
        exp_type = parts.pop(0)  # gpu vs cpu
        # The only experiment without a stated size is aws eks gpu, size 16
        size = "size16"
        if parts:
            size = parts.pop(0)

        if "broken" in size or "noefa" in size:
            continue
        container = item.get("container")
        if not container and "pulled" in item["events"]:
            container = (
                re.search('["].*["]', item["events"]["pulled"]["message"])
                .group()
                .strip('"')
            )

        # We can do our own calculation based on timestamps here
        # These seem to be better in terms of granularity
        seconds = None
        # We can derive pull plus waiting from the message here
        # This is better data
        if "pulled" in item["events"] and seconds is None:
            message = item["events"]["pulled"]["message"]
            # If it's already pulled, don't count it
            if "already present on machine" in message.lower():
                continue
            time_pulled = re.search("[(].*[)]", message)
            time_pulled = time_pulled.group().split(" ")[0].replace("(", "")
            # parse time pulled
            seconds = parse_time_pulled(time_pulled)
            if (
                cloud == "aws"
                and exp_type == "gpu"
                and "libfabric" in container
                and size == "size16"
            ):
                print(seconds)

        elif "pulling" in item["events"] and "pulled" in item["events"]:
            start = item["events"]["pulling"]["timestamp"]
            end = item["events"]["pulled"]["timestamp"]
            parsed_end = datetime.strptime(end, timestamp_format)
            parsed_start = datetime.strptime(start, timestamp_format)
            elapsed = parsed_end - parsed_start
            seconds = elapsed.min.seconds + elapsed.seconds

        if seconds is not None:
            df.loc[idx, :] = [
                "pulled",
                seconds,
                container,
                cloud,
                environment,
                size,
                exp_type,
                experiment,
            ]
            idx += 1
    return df


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
            "platform",
            "arch",
            "digest",
            "os",
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

        if "manifests" not in item:
            continue

        # Have each group of tags as a transaction
        for tag, manifest in item.get("manifests", {}).items():
            # Don't parse manifest lists
            if (
                "mediaType" not in manifest
                or manifest["mediaType"]
                == "application/vnd.docker.distribution.manifest.list.v2+json"
            ):
                continue
            if "layers" not in manifest or manifest["schemaVersion"] == 1:
                continue
            if tag not in item["configs"]:
                continue

            created_at = item["configs"][tag]["created"].rsplit("T")[0]
            created_at = f"{created_at} 00:00:00"

            full_uri = f"{uri}:{tag}"
            for i, layer in enumerate(manifest["layers"]):
                platform = layer.get("platform") or {}
                arch = platform.get("architecture") or "unknown"
                digest = layer["digest"]
                opsys = platform.get("os") or "unknown"
                size = layer["size"]
                sv = manifest["schemaVersion"]
                df.loc[idx, :] = [
                    uri,
                    full_uri,
                    size,
                    platform,
                    arch,
                    digest,
                    opsys,
                    sv,
                ]
                idx += 1

        seen.add(filename)

    return df


def parse_image(uri, image_outdir, tags=None):
    """
    Parse an image, getting manifests and configs and
    layers for each tag.
    """
    image = DockerImage(uri)

    # Cache tags
    if tags is None:
        tags = image.tags()

    manifests = {}
    configs = {}

    # Only get 500 tags
    if len(tags) > 500:
        tags = tags[:500]

    print(f"  Found {len(tags)} for {uri}")
    for tag in tags:
        if tag.endswith("sig") or tag.endswith("att"):
            continue
        print(f"  Retrieving tag {tag}")
        try:
            # This has layers and sizes
            manifests[tag] = image.manifest(tag)
            # Get the image config - this has creation dates
            # And also what is in every layer!
            configs[tag] = image.config(tag)
        except Exception as ex:
            print(f"  Issue retrieving tag {tag}: {ex}")

    # Save data -
    result = {"manifests": manifests, "tags": tags, "configs": configs}
    write_json(result, os.path.join(image_outdir, "manifests-config-layers.json"))


class DockerImage:
    """
    A thin client for getting metadata about an image.
    """

    def __init__(self, container_name):
        self.container_name = container_name

        # might not last forever, but we can use it for now
        self.apiroot = "https://crane.ggcr.dev"

    def get_request(self, url):
        """
        Perform a get request, expecting status code 200.
        """
        response = requests.get(url)
        if response.status_code != 200:
            sys.exit("Issue with request %s" % url)
        return response

    def tags(self):
        """
        Get image tags.
        """
        # Quay does not follow the distribution spec, crane only returns 50
        if "quay.io" in self.container_name:
            return self.tags_quay()

        url = "%s/ls/%s" % (self.apiroot, self.container_name)
        response = self.get_request(url)
        tags = [x.strip() for x in response.text.split("\n") if x.strip()]
        # Don't include tags for vex or sbom
        tags = [x for x in tags if not re.search("[.](sbom|vex)$", x)]
        return tags

    def tags_quay(self):
        """
        Custom endpoint to handle quay and pagination.
        """
        repository = self.container_name.replace("quay.io/", "", 1)
        page = 1
        tags = []
        has_more = True
        while has_more:
            url = f"https://quay.io/api/v1/repository/{repository}/tag/?limit=100&page={page}"
            response = self.get_request(url).json()
            new_tags = [
                x.get("name") for x in response.get("tags", {}) if x.get("name")
            ]
            new_tags = [x for x in new_tags if not re.search("[.](sbom|vex)$", x)]
            tags += new_tags
            has_more = response.get("has_additional") is True
            page += 1
        return tags

    def manifest(self, tag):
        url = "%s/manifest/%s:%s" % (self.apiroot, self.container_name, tag)
        response = self.get_request(url)
        return response.json()

    def digest(self, tag):
        url = "%s/digest/%s:%s" % (self.apiroot, self.container_name, tag)
        response = self.get_request(url)
        if "could not parse reference" in response:
            sys.exit("Issue getting digest: %s" % response)
        if "unsupported status" in response:
            sys.exit("Issue getting digest: %s" % response)
        if "MANIFEST_UNKNOWN" in response.text:
            sys.exit(
                f"The tag {tag} you provided is not known. Check that it and the container both exist."
            )
        return response.text

    def config(self, tag):
        url = "%s/config/%s:%s" % (self.apiroot, self.container_name, tag)
        return self.get_request(url).json()


if __name__ == "__main__":
    main()
