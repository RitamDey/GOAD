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
    - an **AppLocker AUDIT-ONLY policy** (`applocker` role): execution is not
      blocked. The baseline path rules audit nonstandard EXE/script launches
      for all users, including administrators, and MSI installers staged outside
      the Windows Installer cache. The four AppLocker Event Log channels are
      enabled and sent to Elastic's four `windows.applocker_*` data streams.
      Optional DLL-load auditing is available but disabled by default because
      it checks every DLL and can increase event volume.
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
      **Important:** auditpol enables DS Access/Changes subcategories but does
      not configure directory-object SACLs. On DCs the role performs a read-only
      naming-context-root SACL check; it does not rewrite directory security
      descriptors. See the AD DS SACL prerequisite section below for 4662/5136.
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

### AppLocker audit coverage and event collection

The extension applies a local AppLocker policy with every configured collection
in `AuditOnly`; this is telemetry, not an application-control allow-list. No
execution is blocked by this policy. EXE/script rules allow the Windows and
Program Files paths for Everyone, but there is deliberately no catch-all
Administrators allow rule: tools launched by local/domain administrators from
user-writable or other nonstandard locations can generate audit warnings too.
MSI rules allow the Windows Installer cache path only, so signed installers
staged in Downloads/temp are visible as candidates. Signed packaged apps retain
the publisher allow rule.

The optional DLL collection is off by default. Enable it with
`applocker_enable_dll_collection: true` in inventory/instance variables and
re-provision to audit DLLs/OCXs outside the Windows and Program Files paths,
including DLLs loaded by administrator-run processes. AppLocker evaluates each
DLL loaded by applications; Microsoft's guidance warns that this can increase
evaluation overhead, and the EXE/DLL event log can be very verbose. Keep this
setting opt-in unless the lab has enough CPU and ingestion/disk headroom. Any
enabled DLL collection is checked to ensure it remains `AuditOnly`.

The role preserves the original enablement state of these four event channels,
enables them for collection, and restores their previous state on uninstall:

| AppLocker event channel | Elastic Windows data stream | Example audit warning |
|---|---|---|
| EXE and DLL | `windows.applocker_exe_and_dll` | 8003 — EXE/DLL candidate |
| MSI and Script | `windows.applocker_msi_and_script` | 8006 — MSI/script candidate |
| Packaged app-Execution | `windows.applocker_packaged_app_execution` | 8021 — package execution candidate |
| Packaged app-Deployment | `windows.applocker_packaged_app_deployment` | 8024 — package deployment candidate |

The per-host endpoint roll-up reports channel readiness and verifies that the
effective base collections are audit-only. An enabled channel proves local log
readiness, not that a generated event has reached Elasticsearch; verify ingestion
during a live lab run before closing telemetry acceptance work.

### Sysmon config tuning (detection engineering)

Sysmon only logs the event types its XML config tells it to log. This
extension ships a **tuned SwiftOnSecurity sysmon-config v74**
(`ansible/roles/sysmon/files/sysmonconfig-export.xml`), rendered for the selected
profile and applied to every endpoint. It enables selected high-value events
while documenting where filters intentionally limit coverage:

| Sysmon event | stock v74 | shipped by this extension | what it gives you |
|---|---|---|---|
| 10 ProcessAccess | off | **on** - scoped to lsass/winlogon/MsMpEng targets, dump-tool sources and dump-capability access masks | credential-dump hunting (mimikatz-class) |
| 23 FileDelete | commented out | **on** - user paths, ProgramData, shadow copies, .temp | ransomware / dropper-cleanup tells |
| 17/18 PipeEvent | off | **on** - suspicious pipes (psexec/paexec/remcom/csexec classes, lsass, status_*) | named-pipe C2 detection |
| 7 ImageLoad | off | **on** - writable-path DLL loads + selected DLL names under writable process paths | suspicious image-load telemetry (not an unsigned-DLL detector) |
| 9 RawAccessRead | off | **on** - device path reads | raw-disk access (ACL bypass) |
| 25 ProcessTampering | commented out | **on** - collect all ProcessTampering events without local exclusions | process hollowing / image tampering telemetry |

Other stock-v74 events kept as-is include 1 (process), 2 (file time), 4 (Sysmon
service status, unfilterable), 5 (terminate), 6 (driver), 8 (remote thread),
11 (file create), 12/13/14 (registry), 15 (ADS), 16, 19 (WMI) and 22 (DNS).
Events 3 and 22 are enabled in the default profile, but neither provides complete
network-connection or DNS-query coverage.

