# Synthetic Mule timetable migration POC

This example rehearses a MuleSoft delivery pattern: **DEV builds and publishes an application JAR, then DEV/SIT/UAT/PROD select that publication for deployment without rebuilding it.** All application code, timetable data, coordinates and parent configuration are synthetic. No University source, private dependencies, identifiers or credentials are included.

The original beginner examples remain available as workflows **01** and **02**. This POC adds workflows **03** and **04**.

## What runs for real, and what is simulated

| Part | Implementation |
|---|---|
| Application source | A real Mule XML HTTP flow with two synthetic timetable entries, plus a synthetic parent POM |
| Toolchain | Java 17, checksum-verified Maven 3.8.7, Mule Maven plugin 4.3.1, Mule runtime selector 4.9.0 and MUnit 3.4.0 |
| Packaging and Maven publication | Real `mvn clean deploy -e -U -DskipTests=true`, producing a Mule application JAR and publishing it and its POM to a local file-based Maven repository |
| Exchange | Simulated by that Maven repository, retained as a GitHub Actions artifact for seven days; no Anypoint API is contacted |
| Artifact selection | Real verification of group/artifact/version, publication run, source repository and SHA-256 of the published JAR and POM |
| CloudHub deployment | Simulated; no CloudHub API is called and no Mule runtime is started by the deployment jobs |
| Deployment smoke checks | Real HTTP requests to a temporary localhost-only Python service, using timetable data read from the selected JAR. This is explicitly not Mule execution |
| MUnit | Three real MUnit definitions are supplied. Delivery skips them by default; optional execution is a separate mode, and must produce three executed-test records to be reported as successful |
| Secrets | Uses the example repository's inert `DEMO_TOKEN` to demonstrate explicit secret passing and missing-secret failure. It authenticates to no real service |

**A green default run proves packaging, publication, selection, byte preservation and the simulated delivery path. It does not prove Mule runtime behaviour, MUnit execution, Exchange publication or CloudHub deployment.**

## Run the main demo

1. Open **Actions → 03 Synthetic Mule build and promote → Run workflow** on `main`.
2. Enter a version such as `1.0.0`.
3. Leave **execute_munit** unchecked to preserve the delivery path's test-skipping behaviour.
4. Leave **require_secret** checked. The existing inert repository `DEMO_TOKEN` is sufficient.
5. Open **DEV build and publication**: inspect the Maven command and uploaded `mule-exchange-<run-id>` artifact.
6. Follow **DEV → SIT → UAT → PROD**. Each deployment downloads the same publication, checks its coordinates and checksums, starts a Python stand-in, performs three HTTP checks and saves a receipt.
7. Compare the four receipt artifacts. Their `jar_sha256`, `source_commit` and `source_run_id` should match, and `rebuilt` is `false`.

PROD is just a label in a local simulator. These jobs do not create GitHub Environments or configure production approvals. Each simulator is destroyed at the end of its job.

## Demonstrate deployment only from a previous run

1. Copy the numeric run ID and the exact published version from a successful workflow 03 run.
2. Open **04 Synthetic Mule deploy an existing publication → Run workflow**.
3. Enter that run ID and version, choose SIT/UAT/PROD, and run it.
4. There is **no build job, Maven installation or packaging command**. It downloads the saved repository snapshot and selects the requested publication.
5. Try a different version: selection must fail instead of silently rebuilding or choosing another package.

```bash
gh workflow run 03-mule-build-and-promote.yml \
  --repo alex-harvey-z3q/github-actions-example --ref main \
  -f version=1.0.0 -f execute_munit=false -f require_secret=true

# Replace RUN_ID with the successful publication run's numeric ID.
gh workflow run 04-mule-deployment-only.yml \
  --repo alex-harvey-z3q/github-actions-example --ref main \
  -f source_run_id=RUN_ID -f version=1.0.0 \
  -f target_environment=UAT -f require_secret=true
```

GitHub artifacts are a demonstration transport, not a persistent Exchange replacement. After seven days the publication may expire. Different publication runs have separate namespaces: the **run ID plus coordinates plus digest** identifies the selected package here. The POC does not enforce global immutability of a version across separate runs.

## The real pipeline shape

| Stage | Maven/platform behaviour being represented | POC behaviour |
|---|---|---|
| DEV build and publish | `mvn clean deploy -e -U -DskipTests=true` | Same Maven lifecycle/skip flags; repository URL is local, not Exchange |
| DEV deployment after successful build | `mvn mule:deploy -DskipTests=true` with environment-specific settings | Reusable deployment-only workflow selects the published JAR and runs the simulator |
| SIT/UAT/PROD deployment | `mvn mule:deploy -DskipTests=true` selecting an Exchange asset | Same selector/byte-verification path; no rebuild and no new Maven publication |

