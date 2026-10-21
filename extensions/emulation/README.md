# EMULATION extension

- Extension Name: emulation
- Description: Add a MITRE Caldera 5.x adversary-emulation server (with the
  emu, sandcat and atomic plugins) plus the Atomic Red Team framework on all
  the domain Windows machines.
- Machine name : {{lab_name}}-EMULATION
- Compatible with labs : *
- Providers : ludus / virtualbox / vmware / vmware_esxi / proxmox / azure / aws

## What it does

- Deploys **MITRE Caldera 5.3.0** on one linux machine (8GB RAM / 2 cpu) as a
  systemd service, in a python venv, with a fully deterministic `conf/local.yml`
- The Caldera install carries the plugins this extension exists for:
    - **emu** - the CTID Adversary Emulation Plans (APT29, Fin6, ... profiles)
    - **sandcat** - the Caldera agent (prebuilt `sandcat.go-windows` ships in
      the pinned submodule; deploy it manually from the Caldera UI)
    - **atomic** - import/plan Atomic Red Team techniques inside Caldera
- On every domain Windows machine (commit 2):
    - the **Atomic Red Team** PowerShell framework (`invoke-atomicredteam`,
      pinned to an exact PSGallery version) with the atomics repository
      cloned at a pinned commit into `C:\Tools\AtomicRedTeam\atomics`
    - **Windows Defender path exclusions** (Add-MpPreference) for the ART
      directories ONLY - path-scoped so payloads/atomics are not quarantined
      on the `[defender_on]` hosts (DC01-03, SRV03); SRV02 (realtime off)
      is unaffected either way
- Run an adversary emulation from the Caldera UI (or fire TXXXX atomics
  manually with invoke-atomicredteam) and watch the technique fire

This extension is STANDALONE: no coupling to `elastic-edr` (no Fleet/Defend
API integration, no exception-list writes). It coexists happily with
`elastic-edr`, `elk` or `wazuh` - see Coexistence.

## Architecture / ports

| port | service | used by |
|------|---------|---------|
| 8888 | Caldera UI | you (browser) |
| 8888 | Caldera http contact (Sandcat C2 callback) | windows hosts |

One port serves both (Caldera's `conf/default.yml` ships the UI port and the
http contact on the same 8888). **This is the day-one gotcha:** the windows
machines must be able to reach the EMULATION machine on 8888 or Sandcat can
never check in - deploy sandcat from the UI and the first thing to check on
a "stuck" agent is host/provider firewall on that path. The install opens
8888 in ufw when ufw is active; if your provider adds ACLs (ludus, aws
security groups, azure NSG, proxmox firewall), make sure 8888 toward the
emulation VM is allowed.

## Version pins (reproducible lab)

| component | version | where |
|-----------|---------|-------|
| Caldera | 5.3.0 (tag -> commit `b24f6e7a99cab19cbf417009bda9b9c6c81abc31`) | `caldera_server/defaults` (`caldera_version`, `caldera_commit_sha`) |
| emu plugin (submodule) | `fdb0bab5c9c3e1f6fcff57cdd2a4d999955cb7b8` | `caldera_server/defaults` (`caldera_submodule_shas`) |
| sandcat plugin (submodule) | `0a35cd525f1cfabfcf602282428055c41f144513` (agent 2.9.0-0723cab) | `caldera_server/defaults` |
| atomic plugin (submodule) | `b90958810ffae1d328124f9e8af75f524616b27f` | `caldera_server/defaults` |
| python | 3.10 (ubuntu-22.04 default; Caldera 5.3.0 supports 3.9+) | `caldera_server/defaults` (`caldera_python_bin`) |
| pyminizip (emu dep) | 0.2.6 | `caldera_server/tasks` |
| invoke-atomicredteam | 2.3.0 | `atomic_redteam/defaults` (commit 2) |
| atomic-red-team atomics | commit SHA `388942adbd9641f4dfdcf079d7efe9a75ec0ac43` (2026-09-05) | `atomic_redteam/defaults` (commit 2) |

Every pin is verified live at build time (GitHub releases API / PSGallery
API) and re-asserted on install: the clone is checked out at the tag AND the
checked-out commit must match `caldera_commit_sha` (a force-moved tag fails
loudly), and the three submodule SHAs are asserted after the recursive clone.

### Upgrading

- **Caldera**: bump `caldera_version` + `caldera_commit_sha` (+ submodule
  SHAs - check the release notes for submodule pointer moves), re-run the
  install. The role re-clones with `force: yes` and re-asserts everything.
