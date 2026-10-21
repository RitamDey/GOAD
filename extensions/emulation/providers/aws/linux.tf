"emulation" = {
  name               = "emulation"
  linux_sku          = "22_04-lts-gen2"
  linux_version      = "latest"
  ami                = "ami-04c332520bd9cedb4"
  private_ip_address = "{{ip_range}}.54"
  password           = "654qsdIazajsQ*"
  size               = "m5a.large"  # 2cpu / 8GB
}
