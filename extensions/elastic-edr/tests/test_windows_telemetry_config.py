"""Static regression checks for elastic-edr Windows telemetry assets.

Run from the repository root:
    python -m unittest discover -s extensions/elastic-edr/tests -v

These checks validate repository assets only. Sysmon 14.14 and AppLocker imports
still require execution on supported disposable Windows guests.
"""
from pathlib import Path
import unittest
import uuid
import xml.etree.ElementTree as ET

EXTENSION = Path(__file__).resolve().parents[1]
ROLES = EXTENSION / "ansible" / "roles"


class WindowsTelemetryConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sysmon_path = ROLES / "sysmon" / "files" / "sysmonconfig-export.xml"
        cls.applocker_path = ROLES / "applocker" / "files" / "applocker-audit.xml"
        cls.endpoint_tasks = (ROLES / "endpoint_logging" / "tasks" / "main.yml").read_text(encoding="utf-8")
        cls.verify_agents = (ROLES / "health_assertions" / "tasks" / "verify_agents.yml").read_text(encoding="utf-8")
        cls.uninstall = (EXTENSION / "ansible" / "uninstall.yml").read_text(encoding="utf-8")
        cls.readme = (EXTENSION / "README.md").read_text(encoding="utf-8")
        cls.sysmon_root = ET.parse(cls.sysmon_path).getroot()
        cls.applocker_root = ET.parse(cls.applocker_path).getroot()

    def test_sysmon_condition_operators_use_documented_spelling(self):
        allowed = {
            "is", "is not", "contains", "contains any", "contains all", "excludes",
            "excludes any", "excludes all", "begin with", "end with",
            "less than", "more than", "image",
        }
        operators = {node.get("condition") for node in self.sysmon_root.iter() if node.get("condition")}
        self.assertEqual(operators - allowed, set())
        self.assertNotIn('condition="ends with"', self.sysmon_path.read_text(encoding="utf-8-sig"))

    def test_autochk_exclusion_does_not_use_glob_syntax(self):
        raw = self.sysmon_path.read_text(encoding="utf-8-sig")
        self.assertNotIn('autochk.exe *</CommandLine>', raw)
        matches = [node for node in self.sysmon_root.iter("CommandLine") if "autochk.exe " in (node.text or "")]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].get("condition"), "begin with")

    def test_class_registry_coverage_uses_explicit_subtrees(self):
        raw = self.sysmon_path.read_text(encoding="utf-8-sig")
        self.assertNotIn("Classes" + chr(92) + "*" + chr(92), raw)
        for subtree in (
            r"Classes\CLSID", r"Classes\exefile", r"Classes\batfile",
            r"Classes\cmdfile", r"Classes\ps1file", r"Classes\.exe",
            r"Classes\.bat", r"Classes\.cmd", r"Classes\.ps1",
        ):
            self.assertIn(subtree, raw)

    def test_event_25_is_not_active_or_claimed_as_collected(self):
        self.assertEqual(list(self.sysmon_root.iter("ProcessTampering")), [])
        self.assertIn("Event ID 25 (ProcessTampering) is **not collected", self.readme)
        self.assertNotIn("22 (DNS), 25 (tampering)", self.readme)

    def test_applocker_has_expected_audit_only_collection_types(self):
        collections = self.applocker_root.findall("RuleCollection")
        self.assertEqual({item.get("Type") for item in collections}, {"Exe", "Msi", "Script", "Appx"})
        self.assertTrue(all(item.get("EnforcementMode") == "AuditOnly" for item in collections))

    def test_applocker_rule_ids_are_unique_guids(self):
        ids = []
        for rule in self.applocker_root.findall("./RuleCollection/*"):
            rule_id = rule.get("Id")
            self.assertIsNotNone(rule_id)
            ids.append(str(uuid.UUID(rule_id.strip("{}"))))
        self.assertEqual(len(ids), len(set(ids)))

    def test_publisher_conditions_are_nested_in_publisher_rules(self):
        self.assertGreater(len(self.applocker_root.findall("./RuleCollection[@Type='Msi']/FilePublisherRule/Conditions/FilePublisherCondition")), 0)
        self.assertGreater(len(self.applocker_root.findall("./RuleCollection[@Type='Appx']/FilePublisherRule/Conditions/FilePublisherCondition")), 0)
        self.assertEqual(self.applocker_root.findall("./RuleCollection[@Type='Msi']/FilePathRule/Conditions/FilePublisherCondition"), [])
        self.assertEqual(list(self.applocker_root.iter("PackagedAppRule")), [])

    def test_powershell_logging_uses_policy_registry_paths_and_uninstall_snapshot(self):
        policy_path = r"HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell"
        self.assertIn(policy_path + r"\ScriptBlockLogging", self.endpoint_tasks)
        self.assertIn(policy_path + r"\ModuleLogging", self.endpoint_tasks)
        self.assertIn(policy_path + r"\ScriptBlockLogging", self.verify_agents)
        self.assertIn("endpoint-logging-registry-backup.json", self.endpoint_tasks)
        self.assertIn("endpoint-logging-registry-backup.json", self.uninstall)
        self.assertIn("Restored endpoint logging registry values", self.uninstall)

    def test_appidsvc_is_started_and_effective_policy_failures_are_visible(self):
        applocker_tasks = (ROLES / "applocker" / "tasks" / "main.yml").read_text(encoding="utf-8")
        self.assertIn("state: started", applocker_tasks)
        self.assertIn("Configure and start AppIDSvc", applocker_tasks)
        self.assertIn("failed_when: applocker_verify.rc is defined and applocker_verify.rc != 0", applocker_tasks)

    def test_ad_ds_sacl_check_is_read_only_and_reports_prerequisites(self):
        self.assertIn("GetAuditRules", self.endpoint_tasks)
        self.assertIn("ad_ds_sacl_replication_control_access", self.endpoint_tasks)
        self.assertIn("ad_ds_sacl_inherited_write_property", self.endpoint_tasks)
        self.assertNotIn("Set-Acl", self.endpoint_tasks)
        self.assertNotIn("dsacls ", self.endpoint_tasks)


if __name__ == "__main__":
    unittest.main()
