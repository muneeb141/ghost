"""Deprecated site-specific helper; use Desk and versioned app migration defaults."""


def execute():
	raise RuntimeError(
		"Configure Ghost Settings and lead field mapping in Desk. "
		"Run the normal versioned app migration for defaults; "
		"this legacy helper no longer connects to a hard-coded site or changes its database."
	)


if __name__ == "__main__":
	execute()
