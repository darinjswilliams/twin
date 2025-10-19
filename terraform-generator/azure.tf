provider "azurerm" {
  features = {}
}


resource "azurerm_virtual_machine" "ml-vm" {
  name                  = "ml-vm"
  location              = "eastus"
  vm_size               = "Standard_DS1_v2"
  delete_os_disk_on_termination = true
}
