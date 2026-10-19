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
      (`windows_defender`), AppLocker (4 streams) and forwarded events.
      The optional Windows perfmon/service metrics input is **intentionally
      disabled by default** to keep ingestion and disk use manageable; it is
      not part of the default Fleet policy. Host resource metrics in the
      separate `system` integration are also disabled by default.
      (note: `windows.forwarded` stays EMPTY unless you stand up a WEF
      collector / Windows Event Subscription on the domain - the stream is
      kept enabled on purpose for the collect-everything philosophy; wire a
      subscription to `ForwardedEvents` and it starts filling)
- **Enables the Detection Engine and installs + enables the prepackaged SIEM
  detection rules** (enable index -> install prepackaged -> bulk-enable Windows
  rules) - otherwise the engine collects events but fires no alerts
- On every domain Windows machine:
    - **Sysmon 14.14** (tuned SwiftOnSecurity sysmon-config v74; 10/23/17-18/7/9
      enabled by the extension, see the Sysmon section) as the EDR event source
    - an **AppLocker AUDIT-ONLY policy** (`applocker` role): nothing is ever
      blocked, but Windows records Warning-class "would have been prevented"
      events (8003/8006/8021/8024) for anything executing outside the standard
      OS/application locations - the drop zones where lateral-movement tooling
      lands. Local per-host policy via `Set-AppLockerPolicy`, no GPO needed.
      The AppIDSvc service is set to automatic so the channels actually emit.
    - **host-side logging enablement** (`endpoint_logging` role) - 27 audit
      subcategories enabled (success+failure), the union of the Sigma
      logsource prerequisites and the Palantir WEF baseline:
      Security **4688/4689** process creation **with command lines**
      (unlocks 1525 process_creation Sigma rules), **4104** PowerShell
      script-block logging + **4103** module logging (unlocks 481
      powershell_operational rules), the full **Logon/Logoff + Account
      Management + Account Logon** families (4624-4648/4720-4799/4776/
      4768/4769), **4662/5136** DS access/changes (DCSync/replication
      hunting), scheduled-task events (**4696-4702**), **1102** audit-log
      cleared, PNP activity, System Integrity (code-integrity/DPAPI crypto).
      The noisy SACL-dependent families (Registry, File Share/5145,
      Privilege Use, MPSSVC, SAM, Handle Manipulation) are deliberately
      left disabled - enable them all later with
      `endpoint_logging_enable_extra: true`, or move individual names from
      `endpoint_logging_audit_subcategories_extra` up into
      `endpoint_logging_audit_subcategories` (applies on the next provision
      run, no reboot; reversible via `auditpol /set ... /disable`).
    - the **Elastic Agent** (MSI, the official Windows install path), enrolled
      in the Fleet Server using an enrollment token
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
| Elastic stack            | 8.19.23   | `elastic_stack/defaults` (`elastic_stack_version`, exact apt pin from the `8.x` suite) |
| Elastic agent (windows)  | 8.19.23   | `elastic_agent_win/defaults` (MSI) |
| Elastic agent (linux, Fleet Server) | 8.19.23 | `elastic_stack/defaults` (`elastic_agent_linux_version`, tarball) |
| Integration: system      | 2.6.3     | `elastic_stack/templates/kibana.yml` (pinned, EPR-scoped to Kibana 8.19.23) |
| Integration: windows     | 3.10.0    | `elastic_stack/templates/kibana.yml` |
| Integration: endpoint (Elastic Defend) | 8.19.3 | `elastic_stack/templates/kibana.yml` |
| Integration: fleet_server | 1.6.1    | `elastic_stack/templates/kibana.yml` |
| Sysmon                   | 14.14     | bundled `sysmon/files/Sysmon.zip` (sha256 `878fa596b2b8f0080c716d1840c0fcf3cebb46ebabe5b169f6cb40bbf81d9aef`) |
| Sysmon config            | v74       | bundled `sysmon/files/sysmonconfig-export.xml` (latest upstream release) |
| Defend preset            | EDRComplete | `elastic_stack/defaults` (`edr_preset`) |

Everything is pinned to an exact version: the stack (exact apt pin installed
from the rolling `8.x` suite - only `8.x` exists as an apt suite, per-patch
suites are 404), both agents, the four Fleet integration packages (from the
Elastic Package Registry, scoped to the pinned Kibana), and the Sysmon binary
(sha256-locked).
To upgrade, bump `elastic_stack_version` (NOT the apt suite - `elastic_repo_version`
stays `8.x`), the two agent versions and the four
package versions in `kibana.yml` together - see the comments in
`elastic_stack/defaults/main.yml`.

Sysmon is pinned to 14.x because 15.x dropped Windows Server 2016 support and
DC03 runs the `win2016-server-x64-template`.

### Sysmon config tuning (detection engineering)

Sysmon only logs the event types its XML config tells it to log. This
extension ships a **tuned SwiftOnSecurity sysmon-config v74**
(`ansible/roles/sysmon/files/sysmonconfig-export.xml`), copied to
`c:\sysmon\sysmonconfig-export.xml` on every agent. Compared to stock v74,
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

## Two hunting postures (prepackaged rules)

The prepackaged detection rules are **installed** on first deploy either way -
the switch is whether they are **enabled**:

