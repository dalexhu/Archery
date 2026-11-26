# High-priority CodeQL review

Scope is the 15 high-priority alerts first reported on downstream/integration.
Alert numbers refer to dalexhu/Archery. These conclusions concern the reported
flows and assume existing authorization checks remain enforced.

| Alerts | Finding | Assessment and action |
| --- | --- | --- |
| 62 (critical) | Plugin command-line injection | False positive for the reported shell-injection flows only; this does not establish safety against every tool-specific option or URI interpretation. Executable paths come from administrator configuration, argument names are constructed by server code, and subprocess receives a list with shell=False. A regression keeps shell metacharacters inside one argument and checks shell=False. |
| 60, 61 (high) | GoInception/MySQL SQL execution | Intentional SQL execution. These engine APIs accept complete SQL statements. Query-service callers check instance access, query validity and query privileges. Parameterizing the entire SQL statement would change the API contract. Mocked regressions verify that the intended SQL reaches the cursor unchanged. |
| 58, 59 (high) | Rollback file paths | False positives for traversal. The view converts the identifier to int before workflow lookup and file access. Tests reject traversal identifiers before file access. Additional hardening uses the loaded workflow's integer ID for the filename and response header. |
| 56, 57 (high) | SchemaSync result paths | Confirmed directory-boundary violation. Database names became filename components without validation. Reject separators/NUL before instance lookup or plugin invocation and use Django safe_join for result paths. A synthetic matching file outside the result directory verifies rejection. |
| 54, 55 (high) | Mongo query-check regex | Confirmed exponential backtracking. Nested repetitions over word characters can hang on malformed long inputs. Replace them with word segments separated by literal dots. Bounded subprocess regressions cover both reported prefixes and preserve valid dotted/Unicode collections. |
| 1, 6 (high) | DingTalk/WeChat token responses in logs | Confirmed sensitive-response logging. Error responses may reflect credentials. Log provider/operation failure without serializing raw responses. Mocked responses contain secret canaries that must be absent from captured logs. |
| 4, 5 (high) | Message failure URLs/payloads in logs | Confirmed access-token and message exposure. Remove URL, payload and response logging. Apply the same treatment to adjacent webhook logging. Tests cover personal messages and successful/failed webhook requests. |
| 2, 3 (high) | Doris/MySQL execution error logs | Confirmed SQL/exception exposure, including password literals. Log engine and exception class while retaining the existing caller-facing result error. Tests assert secret SQL and exception canaries are absent from logs. |

The result is 10 confirmed alerts and 5 contextual false positives. The two
rollback alerts also receive canonical-ID hardening. False-positive conclusions
are recorded here without suppressing or dismissing scanner results.

Regression tests use in-memory values, mocked clients and synthetic temporary
files. They execute no real database or provider requests. Remaining medium
alerts are outside this review's scope.
