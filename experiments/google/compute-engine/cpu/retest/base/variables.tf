
variable "cluster_storage" { 
    description = "A map with keys 'share' and 'mountpoint' describing an NFS export and its intended mount point"
    type        = map(string)
}

variable "family" {
    description = "The source image x86 prefix to be used by the compute node(s)"
    type        = string
    default     = "global"
}

variable "compute_node_specs" {
    description = "A list of compute node specifications"
    type = list(object({
       name_prefix  = string
       machine_arch = string
       machine_type = string
       gpu_type     = string
       gpu_count    = number
       compact      = bool
       instances    = number
       properties   = set(string)
       boot_script  = string
    }))
    default = []
}

variable "compute_scopes" {
    description = "The set of access scopes for compute node instances"
    default     = [ "cloud-platform" ]
    type        = set(string)
}

variable "project_id" {
    description = "The GCP project ID"
    type        = string
}

variable "region" {
    description = "The GCP region where the cluster resides"
    type = string
}

variable "service_account_emails" {
    description = "A map with keys: 'compute', 'login', 'manager' that map to the service account to be used by the respective nodes"
    type        = map(string)
}

variable "subnetwork" {
    description = "Subnetwork to deploy to"
    type        = string
}
