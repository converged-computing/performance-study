# "Bare Metal" on Google Cloud Compute Engine

This is a setup akin to Cluster Toolkit (using Terraform) to run a performance study with Flux on Google Cloud.
It is close to the cluster toolkit setup with a few optimizations. Note that You'll need these commands to share
the image we have in our project (or build from [build-images](build-images).

```bash
# Give permission to the other project to see your image
gcloud projects add-iam-policy-binding [source-project] --member serviceAccount:[target-project-id]-compute@developer.gserviceaccount.com --role roles/compute.imageUser

# Create an image from it!
gcloud compute instances create flux-singularity-rocky-2 --image-project [source-project] --image flux-singularity-rocky-8-2 --project converged-computing --machine-type c2d-standard-112 
```

After that, you'll need to save the image to the `flux-framework` family in your new project. I usually call it flux-singularity-rocky-N.

## Usage

### Create Google Service Accounts

Create default application credentials (just once):

```bash
$ gcloud auth application-default login
```

We build here with packer, so make sure you have it installed on your machine and are logged in with Google credentials.

```bash
cd build-images/cpu
make

cd build-images/gpu
```

#### CPU

For manual building, make sure to do:

- c2d-standard-112
- HPC VM instance type with Rocky 8
- 200GB boot disk, check to keep

I previously had built images with packer, but I am opting for a manual approach now to be more conservative and look at everything going on.
This means you'll want to create a c2d-standard-112 instance in the UI, run the commands, and then save the image after.

#### GPU

For manual building 

- n1-standard-32
- HPC VM instance type with Rocky 8
- 200GB boot disk, check to keep
- add 8 x v100 GPUs

### Deploy with Terraform

You can build images under [build-images](build-images) and then use the modules
provided [base](base) via [tf](tf).  Note that each experiment directory has equivalent terraform
directories with the sizes defined.
