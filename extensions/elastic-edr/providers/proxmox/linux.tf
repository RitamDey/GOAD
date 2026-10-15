"elastic-edr" = {
  name               = "ELASTIC-EDR"
  desc               = "elastic-edr GOAD"
  cores              = 4
  memory             = 16384
  clone              = "Ubuntu_2204_x64"
  dns                = "{{ip_range}}.1"
  ip                 = "{{ip_range}}.53/24"
  gateway            = "{{ip_range}}.1"
}