The real `mule:deploy` goal is **not executed** against a pretend CloudHub endpoint. Replacing the simulated adapter with real Exchange and CloudHub access is a distinct later integration task requiring an authorised personal sandbox or approved enterprise environment.

The synthetic parent POM is installed before the main application build. This substitutes for an existing internal parent dependency without using private Nexus access. Only public Maven/MuleSoft dependencies are fetched. The Mule plugin version and Java 17 are explicit demo choices; this example is not a reproduction of a particular organisation's full parent hierarchy or runtime configuration.

## Three synthetic MUnit cases

The suite in [mule-app/src/test/munit/timetable-test.xml](mule-app/src/test/munit/timetable-test.xml) checks:

1. Monday selects the expected packaged session.
2. Tuesday uses a mocked data-loading boundary.
3. An unknown day produces an empty result.

The optional `execute_munit` input changes Maven's test-skip flag to `false` and enables the declared 80% coverage gate for the application logic. The HTTP adapter flow is explicitly excluded from this MUnit coverage calculation; the synthetic tests call the logic flow directly. The manifest requires evidence of exactly three executed, non-failing tests. It cannot turn a skipped run into an apparent MUnit success.

The POM selects the **Mule Kernel** runtime so the synthetic app does not intentionally require an Enterprise account. Execution still depends on public availability and compatibility of that exact runtime and MUnit combination. Enterprise runtime tests commonly require vendor repository credentials; none are included or taken from another organisation. An unavailable runtime must result in a visible failed test run, not a simulated pass.

## Files to present

| File | Purpose |
|---|---|
| [mule-app/pom.xml](mule-app/pom.xml) | Mule packaging, file repository and MUnit execution/coverage configuration |
| [mule-app/demo-parent/pom.xml](mule-app/demo-parent/pom.xml) | Synthetic shared versions and public repositories |
| [mule-app/src/main/mule/timetable.xml](mule-app/src/main/mule/timetable.xml) | HTTP listener, flow references, resource loading and filtering |
| [.github/workflows/03-mule-build-and-promote.yml](.github/workflows/03-mule-build-and-promote.yml) | Thin orchestration caller and ordered environment jobs |
| [.github/workflows/reusable-mule-build.yml](.github/workflows/reusable-mule-build.yml) | Reusable build/publication workflow |
| [.github/workflows/reusable-mule-deploy.yml](.github/workflows/reusable-mule-deploy.yml) | Reusable deployment-only workflow |
| [.github/workflows/04-mule-deployment-only.yml](.github/workflows/04-mule-deployment-only.yml) | Manual promotion from an existing publication run |
| [mule-app/scripts/platform.py](mule-app/scripts/platform.py) | Selector/checksum verification, local runtime stand-in, smoke checks and receipts |
| [mule-app/tests/test_platform.py](mule-app/tests/test_platform.py) | Simulator/selection tests, separate from MUnit |
| [mule-app/jenkins](mule-app/jenkins) | Synthetic Jenkins shell equivalents, not exports from a live server |

## Local use

Use Java 17, Maven 3.8.7 and Python 3.12 or newer. The helper uses Python's standard library.

```bash
cd mule-app
python3 -m unittest discover -s tests -v
python3 scripts/platform.py set-version --version 1.0.0
mvn -B -f demo-parent/pom.xml clean install -DskipTests=true
mvn -B clean deploy -e -U -DskipTests=true
python3 scripts/platform.py manifest --version 1.0.0
DEMO_TOKEN=local-demo-only python3 scripts/platform.py deploy \
  --version 1.0.0 --environment DEV --require-secret true
DEMO_TOKEN=local-demo-only python3 scripts/platform.py deploy \
  --version 1.0.0 --environment UAT --require-secret true
```

Local simulator tests use a tiny ZIP fixture to exercise selection and HTTP handling. **That fixture is not used by the build workflow**, which requires the real Maven-published Mule application JAR.

## Design improvements deliberately made visible

- Job dependencies prevent promotion after failed publication or deployment.
- Deployment-only jobs verify the selected JAR/POM bytes before use.
- Each environment records the same artifact identity and whether tests actually ran.
- Secret values are absent from logs, summaries and receipts.
- All network deployment calls are confined to loopback; no application deployment reaches external systems.
- The original test-skipping delivery baseline is distinct from optional test execution.

## Primary documentation

- [MuleSoft: MUnit Maven plugin, skip flags and runtime selection](https://docs.mulesoft.com/munit/latest/munit-maven-plugin)
- [MuleSoft: CloudHub 2 deployment through Maven](https://docs.mulesoft.com/mule-runtime/latest/deploy-to-cloudhub-2)
- [MuleSoft: publishing assets through Maven](https://docs.mulesoft.com/exchange/to-publish-assets-maven)
- [GitHub: reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
