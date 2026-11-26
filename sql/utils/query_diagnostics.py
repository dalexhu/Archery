"""Public query diagnostics built from codes, never exception text."""

from django.utils.translation import gettext as _, gettext_noop

# Keep this allowlist limited to actionable SQL errors. Connection/authentication,
# file access and unknown errors deliberately receive no driver detail.
MYSQL_DIAGNOSTICS = {
    1052: gettext_noop("SQL column reference is ambiguous."),
    1054: gettext_noop("SQL refers to an unknown column."),
    1055: gettext_noop("SQL GROUP BY clause is invalid."),
    1064: gettext_noop("SQL syntax is invalid."),
    1142: gettext_noop("SQL command is not permitted."),
    1146: gettext_noop("SQL refers to a table that does not exist."),
    1227: gettext_noop("SQL requires additional database privileges."),
    1305: gettext_noop("SQL refers to a routine that does not exist."),
    1317: gettext_noop("SQL execution was interrupted."),
    3024: gettext_noop("SQL execution exceeded the time limit."),
}


def public_query_error(code=None):
    if type(code) is int and code in MYSQL_DIAGNOSTICS:
        return f"{_(MYSQL_DIAGNOSTICS[code])} (MySQL {code})"
    return _("Operation failed; contact an administrator.")
