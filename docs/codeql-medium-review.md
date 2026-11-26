# Medium CodeQL review

Scope: the 47 open `py/stack-trace-exposure` findings on downstream/integration
at 9453cc84. Findings were traced using the CodeQL SARIF code flows, including
shared sources rather than only the reported response locations.

## Confirmed exposure: 31 findings

Alerts **8, 10, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25, 28,
26, 31, 34, 36, 38, 39, 40, 43, 44, 45, 48, 49, 50, 51, 52, 53** expose
unexpected application/provider exceptions or account/schema write failures.
Those failures can include paths, connection details or reflected parameters.
Responses now retain their existing failure status/shape with fixed messages.
SMS provider responses and missing 2FA configuration no longer forward raw
provider/exception details. Explicit validation errors remain available.

Additional source hardening removes complete tracebacks from cloud client
initialization, email delivery failure returns, and MongoDB shell execution
failure results. Existing provider logs are outside this response-exposure
review; no claim is made that all application logs are sanitized.

## Contextual false positives: 16 original findings (5 still reported)

These are false positives for **stack trace exposure**, not assertions that
arbitrary database diagnostics are suitable for anonymous access. Existing
instance authorization, query permissions and administrative permissions must
remain enforced. No scanner suppression or dismissal is applied.

| Alerts | Reported flow and rationale |
| --- | --- |
| 17, 33, 37, 46, 47 | Django password ValidationError messages are intentional password-policy feedback; the response contains messages rather than a Python traceback. |
| 7, 9, 11, 18, 27, 29, 30, 32, 35, 41, 42 | Authorized SQL/resource clients return database driver diagnostic strings for query troubleshooting. They do not format a Python traceback. Removing all such messages would remove a deliberate SQL-client capability. Application exceptions in the resource service are sanitized separately, including the additional source for alert 7. |


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
translated message and logs only the exception class. Alert 53 was first reclassified as mixed rather than wholly a false positive;
the completion section below records the subsequent source-level fix.
The remaining contextual conclusions cover the reported flows only; broad
engine exception handling is not proof that every possible exception is safe. See GitHub Actions for the final commit's CI results. The five
high-priority contextual findings documented in codeql-high-priority-review.md
remain unchanged. This review does not publish or deploy an application.

## Alert 53 completion

The mixed assessment is superseded. MySQL query exceptions no longer become
raw public strings: known SQL error codes produce fixed translated diagnostics
with the numeric code; unknown, authentication and connection failures produce
the generic failure message. Driver text, SQL fragments and file paths are
never interpolated. Query-result errors in export prechecks use only the
allowlisted diagnostic code; unclassified errors from other engines fail closed.
Explicit query-check validation messages and normal count/limit results remain.
The precheck boundary also catches setup and engine-cleanup exceptions. Its
failure logs contain exception classes rather than SQL or exception payloads.

Mocked regressions run the MySQL-to-export path for syntax, column, table,
timeout, authentication and unexpected failures in both languages, and cover
configuration, engine initialization and actual MySQL cleanup failure. COUNT
fallback and successful export checks remain covered by the existing suite.

## Final six-alert review

The remaining baseline was 15, 17, 33, 37, 46 and 47 at b1bc94ad.

**15 is confirmed, not a false positive.** GoInception.query caught every
exception and returned its string. An authenticated OSC response could therefore
include connection, filesystem or runtime details. The earlier exception
handler at the API boundary did not help when the engine returned an error
instead of raising. GoInception now uses the same allowlisted, translated SQL
code diagnostics as MySQL. Unknown/authentication errors use the generic
message. Its connection initialization is inside the protected block, and the
OSC boundary logs exception class rather than traceback or payload. Successful
OSC progress rows and the existing view/execute authorization checks remain.

**17, 33, 37, 46 and 47 remain contextual false positives.** They respectively
cover registration, database-account creation, account password reset, API user
creation and API user update. All five catch Django ValidationError from
password-policy validation. Current AUTH_PASSWORD_VALIDATORS contains only
Django's UserAttributeSimilarityValidator, MinimumLengthValidator (9),
CommonPasswordValidator and NumericPasswordValidator. Their messages are
intentional policy feedback; a caught ValidationError object is not a Python
traceback. No format_exc/traceback payload is constructed in these handlers.
The registration handler also catches create_user ValidationError; its standard
Django manager does not add an internal exception wrapper. This conclusion is
limited to the configured built-ins and must be revisited if custom validators
or custom user-manager validation are introduced.

Ten tests exercise all five password entry points in both languages with the
real MinimumLengthValidator, checking policy feedback and rejection before
engine/user writes. Further mocked tests cover OSC connection/query/cleanup
failures and logs, known SQL versus authentication errors, and successful
progress rows. Existing API permission tests cover view-only progress and
execution permission for mutations. No real OSC operation or account write is
performed by these regressions. None of the five alerts is suppressed.
