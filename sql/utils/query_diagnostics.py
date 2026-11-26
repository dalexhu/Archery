"""Public query diagnostics built from codes, never exception text."""

from django.utils.translation import gettext as _

# Keep this allowlist limited to actionable SQL errors. Connection/authentication,
# file access and unknown errors deliberately receive no driver detail.
MYSQL_DIAGNOSTICS = {
    1052: "SQL column reference is ambiguous.",
    1054: "SQL refers to an unknown column.",
    1055: "SQL GROUP BY clause is invalid.",
    1064: "SQL syntax is invalid.",
    1142: "SQL command is not permitted.",
    1146: "SQL refers to a table that does not exist.",
    1227: "SQL requires additional database privileges.",
    1305: "SQL refers to a routine that does not exist.",
    1317: "SQL execution was interrupted.",
    3024: "SQL execution exceeded the time limit.",
}


def public_query_error(code=None):
    if type(code) is int and code in MYSQL_DIAGNOSTICS:
        return f"{_(MYSQL_DIAGNOSTICS[code])} (MySQL {code})"
    return _("Operation failed; contact an administrator.")
