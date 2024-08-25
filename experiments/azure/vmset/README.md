# Flux on Azure

This is an attempt at a "bare metal" experience for running Singularity on Azure, and with CPU. I am creating this as a backup for CycleCloud.


## Usage

### 1. Build Images

Since I'm new to Azure, I'm starting by creating a VM and then saving the image, which I did through the console (and saved the template) and all of the associated scripts are in [build-images](build-images). 

**CPU** 

I chose:

- ubuntu HPC 22.04 preview NDv5 x86 gen2
- South Central US
- Zone (allow auto select, or select infrastructure redundant)
- HB120-96rs_v3 (about $4/hour)
- username: ubuntu
- select your ssh key
- defaults to 30GB disk, but I chose 256 anticipating container pulls.

And interactively I ran each of:

- install-deps.sh
- install-flux.sh
- install-singularity.sh

And then you can actually click to create the instance group in the user interface, and it's quite easy.

#### Important Notes

If you don't give your VMset a long enough name, you get it filled in with random letters and numbers, e.g., `fluxp4z4m000000` which we don't want. I usually do `flux-usernetes` only because I know that will come out to be `flux-user0000[0-1]`. If you call it something else you need to change that prefix in the startup-script.sh. I also was never able to create this with a proximity group, despite having this with my template. More specifically you will need to:

- Add the `startup-script.sh` to the user data section
- Ensure you click on the network setup and enable the public ip address and port 22 open so you can ssh in
- use a PEM key over a password

Note that if your instances don't connect, check the VMset networking tab and make sure port 8050 ingress/egress is open. Add other rules that make sense.

### 2. Check Flux

Check the cluster status, the overlay status, and try running a job:

```bash
flux resource list
```
```bash
flux run -N 2 hostname
```

And lammps?

```bash
cd /home/azureuser/lammps
flux run -N 2 --ntasks 96 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 2 -v y 2 -v z 2 -in ./in.reaxff.hns -nocite
```

How to sanity check Infiniband:

```bash
ip link
# should show ib0 UP

ibv_devices 
# (should show two)
ibv_devinfo
# for a device

/etc/init.d/openibd status
```

If you need to check memory that is seen by flux:

```bash
flux run sh -c 'ulimit -l' --rlimit=memlock
```

Note that if you need to share files:

```bash
flux archive create --mmap -C /home/azureuser/usernetes join-command
flux exec -x 0 -r all flux archive extract -C /home/azureuser/usernetes
```
