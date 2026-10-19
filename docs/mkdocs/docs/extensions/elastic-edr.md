# elastic-edr

- Extension name : `elastic-edr`
- Compatibility : `*`
- Providers : ludus/virtualbox/vmware/vmware_esxi/proxmox/azure/aws
- Add a machine : elastic-edr (ip_range.53, 16GB RAM / 4 cpu)

- Kibana / Fleet is configured on http://{{ip_range}}.53:5601
- Elastic Stack 8.x (Elasticsearch + Kibana + Fleet) with a **dedicated Fleet
  Server on :8220** (agent control plane), the **Elastic Defend engine** (the
  `endpoint` integration, `EDRComplete` preset) + the `windows` integration
  (Sysmon / PowerShell / Defender / AppLocker winlog)
- **Prepackaged SIEM detection rules installed and enabled** (the attack -> alert loop)
- Installs **Sysmon 14.14** + the **Elastic Agent** (MSI) on all domain windows
  machines and enrolls them in the Fleet Server

This extension is the full attack / defend / purple team upgrade of the `elk`
extension. `elk` ships winlogbeat log aggregation, `elastic-edr` ships real
Fleet + EDR + Defend detection. Do not install both at the same time (both
install Sysmon).

## What gets deployed on each agent

- The Elastic Agent (Fleet managed, enrolls on Fleet Server :8220, events to ES :9200)
- Sysmon 14.14 with the SwiftOnSecurity sysmon-config v74 (EDR event source)
- The agent policy carries : `system`, Elastic Defend (`endpoint`, EDRComplete)
  and the `windows` integration with the `sysmon_operational`, `powershell`,
  `powershell_operational`, `windows_defender`, `applocker_*` and `forwarded`
  winlog streams + windows metrics

Sysmon is pinned to 14.x because 15.x dropped Windows Server 2016 support
(DC03 runs the 2016 template).

## Architecture / ports

| port | service | used by |
|------|---------|---------|
| 5601 | Kibana (Fleet UI, Alerts, SIEM) | you (browser) |
| 8220 | Fleet Server (agent enroll + checkin, self-signed https) | windows agents |
| 9200 | Elasticsearch (agent events / data plane) | windows agents |

No new machine is added: the Fleet Server runs on the same machine as
ES + Kibana, and the Fleet management UI stays inside Kibana - only the agent
control plane moves to 8220. The windows machines need 8220 + 9200 open toward
the ELASTIC-EDR machine.

## Coexistence with other extensions

- **Windows-based extensions are covered automatically.** GOAD merges the
  inventory of every enabled extension, so hosts added by `ws01` (Win10
  workstation) or `exchange` (srv01) land in the merged `[domain]` group -
  exactly what the agents play targets (`[elastic-edr_agents:children]
  domain`). No extra configuration is needed for those machines to receive
  Sysmon + the Elastic Agent.
- **Ordering rule.** If `elastic-edr` is installed first and `ws01` /
  `exchange` (or any other extension adding Windows machines) afterwards,
  the new machines get no agent until you re-run the extension install:
  `install_extension elastic-edr` (or `provision_extension elastic-edr` on
  an already loaded instance). The re-run is fully idempotent: the Fleet
  Server, the agent policies, the detection rules and the enrollment tokens
  are all guarded (service / policy / token presence checks) and only the
  newcomers get touched.
- **Conflicts - do not co-install.** This extension conflicts with the `elk`
  and `wazuh` extensions: they provide overlapping monitoring / EDR stacks,
  and `elk` additionally installs Sysmon into the same `c:\sysmon` path. Run
  one or the other, not both.
- **Linux-based extensions are not a concern.** `guacamole`, `lx01` and any
  `[linux_domain]` member are never targeted by the agents play, which only
  covers Windows machines in `[domain]`.

## License / feature levels

Self managed Kibana defaults to the **Basic** license: the EDR engine, malware
detection and the built-in SIEM rules work out of the box. Behavior /
ransomware / memory **prevention** need Platinum and auto-degrade on Basic
(detection is unaffected).

## Credentials (this is a lab)

| user          | password        |
|---------------|-----------------|
| elastic       | changeme-elastic    |
| kibana_system | changeme-kibana     |

## prerequisites

- 16GB RAM / 4 cpu / >= 80GB free disk on the ELASTIC-EDR machine

- On ludus prepare template :
```bash
ludus templates add -d ubuntu-22.04-x64-server
ludus templates build
```

- On proxmox you need an `Ubuntu_2204_x64` template (default id 922040)

## Install

- select your instance
```
load <instance_id>
```

- install the elastic-edr extension
```
install_extension elastic-edr
```

- The first run can take a few minutes (stack install + agent enrollment)

## Usage (purple team)

- Open Kibana : http://{{ip_range}}.53:5601 (elastic / changeme-elastic)
- Management -> Fleet : you should see the windows domain machines as agents
- Run a GOAD attack (e.g. mimikatz on SRV02, kerberoast, ...)
- Look for the generated alert in Kibana -> Security -> Alerts

## Uninstall

- Not implemented yet
