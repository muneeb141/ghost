"""Deprecated site-specific helper; app fixtures own the bundled template."""


def create_magic_link_template():
	raise RuntimeError(
		"The bundled Ghost Magic Link template is installed through versioned app fixtures. "
		"Create custom templates in Desk; this legacy helper no longer connects to a hard-coded site."
	)


if __name__ == "__main__":
	create_magic_link_template()
