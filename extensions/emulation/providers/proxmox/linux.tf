"emulation" = {
  name               = "EMULATION"
  desc               = "emulation GOAD"
  cores              = 2
  memory             = 8192
  clone              = "Ubuntu_2204_x64"
  dns                = "{{ip_range}}.1"
  ip                 = "{{ip_range}}.54/24"
  gateway            = "{{ip_range}}.1"
}
