"""Deprecated manual helper; use the scoped integration tests instead."""


def debug():
	raise RuntimeError(
		"Use bench --site <disposable-site> run-tests --app ghost "
		"--module ghost.tests.test_lead_capture; this legacy helper no longer deletes site data."
	)


if __name__ == "__main__":
	debug()
