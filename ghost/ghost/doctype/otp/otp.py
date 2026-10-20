"""Deprecated controller import; use ghost.ghost.doctype.ghost_otp.ghost_otp.

Alias the module so existing function imports and monkeypatches address the same
implementation. This does not alias old DocType names, REST resources or SQL.
"""

import sys

from ghost.ghost.doctype.ghost_otp import ghost_otp

sys.modules[__name__] = ghost_otp
