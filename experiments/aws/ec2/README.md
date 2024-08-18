# Flux with EFA on EC2

This is a backup because parallel cluster with Slurm is really hard to get working,
but terraform has been more reliably. We are going to create a Flux cluster in EC2 and then
pull down Singularity containers to it.

## Usage

### 1. Build Images

Note that we previously built with packer. That no longer seems to work ([maybe this issue](https://github.com/hashicorp/packer/issues/8180))
Instead we are going to run the commands there manually and save the AMI. The previous instruction was to export AWS credentials, cd into build-images,
and `make`. For the manual build, you'll need to create an m5.large instance in the web UI, ubuntu 22.04, and manually run the contents of each
of the scripts in [build-images](build-images). For example, for the top AMI below I ran each of:

- install-deps.sh
- install-flux.sh
- install-singularity.sh

### Deploy with Terraform

Once you have images, we deploy! Make sure you update the AMI to be the one you built.

```bash
$ cd tf
```

And then init and build. Note that this will run `init, fmt, validate` and `build` in one command.
They all can be run with `make`. Make sure to change the number of instances to the size that you want - the min and max should be identical:

```bash
$ make
```

You can then shell into any node, and check the status of Flux. I usually grab the instance
name via "Connect" in the portal, but you could likely use the AWS client for this too.

```bash
$ ssh -o 'IdentitiesOnly yes' -i "mykey.pem" ubuntu@ec2-xx-xxx-xx-xxx.compute-1.amazonaws.com
```

#### Check Flux

Check the cluster status, the overlay status, and try running a job:

```bash
$ flux resource list
     STATE NNODES   NCORES NODELIST
      free      2        2 i-012fe4a110e14da1b,i-0354d878a3fd6b017
 allocated      0        0 
      down      0        0 
```
```bash
$ flux run -N 2 hostname
i-012fe4a110e14da1b.ec2.internal
i-0354d878a3fd6b017.ec2.internal
```

You can look at the startup script logs like this if you need to debug.

```bash
$ cat /var/log/cloud-init-output.log
```

At this point (with a running, working cluster) move into the [experiment](experiment) directory.
