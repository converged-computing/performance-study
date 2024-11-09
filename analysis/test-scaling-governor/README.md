# Scaling Governor

We want to bring up two quick clusters (on AWS and Google) and look at the default setting for the scaling governor ([reference](https://docs.kernel.org/admin-guide/pm/cpufreq.html)). Also note that if you are using node feature discovery, this is set as an [NFD label](https://kubernetes-sigs.github.io/node-feature-discovery/master/usage/features.html#cpu). Since AWS had values varying and Google all the same, I'll look at those two clouds. I suspect Google is set to performance (to max value at the cost of power) and AWS the opposite, but that is my guess. This experiment was run on November 9, 2024.

Note that both seem to be set to "performance" so that doesn't explain it, but there is a lot more interesting stuff to look at with respect to drivers, etc. I am saving the dmesg output and some quick glances I took, and maybe we should do a Hackathon to explore more together.

## AWS

```bash
time eksctl create cluster --config-file ./eks-config.yaml
aws eks update-kubeconfig --region us-east-2 --name scaling-government
```

The default scaling governor is set for performance.

```console
# cat /sys/module/cpufreq/parameters/default_governor 
performance

# cat module/cpufreq/parameters/off 
0
```
```console
for filename in  $(ls /sys/devices/system/cpu/cpu0/cache/index0/); do echo $filename; cat /sys/devices/system/cpu/cpu0/cache/index0/$filename; echo; done
coherency_line_size
64

id
0

level
1

number_of_sets
64

physical_line_partition
1

shared_cpu_list
0

shared_cpu_map
00000000,00000000,00000001

size
32K

type
Data

uevent

ways_of_associativity
8
```

```console
# ls /sys/devices/cpu/power/
autosuspend_delay_ms  runtime_active_time  runtime_suspended_time
control               runtime_status
[root@ip-192-168-10-93 sys]# cat /sys/devices/cpu/power/runtime_status 
unsupported
[root@ip-192-168-10-93 sys]# cat /sys/devices/cpu/power/runtime_active_time 
0
[root@ip-192-168-10-93 sys]# cat /sys/devices/cpu/power/runtime_suspended_time 
0
[root@ip-192-168-10-93 sys]# cat /sys/devices/cpu/power/control 
auto
```

```console
# cat module/cpuidle/parameters/
governor  off       
gke-test-cluster-default-pool-6c51551d-t6mb /sys # cat module/cpuidle/parameters/off 
0
```

```console
 find . -name *governor
./devices/system/cpu/cpuidle/current_governor
./module/cpuidle/parameters/governor
./module/cpufreq/parameters/default_governor
[root@ip-192-168-10-93 sys]# cat devices/system/cpu/cpuidle/current_governor
menu
[root@ip-192-168-10-93 sys]# cat module/cpuidle/parameters/governor 

[root@ip-192-168-10-93 sys]# cat module/cpufreq/parameters/default_governor 
performance
```

```console
# cat /etc/default/grub 
GRUB_CMDLINE_LINUX_DEFAULT="console=tty0 console=ttyS0,115200n8 net.ifnames=0 biosdevname=0 nvme_core.io_timeout=4294967295 rd.emergency=poweroff rd.shell=0"
GRUB_TIMEOUT=0
GRUB_DISABLE_RECOVERY="true"
GRUB_TERMINAL="ec2-console"
GRUB_X86_USE_32BIT="true"
```

```console
[root@ip-192-168-10-93 sys]# cat /etc/kubernetes/kubelet/kubelet-config.json 
{
  "kind": "KubeletConfiguration",
  "apiVersion": "kubelet.config.k8s.io/v1beta1",
  "address": "0.0.0.0",
  "authentication": {
    "anonymous": {
      "enabled": false
    },
    "webhook": {
      "cacheTTL": "2m0s",
      "enabled": true
    },
    "x509": {
      "clientCAFile": "/etc/kubernetes/pki/ca.crt"
    }
  },
  "authorization": {
    "mode": "Webhook",
    "webhook": {
      "cacheAuthorizedTTL": "5m0s",
      "cacheUnauthorizedTTL": "30s"
    }
  },
  "clusterDomain": "cluster.local",
  "hairpinMode": "hairpin-veth",
  "readOnlyPort": 0,
  "cgroupDriver": "systemd",
  "cgroupRoot": "/",
  "featureGates": {
    "RotateKubeletServerCertificate": true,
    "KubeletCredentialProviders": true
  },
  "protectKernelDefaults": true,
  "serializeImagePulls": false,
  "serverTLSBootstrap": true,
  "tlsCipherSuites": [
    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305",
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_AES_128_GCM_SHA256"
  ],
  "clusterDNS": [
    "10.100.0.10"
  ],
  "evictionHard": {
    "memory.available": "100Mi",
    "nodefs.available": "10%",
    "nodefs.inodesFree": "5%"
  },
  "kubeReserved": {
    "cpu": "310m",
    "ephemeral-storage": "1Gi",
    "memory": "1355Mi"
  },
  "providerID": "aws:///us-east-2b/i-046aec8bd20ee1851",
  "systemReservedCgroup": "/system",
  "kubeReservedCgroup": "/runtime"
}
```

## Google

```bash
time gcloud container clusters create test-cluster \
    --threads-per-core=1 \
    --num-nodes=2 \
    --machine-type=c2d-standard-112 \
    --enable-gvnic \
    --network=mtu9k \
    --placement-type=COMPACT \
    --region=us-central1-a \
    --project=llnl-flux
```

Note that the content in cpufreq is empty, so I'm going to look at an individual CPU.
Ah wait, I think I found it elsewhere:

```console
# cat /sys/module/cpufreq/parameters/default_governor 
performance
```

and "off" is set to 0.

```console
for filename in  $(ls /sys/devices/system/cpu/cpu0/cache/index0/); do echo $filename; cat sys/devices/system/cpu/cpu0/cache/index0/$filename; echo; done
coherency_line_size
64

id
0

level
1

number_of_sets
64

physical_line_partition
1

shared_cpu_list
0

shared_cpu_map
000000,00000001

size
32K

type
Data

uevent

ways_of_associativity
8
```

```console
cat /sys/devices/system/cpu/cpu0/cache/uevent 
# empty
```

```console
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/isolated 

gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/kernel_max 
511
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/modalias 
cpu:type:x86,ven0002fam0019mod0001:feature:,0000,0001,0002,0003,0004,0005,0006,0007,0008,0009,000B,000C,000D,000E,000F,0010,0011,0013,0017,0018,0019,001A,001C,0020,0021,0022,0023,0024,0025,0026,0027,0028,0029,002B,002C,002D,002E,002F,0030,0031,0034,0036,0037,0038,0039,003A,003B,003D,0064,0068,006E,0070,0072,0074,0075,0078,0079,007A,007F,0080,0081,0083,0089,008C,008D,0091,0093,0094,0095,0096,0097,0099,009A,009B,009C,009D,009E,009F,00C0,00C1,00C4,00C5,00C6,00C7,00C8,00C9,00D6,00E7,00EA,00ED,00F0,00F1,00F3,00F5,00F6,00F9,00FA,00FB,00FC,010F,0120,0121,0123,0125,0127,0128,0129,012A,0132,0133,0134,0137,0138,013D,0140,0141,0142,0165,016C,016E,016F,0179,01A0,01A2,01AC,01AE,01AF,01B2,01B3,01B8,01BC,01C2,01E0,01E3,0202,0209,020A,0216,0244,029C
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/offline 

gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/online 
0-55       
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/possible 
0-55

```

```console
# cat /sys/devices/system/cpu/power/runtime_active_time 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/power/runtime_status 
unsupported
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/power/runtime_suspended_time 
0
```
```console
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/smt/active 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/smt/control 
notsupported
```

```console
 ls /sys/devices/system/cpu/cpuidle/
available_governors  current_driver  current_governor  current_governor_ro
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpuidle/available_governors 
ladder menu 
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpuidle/current_
cat: /sys/devices/system/cpu/cpuidle/current_: No such file or directory
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpuidle/current_driver 
acpi_idle
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpuidle/current_governor
menu
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpuidle/current_governor_ro 
menu

```

```console
# ls /sys/devices/system/cpu/cpu0/cpuidle/state0/
above  below  default_status  desc  disable  latency  name  power  rejected  residency  time  usage
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/above 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/below 
5
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/default_status 
enabled
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/desc 
CPUIDLE CORE POLL IDLE
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/disable 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/latency 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/name
POLL
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/power
4294967295
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/rejected 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/residency 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/time 
274
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/cpuidle/state0/usage 
5
```

```console
/ # cat /sys/devices/system/cpu/cpu0/power/autosuspend_delay_ms 
cat: /sys/devices/system/cpu/cpu0/power/autosuspend_delay_ms: Input/output error
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/power/control 
auto
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/power/pm_qos_resume_latency_us 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/power/runtime_active_time 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/power/runtime_status 
unsupported
gke-test-cluster-default-pool-6c51551d-t6mb / # cat /sys/devices/system/cpu/cpu0/power/runtime_suspended_time 
0
gke-test-cluster-default-pool-6c51551d-t6mb / # 

```

```console
for filename in  $(ls /sys/devices/system/cpu/cpu0/topology/); do echo $filename; cat sys/devices/system/cpu/cpu0/topology/$filename; echo; done
cluster_cpus
000000,00000001

cluster_cpus_list
0

cluster_id
65535

core_cpus
000000,00000001

core_cpus_list
0

core_id
0

core_siblings
000000,0fffffff

core_siblings_list
0-27

die_cpus
000000,0fffffff

die_cpus_list
0-27

die_id
0

package_cpus
000000,0fffffff

package_cpus_list
0-27

physical_package_id
0

thread_siblings
000000,00000001

thread_siblings_list
0

```

```console
processor       : 0
vendor_id       : AuthenticAMD
cpu family      : 25
model           : 1
model name      : AMD EPYC 7B13
stepping        : 0
microcode       : 0xffffffff
cpu MHz         : 3049.998
cache size      : 512 KB
physical id     : 0
siblings        : 28
core id         : 0
cpu cores       : 28
apicid          : 0
initial apicid  : 0
fpu             : yes
fpu_exception   : yes
cpuid level     : 13
wp              : yes
flags           : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx mmxext fxsr_opt pdpe1gb rdtscp lm constant_tsc rep_good nopl nonstop_tsc cpuid extd_apicid tsc_known_freq pni pclmulqdq monitor ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt aes xsave avx f16c rdrand hypervisor lahf_lm cmp_legacy cr8_legacy abm sse4a misalignsse 3dnowprefetch osvw topoext invpcid_single ssbd ibrs ibpb stibp vmmcall fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid rdseed adx smap clflushopt clwb sha_ni xsaveopt xsavec xgetbv1 clzero xsaveerptr arat npt nrip_save umip vaes vpclmulqdq rdpid fsrm
bugs            : sysret_ss_attrs null_seg spectre_v1 spectre_v2 spec_store_bypass srso
bogomips        : 6099.99
TLB size        : 2560 4K pages
clflush size    : 64
cache_alignment : 64
address sizes   : 48 bits physical, 48 bits virtual
power management:

```

kubelet settings

```console
# cat /etc/default/kubelet 
KUBELET_OPTS="--v=2 --cloud-provider=external --experimental-mounter-path=/home/kubernetes/containerized_mounter/mounter --cert-dir=/var/lib/kubelet/pki/ --kubeconfig=/var/lib/kubelet/kubeconfig --image-credential-provider-config=/etc/srv/kubernetes/cri_auth_config.yaml --image-credential-provider-bin-dir=/home/kubernetes/bin --max-pods=110 --node-labels=cloud.google.com/gke-boot-disk=pd-balanced,cloud.google.com/gke-container-runtime=containerd,cloud.google.com/gke-cpu-scaling-level=112,cloud.google.com/gke-logging-variant=DEFAULT,cloud.google.com/gke-max-pods-per-node=110,cloud.google.com/gke-memory-gb-scaling-level=458,cloud.google.com/gke-nodepool=default-pool,cloud.google.com/gke-os-distribution=cos,cloud.google.com/gke-placement-group=default-pool,cloud.google.com/gke-provisioning=standard,cloud.google.com/gke-stack-type=IPV4,cloud.google.com/machine-family=c2d,cloud.google.com/private-node=false --volume-plugin-dir=/home/kubernetes/flexvolume --node-status-max-images=25 --container-runtime-endpoint=unix:///run/containerd/containerd.sock --runtime-cgroups=/system.slice/containerd.service --registry-qps=10 --registry-burst=20 --config /home/kubernetes/kubelet-config.yaml --pod-sysctls='net.core.somaxconn=1024,net.ipv4.conf.all.accept_redirects=0,net.ipv4.conf.all.forwarding=1,net.ipv4.conf.all.route_localnet=1,net.ipv4.conf.default.forwarding=1,net.ipv4.ip_forward=1,net.ipv4.tcp_fin_timeout=60,net.ipv4.tcp_keepalive_intvl=60,net.ipv4.tcp_keepalive_probes=5,net.ipv4.tcp_keepalive_time=300,net.ipv4.tcp_rmem=4096 87380 6291456,net.ipv4.tcp_syn_retries=6,net.ipv4.tcp_tw_reuse=0,net.ipv4.tcp_wmem=4096 16384 4194304,net.ipv4.udp_rmem_min=4096,net.ipv4.udp_wmem_min=4096,net.ipv6.conf.all.disable_ipv6=1,net.ipv6.conf.default.accept_ra=0,net.ipv6.conf.default.disable_ipv6=1,net.netfilter.nf_conntrack_generic_timeout=600,net.netfilter.nf_conntrack_tcp_be_liberal=1,net.netfilter.nf_conntrack_tcp_timeout_close_wait=3600,net.netfilter.nf_conntrack_tcp_timeout_established=86400' --cgroup-driver=systemd  --pod-infra-container-image=us-central1-artifactregistry.gcr.io/gke-release/gke-release/pause:3.8@sha256:880e63f94b145e46f1b1082bb71b85e21f16b99b180b9996407d61240ceb9830 --version=v1.30.5-gke.1355000"
KUBE_COVERAGE_FILE="/var/log/kubelet.cov"
```
