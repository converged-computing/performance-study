# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

module "compute_nodes" {
    source          = "./modules/compute"

    for_each = {
        for index, node in var.compute_node_specs:
        node.name_prefix => node
    }
    project_id        = var.project_id
    region            = var.region

    family            = var.family
    
    name_prefix       = each.value.name_prefix
    subnetwork        = var.subnetwork
    machine_arch      = each.value.machine_arch
    machine_type      = each.value.machine_type
    num_instances     = each.value.instances

    boot_script       = lookup(each.value, "boot_script", null)
    compact_placement = lookup(each.value, "compact", false)
    gpu               = lookup(each.value, "gpu_type", null) == null || lookup(each.value, "gpu_count", 0) <= 0 ? null : {
        type  = each.value.gpu_type
        count = each.value.gpu_count
    }
    service_account   = {
        email  = var.service_account_emails["compute"]
        scopes = var.compute_scopes
    }
    nfs_mounts         = var.cluster_storage
}