- **ART**: there is no semver to lean on - `redcanaryco/atomic-red-team`
  has **zero releases and zero tags** (curl-verified on the GitHub API:
  both endpoints return empty arrays). Upgrades are **commit-SHA bumps**:
  take the new master SHA, note the date in the pinning table, bump
  `atomic_redteam_defaults` and re-run. Check the commit log for behavior
  changes in the atoms you use before bumping.

## Coexistence with other extensions

- **Standalone by design.** No elastic-edr API coupling, no Defend exception
  lists, no writes into other extensions' config. The only endpoint changes
  are the ART install + the Defender path exclusions.
- **The install playbook targets `[emulation_agents:children] domain`** -
  the merged-inventory mechanism (`goad/provisioner/ansible/ansible.py` ->
  `run_extension`) resolves the same hosts whether or not any other
  extension is enabled.
- **With elastic-edr co-installed, ART executions WILL generate Defend
  detections and Sysmon events - that is the data, not an alert flood to
  fix.** The pairing (ART attacks -> elastic-edr detects) is the entire
  point of running both; the extension deliberately does NOT touch Defend
  exception lists so the detections stay honest.
- **ART on domain controllers is deliberate.** The agents play covers all of
  `[domain]`, i.e. DC01-03 too - DCs are the emulation target (credential
  access, DCSync, enumeration), so an emulation lab without ART on the DCs
  would skip the most interesting techniques. The Defender exclusions are
  `Add-MpPreference -ExclusionPath` scoped to the ART directories only -
  they do NOT disable Defender or realtime protection anywhere.
- **Ordering rule.** If `ws01` / `exchange` (or any extension adding Windows
  machines) is installed after `emulation`, the newcomers get no ART until
  you re-run the install (`install_extension emulation` /
  `provision_extension emulation`). The re-run is idempotent.
- **Sandcat is a second agent on the hosts** - it coexists with the Elastic
  Agent / wazuh agent / sysmon; nothing is uninstalled or reconfigured.

## Credentials (this is a lab)

| user | password |
|------|----------|
| red (UI) | changeme |
| blue (UI) | changeme |
| red API key | ADMIN123 |
| blue API key | BLUEADMIN123 |

Caldera UI / Sandcat contact : http://{{ip_range}}.54:8888

Override in `caldera_server/defaults/main.yml` (the values are written into
the VM's `conf/local.yml` at install).

## prerequisites

- 8GB RAM / 2 cpu / >= 20GB free disk on the EMULATION machine (already set
  in every provider file)
- On ludus prepare template :
```
ludus templates add -d ubuntu-22.04-x64-server
ludus templates build
```
- On proxmox you need an `Ubuntu_2204_x64` template (default id 922040)

## Install
```
instance_id> install_extension emulation
```

## Uninstall

Per-host teardown of everything the extension puts ON THE ENDPOINTS plus the
server - `ansible/uninstall.yml` (2 plays, mirrors install.yml):

```
ansible-playbook -i <workspace>/<instance>/emulation_inventory \
  extensions/emulation/ansible/uninstall.yml
```

(The goad CLI on main has no `uninstall_extension` command - `goad.py` only
calls `run_extension` with `install=True` - so the playbook IS the supported
teardown path. `disable_extension emulation` drops it from the instance's
enabled list.)

Removes: on the agents, `C:\Tools\AtomicRedTeam` (atomics + installers), the
`invoke-atomicredteam` module at the pinned version (`Uninstall-Module
-AllUsers`), the AllUsers profile import line, and the two Windows Defender
`ExclusionPath` entries (`Remove-MpPreference`, ONLY the ART paths). On the
emulation VM, the caldera systemd unit + service, `/opt/caldera`, the
`/etc/emulation` state dir, the ufw 8888 rule (ufw-active hosts only), and
the `caldera` service user.

Kept on purpose: git itself (a system tool), every other Defender setting
(realtime/ASR/PPL stay exactly as GOAD core configured them), and the
emulation VM machine itself (destroy it through goad/the provider when you
want the host gone). Caldera operation reports live in `/opt/caldera/data`
- the playbook prints a reminder before removing it; copy the folder out
first if you need the history.

## credits
- Based on the structure of the `elastic-edr` extension (providers layout,
  health_assertions pattern, pinning convention)
- MITRE Caldera : https://github.com/mitre/caldera
- CTID Adversary Emulation Library : https://github.com/center-for-threat-informed-defense/adversary_emulation_library
- Atomic Red Team : https://github.com/redcanaryco/atomic-red-team
- invoke-atomicredteam : https://www.powershellgallery.com/packages/invoke-atomicredteam
