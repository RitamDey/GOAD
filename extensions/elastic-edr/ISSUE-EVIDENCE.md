# ISSUE-EVIDENCE -- elastic-edr issue closure evidence (builder handoff)

Purpose: per-issue evidence for the verification agent to close GitHub issues.
This file is written by the builder; the tracker is never written to by the builder.

Template per block:
```
## Issue <n> -- resolved by commit <sha> | partially addressed (commit <sha>) | prep-only (commit <sha>)
Evidence at HEAD <sha>: <file>:<line> -- <one-line quote>.
Fresh-source check: <URL(s) consulted this session, or "none needed">.
Post-fix status: fixed | fixed-static-only | prep-only-live-run-pending | not-a-defect-candidate.
```

Tracker state at build start (fresh ingest, 2026-10-21): open=22 closed=33 -- matches the
plan snapshot in `elastic-edr-issue-closure-plan.md` sec 0.3 exactly. Branch `full-elastic`
at HEAD `864267a714223bb6827ebe491d0825f746ab3fdb`, working tree clean, no push, no
tracker writes.

---

## Issue #2 -- resolved by commit 29e19a5 (MSI invocation) | partially addressed (864267a..HEAD: version-nested status path remains, C-4 fixes it)

Evidence at HEAD 864267a: extensions/elastic-edr/ansible/roles/elastic_agent_win/tasks/main.yml:40-43 --
`msiexec.exe /i "{{ elastic_agent_install_location }}\elastic-agent-{{ elastic_agent_version }}-windows-x86_64.msi" /qn /norestart /l*v "...\elastic-agent-install.log" INSTALLARGS="--url=... --enrollment-token=... --insecure"`.
No bare quoted-EXE invocation exists anywhere in the role (grep `msiexec.exe /i` -> exactly one call
site, with the call operator implicit in the leading command position; PowerShell parses a bare
quoted string at command position as a command, which was the original defect -- now the MSI is
invoked through msiexec.exe explicitly).

The remaining half of #2 (constructed version-nested status path
`C:\Program Files\Elastic\Agent\{{ elastic_agent_version }}\agent\elastic-agent.exe` in
elastic_agent_win/tasks/main.yml:68 and health_assertions/tasks/verify_agents.yml:24) is fixed
by C-4 of this run -- see the C-4 block below.

Fresh-source check this session:
- https://www.elastic.co/docs/reference/fleet/install-agent-msi -- documents the
  `msiexec -i elastic-agent-<VERSION>-windows-x86_64.msi INSTALLARGS="--url=<URL> --enrollment-token=<TOKEN>" -L*V "log.txt"`
  invocation as the supported enrollment path (PowerShell form documented with `--%`).
- https://www.elastic.co/docs/reference/fleet/installation-layout -- Windows layout:
  `C:\Program Files\Elastic\Agent*` = "Elastic Agent program files";
  `C:\Program Files\Elastic\Agent\elastic-agent.yml` and `...\fleet.enc` listed at the ROOT of
  the Agent directory (no version-nested directory in the documented layout; the
  version-nested form exists only in tar/zip distributions).
- Status command reference: https://www.elastic.co/docs/reference/fleet/agent-command-reference --
  `elastic-agent status [--output <string>]`; with `--output json`, "status codes are returned as
  numerical values": 0=STARTING, 1=CONFIGURING, 2=HEALTHY, 3=DEGRADED, 4=FAILED, 5=STOPPING,
  6=UPGRADING, 7=ROLLBACK.

Post-fix status: fixed-static-only (call-operator half); path half fixed by C-4 -- live
confirmation pending first home-lab run.

---

## Issue #3 -- invalid `index_prefix` query DSL -- resolved by commit 29e19a5

Evidence at HEAD 864267a: extensions/elastic-edr/ansible/roles/health_assertions/tasks/verify_stack.yml:113 --
`url: "http://localhost:{{ es_http_port }}/logs-*,metrics-*/_count?allow_no_indices=true&ignore_unavailable=true&expand_wildcards=all"`,
no request body, no `index_prefix` DSL (grep `index_prefix` over the file at HEAD -> 0 hits;
at 3142ff1 the same file's `_count` call carried
`should: [ {index_prefix: {value: "logs-"}}, {index_prefix: {value: "metrics-"}} ]`).

