# Synthetic POC validation

Validation performed on 28 November 2026 using only synthetic source/data and public dependencies.

- [Build, publish and DEV/SIT/UAT/PROD promotion](https://github.com/alex-harvey-z3q/github-actions-example/actions/runs/46140474787): passed. Real Maven Mule packaging and file-repository publication; deployment stages used the local Python stand-in.
- [Deployment-only promotion from that earlier run](https://github.com/alex-harvey-z3q/github-actions-example/actions/runs/46140804325): passed. Selected version 1.0.1 for UAT without a build job.
- Four downloaded environment receipts contain the same JAR SHA-256: `b887657df207c4de6b444c89256a935f66561dd4abce8bced8f63bf6b7c9461b`. Each records `rebuilt: false`, three HTTP smoke checks and `mule_runtime_executed: false`.
- Seven simulator/selection unit tests passed locally and in GitHub Actions.
- Actionlint validated all four new workflow files. All synthetic XML files parsed.

The default delivery run explicitly skipped MUnit. Its success is not evidence of an executed unit-test gate or an actual CloudHub deployment.

## Real MUnit validation

[Run 46140801478](https://github.com/alex-harvey-z3q/github-actions-example/actions/runs/46140801478) passed with `execute_munit=true` for version 1.1.0. The downloaded Surefire report `TEST-munit.MULE_CE.4.9.0.timetable-test.xml` records **3 tests, 0 failures, 0 errors, 0 skipped**. The 80% gate applies to the included logic flows; the HTTP adapter flow is explicitly excluded.

All four tested-release receipts have JAR SHA-256 `155af21a2da2171e5d343738ead619d883e93c87eb9048dd2e88f27c67ae1642` and record three executed MUnit tests. Real Mule Kernel execution happened during MUnit in the build job. Deployment jobs still used only the Python runtime stand-in and made no CloudHub calls.
