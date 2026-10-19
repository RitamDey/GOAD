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
- Sysmon 14.14 with a **tuned SwiftOnSecurity sysmon-config v74** (EDR event
  source; 10/23/17-18/7/9 enabled by the extension, see the Sysmon section)
- An **AppLocker audit-only policy**: nothing blocked, but Warning-class
  "would have been prevented" events (8003/8006/8021/8024) for anything
  executing outside standard locations - local per-host policy, no GPO
- **Host-side logging enablement**: 27 audit subcategories (the Sigma
  logsource prerequisites + the Palantir WEF baseline) - 4688/4689 process
  creation with command lines, 4104 script-block + 4103 module logging,
  the full Logon/Logoff, Account Management and Account Logon families
  (4624-4648/4720-4799/4776/4768/4769), 4662/5136 DS access/changes,
  scheduled-task events 4696-4702, 1102 audit-log cleared, PNP activity,
  System Integrity. Noisy SACL-dependent families (Registry, File Share,
  Privilege Use, MPSSVC, SAM) stay disabled by default - enable them all
  later with `endpoint_logging_enable_extra: true`, or move individual
  names from `endpoint_logging_audit_subcategories_extra` up into
  `endpoint_logging_audit_subcategories` (applies on the next provision
  run, no reboot; reversible via `auditpol /set ... /disable`)
- The agent policy carries : `system`, Elastic Defend (`endpoint`, EDRComplete)
  and the `windows` integration with the `sysmon_operational`, `powershell`,
  `powershell_operational`, `windows_defender`, `applocker_*` and `forwarded`
  winlog streams (host resource metrics are intentionally disabled)

Sysmon is pinned to 14.x because 15.x dropped Windows Server 2016 support
(DC03 runs the 2016 template).

### Sysmon config tuning (detection engineering)

Sysmon only logs the event types its XML config tells it to log. This
extension ships a **tuned SwiftOnSecurity sysmon-config v74**
(`ansible/roles/sysmon/files/sysmonconfig-export.xml` in the extension), copied
to `c:\sysmon\sysmonconfig-export.xml` on every agent. Compared to stock v74,
this extension **enables the event types most community detections rely on**:

| Sysmon event | stock v74 | shipped by this extension | what it gives you |
|---|---|---|---|
| 10 ProcessAccess | off | **on** - scoped to lsass/winlogon/MsMpEng targets, dump-tool sources and dump-capability access masks | credential-dump hunting (mimikatz-class) |
| 23 FileDelete | commented out | **on** - user paths, ProgramData, shadow copies, .temp | ransomware / dropper-cleanup tells |
| 17/18 PipeEvent | off | **on** - suspicious pipes (psexec/paexec/remcom/csexec classes, lsass, status_*) | named-pipe C2 detection |
| 7 ImageLoad | off | **on** - loads from user paths/ProgramData/Temp + credential-DLLs | DLL-sideloading telemetry |
| 9 RawAccessRead | off | **on** - device path reads | raw-disk access (ACL bypass) |

Already on in stock v74 (kept as-is): 1 (process), 2 (file time), 3 (network),
5 (terminate), 6 (driver), 8 (remote thread), 11 (file create),
12/13/14 (registry), 15 (ADS), 16, 19 (WMI), 22 (DNS), 25 (tampering).

The scoping in each section keeps volume manageable (stock v74's warning about
event 10 applies only if you open it up to all targets). To tune further, edit
the XML in the repo and reload on hosts with
`sysmon64.exe -c c:\sysmon\sysmonconfig-export.xml` (the install role only
runs the initial `-i` on first install).

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

| user          | password   |
|---------------|------------|
| elastic       | changeme   |
| kibana_system | changeme   |

One lab password for both users (aligned with the `elk` extension's
stock-credential convention). Override via instance vars if needed -
`elastic_stack/defaults/main.yml` is the only place they are defined.

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

- Open Kibana : http://{{ip_range}}.53:5601 (elastic / changeme)
- Management -> Fleet : you should see the windows domain machines as agents
- Run a GOAD attack (e.g. mimikatz on SRV02, kerberoast, ...)
- Look for the generated alert in Kibana -> Security -> Alerts

## Uninstall

- Not implemented yet
