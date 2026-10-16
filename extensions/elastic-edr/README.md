# ELASTIC-EDR extension

- Extension Name: elastic-edr
- Description: Add an Elastic Stack 8.x (Elasticsearch + Kibana + Fleet) with
  Elastic Defend (EDR) and an Elastic Agent on all the domain computers.
  Sysmon is installed as the EDR event source.
- Machine name : {{lab_name}}-ELASTIC-EDR
- Compatible with labs : *
- Providers : ludus / virtualbox / vmware / vmware_esxi / proxmox / azure / aws

## What it does

- Deploys a self managed Elastic Stack 8.x on one linux machine (16GB RAM / 4 cpu)
- X-Pack security is enabled (TLS is left off for a simple isolated lab)
- Creates the Fleet agent policy `GOAD-EDR-Policy` (preconfigured in kibana.yml)
  and attaches to it, through the Fleet API:
    - the **Elastic Defend engine** (the `endpoint` integration, `EDRComplete`
      preset) - process lineage, memory, detections, prevention
    - the **`windows` integration** - Sysmon (`sysmon_operational`),
      PowerShell (`powershell_operational`) and Defender (`windows_defender`)
      winlog streams
  The EDR engine cannot be preconfigured in kibana.yml, so it is attached via
  `POST /api/fleet/package_policies` (the `system` package stays preconfigured)
- Installs **Sysmon 14.14** (SwiftOnSecurity sysmon-config v74) + the
  **Elastic Agent** (MSI, the official Windows install path) on every domain
  Windows machine and enrolls it in Fleet using an enrollment token
- Kibana / Fleet is served on http://{{ip_range}}.53:5601 (Kibana also acts as
  the Fleet control plane: agents enroll/check in on 5601, events go to ES on 9200)
- Run a GOAD attack and watch the alert appear in Kibana -> Security -> Alerts

This is the "full attack / defend / purple team" upgrade of the `elk` extension:
`elk` ships winlogbeat log aggregation, `elastic-edr` ships real Fleet + EDR +
Defend detection. Do not install both at the same time (both install Sysmon).

## Version pins (reproducible lab)

| component        | version   | where |
|------------------|-----------|-------|
| Elastic stack    | 8.x       | `elastic_stack/defaults` (`elastic_repo_version`) |
| Elastic agent    | 8.19.23   | `elastic_agent_win/defaults` (MSI from artifacts.elastic.co) |
| Sysmon           | 14.14     | bundled `sysmon/files/Sysmon.zip` (sha256 `878fa596b2b8f0080c716d1840c0fcf3cebb46ebabe5b169f6cb40bbf81d9aef`) |
| Sysmon config    | v74       | bundled `sysmon/files/sysmonconfig-export.xml` (latest upstream release) |
| Defend preset    | EDRComplete | `elastic_stack/defaults` (`edr_preset`) |

Sysmon is pinned to 14.x because 15.x dropped Windows Server 2016 support and
DC03 runs the `win2016-server-x64-template`.

## License / feature levels

Self managed Kibana defaults to the **Basic** license: the EDR engine, malware
detection and the built-in SIEM detection rules work out of the box. Behavior /
ransomware / memory **prevention** need a Platinum license and auto-degrade on
Basic (detection is unaffected).

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
- Sysmon config : https://github.com/SwiftOnSecurity/sysmon-config (v74)
