# ELK extension

- Extension Name: elk
- Description: Add an ELK to the current lab
- Machine name : {{lab_name}}-ELK
- Compatible with labs : *

## prerequisites

On ludus prepare template :
```
ludus templates add -d ubuntu-22.04-x64-server
ludus templates build
```

## Install

```
instance_id> install_extension elk
```

- machine: {{lab_name}}-ELK
- filebeat agent domain computer machines


## Uninstall

- Not implemented yet

## Coexistence note

The `elastic-edr` extension also installs Sysmon on the domain machines,
into the same `c:\sysmon` path (config reloaded from its own bundled file).
Do not enable `elk` and `elastic-edr` on the same instance: the two Sysmon
installations would clobber each other's configuration and double the
endpoint event volume.
