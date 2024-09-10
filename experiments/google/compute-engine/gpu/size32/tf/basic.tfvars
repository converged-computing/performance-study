compute_family = "flux-framework-ubuntu-gpu"
compute_node_specs = [
  {
    name_prefix  = "flux"
    machine_arch = "x86-64"
    machine_type = "n1-standard-32"
    gpu_type     = "nvidia-tesla-v100"
    gpu_count    = 8
    compact      = false
    zone         = "us-central1-c"
    instances    = 32
    properties   = []
    boot_script  = <<BOOT_SCRIPT
#!/bin/bash

# sudo journalctl -u google-startup-scripts.service

# IMPORTANT - this needs to match the local cluster
fluxroot=/usr

# ens8

echo "Flux username: flux"
echo "Flux install root: /usr"
export fluxroot

mkdir -p /var/nfs/home || true
chown nobody:nobody /var/nfs/home || true

ip_addr=$(hostname -I)

echo "flux ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
printf "flux user identifiers:\n$(id flux)\n"

# This is done in build
printf "\n📦 Resources\n"
cat /usr/etc/flux/system/R

printf "\n🦊 Independent Minister of Privilege\n"
cat /etc/flux/imp/conf.d/imp.toml

echo "🐸 Broker Configuration"
cat /usr/etc/flux/system/conf.d/system.toml

mkdir -p /run/flux
chown -R flux /run/flux

# /usr/sbin/create-munge-key
service munge start
systemctl start flux.service
echo "export FLUX_URI=local:///run/flux/local" >> /home/sochat1_llnl_gov/.bashrc
echo "LD_LIBRARY_PATH=/usr/local/cuda/lib" >> /etc/environment

# This enables NFS
nfsmounts=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/nfs-mounts" -H "Metadata-Flavor: Google")

if [[ "X$nfsmounts" != "X" ]]; then
    echo "Enabling NFS mounts"
    share=$(echo $nfsmounts | jq -r '.share')
    mountpoint=$(echo $nfsmounts | jq -r '.mountpoint')

    bash -c "sudo echo $share $mountpoint nfs defaults,hard,intr,_netdev 0 0 >> /etc/fstab"
    mount -a
fi
BOOT_SCRIPT

  },
]
compute_scopes = ["cloud-platform"]
