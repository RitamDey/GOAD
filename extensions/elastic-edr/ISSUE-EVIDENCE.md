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

## Issue #3 -- invalid `index_prefix` query DSL -- [label half; SUPERSEDED by the canonical #3 block below for the PASS 2 retry-logic work] resolved by commit 29e19a5

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

## Issue #45 -- Tor label on port 1723 -- [SUPERSEDED by the canonical #45 block below (commit 69547fe); kept for the review trail] label resolved by commit 5b4d4fe; section-comment residue fixed by C-10 of this run

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

## Issue #38 -- Event ID 7 conjunction mislabeled -- [SUPERSEDED by the canonical #38 block below] branches resolved by commit 5b4d4fe (branches + README); stale "disabled by default" comment residue fixed by C-10 of this run

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

---

## Issue #28 -- prep-only (commit lands with C-11)

Restructured to the documented self-enrollment form: --url=https://localhost:{{ fleet_server_port }}
+ --insecure (the agent auto-generates a self-signed cert when no
--fleet-server-cert* flags are given; per the 8.19 command reference,
enrolling into a self-signed-cert Fleet Server requires --insecure).
Added failed_when on the install rc + a log-tail diagnostic task because the
install command is no_log'd (#33) - failures previously surfaced nothing.
Live confirmation of BOTH forms (old --url=http://localhost:5601 vs new
--url=https://localhost:8220 + --insecure) still pending home-lab run.

Fresh-source check: https://www.elastic.co/guide/en/fleet/8.19/elastic-agent-cmd-options.html
("Fleet Server URL to use to enroll the Elastic Agent into Fleet"; documented
setup example passes --url=https://fleet-server:8220; self-signed + --insecure
rule quoted in the task comment).

Post-fix status: prep-only-live-run-pending.
---

## Issue #16 -- partially addressed (C-12 commit) - identity split, live confirmation pending

[BOOKKEEPING NOTE (PASS 2): this early block duplicated the canonical #16 block
below (commit 756da82) and carried a wrong count (~10). The CANONICAL count is
9 write-sites switched. This block is superseded by the 756da82 block below --
kept for the review trail only.]

Docs outcome B (docs silent/ambiguous on kibana_system holding ALL Fleet feature
privileges): 9 bootstrap/WRITE Fleet call sites now authenticate as the
`elastic` superuser; the 8 remaining READ-ONLY call sites (status wait, epm
version GETs, package_policies listings, enrollment-token LISTs,
fleet_server_hosts GET) stay on `kibana_system`. The split + rationale is
documented in elastic_stack/defaults/main.yml (identity/which-class block).

Fresh-source check (fetched 2026-10-21):
- elasticsearch v8.19.23 KibanaOwnedReservedRoleDescriptors.kibanaSystem():
  ManageApplicationPrivileges limited to "kibana-*" apps; fleet-related cluster
  grants (write_fleet_secrets, .fleet-secrets* index) exist, but Kibana-side
  fleet feature privileges are registered release-movable (fleet/server/plugin.ts
  registerKibanaFeature; the fleet-setup reserved privilege is documented
  "Intended for use by the elastic/fleet-server service account only").
- https://www.elastic.co/guide/en/elasticsearch/reference/8.19/built-in-roles.html
  (kibana_system: "should not be assigned to users as the granted permissions
  may change between releases").

Post-fix status: prep-only-live-run-pending (tracker closure = verification
agent's call).
---

## Issue #4 -- structurally resolved at HEAD (no commit needed)

Evidence at HEAD 864267a: extensions/elastic-edr/ansible/roles/elastic_stack/tasks/main.yml --
grep _index_template over the whole file returns 0 hits (the priority-200 composable
template PUT from 3142ff1 was removed by 29e19a5); the role uses ONLY logs@custom /
metrics@custom component templates, so the template-priority collision risk as filed is
structurally gone. The #31 fix rides the same @custom hooks.
Fresh-source check: none needed (structural grep).
Post-fix status: fixed-static-only (no collision surface remains).

## Issue #5 -- open by design (live measurement)

Evidence: no code change -- measuring real ingest against the 60-day ILM window requires
a running stack. The C-14 README "Live-run validation checklist" row gives the exact
command (GET _cat/indices?v&s=store.size:desc, daily for the first week; tighten
elastic_ilm_retention_days per the Data retention section).
Fresh-source check: none needed.
Post-fix status: open-by-design.

## Issue #12 -- open by design (live measurement)

Same posture as #5: per-source telemetry readiness checks need live event flows.
Static preparatory work only, per the plan's no-scope-creep rule.
Fresh-source check: none needed.
Post-fix status: open-by-design.

## Issue #7 -- resolved by commit 864267a

Evidence at HEAD 864267a: extensions/elastic-edr/ansible/roles/applocker/tasks/main.yml --
the hashes/apply steps are merged into ONE task whose changed_when parses the explicit
applocker_policy_changed=1 marker (ordering defect gone).
Fresh-source check: none needed.
Post-fix status: fixed-static-only.

## Issue #36 -- resolved by commit 6d8fd16

Evidence at HEAD (this run): extensions/elastic-edr/ansible/roles/elastic_stack/tasks/main.yml --
status_code added to fleet_setup [200,400], endpoint_policy [200,409], windows_policy
[200,409], endpoint_detect [200,409], de_enable [200,400], de_bulk_enable [200,400],
de_bulk_disable [200,400]; failed_when body-validation on the four 400-accepting tasks
(only the documented already/initialized 400 is terminal).
Fresh-source check: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/uri_module.html
(status_code: "list of valid, numeric, HTTP status codes that signifies success";
Default: [200]; fetched this session).
Post-fix status: fixed-static-only.

## Issue #19 -- resolved by commit 714475d

Evidence: elastic_stack/tasks/main.yml "Ensure the elastic-agent service is running and
enabled" -- start_mode removed, enabled: true set; grep start_mode in this Linux role = 0
(the win_service start_mode uses in elastic_agent_win/applocker are correct for that
module and untouched).
Fresh-source check: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/service_module.html
(no start_mode param; enabled = "Whether the service should start on boot"; fetched).
Post-fix status: fixed-static-only.

## Issue #23 -- resolved by commit 74393b1

Evidence: elastic_stack/tasks/main.yml posture block -- "Verify effective rule posture
after bulk action (#23)" read-after-write _find (filter=alert.attributes.params.immutable:
true AND alert.attributes.enabled:true|false), "Fail if the bulk posture transition did
not take effect (#23)" diagnostics, marker persisted only after a green verification
(truth table for first-enable / re-run-no-op / first-disable / bulk-400 / find-500 /
malformed-200 all marker-consistent -- recorded in the commit body).
Fresh-source check: Kibana v8.19.23 bulk_actions_route.gen.ts (BulkEditActionResponse:
attributes.results{updated,created,deleted,skipped} + summary{failed,skipped,succeeded,total}
+ errors) + find_rules_route.gen.ts (FindRulesResponse {page,perPage,total,data}) +
common/detection_engine/rule_management/rule_fields.ts (PARAMS_IMMUTABLE_FIELD /
ENABLED_FIELD). All fetched this session.
Post-fix status: fixed-static-only.

## Issue #25 -- resolved by commit 1c0f111

Evidence: extensions/elastic-edr/ansible/roles/health_assertions/tasks/aggregate.yml --
endpoint_rollup_4688_check / endpoint_rollup_4104_check facts (selectattr on the exact
'CHECK' strings verify_agents.yml:85-86 records) + the roll-up warning's OR-condition and
message extended; warnings stay non-fatal per the documented aggregate design.
Fresh-source check: none needed.
Post-fix status: fixed-static-only.

## Issue #31 -- resolved by commit ef9cc00

Evidence: elastic_stack/tasks/main.yml -- index.number_of_replicas: 0 in BOTH the
logs@custom and metrics@custom component-template PUT bodies and in the renamed
"Apply ILM and zero-replica settings to existing logs and metrics data streams" task;
template-vs-component precedence caveat documented in the comment block.
Fresh-source check: https://www.elastic.co/guide/en/elasticsearch/reference/8.19/index-templates.html
(component-template inheritance + precedence rules; fetched this session).
Post-fix status: fixed-static-only (live inheritance check on the C-14 checklist).

## Issue #33 -- resolved by commit 0b5fd59

Evidence: no_log: true on 7 secret-bearing elastic_stack tasks (service-token create +
set_fact, 2x enrollment-token create + set_fact, fleet-server install command), the
install.yml token-read pre_task, and the elastic_agent_win MSI task; grep no_log in
extensions/elastic-edr/ansible/ = 9 (was 1). The changeme lab passwords deliberately stay
visible (user decision; the issue excludes them). Downstream until/when/changed_when
consumers verified unaffected (no_log hides display, not the registered variable).
Fresh-source check: none needed.
Post-fix status: fixed-static-only.

## Issue #51 -- resolved by commit fb1cc74

Evidence: health_assertions/tasks/aggregate.yml -- expected_agents / reported_agents /
missing_agents census facts from groups['elastic-edr_agents'] (group name cross-checked
against install.yml play 2 hosts: and the extension inventory's
[elastic-edr_agents:children]), expected/reported counts in the no-report fail message,
non-fatal missing-endpoints warning.
Fresh-source check: none needed.
Post-fix status: fixed-static-only.

## Issue #52 -- resolved by commit fb1cc74

Evidence: extensions/elastic-edr/ansible/install.yml -- any_errors_fatal: true on all
three plays + header comment documenting the --tags partial-run caveat (minimal
acceptable fix per plan C-6a; the fact-passing variant was evaluated and dropped as
bypassable under partial tag runs).
Fresh-source check: none needed.
Post-fix status: fixed-static-only.

## Issue #16 -- partially addressed by commit 756da82

Docs outcome B per plan C-12: the docs do NOT conclusively grant kibana_system every
Fleet feature privilege. 9 bootstrap/WRITE call sites switched to user: "elastic"
(agent-policy id lookups x2, 2x enrollment-token create, fleet_server_hosts register,
default-output update, 2x package-policy create, Defend detect-mode PUT); 8 READ call
sites stay on kibana_system, documented per-class in
elastic_stack/defaults/main.yml (identity-map comment block).
Fresh-source check: elasticsearch v8.19.23 KibanaOwnedReservedRoleDescriptors.java
(kibanaSystem descriptor: cluster grants + ManageApplicationPrivileges LIMITED to
"kibana-*" applications; write_fleet_secrets etc.) + built-in-roles.html
("should not be assigned to users as the granted permissions may change between
releases") + kibana issue #51688 (kibana_system intentionally constrained). All fetched
this session.
Post-fix status: prep-only-live-run-pending (the 8 remaining kibana_system GETs are the
live question; any 403 -> switch the same way).

## Issue #34 -- resolved by commit 69547fe

Evidence: sysmonconfig-export.xml Event ID 3 semantics comment block (different fields
ANDed / same-field values ORed / exclude precedence, both blind spots by design, broad
escape hatch) + README Event ID 3 paragraph cross-reference. Comments-only verified
(XML with comments stripped is whitespace-identical to the pre-change structure).
Fresh-source check: none needed.
Post-fix status: fixed-static-only.

## Issue #40 -- resolved by commit 69547fe

Evidence: sysmonconfig-export.xml Event ID 22 DNS-posture comment block (always-vs-
filtered exclusions, C2-lookalike trade-off, both broadening paths, endpoint-side
no-recovery caveat) + README Event ID 22 paragraph.
Fresh-source check: none needed.
Post-fix status: fixed-static-only.

## Issue #45 -- label resolved by commit 5b4d4fe; section-comment residue resolved by commit 69547fe

Evidence: sysmonconfig-export.xml -- the "Ports: Tor" heading replaced by a
remote-access/tunneling heading carrying the IANA citation (1723/tcp = pptp, RFC 2637;
9001/9030 are conventions, not registry assignments); the PPTP rule comment says
"suggests, not proves". No Event ID 3 inclusion-scope change (per the issue constraint).
Fresh-source check: https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.csv
(pptp,1723,tcp,...,RFC 2637; fetched 2026-10-21).
Post-fix status: fixed-static-only.

## Issue #38 -- branches resolved by commit 5b4d4fe; stale-comment residue resolved by commit 69547fe

Evidence: sysmonconfig-export.xml Event ID 7 -- the stock "disabled by default" comment
above the ACTIVE include block replaced with an honest one; the two Rule branches
("DLL from user-writable path" OR-group / "Selected DLL names from user-writable
processes" AND-group) and the README semantics untouched.
Fresh-source check: none needed.
Post-fix status: fixed-static-only.

## Standing residue (honest)

- Zero live runs: every fix above is static verification only. The README
  "Live-run validation checklist" (C-14) is the runbook for #5, #12, #28, #16,
  #37-enum, #10-path, #23-marker, #31-replicas.
- #16's remaining 8 kibana_system GETs: live 403 test pending.
- #4: no commit because the collision surface no longer exists at HEAD (grep
  evidence above); the review agent re-greps before closing.
- #5 / #12: open by design until the home-lab run measures ingest.
---

## Plan deviation: C-13 static regression tests -- formally dropped

The PASS 1 plan premise that `extensions/elastic-edr/tests/test_windows_telemetry_config.py`
"already exists" was stale: the file was created in c40aeee and DELIBERATELY DELETED
upstream in 8883f61 ("Remove the standalone unittest file added in the previous change.
This repository does not use that proposed test harness."). The user then ruled
explicitly: "No test harnesses are used in the GOAD project. You are to not build any
unittests."

Therefore: C-13's static regression tests were NOT built and are FORMALLY DROPPED.
The #36 invariant (every until-with-400/409 uri task carries a matching status_code)
is guarded instead by the per-task failed_when blocks landed with commit 6d8fd16 and
is re-checkable by hand: grep status_code in elastic_stack/tasks/main.yml (15 lines)
against the 7 until-predicates. No tests will follow unless the project changes its
no-test-harness convention.

---

# PASS 2 evidence blocks (2026-10-22 re-opened issues)

## Issue #3 -- fixed-static-only (commit 35bb237, PASS 2 P-1)

Evidence at HEAD: extensions/elastic-edr/ansible/roles/health_assertions/tasks/
verify_stack.yml ingest poll block -- status_code widened to
[200,401,403,404,500,503]; failed_when fails promptly on any non-[200,503] AND on a
200 whose body has no usable integer count; until succeeds ONLY on
200 + count is number + count|int > 0 (a valid zero-count 200 falls through
failed_when without satisfying until = the ONLY retry case, plus 503 boot-window
retries); es_probe_class fact (probe-error | malformed-response | no-data-yet) drives
a 3-way rescue message that separates the outcomes. default(0) removed from the
until/failed_when chain (remaining default(0)s in the file are unrelated rules_status
debug lines).
Verification: the 7-case truth table (200/0 retry, 200/5 success, 200-malformed fail,
401 fail, 503 retry, 500 fail, 200-"abc" fail) EXECUTED against real ansible-core 2.18
debug-task renderings of the exact expressions -- ALL OK (recorded in the commit body).
`is number` confirmed available in the pinned toolchain (ansible-core 2.18/jinja 3.1.6;
the plan's type_debug fallback not needed).
Fresh-source check: docs.ansible.com playbook_guide/playbooks_loops.html (until
semantics) + live expression execution above.
Post-fix status: fixed-static-only (live ES cases explicitly deferred by the issue).

## Issue #33 -- fixed-static-only (commit 4e97e55, PASS 2 P-2)

Evidence at HEAD: elastic_stack/tasks/main.yml -- the service token is persisted to
{{ state_dir }}/fleet-service-token (mode 0600, root:root, no_log'd copy) and the
install command now passes --fleet-server-service-token-path=<file>; the value form
--fleet-server-service-token= is GONE from argv (grep clean). Sanitized stat/debug
diagnostic pair prints exists/mode/uid, never the value. no_log remains on the install
task (the enrollment token stays in argv by design: no -path equivalent exists for
--enrollment-token in the 8.19 CLI option list, and the Windows MSI documents
INSTALLARGS="--url=... --enrollment-token=..." with no token-path alternative --
both verified this session). README "Token revocation and rotation" subsection added:
DELETE /_security/service/elastic/fleet-server/credential/token/<name> (per the 8.19
Delete service account tokens API page), enrollment-key revocation via Fleet UI /
DELETE /api/fleet/enrollment_api_keys/<id>, when-to-rotate.
Fresh-source check: elastic-agent-cmd-options.html (--fleet-server-service-token-path
"Mutually exclusive with --fleet-server-service-token"); install-agent-msi page (no
token-path alternative); security-api-delete-service-token.html (DELETE path shape).
Post-fix status: fixed-static-only (verbose-log/token-file live confirmation pending).

## Issue #7 -- fixed-static-only (commit 1d823be, PASS 2 P-3)

Evidence at HEAD: applocker/tasks/main.yml -- NEW "Compute effective-policy drift
before applying (issue #7)" read-only task (hashes effective vs shipped policy,
applocker_drift=0|1, explicit non-zero exit on retrieval failure); the apply task is
now when:-gated on applocker_drift=1 -- Set-AppLockerPolicy runs ONLY on genuine
drift (grep confirms the call lives only inside the gated task). The single-task
before/apply/after changed_when pattern from 864267a is preserved for the apply path.
Serialization-sensitivity caveat documented above the drift task (cosmetic
re-serialization may re-apply; idempotent, audit-only).
Fresh-source check: none needed (structure-only change; hash helpers reused from the
existing task).
Post-fix status: fixed-static-only (first-run/no-op/drift transcripts = live-run
evidence criterion, pending home lab).

## Issue #31 -- prep-only-live-run-pending (commit d0bbdc6, PASS 2 P-4)

Evidence at HEAD: elastic_stack/tasks/main.yml -- NEW "Report the effective resolved
template settings for logs-* (issue #31)": POST
/_index_template/_simulate_index/logs-windows.sysmon_operational-2026.01.01 resolves
the full composable chain (index + component templates, precedence applied) and the
debug task prints the effective index.number_of_replicas / index.lifecycle.name
(NOT-RESOLVED fallback) flagged "verify on live run: must read 0 / goad-edr-logs",
plus a 404 warn task (integration templates not yet created). Representative data-stream
name taken from THIS lab's windows integration config (windows.sysmon_operational),
not guessed. Component-template comment block + README checklist row #31 updated to
name the simulation task and the escalation path.
Fresh-source check: elasticsearch 8.19 simulate-index API page
(operation-indices-simulate-index-template: endpoint + response
template.settings.index.number_of_replicas). All fetched this session.
Post-fix status: prep-only-live-run-pending (the task SHIPS the proof mechanism;
the value confirmation is live-gated per the verifier's criterion 1).

## PASS 2 standing residue (honest)

- Zero live runs: all four PASS 2 fixes are static verification only. The README
  "Live-run validation checklist" remains the runbook; rows #3-classified-probe,
  #7-drift-transcripts, #31-simulation-readout, #33-argv-free-install now map to
  the four new commits.
- #33: the Windows MSI enrollment-token argv exposure REMAINS BY DESIGN (no
  token-path alternative exists in the MSI mechanism -- verified); suppression is
  via no_log only.
- #31: the simulation task proves the MECHANISM; the effective value (0 vs
  integration-template's 1) is the live-gated half.
- #7: hash-compare serialization sensitivity may cause benign re-applies;
  documented, deferred.
- #3: live ES cases explicitly deferred by the issue itself.
