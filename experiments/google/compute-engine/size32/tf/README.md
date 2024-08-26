# Flux Framework on GCP (size 32)

This deployment illustrates deploying a flux-framework cluster on GCP.
We use one single image base and configure via a bootscript.

# Usage

## Build images

Make note that the machine types should be compatible with those you chose in [build-images](../../build-images)
First, edit variables in [basic.tfvars](basic.tfvars).

## Curve Cert

We will need a shared curve certificate for the nodes. We provide an example [curve.cert](curve.cert),
however you can (and should) generate one on your own for cases that go beyond testing. You can do this
with a flux container:

```bash
docker run -it fluxrm/flux-sched:jammy bash
flux keygen curve.cert
```

Then copy the file locally, and later we are going to encode it into our boot script.

## Bootscript Template

> Note that we have a template provided if you don't want to customize defaults.

Set variables for your nodelist and curve certificate (and check they are good):
Make the generated script with your NODEDLIST:

```bash
make template NODELIST='flux-[001-003]'
```

Then base64 encode your curve cert and copy paste it into the variable `CURVECERT`.
Note that this can work in a programming language but bash does weird things with
the unexpected characters.

```
curve=$(cat curve.cert | base64)
$ echo $curve
```

Finally (sorry I know this is annoying) copy the entire bootscript into the
variable in [basic.tfvars](basic.tfvars).

## Deploy

Initialize the deployment with the command:

```bash
$ terraform init
```

I find it's easiest to export my Google project in the environment for any terraform configs
that mysteriously need it.

```bash
export GOOGLE_PROJECT=$(gcloud config get-value core/project)
```

You'll want to inspect basic.tfvars and change for your use case. Then:

```bash
$ make
```

And inspect the [Makefile](Makefile) to see the terraform commands we apply
to init, format, validate, and deploy. The deploy will setup networking and all the instances! Note that
you can change any of the `-var` values to be appropriate for your environment.
Verify that the cluster is up. You can shell into any compute node.

```bash
gcloud compute ssh gffw-compute-a-001 --zone us-central1-a
```

You can check the startup scripts to make sure that everything finished.

```bash
sudo journalctl -u google-startup-scripts.service
```

And then you should be able to interact with Flux!

```bash
$ flux resource list
     STATE NNODES   NCORES NODELIST
      free      3       12 gffw-compute-a-[001-003]
 allocated      0        0 
      down      0        0 
```
```bash
$ flux run --cwd /tmp -N 2 hostname
gffw-compute-a-001
gffw-compute-a-002
```

And when you are done, exit and:

```bash
$ make destroy
```

## Advanced

### Adding Buckets

You'll first want to make your buckets! Edit the script [mkbuckets.sh](scripts/mkbuckets.sh)
to your needs. E.g.,:

 - If the bucket already exists, comment out the creation command for it

You'll want to run the script and provide the name of your main bucket (e.g.,
the one with some data to mount):

```bash
$ ./mkbuckets.sh flux-operator-bucket
```

And then add the logic from [fuse-mounts.sh](scripts/fuse-mounts.sh) to your boot script.
