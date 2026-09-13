# Windows ModelScope identity and lifecycle correction

Status: dated engineering evidence, 2026-09-13; not a runtime gate

## Original failure and confirmed defects

Consumer PR 169, head `c33399f07d6b13d1db6b913ba5c455a5d0b837fc`, had
one Windows failure in `test_status_preserves_worker_and_resume_verification`.
The offline SDK had reached its controlled waiting phase, but status reported
`needs-download` instead of `active`. The unchanged rerun passed. Its 10.680 s
duration was comparable to the failed case's 10.63 s: duration does not prove
a CIM timeout, and the original log did not retain the process identity.

Follow-up reproduction used the controller from merged baseline
`4d10301c69946f071cc8e2680736db0c7a129be2`, whose SHA256 was
`9634c2911e21221e89363bde17f098aa53fba53221f8078a389ec62848afce4d`.
Only the first launch-time identity observation was replaced with `None`.
The actual offline worker reached SDK-ready; subsequent native observations
could read its identity. Nevertheless, three status calls reported
`needs-download`, and another `ensure` started a second live worker. Both
owned workers exited after fixture release. A separate deterministic test
showed that temporary observation failure for an already valid record also
triggered another launch. Two new regression tests against the old controller
produced eight assertion failures, with no test errors.

These experiments establish product defects in handling unknown identity.
They do not reconstruct which observation failed in the original CI run.

## Correction

Windows identity reads now use a held process handle, a bounded native command
query and process creation time. The raw command and microsecond precision of
existing CIM records are preserved. No dependency or background process is
added. The internal NT command query can be unavailable; that result remains
unknown rather than authorizing reuse or termination.

ModelScope distinguishes an unobservable live PID from an inactive or
explicitly mismatched process. `status` and `ensure` report
`identity-unavailable` with exit code 1; `ensure` does not launch another worker.
A later valid observation recovers normally. Missing or malformed identity
fields remain unowned. A startup detaches only after a valid identity record
has been written. Failed registration closes the owned process tree.

The original lifecycle test retains its strict `active` assertions. It disables
SDK retries, retains bounded command/PID/log diagnostics before cleanup, and
keeps Windows Job handles through the whole case. Cleanup no longer relies on
the identity lookup being tested or an unbounded `taskkill` call. Additional
native tests prove both successful live detachment and exception cleanup of a
parent and grandchild. Live legacy CIM comparison is explicit compatibility
acceptance; ordinary native tests do not depend on PowerShell availability.

## Evidence and limits

The corrected complete ModelScope directory passed 22 tests and 18 subtests
on native Windows/Python 3.13.12. The six Windows bootstrap tests passed,
including both new descendant-lifecycle cases. Shared monitor and identity
callers also passed their focused validation. Final CI and merge provenance
belong to the pull request containing this correction.

Private reproduction artifacts retain `identity-regressions-before.json`,
the original failed CI log, the unchanged rerun, and the corrected
`modelscope-final.xml`. These are offline SDK/HTTP fixtures and OS process
tests, not a live ModelScope account, network-download or NPU acceptance.
