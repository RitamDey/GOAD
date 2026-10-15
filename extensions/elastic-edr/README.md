# ELASTIC-EDR extension

- Extension Name: elastic-edr
- Description: Add an Elastic Stack 8.x (Elasticsearch + Kibana + Fleet) with
  Endpoint Security (EDR) and Elastic Defend, and an Elastic Agent on all the
  domain computers. Sysmon is installed as the EDR event source.
- Machine name : {{lab_name}}-ELASTIC-EDR
- Compatible with labs : *
- Providers : ludus / virtualbox / vmware / vmware_esxi / proxmox / azure / aws

## What it does

- Deploys a self managed Elastic Stack 8.x on one linux machine (16GB RAM / 4 cpu)
- X-Pack security is enabled (TLS is left off for a simple isolated lab)
- A Fleet agent policy (GOAD-EDR-Policy) with the `system` package is created,
  which enables Endpoint Security (process lineage, memory, detections) on the
  enrolled agents -> this is the EDR + Elastic Defend part
- Installs Sysmon + Elastic Agent on every domain Windows machine and enrolls it
  in Fleet using an enrollment token
- Kibana / Fleet is served on http://{{ip_range}}.53:5601
- Run a GOAD attack and watch the alert appear in Kibana -> Security -> Alerts

This is the "full attack / defend / purple team" upgrade of the `elk` extension:
`elk` ships winlogbeat log aggregation, `elastic-edr` ships real Fleet + EDR +
Defend detection. Do not install both at the same time.

## Credentials (this is a lab)

| user          | password             |
|---------------|----------------------|
| elastic       | changeme-elastic     |
| kibana_system | changeme-kibana      |

Kibana / Fleet : http://{{ip_range}}.53:5601
Elasticsearch  : http://{{ip_range}}.53:9200

## prerequisites

- 16GB RAM / 4 cpu / >= 80GB free disk on the ELASTIC-EDR machine (already set in
  every provider file)
- On ludus prepare template :
```
ludus templates add -d ubuntu-22.04-x64-server
ludus templates build
```
- On proxmox you need an `Ubuntu_2204_x64` template (default id 922040)

## Install
```
instance_id> install_extension elastic-edr
```

## Uninstall

- Not implemented yet

## credits
- Based on the structure of the `elk` and `wazuh` extensions
- Elastic Fleet / EDR : https://www.elastic.co/guide/en/fleet/current/index.html
