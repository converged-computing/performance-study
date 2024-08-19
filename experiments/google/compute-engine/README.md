# "Bare Metal" on Google Cloud Compute Engine

This is a backup for HPC Toolkit to run a performance study with Flux on Google Cloud.

## Usage

### Create Google Service Accounts

Create default application credentials (just once):

```bash
$ gcloud auth application-default login
```

We build here with packer, so make sure you have it installed on your machine and are logged in with Google credentials.

```bash
cd build-images
make
```

For manual building, make sure to do:

- HPC VM instance type with Rocky 8
- 200GB boot disk, check to keep

I previously had built images with packer, but I am opting for a manual approach now to be more conservative and look at everything going on.
This means you'll want to create a c2d-standard-112 instance in the UI, run the commands, and then save the image after.

### Deploy with Terraform

You can build images under [build-images](build-images) and then use the modules
provided [base](base) via [tf](tf). 
