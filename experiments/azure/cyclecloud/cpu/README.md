# Azure CycleCloud

This setup study aims to prototype using [Azure CycleCloud](https://learn.microsoft.com/en-us/azure/cyclecloud/overview?view=cyclecloud-8). The setup uses a web-based GUI to configure a CycleCloud web server which requires a lot of box checking, RBAC, and IAM updates.

The CycleCloud VM needs Contributor Role permissions in the account Subscription for VirtualMachine, Storage, and Network. Adding those roles will allow the VM to start and control clusters.