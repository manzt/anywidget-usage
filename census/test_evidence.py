import unittest

from build import prerelease
from collect import dependencies, github_repo
from inspect_artifacts import source_findings
from reconcile import declared_names


class EvidenceTests(unittest.TestCase):
    def test_import_alias_and_local_subclass(self):
        findings, parsed = source_findings(
            "import anywidget as aw\nclass Base(aw.AnyWidget): pass\nclass Child(Base): pass",
            "module.py",
        )
        self.assertTrue(parsed)
        self.assertEqual([f["kind"] for f in findings], ["anywidget", "anywidget"])

    def test_composing_builtin_controls_is_not_custom_frontend(self):
        findings, _ = source_findings(
            "import ipywidgets as w\nclass Box(w.VBox): pass", "module.py"
        )
        self.assertFalse(findings[0]["custom_signal"])

    def test_custom_frontend_and_builtin_frontend(self):
        custom, _ = source_findings(
            'from ipywidgets import DOMWidget\nclass Plot(DOMWidget):\n _model_module = "my-plot"',
            "module.py",
        )
        builtin, _ = source_findings(
            'from ipywidgets import DOMWidget\nclass Plot(DOMWidget):\n _model_module = "@jupyter-widgets/controls"',
            "module.py",
        )
        self.assertTrue(custom[0]["custom_signal"])
        self.assertFalse(builtin[0]["custom_signal"])

    def test_mentioned_dependency_is_not_an_implementation(self):
        findings, _ = source_findings(
            'import anywidget\ntext = "class Fake(anywidget.AnyWidget): pass"',
            "module.py",
        )
        self.assertEqual(findings, [])

    def test_dependency_markers_are_retained(self):
        entries = dependencies(
            {"requires_dist": ['AnyWidget>=0.9; extra == "docs"', "not [ valid"]}
        )
        self.assertEqual(entries[0]["name"], "anywidget")
        self.assertEqual(entries[0]["marker"], 'extra == "docs"')
        self.assertTrue(entries[1]["parse_error"])

    def test_github_identity_requires_actual_host(self):
        self.assertEqual(
            github_repo("https://github.com/manzt/quak.git/tree/main"), "manzt/quak"
        )
        self.assertIsNone(github_repo("https://example.com/github.com/manzt/quak"))

    def test_preview_and_stable_are_distinct(self):
        self.assertTrue(prerelease("6.0.0rc0"))
        self.assertTrue(prerelease("2025.1.23.1209.dev0"))
        self.assertFalse(prerelease("6.0.0"))

    def test_source_evidence_does_not_require_declared_dependency(self):
        self.assertEqual(dependencies({"requires_dist": None}), [])
        findings, _ = source_findings(
            "import anywidget\nclass BaseFigureWidget(anywidget.AnyWidget): pass",
            "basewidget.py",
        )
        self.assertTrue(findings[0]["custom_signal"])

    def test_manifest_parsing_does_not_execute_setup_code(self):
        self.assertEqual(
            declared_names(
                "setup.py",
                'raise Exception("must not execute")\nsetup(name="widget-package")',
            ),
            ["widget-package"],
        )
        self.assertEqual(
            declared_names("pyproject.toml", '[project]\nname="widget-package"'),
            ["widget-package"],
        )


if __name__ == "__main__":
    unittest.main()
