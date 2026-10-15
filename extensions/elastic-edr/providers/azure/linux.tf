"elastic-edr" = {
  name               = "elastic-edr"
  linux_offer        = "0001-com-ubuntu-server-jammy"
  linux_sku          = "22_04-lts-gen2"
  linux_version      = "latest"
  private_ip_address = "{{ip_range}}.53"
  password           = "654qsdIazajsQ*"
  size               = "Standard_B4ms"  # 4cpu/16G
}
