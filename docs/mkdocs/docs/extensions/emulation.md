# emulation

- Extension name : `emulation`
- Compatibility : `*`
- Providers : ludus/virtualbox/vmware/vmware_esxi/proxmox/azure/aws
- Add a machine : emulation (ip_range.54, 8GB RAM / 2 cpu)

- MITRE **Caldera 5.3.0** adversary-emulation server (systemd service, python
  venv, deterministic `conf/local.yml`) with the **emu** (CTID Adversary
  Emulation Plans), **sandcat** (the agent) and **atomic** (ART technique
  import) plugins
- **Atomic Red Team** PowerShell framework on all domain windows machines
  (pinned `invoke-atomicredteam` + the atomics repo at a pinned commit into
  `C:\Tools\AtomicRedTeam\atomics`), with **Windows Defender path
  exclusions** scoped to the ART directories only

This extension is STANDALONE - it does not couple to `elastic-edr` (no
Fleet/Defend API integration, no exception lists) and coexists with
`elastic-edr`, `elk` or `wazuh`. With elastic-edr co-installed, ART
executions generate Defend detections and Sysmon events **by design - that
is the test data**, not an alert flood to fix.

## Port matrix (the day-one gotcha)

| port | service | direction |
|------|---------|-----------|
| 8888 | Caldera UI | your browser -> emulation VM |
| 8888 | Caldera http contact (Sandcat C2 callback) | windows hosts -> emulation VM |

The UI and the agent callback share one port (Caldera default). Sandcat is
deployed manually from the Caldera UI (v1) and checks back into the SAME
port - if an agent never checks in, verify 8888 is open from the windows
hosts toward the emulation VM (ufw is opened by the install; provider-level
ACLs - ludus, aws SG, azure NSG, proxmox firewall - are yours to allow).

## Version pins

Everything is pinned to an exact version/SHA (see the README's pinning
table): the Caldera tag -> commit + the three submodule SHAs (emu, sandcat,
atomic) are asserted on every install (a force-moved tag fails loudly), the
python venv installs the TAG's own `requirements.txt`, and ART is pinned to
an exact PSGallery version + a repository commit SHA (the atomics repo has
no releases/tags - upgrades are SHA bumps, documented in the README).

## What gets deployed where

- emulation VM (`ip_range.54`): Caldera 5.3.0 in `/opt/caldera` (dedicated
  `caldera` user, venv, systemd unit `caldera`, state in `/etc/emulation`),
  UI + Sandcat contact on `http://{{ip_range}}.54:8888`
- domain windows machines: `C:\Tools\AtomicRedTeam\atomics` (pinned commit),
  the `invoke-atomicredteam` module auto-imported from the AllUsers profile,
  Defender `ExclusionPath` entries for the ART directories (path-scoped, NOT
  an AV disable - realtime protection stays as GOAD core configured it:
  on for DC01-03/SRV03, off for SRV02)

## ART on the domain controllers - deliberate

The agents play covers all of `[domain]`, DCs included: DCs are the emulation
target (credential access, DCSync, kerberoasting - the CTID APT29/Fin6 plans
hit them hard), so an emulation lab without ART on the DCs skips the most
interesting techniques. The exclusions added are path-scoped
(`Add-MpPreference -ExclusionPath`) to the ART install/atomics directories
only - nothing else about Defender's posture changes.

## Sandcat deploy (manual, v1)

1. Browse to `http://{{ip_range}}.54:8888`, log in red/changeme
2. Plugins -> Sandcat -> deploy the `sandcat.go-windows` payload with the
   http contact `http://{{ip_range}}.54:8888` on a host
3. The agent appears in the Agents view; from there run an adversary from
   the Adversary tab (emu profiles) against it

## Install / uninstall
```
instance_id> install_extension emulation
```
Uninstall: `ansible/uninstall.yml` (per-host teardown, mirrors install.yml -
see the README's Uninstall section).
