#!/bin/bash

# Write the hostlist size here:
NODELIST=flux-user00000[0-9],flux-user00000A,flux-user00000B,flux-user00000C,flux-user00000D,flux-user00000E,flux-user00000F,flux-user00000G,flux-user00000H,flux-user00000I,flux-user00000J,flux-user00000K,flux-user00000L,flux-user00000M,flux-user00000N,flux-user00000O,flux-user00000P,flux-user00000Q,flux-user00000R,flux-user00000S,flux-user00000T,flux-user00000U,flux-user00000V
lead_broker=flux-user000000

flux R encode --hosts=$NODELIST --local > R
mv R /etc/flux/system/R
chown ubuntu /etc/flux/system/R

# Figure out the lead broker, the first in the list
echo "The lead broker is $lead_broker"
host=$(hostname)
echo "The host is $host"

# Make the run directories in case not made yet
mkdir -p /run/flux
mkdir -p /home/ubuntu/run/flux
chown -R ubuntu /run/flux

# Write updated broker.toml
cat <<EOF | tee /tmp/broker.toml
# Flux needs to know the path to the IMP executable
[exec]
imp = "/usr/libexec/flux/flux-imp"

# Allow users other than the instance owner (guests) to connect to Flux
# Optionally, root may be given "owner privileges" for convenience
[access]
allow-guest-user = true
allow-root-owner = true

# Point to resource definition generated with flux-R(1).
# Uncomment to exclude nodes (e.g. mgmt, login), from eligibility to run jobs.
[resource]
path = "/etc/flux/system/R"

# Point to shared network certificate generated flux-keygen(1).
# Define the network endpoints for Flux's tree based overlay network
# and inform Flux of the hostnames that will start flux-broker(1).
[bootstrap]
curve_cert = "/etc/flux/system/curve.cert"

default_port = 8050
default_bind = "tcp://eth0:%p"
default_connect = "tcp://%h:%p"

# Rank 0 is the TBON parent of all brokers unless explicitly set with
# parent directives.
# The actual ip addresses (for both) need to be added to /etc/hosts
# of each VM for now.
hosts = [
   { host = "$NODELIST" },
]
# Speed up detection of crashed network peers (system default is around 20m)
[tbon]
tcp_user_timeout = "2m"
EOF

mkdir -p /etc/flux/system/conf.d
mv /tmp/broker.toml /etc/flux/system/conf.d/broker.toml

# Write new service file
cat <<EOF | tee /tmp/flux.service
[Unit]
Description=Flux message broker
Wants=munge.service

[Service]
Type=notify
NotifyAccess=main
TimeoutStopSec=90
KillMode=mixed
ExecStart=/bin/bash -c '\
  XDG_RUNTIME_DIR=/run/user/$UID \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$UID/bus \
  /usr/bin/flux broker \
  --config-path=/etc/flux/system/conf.d \
  -Scron.directory=/etc/flux/system/cron.d \
  -Srundir=/home/ubuntu/run/flux \
  -Sstatedir=/var/lib/flux \
  -Slocal-uri=local:///home/ubuntu/run/flux/local \
  -Slog-stderr-level=6 \
  -Slog-stderr-mode=local \
  -Sbroker.rc2_none \
  -Sbroker.quorum=1 \
  -Sbroker.quorum-timeout=none \
  -Sbroker.exit-norestart=42 \
  -Sbroker.sd-notify=1 \
  -Scontent.restore=auto'
SyslogIdentifier=flux
ExecReload=/usr/bin/flux config reload
Restart=always
RestartSec=5s
RestartPreventExitStatus=42
SuccessExitStatus=42
User=ubuntu
RuntimeDirectory=flux
RuntimeDirectoryMode=0755
StateDirectory=flux
StateDirectoryMode=0700
PermissionsStartOnly=true
DefaultLimitMEMLOCK=infinity
LimitMEMLOCK=infinity
TasksMax=infinity
LimitNPROC=infinity
# ExecStartPre=/usr/bin/loginctl enable-linger flux
# ExecStartPre=bash -c 'systemctl start user@$(id -u flux).service'


#
# Delegate cgroup control to user flux, so that systemd doesn't reset
#  cgroups for flux initiated processes, and to allow (some) cgroup
#  manipulation as user flux.
#
Delegate=yes

[Install]
WantedBy=multi-user.target
EOF
mv /tmp/flux.service /lib/systemd/system/flux.service

# See the README.md for commands how to set this manually without systemd
systemctl daemon-reload
systemctl restart flux.service
systemctl status flux.service

export FLUX_URI=local:///home/ubuntu/run/flux/local
echo "export FLUX_URI=local:///home/ubuntu/run/flux/local" >> /home/ubuntu/.bashrc