| Posture | `prepackaged_rules_enabled` | Alerts view |
|---|---|---|
| **Out-of-the-box SIEM** (default) | `true` | 700+ Elastic + community detections live - attack, watch what the vendor catches |
| **Solo hunting** | `false` | Empty - hunt raw telemetry in Discover, build your own alert rules, every alert is yours |

Switch posture by flipping the flag (in `elastic_stack/defaults/main.yml`) and
re-running `provision_extension elastic-edr`:
- enabled -> solo: bulk-disables all prepackaged rules
- solo -> enabled: bulk-enables all prepackaged rules (e.g. after building
  your own rules, turn the vendor rules on and re-attack to compare)

Scope of the bulk actions: they match `alert.attributes.params.immutable: true`
- exactly the prepackaged (Elastic-managed) rule corpus, every platform. On
first-run enable that means the WHOLE corpus ships enabled, not just
Windows-relevant rules: Linux/macOS/cloud/ML-class rules come up too (ML rules
auto-skip on the Basic license). They sit enabled-but-dormant on this
Windows-only lab - harmless, and symmetric with the disable path, which also
sweeps the whole corpus. Prune them in the UI if you want a shorter rules list.

The default Fleet policy does not collect Windows perfmon/service metrics or
system resource metrics. Prepackaged rules that query those metric streams can
therefore remain enabled without matching data in this lab until the relevant
metrics inputs are deliberately enabled and validated. The presence of an
enabled rule does not mean its data source is configured or its coverage has
been tested.

Between provisions your per-rule enable/disable toggles from the Kibana UI
(Security -> Rules) are preserved for UNCHANGED-flag re-runs - the posture
change only runs when the flag itself changes vs the stored state, and it
only ever touches prepackaged rules (your hand-authored rules are never
enabled/disabled by a flip). You can also toggle rules per-rule in the
UI at any time without touching the extension. Deleting the state file
(`{{ state_dir }}/prepackaged-rules-state` on the ELASTIC-EDR machine)
re-applies the configured posture on the next run.

## What GOAD core does to your specimen (read before writing detections)

This is an observation lab: the hosts you attack are also hosts GOAD core has
hardened. Know what was done to the specimen, or you will misattribute
telemetry gaps to your rules:

- **Defender realtime is OFF only on SRV02.** Core's `ansible/security.yml`
  runs `settings/windows_defender` per group: `[defender_on]` (DC01, DC02,
  DC03, SRV03) keep realtime protection ON; `[defender_off]` (SRV02) gets
  `Set-MpPreference -DisableRealtimeMonitoring $true`. So the
  `windows.windows_defender` stream watches a hobbled engine on SRV02 and a
  live one elsewhere - SRV02 is the EDR-only comparison host by design.
- **ASR (Attack Surface Reduction) rules are enforced core-wide**
  (`ansible/roles/security/asr`). Some tradecraft will be silently blocked or
  deformed by ASR before your detection ever sees it - a "no alert" may be an
  ASR kill, not a rule gap.
- **RunAsPPL=1 is set core-wide** (`ansible/roles/security/enable_run_as_ppl`).
  LSASS runs as protected process light: Sysmon Event 10 OpenProcess access
  masks against lsass (and the EDR's credential-access events) are shaped by
  which handles PPL grants - expect truncated access masks rather than
  full-handle reads from vanilla mimikatz-class tools.

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

## Data retention (ILM)

The lab ingests several GB/day (Sysmon 10/17/18/23/7/9 + full winlog +
4688-with-cmdline + 4103 + Defend from 5-7 hosts) onto an 80GB single node.
Without expiry, Elasticsearch hits its flood watermark within weeks and turns
the cluster READ-ONLY - the lab dies mid-hunt with a cryptic error. The
install ships a minimal ILM policy (`goad-edr-logs`, delete phase) bound to
`logs-*` and `metrics-*` via an index template.

- Default window: **60 days** (`elastic_ilm_retention_days` in
  `elastic_stack/defaults/main.yml`)
- Disk math for the default: at ~1GB/day you hold ~60GB of indices - tight on
  80GB with the stack itself. Measure real growth after a few days
  (`GET _cat/indices?v&s=store.size:desc`) and tighten to 30-45d if needed.
- Change `elastic_ilm_retention_days` and re-provision: both PUTs are
  idempotent and re-apply the policy.

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

Per-host teardown of everything the extension puts ON THE ENDPOINTS plus the
extension state - `ansible/uninstall.yml` (2 plays, mirrors install.yml):

```
ansible-playbook -i <inventory> extensions/elastic-edr/ansible/uninstall.yml
```

Removes: the Elastic Agent (MSI uninstall), Sysmon (service + `c:\sysmon`),
the AppLocker policy (restored to a default allow-everyone policy, AppIDSvc
back to Manual), all 27+9 audit subcategories (disabled again), the 5
PowerShell/4688 registry values, the `C:\elastic-agent` / `c:\applocker`
directories, and `/etc/elastic-edr` on the ELASTIC-EDR machine.

Kept on purpose: the elasticsearch/kibana packages, the apt repo, the
detection rules and all event indices (they hold your detection work). Full
stack purge commands are in the `uninstall.yml` header.

## credits
- Based on the structure of the `elk` and `wazuh` extensions
- Elastic Fleet / EDR : https://www.elastic.co/guide/en/fleet/current/index.html
- Sysmon config : https://github.com/SwiftOnSecurity/sysmon-config (v74)
