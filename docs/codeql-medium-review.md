# Medium CodeQL review

Scope: the 47 open `py/stack-trace-exposure` findings on downstream/integration
at 9453cc84. Findings were traced using the CodeQL SARIF code flows, including
shared sources rather than only the reported response locations.

## Confirmed exposure: 29 findings, plus one mixed finding

Alerts **8, 10, 12, 13, 14, 16, 19, 20, 21, 22, 23, 24, 25, 28,
26, 31, 34, 36, 38, 39, 40, 43, 44, 45, 48, 49, 50, 51, 52** expose
unexpected application/provider exceptions or account/schema write failures.
Those failures can include paths, connection details or reflected parameters.
Responses now retain their existing failure status/shape with fixed messages.
SMS provider responses and missing 2FA configuration no longer forward raw
provider/exception details. Explicit validation errors remain available.

Additional source hardening removes complete tracebacks from cloud client
initialization, email delivery failure returns, and MongoDB shell execution
failure results. Existing provider logs are outside this response-exposure
review; no claim is made that all application logs are sanitized.

## Contextual false positives: 17 findings, plus one mixed finding

These are false positives for **stack trace exposure**, not assertions that
arbitrary database diagnostics are suitable for anonymous access. Existing
instance authorization, query permissions and administrative permissions must
remain enforced. No scanner suppression or dismissal is applied.

| Alerts | Reported flow and rationale |
| --- | --- |
| 17, 33, 37, 46, 47 | Django password ValidationError messages are intentional password-policy feedback; the response contains messages rather than a Python traceback. |
| 7, 9, 11, 18, 27, 29, 30, 32, 35, 41, 42 | Authorized SQL/resource clients return database driver diagnostic strings for query troubleshooting. They do not format a Python traceback. Removing all such messages would remove a deliberate SQL-client capability. Application exceptions in the resource service are sanitized separately, including the additional source for alert 7. |
| 15 | The authorized OSC control response contains the GoInception engine diagnostic, not a formatted traceback. The API's own unexpected exception handler already returns a fixed failure message. |

| 53 (mixed) | The original false-positive classification was too broad: unexpected parser/query-check/count exceptions can reveal internals and are now sanitized. Explicit query-check results and database review diagnostics remain intentional feedback. The database-engine source can keep this scanner alert open. |

## Validation

Fixed response messages use Django translation at request time; Chinese catalog
entries and compiled messages accompany the changes.

New mocked regressions cover cloud authentication, email failure, unexpected
resource-service failures, SMS/TOTP save failure, MongoDB shell write failure,
and preservation of password-policy feedback. Existing tests expecting raw
unexpected exception text are updated to require the sanitized responses.
Tests use synthetic values, mocks and the disposable CI databases; they do not
connect to business databases, send messages or launch business tasks.

The first post-fix scan reduced medium findings from 47 to 19. Follow-up review
reclassified alert 26 as confirmed: the cloud kill handler also referenced an
undefined logger and could mask the original failure. It now returns a fixed,
translated message and logs only the exception class. Alert 53 is mixed rather
than wholly a false positive; unexpected exceptions are fixed at their source.
The remaining contextual conclusions cover the reported flows only; broad
engine exception handling is not proof that every possible exception is safe. See GitHub Actions for the final commit's CI results. The five
high-priority contextual findings documented in codeql-high-priority-review.md
remain unchanged. This review does not publish or deploy an application.
