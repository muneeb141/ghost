"""Local release preflight, not a substitute for Frappe Cloud's hosted audit.

Developer tooling: Python 3.12+ and semantic-version. Never connects to a site.
"""

import argparse
import ast
import json
from pathlib import Path

import tomllib
from semantic_version import SimpleSpec, Version

ROOT = Path(__file__).resolve().parents[1]


def literals(path):
	values = {}
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign):
			for target in node.targets:
				if isinstance(target, ast.Name):
					try:
						values[target.id] = ast.literal_eval(node.value)
					except (ValueError, TypeError):
						pass
	return values


def preflight(release=False):
	project = tomllib.loads((ROOT / "pyproject.toml").read_text())
	hooks = literals(ROOT / "ghost/hooks.py")
	assert project["project"]["name"] == hooks["app_name"] == "ghost"
	assert hooks["app_license"].lower() == "mit"
	assert (ROOT / "license.txt").is_file()
	spec = SimpleSpec(project["tool"]["bench"]["frappe-dependencies"]["frappe"])
	for version in ("15.123.1", "16.52.0"):
		assert Version(version) in spec, version
	assert Version("17.0.0") not in spec, "Do not advertise an untested framework major"
	assert not project["project"].get("dependencies"), "Review new runtime dependencies and isolation"
	assert not hooks.get("required_apps"), "Ghost must remain Frappe-only"
	for override in ("override_doctype_class", "override_whitelisted_methods"):
		assert not hooks.get(override), override
	assert "*" not in hooks.get("doc_events", {}), "Avoid global document hooks"
	assert hooks["before_migrate"] == "ghost.patches.v2_0.rename_otp_to_ghost_otp.validate_migration"
	assert "ghost.patches.v2_0.rename_otp_to_ghost_otp" in (ROOT / "ghost/patches.txt").read_text()
	assert hooks["never_skip_patches"] == ["ghost.patches.v2_0.rename_otp_to_ghost_otp"]
	for path in (ROOT / "ghost").rglob("*"):
		assert not path.is_symlink(), str(path)
		if path.suffix == ".py":
			tree = ast.parse(path.read_text(), filename=str(path))
			for node in ast.walk(tree):
				if not isinstance(node, ast.FunctionDef):
					continue
				public = any(
					isinstance(d, ast.Call)
					and isinstance(d.func, ast.Attribute)
					and d.func.attr == "whitelist"
					for d in node.decorator_list
				)
				if public:
					assert all(a.annotation for a in node.args.args if a.arg not in ("self", "cls")), (
						str(path),
						node.name,
					)
	meta = json.loads((ROOT / "ghost/ghost/doctype/ghost_otp/ghost_otp.json").read_text())
	assert meta["name"] == "Ghost OTP" and meta["module"] == "Ghost"
	assert not meta["index_web_pages_for_search"]
	assert not {"Guest", "All"}.intersection(p["role"] for p in meta["permissions"])
	assert not (ROOT / "ghost/ghost/doctype/otp/otp.json").exists()
	version = literals(ROOT / "ghost/__init__.py")["__version__"]
	Version(version)
	if release:
		assert Version(version).major >= 2, "Breaking candidate must receive its approved major version"
		assert f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text(), "Add dated release notes"
	print(f"PASS: repository metadata, bounded Frappe support, hooks, typed APIs and OTP schema ({version})")
	if not release:
		print(
			"Candidate preflight only; version approval, live providers, restore and hosted audit remain release gates"
		)


def scan_report(path):
	payload = json.loads(Path(path).read_text())
	assert not payload.get("errors"), f"Scanner errors: {payload.get('errors')}"
	findings = payload["results"]
	blocking = []
	for finding in findings:
		extra = finding["extra"]
		if extra.get("metadata", {}).get("is_blocking") or extra["severity"] in ("ERROR", "HIGH", "CRITICAL"):
			blocking.append(finding)
		print(
			f"{extra['severity']}: {finding['path']}:{finding['start']['line']} {finding['check_id'].rsplit('.', 1)[-1]}"
		)
	assert not blocking, f"{len(blocking)} blocking scanner finding(s); inspect the report"
	print(
		f"PASS: scanner completed without errors or blocking findings; {len(findings)} advisory findings need review"
	)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--release", action="store_true", help="Also require the approved major version and release notes"
	)
	parser.add_argument(
		"--semgrep-report", help="Gate the ordinary scan report using Press severity/blocking metadata"
	)
	args = parser.parse_args()
	preflight(release=args.release)
	if args.semgrep_report:
		scan_report(args.semgrep_report)
