# WAZUH extension

- Extension Name: wazuh
- Description: Add wazuh free EDR server and agent on all the domain computers + soc fortress rules (https://github.com/socfortress/Wazuh-Rules)
- Machine name : {{lab_name}}-WAZUH
- Compatible with labs : *

## prerequisites

On ludus prepare template :
```
ludus templates add -d ubuntu-22.04-x64-server
ludus templates build
```

## Install
```
instance_id> install_extension wazuh
```

## Coexistence note

The `elastic-edr` extension also installs Sysmon on the domain machines,
into the same `c:\sysmon` path. Do not enable `wazuh` and `elastic-edr` on
the same instance: the two Sysmon installations would clobber each other's
configuration and double the endpoint event volume.


## credits
- https://github.com/aleemladha (https://github.com/Orange-Cyberdefense/GOAD/pull/215)