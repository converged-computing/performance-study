
# VARIABLES # for you to edit!

locals {
  name   = "flux"
  pwd    = basename(path.cwd)
  location = "West US"  
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "example" {
  name     = "${local.name}-resource-group"
  location = local.location
}

resource "azurerm_virtual_network" "example" {
  name                = "${local.name}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
}

resource "azurerm_subnet" "example" {
  name                 = "internal"
  resource_group_name  = azurerm_resource_group.example.name
  virtual_network_name = azurerm_virtual_network.example.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_public_ip" "example" {
  name                = "${local.name}-batch-ip"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  allocation_method   = "Dynamic"
  domain_name_label   = "batch-custom-img"
}

resource "azurerm_network_interface" "example" {
  name                = "${local.name}-batch-nic"
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name

  ip_configuration {
    name                          = "${local.name}-configuration-source"
    subnet_id                     = azurerm_subnet.example.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.example.id
  }
}

resource "azurerm_storage_account" "example" {
  name     = "${local.name}-storage"
  resource_group_name      = azurerm_resource_group.example.name
  location                 = azurerm_resource_group.example.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}


resource "azurerm_batch_account" "example" {
  name     = "${local.name}-batch"
  resource_group_name                 = azurerm_resource_group.example.name
  location                            = azurerm_resource_group.example.location
  account_tier                        = "Standard"
  account_replication_type            = "LRS"
  pool_allocation_mode                = "BatchService"
  storage_account_id                  = azurerm_storage_account.example.id
  storage_account_authentication_mode = "StorageKeys"
}


resource "azurerm_storage_container" "example" {
  name                  = "vhds"
  storage_account_name  = azurerm_storage_account.example.name
  container_access_type = "blob"
}

resource "azurerm_virtual_machine" "example" {
  name                  = "${local.name}-vm"
  location              = azurerm_resource_group.example.location
  resource_group_name   = azurerm_resource_group.example.name
  network_interface_ids = ["${azurerm_network_interface.example.id}"]
  vm_size               = "Standard_D1_v2"

  storage_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  storage_os_disk {
    name          = "myosdisk1"
    vhd_uri       = "${azurerm_storage_account.example.primary_blob_endpoint}${azurerm_storage_container.example.name}/myosdisk1.vhd"
    caching       = "ReadWrite"
    create_option = "FromImage"
    disk_size_gb  = "30"
  }

  os_profile {
    computer_name  = "${local.name}-vm"
  }

  os_profile_linux_config {
    disable_password_authentication = false
  }
}










resource "azurerm_batch_certificate" "example" {
  resource_group_name  = azurerm_resource_group.example.name
  account_name         = azurerm_batch_account.example.name
  certificate          = filebase64("certificate.cer")
  format               = "Cer"
  thumbprint           = "312d31a79fa0cef49c00f769afc2b73e9f4edf34"
  thumbprint_algorithm = "SHA1"
}

resource "azurerm_batch_pool" "example" {
  name     = "${local.name}-batch-pool"
  resource_group_name = azurerm_resource_group.example.name
  account_name        = azurerm_batch_account.example.name
  display_name        = "Test Acc Pool Auto"
  vm_size             = "Standard_A1"
  node_agent_sku_id   = "batch.node.ubuntu 20.04"

  auto_scale {
    evaluation_interval = "PT15M"

    formula = <<EOF
      startingNumberOfVMs = 2;
      maxNumberofVMs = 2;
      pendingTaskSamplePercent = $PendingTasks.GetSamplePercent(180 * TimeInterval_Second);
      pendingTaskSamples = pendingTaskSamplePercent < 70 ? startingNumberOfVMs : avg($PendingTasks.GetSample(180 *   TimeInterval_Second));
      $TargetDedicatedNodes=min(maxNumberofVMs, pendingTaskSamples);
EOF

  }

  storage_image_reference {
    publisher = "microsoft-azure-batch"
    offer     = "ubuntu-server-container"
    sku       = "20-04-lts"
    version   = "latest"
  }

  start_task {
    command_line       = "echo 'Hello World from $env'"
    task_retry_maximum = 1
    wait_for_success   = true

    common_environment_properties = {
      env = "TEST"
    }

    user_identity {
      auto_user {
        elevation_level = "NonAdmin"
        scope           = "Task"
      }
    }
  }

  certificate {
    id             = azurerm_batch_certificate.example.id
    store_location = "CurrentUser"
    visibility     = ["StartTask"]
  }
}
