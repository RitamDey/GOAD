"elastic-edr" = {
  name               = "elastic-edr"
  linux_sku          = "22_04-lts-gen2"
  linux_version      = "latest"
  ami                = "ami-04c332520bd9cedb4"
  private_ip_address = "{{ip_range}}.53"
  password           = "654qsdIazajsQ*"
  size               = "m5a.xlarge"  # 4cpu / 16GB
}
