# Google Cloud Prototype

This will deploy a small SLURM cluster to Google Cloud. 

1. Note that I had most APIs enabled, but needed to enable the last one (secrets API)
2. They make you estimate your own costs. 
3. I already had the default service accounts enabled. If you don't, you get error messages.

## Tutorial

Clone the cluster-toolkit and build it. You need to have Go installed and [packer too](https://developer.hashicorp.com/packer/tutorials/docker-get-started/get-started-install-cli)

```bash
git clone https://github.com/GoogleCloudPlatform/cluster-toolkit.git
cd cluster-toolkit/
make
```
```console
$ ./gcluster --version
gcluster version v1.38.0
Built from 'main' branch.
Commit info: v1.38.0-0-g1e38ce0c
Terraform version: 1.9.4
```

Go up one directory to our cluster config:

```bash
cd ../
```

We are advised to use this version of terraform, but I tried latest (1.9.4) and it was OK.
Note that the Google Project is in the config. So we can do:

```bash
# Using a newer version of Terraform can lead to controller replacement on reconfigure for Slurm GCP v6
# Please be advised of this known issue: https://github.com/GoogleCloudPlatform/hpc-toolkit/issues/2774
# Until resolved it is advised to use Terraform 1.4.0 with Slurm deployments.
./cluster-toolkit/gcluster create ./cluster.yaml -l ERROR --skip-validators=test_tf_version_for_slurm
```

That creates a new directory. Then follow the instructions:

```bash
./cluster-toolkit/gcluster deploy performance-study --auto-approve
```

To bring it down:

```bash
./cluster-toolkit/ghpc destroy performance-study --auto-approve
```

Damn that was so much easier than the other clouds, sorry have to say it!
Note that there was some small issues with cleanup for me - the cluster seemed to add nodes and then I wasn't able to delete the network. I manually deleted the VMs and ran the delete again and that seemed to work. Note that you also need to clean up the packer images (which you will pay for).