Event ID 25 (ProcessTampering) is enabled by this extension with an empty
`onmatch="include"` filter, which collects all ProcessTampering events. The
event itself is focused on process-image tampering behavior, so the default
does not apply an unvalidated image exclusion such as the commented SwiftOnSecurity
Edge example. This favors coverage in a threat-research lab. Add a narrow
exclusion only if a supported workload demonstrates a benign match and the
exclusion has been validated against the pinned Sysmon binary.

**Event ID 3 — network connections:** `sysmon_network_telemetry: high_signal`
is the default intersection filter. An included event must match a configured
process image/path **and** a configured destination port; alternatives within
one field are ORed, different fields are combined, and excludes suppress
matching events. This can miss a listed process using ordinary HTTPS/443 or a
normal process connecting to a listed port. For infrastructure hunts, set
`sysmon_network_telemetry: broad` in inventory/instance variables and
re-provision. Broad mode removes the process/port filter and logs all Event ID 3
connections; expect higher volume.

**Event ID 22 — DNS:** `sysmon_dns_telemetry: filtered` keeps the inherited
Microsoft/platform, third-party, CDN and advertising-domain exclusions.
`sysmon_dns_telemetry: broad` removes that long domain-exclusion list while
retaining preceding local/reverse-DNS/noise exclusions. This helps surface
tenant-specific or attacker-controlled names under otherwise excluded service
suffixes. Filtering occurs on the endpoint: excluded events cannot be recovered
later. Measure volume and disk growth before leaving broad profiles enabled.

**Event ID 7 — image loads:** path-based telemetry, not an unsigned-DLL test.
It captures DLL loads from user-writable paths regardless of loader path, plus
selected DLL-name matches when the loader is under Users/ProgramData. Port 1723
is labeled PPTP control; ports 9001/9030 are Tor-associated port heuristics, not
proof of the protocol.

The selected rendered configuration is installed with `-i` on fresh hosts;
on existing Sysmon installations, the role applies `-c` whenever the rendered
configuration changes. Set profile overrides and re-provision `elastic-edr`.


### AD DS SACL prerequisite (Events 4662 and 5136)

The role enables the Directory Service Access and Directory Service Changes
audit subcategories, but auditpol alone does not guarantee the expected
directory events. Event 4662 for replication-control-access hunting depends on
appropriate success-audit ACEs for the relevant replication rights at the
domain naming-context root. Event 5136 requires an appropriate SACL on the
changed directory object or an ancestor whose audit ACE is inherited by it.

During provisioning, the endpoint logging role performs a read-only indicator
check on domain controllers and reports whether it detects replication-right
auditing and inheritable WriteProperty auditing on the naming-context root.
This is not an exhaustive proof for every object: some GOAD variants or
exercises may place SACLs on specific objects/OUs instead. The role does not
add, replace, or reset AD security descriptors automatically. Review effective
SACLs for the exact objects used by your exercise, add only the required
success-audit ACEs where missing, and preserve existing DACL/SACL entries. If
the check cannot read the descriptor, treat the result as unknown and inspect
it manually rather than assuming coverage.

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
Fleet-managed log and metric data streams through the `logs@custom` and
`metrics@custom` component-template hooks. It avoids a competing generic
index template, preserves existing custom-template content, and applies the
setting to already-created streams as well as future backing indices.

- Default window: **60 days** (`elastic_ilm_retention_days` in
  `elastic_stack/defaults/main.yml`)
- Disk math for the default: at ~1GB/day you hold ~60GB of indices - tight on
  80GB with the stack itself. Measure real growth after a few days
  (`GET _cat/indices?v&s=store.size:desc`) and tighten to 30-45d if needed.
- Change `elastic_ilm_retention_days` and re-provision to update the policy.
  The role also updates the Fleet custom component-template hooks and applies
  the policy to existing data streams/backing indices. The default of 60 days
  remains a sizing estimate, not a measured recommendation; record real
  store-size and filesystem growth before deciding whether to tighten it.

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
the AppLocker policy (reset to a benign default, AppIDSvc back to Manual, and
original AppLocker event-channel enablement restored), all 27+9 audit
subcategories (disabled again), the 5
PowerShell/4688 registry values, the `C:\elastic-agent` / `c:\applocker`
directories, and `/etc/elastic-edr` on the ELASTIC-EDR machine.

Kept on purpose: the elasticsearch/kibana packages, the apt repo, the
detection rules and all event indices (they hold your detection work). Full
stack purge commands are in the `uninstall.yml` header.

## credits
- Based on the structure of the `elk` and `wazuh` extensions
- Elastic Fleet / EDR : https://www.elastic.co/guide/en/fleet/current/index.html
- Sysmon config : https://github.com/SwiftOnSecurity/sysmon-config (v74)
