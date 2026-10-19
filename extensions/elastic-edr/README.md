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
- Runs a **dedicated Fleet Server** on the same VM (https://{{ip_range}}.53:8220,
  self-signed cert) - the battle-tested lab pattern (Bad Sector Labs Elastic
  Security Lab, cisagov/LME, peasead/elastic-container). The Fleet Server agent
  is the single elastic-agent on that VM, enrolled in a preconfigured
  `Fleet-Server-Policy`; Kibana stops being the agent control plane.
- Creates the Fleet agent policy `GOAD-EDR-Policy` (preconfigured in kibana.yml)
  and attaches to it, through the Fleet API:
    - the **Elastic Defend engine** (the `endpoint` integration, `EDRComplete`
      preset) - process lineage, memory, detections, prevention
    - the **`windows` integration** - Sysmon (`sysmon_operational`),
      PowerShell (`powershell` + `powershell_operational`), Defender
      (`windows_defender`), AppLocker (4 streams), forwarded events + the
      windows metrics (perfmon / service)
- **Enables the Detection Engine and installs + enables the prepackaged SIEM
  detection rules** (enable index -> install prepackaged -> bulk-enable Windows
  rules) - otherwise the engine collects events but fires no alerts
- Installs **Sysmon 14.14** (SwiftOnSecurity sysmon-config v74) + the
  **Elastic Agent** (MSI, the official Windows install path) on every domain
  Windows machine and enrolls it in the Fleet Server using an enrollment token
- Kibana is served on http://{{ip_range}}.53:5601 (Fleet management + Alerts UI)
- Run a GOAD attack and watch the alert appear in Kibana -> Security -> Alerts

This is the "full attack / defend / purple team" upgrade of the `elk` extension:
`elk` ships winlogbeat log aggregation, `elastic-edr` ships real Fleet + EDR +
Defend detection. Do not install both at the same time (both install Sysmon).

## Architecture / ports

| port | service | used by |
|------|---------|---------|
| 5601 | Kibana (Fleet UI, Alerts, SIEM) | you (browser) |
| 8220 | Fleet Server (agent enroll + checkin, self-signed https) | windows agents |
| 9200 | Elasticsearch (agent events / data plane) | windows agents |

The windows machines need 8220 + 9200 open toward the ELASTIC-EDR machine
(5601 is only for your browser). No new VM is added: the Fleet Server runs on
the same machine as ES + Kibana, and the Fleet management UI stays inside
Kibana on 5601 - only the agent control plane moves to 8220.

## Version pins (reproducible lab)

| component                | version   | where |
|--------------------------|-----------|-------|
| Elastic stack            | 8.19.23   | `elastic_stack/defaults` (`elastic_repo_version`, exact apt suite) |
| Elastic agent (windows)  | 8.19.23   | `elastic_agent_win/defaults` (MSI) |
| Elastic agent (linux, Fleet Server) | 8.19.23 | `elastic_stack/defaults` (`elastic_agent_linux_version`, tarball) |
| Integration: system      | 2.6.3     | `elastic_stack/templates/kibana.yml` (pinned, EPR-scoped to Kibana 8.19.23) |
| Integration: windows     | 3.10.0    | `elastic_stack/templates/kibana.yml` |
| Integration: endpoint (Elastic Defend) | 8.19.3 | `elastic_stack/templates/kibana.yml` |
| Integration: fleet_server | 1.6.1    | `elastic_stack/templates/kibana.yml` |
| Sysmon                   | 14.14     | bundled `sysmon/files/Sysmon.zip` (sha256 `878fa596b2b8f0080c716d1840c0fcf3cebb46ebabe5b169f6cb40bbf81d9aef`) |
| Sysmon config            | v74       | bundled `sysmon/files/sysmonconfig-export.xml` (latest upstream release) |
| Defend preset            | EDRComplete | `elastic_stack/defaults` (`edr_preset`) |

Everything is pinned to an exact version: the stack (single-version apt suite),
both agents, the four Fleet integration packages (from the Elastic Package
Registry, scoped to the pinned Kibana), and the Sysmon binary (sha256-locked).
To upgrade, bump `elastic_repo_version`, the two agent versions and the four
package versions in `kibana.yml` together - see the comments in
`elastic_stack/defaults/main.yml`.

Sysmon is pinned to 14.x because 15.x dropped Windows Server 2016 support and
DC03 runs the `win2016-server-x64-template`.

## Coexistence with other extensions

- **Windows-based extensions are covered automatically.** GOAD merges the
  inventory of every enabled extension (`goad/provisioner/ansible/ansible.py`
  -> `run_extension`), so hosts added by `ws01` (Win10 workstation) or
  `exchange` (srv01) land in the merged `[domain]` group - exactly what
  `[elastic-edr_agents:children] domain` targets. No extra configuration is
  needed for those machines to receive Sysmon + the Elastic Agent.
- **Ordering rule.** If `elastic-edr` is installed first and `ws01` /
  `exchange` (or any other extension adding Windows machines) afterwards,
  the new machines get no agent until you re-run the extension install:
  ```
  instance_id> install_extension elastic-edr
  ```
  (or `provision_extension elastic-edr` on an already loaded instance). The
  re-run is fully idempotent: the Fleet Server, the agent policies, the
  detection rules and the enrollment tokens are all guarded (service /
  policy / token presence checks) and only the newcomers get touched.
- **Conflicts - do not co-install.** This extension conflicts with the
  `elk` and `wazuh` extensions: they provide overlapping monitoring / EDR
  stacks, and `elk` additionally installs Sysmon into the same `c:\sysmon`
  path. Run one or the other, not both.
- **Linux-based extensions are not a concern.** `guacamole`, `lx01` and any
  `[linux_domain]` member are never targeted by the agents play, which only
  covers Windows machines in `[domain]`.

## License / feature levels

Self managed Kibana defaults to the **Basic** license: the EDR engine, malware
detection, the prepackaged SIEM rules and the built-in detection rules work out
of the box (ML-based rules are skipped on Basic). Behavior / ransomware /
memory **prevention** need a Platinum license and auto-degrade on Basic
(detection is unaffected). For full prevention during a 30-day window, start a
trial in Kibana (Management -> Stack Management -> License).

## Credentials (this is a lab)

| user          | password   |
|---------------|------------|
| elastic       | changeme   |
| kibana_system | changeme   |

One lab password for both users (aligned with the `elk` extension's
stock-credential convention). Override via instance vars if needed -
`elastic_stack/defaults/main.yml` is the only place they are defined.

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
