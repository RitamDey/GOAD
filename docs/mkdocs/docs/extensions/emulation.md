# emulation

- Extension name : `emulation`
- Compatibility : `*`
- Providers : ludus/virtualbox/vmware/vmware_esxi/proxmox/azure/aws
- Add a machine : emulation (ip_range.54, 8GB RAM / 2 cpu)

- MITRE **Caldera 5.3.0** adversary-emulation server (systemd service, python
  venv, deterministic `conf/local.yml` = the release's `conf/default.yml` +
  lab overrides) with the **emu** (CTID Adversary Emulation Plans),
  **sandcat** (the agent) and **atomic** (ART technique import) plugins, and
  the v5 Vue UI built once at install time (pinned Node.js 22.23.5)
- **Atomic Red Team** PowerShell framework on all domain windows machines
  (pinned `invoke-atomicredteam` + the atomics repo at a pinned commit into
  `C:\Tools\AtomicRedTeam\atomics`; the AllUsers profile points
  `Invoke-AtomicTest` at its `atomics` subfolder), with **Windows Defender
  path exclusions** scoped to the ART and sandcat directories only
- A live **Sandcat agent** on every domain windows machine (boot scheduled
  task, started at install) that checks in to the Caldera server

The emu and atomic plugin content (adversary-emulation-plans,
atomic-red-team) is pre-cloned at pinned SHAs before the first start, so the
whole lab is reproducible (not just the Caldera code). The first start
populates/decrypts that content, so
the UI can take a few minutes to come up (the install waits up to 10 min).
The emu plugin's non-redistributable payloads are fetched best-effort after
the server is up (`caldera_fetch_emu_payloads`, see the extension README).

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

The UI and the agent callback share one port (Caldera default). The Sandcat
agent is deployed automatically on every windows host and checks back into
this SAME port - if an agent never checks in, verify 8888 is open from the
windows hosts toward the emulation VM (ufw is opened by the install;
provider-level ACLs - ludus, aws SG, azure NSG, proxmox firewall - are yours
to allow).

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
  a Sandcat agent in `C:\Tools\Sandcat` running as the `GOAD-Sandcat` boot
  scheduled task (checks in to the Caldera server as a `red`-group agent),
  and Defender `ExclusionPath` entries for the ART and sandcat directories
  (path-scoped, NOT an AV disable - realtime protection stays as GOAD core
  configured it: on for DC01-03/SRV03, off for SRV02)

## ART on the domain controllers - deliberate

The agents play covers all of `[domain]`, DCs included: DCs are the emulation
target (credential access, DCSync, kerberoasting - the CTID APT29/Fin6 plans
hit them hard), so an emulation lab without ART on the DCs skips the most
interesting techniques. The exclusions added are path-scoped
(`Add-MpPreference -ExclusionPath`) to the ART install/atomics directories
only - nothing else about Defender's posture changes.

## Sandcat agent (deployed automatically)

The extension deploys the `sandcat.go-windows` agent on every domain windows
host (downloaded from the Caldera server, run as the `GOAD-Sandcat` SYSTEM
boot scheduled task, started during provisioning), so agents are already
checked in when the install finishes. To drive one:

1. Browse to `http://{{ip_range}}.54:8888`, log in red/changeme
2. Agents view - the hosts appear as `red`-group agents (paw = hostname)
3. Run an adversary from the Adversary tab (emu profiles) against them

The install's sandcat health check reports how many hosts have checked in
and names any that have not (usually a firewall on 8888, or a slow first
beacon - re-run `install_extension emulation`).

## Install / uninstall
```
instance_id> install_extension emulation
```
Uninstall: `ansible/uninstall.yml` (2 plays, mirrors install.yml; the goad
CLI has no uninstall command on main, the playbook is the supported
teardown). Run it with the same inventories the install uses:
```
cd extensions/emulation/ansible
ansible-playbook \
  -i ../../../ad/<lab>/data/inventory \
  -i ../../../workspace/<instance_id>/inventory \
  -i ../../../workspace/<instance_id>/emulation_inventory \
  -i ../../../globalsettings.ini \
  uninstall.yml
```
It removes, on the agents: the ART dirs + module + profile lines, the Sandcat
agent (`GOAD-Sandcat` scheduled task, the running process and `C:\Tools\Sandcat`),
and the ART + sandcat Defender exclusions; and on the emulation VM: the caldera
service + `/opt/caldera` + the Node.js build toolchain + `/etc/emulation` + the
ufw rule. Kept on purpose: git, powershell-yaml, every other Defender setting,
the VM itself. Caldera operation reports (`/opt/caldera/data`) are printed as a
copy-me reminder before deletion.