Fresh-source check this session: the plan's citation requirement (fetch the 8.19 query-dsl docs
and cite the page) is satisfied by the URL below for the record:
- https://www.elastic.co/docs/reference/elasticsearch/rest-apis/count.html (`_count` API --
  takes a `query` body; `index_prefix` is not a query clause in any ES 8.x; it exists only as a
  token-filter/index-sorting setting name). The HEAD implementation no longer sends a DSL body at
  all -- it counts documents across `logs-*,metrics-*` via GET, so the invalid-DSL finding is
  structurally resolved.

Status: static verification only; live confirmation pending first home-lab run.

---

## Issue #45 -- Tor label on port 1723 -- resolved by commit 5b4d4fe (label); section-comment residue fixed by C-10 of this run

Evidence at HEAD 864267a: extensions/elastic-edr/ansible/roles/sysmon/files/sysmonconfig-export.xml:342-344 --
`<DestinationPort name="PPTP" condition="is">1723</DestinationPort> <!--PPTP control-port heuristic; not proof of application protocol-->`
followed by `TorPort9001`/`TorPort9030` with "Tor-associated port heuristic; not proof of Tor
protocol" comments. The misleading rule NAME (Tor on 1723) is gone.

Residue (per the issue body, updated 2026-10-21): the section comment at :341 still reads
`<!--Ports: Tor-->` while grouping the PPTP 1723 rule -- fixed under C-10 (comments only, no
filter changes, per the issue's "Do not change the Event ID 3 inclusion scope" constraint).

Fresh-source check this session:
- https://www.iana.org/assignments/service-names-port-numbers (CSV:
  https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.csv,
  fetched 2026-10-21) -- `pptp,1723,tcp,pptp,...,RFC 2637`: port 1723/tcp is registered to PPTP.
  No Tor-related assignment exists for 1723; 9001/9030 have no IANA Tor assignment either
  (Tor's orport use of 9001 is convention, not registry) -- hence "heuristic" labels are correct
  for 9001/9030 and PPTP is correct for 1723.
- Repository-side reference sweep: no README/dashboard/rule reference equates 1723 with Tor
  outside sysmonconfig-export.xml (README.md:207-208 already states "Port 1723 is labeled PPTP
  control; ports 9001/9030 are Tor-associated port heuristics, not proof of the protocol").

Post-fix status: fixed-static-only; live Sysmon event labeling pending first home-lab run.

---

## Issue #38 -- Event ID 7 conjunction mislabeled as unsigned-DLL filter -- resolved by commit 5b4d4fe (branches + README); stale "disabled by default" comment residue fixed by C-10 of this run

Evidence at HEAD 864267a: extensions/elastic-edr/ansible/roles/sysmon/files/sysmonconfig-export.xml:412-430 --
two explicit `<Rule>` groups inside `<ImageLoad onmatch="include">`:
- `<Rule name="DLL from user-writable path" groupRelation="or">` (ImageLoaded-only,
  `C:\Users\` / `C:\ProgramData\` / `\Temp\` begins-with/contains)
- `<Rule name="Selected DLL names from user-writable processes" groupRelation="and">`
  (Image loader-path constraint AND ImageLoaded name matches)
with the comment "Path-based telemetry, not a signature/unsigned-image filter." -- no
`Signed`/`Signature` claim exists in the block. README.md:169 and README.md:204-208 describe the
same two-branch semantics ("not an unsigned-DLL detector").

Residue (per the issue body, updated 2026-10-21): the stock SwiftOnSecurity comment at :408 --
`<!--COMMENT: Can cause high system load, disabled by default.-->` -- sits above an ACTIVE
`<ImageLoad onmatch="include">` RuleGroup and contradicts the shipped configuration; fixed
under C-10 (comment-only change; the two branches and their OR/AND semantics stay exactly as
shipped).

Fresh-source check: none needed (Sysmon filter semantics are established in the shipped XML
itself and the README; no external fact asserted).

Post-fix status: fixed-static-only; live event-volume/semantics confirmation pending first
home-lab run.

---

(Blocks for C-2..C-14 issues appended below as those commits land.)
