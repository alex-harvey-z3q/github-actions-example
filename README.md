# Jenkins to GitHub Actions demo

A tiny Python application demonstrates the same **test → build → deploy** flow in Jenkins and GitHub Actions. Deployment is simulated: it writes a JSON receipt on the runner and changes no external system. No Python packages or cloud accounts are needed.

## Start the demo

1. Open this repository's **Actions** tab.
2. Choose **01 Migrated Jenkins pipeline**, then **Run workflow** on `main`.
3. Enter a greeting and release such as `1.0.0`, choose `dev`, `test` or `staging`, and select **Run workflow**.
4. Open the run. Expand **Build and test** to show checkout, Python setup, tests and packaging. Open **Simulated deployment** to show the dependent job downloading the package.
5. Read the deployment job's **Summary**, then download the package and receipt under the run's **Artifacts**.
6. Run **02 Matrix deployment demo** with its defaults. Two release versions × two Python versions produce **four** delivery combinations, with at most two combinations active at once.
7. Change `releases` to `["3.0.0"]` and rerun: there are now two combinations. The input is a JSON list, including quotes and brackets.

The first workflow also runs automatically on a push to `main`. The matrix workflow runs only when manually dispatched. The reusable workflow has no separate Run workflow button: it is invoked by its callers.

## Files to open while presenting

| File | What it shows |
|---|---|
| [jenkins/config.xml](jenkins/config.xml) | A freestyle Jenkins job with parameters, Git checkout, shell commands, credential binding and artifact archiving |
| [.github/workflows/01-migrated-pipeline.yml](.github/workflows/01-migrated-pipeline.yml) | Push/manual triggers, the input form and a caller of the reusable template |
| [.github/workflows/reusable-delivery.yml](.github/workflows/reusable-delivery.yml) | The reusable `workflow_call` contract; jobs, steps, runners, `needs`, artifacts, inputs and explicit secret passing |
| [.github/workflows/02-matrix-deploy.yml](.github/workflows/02-matrix-deploy.yml) | Validated manual input, step/job outputs, a two-axis matrix and repeated calls to the same template |
| [app.py](app.py) | Packaging and simulated deployment, including the secret presence check |
| [tests/test_app.py](tests/test_app.py) | Tests of build inputs, invalid versions, required secrets and absence of secrets in logs/receipts |

## Jenkins to GitHub Actions mapping

| Jenkins | GitHub Actions |
|---|---|
| Build with Parameters | `workflow_dispatch` and typed inputs |
| Git SCM checkout | `actions/checkout` step |
| Agent | `runs-on: ubuntu-latest` runner |
| Shell build step | A step with `run` |
| Stop when a command fails | Failed step/job blocks its dependent job |
| Sequential build and deploy commands | Two jobs linked by `needs: build` |
| Archive artifacts | Upload/download artifact actions between fresh runners |
| Credentials Binding `DEMO_TOKEN` | Repository secret → caller `secrets` → reusable secret → step environment |
| Repeated environment/version jobs | A matrix calling the reusable workflow |

The Jenkins XML and pipeline 01 use the same application commands and defaults on a manual run. Jenkins uses Python 3 from its agent; Actions pins the selected Python minor version. Jenkins runs everything in one workspace; Actions deliberately splits build and deployment to demonstrate artifact handoff. Jenkins credential binding requires its credential to exist, while Actions allows the secret to be optional unless **require_secret** is selected. These are explicit demo differences, not a claim of identical Jenkins/GitHub execution environments.

## The basic GitHub Actions concepts

- **Workflow:** a YAML file defining when and how automation runs.
- **Event:** a trigger, such as `push` or manual `workflow_dispatch`.
- **Job:** a group of steps running on a runner. A new job gets a fresh machine.
- **Step:** a command (`run`) or packaged action (`uses`). Steps in a job run in order.
- **Reusable workflow:** a template triggered with `workflow_call`, called using `jobs.<name>.uses`. It can contain multiple jobs.
- **Input:** a value supplied to a run or reusable workflow. Callers pass inputs using `with`.
- **Secret:** a separately stored value, passed explicitly using `secrets` and exposed only to the deployment step's environment.
- **Matrix:** a list of combinations. Each combination calls the same reusable workflow with different inputs.
- **Output:** data passed from a step through a job to a downstream job. The matrix's validated release list is an example.
- **Artifact:** files saved by one job and downloaded by another or by the presenter.

The template lives in this repository and callers use a relative path, so caller and template use the same commit. Official actions are pinned to full commit hashes, with readable release tags beside them.

## Demonstrating a secret

This demo repository is configured with a disposable made-up **DEMO_TOKEN**. It does not grant access to any service. To replace it or reproduce the setup in another repository:

In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**. Name it `DEMO_TOKEN` and enter any dummy value. Alternatively, use the hidden CLI prompt:

```bash
gh secret set DEMO_TOKEN --repo alex-harvey-z3q/github-actions-example
```

Then manually run either workflow with **require_secret** checked. The deployment reports whether a secret was supplied, without printing its value, length or hash. A missing required secret fails that step. With the checkbox off, missing secrets are allowed so the rest of the demonstration can still run.

The code checks availability only; it does not claim to authenticate to a real deployment service. For a real integration, the deployment client would consume the environment variable to authenticate. Do not put secret values in dispatch inputs or committed files. GitHub also masks registered secrets in logs, but this demo does not print a secret to demonstrate masking.

Targets such as `dev` are inputs to the simulator, **not GitHub Environments**. This example does not configure environment approvals or production deployment controls.

## Manual dispatch from the CLI

```bash
gh workflow run 01-migrated-pipeline.yml \
  --repo alex-harvey-z3q/github-actions-example --ref main \
  -f message='Hello Monday audience' -f release=1.0.0 \
  -f target_environment=dev -f require_secret=true

gh workflow run 02-matrix-deploy.yml \
  --repo alex-harvey-z3q/github-actions-example --ref main \
  -f releases='["1.0.0","2.0.0"]' -f message='Hello matrix' \
  -f target_environment=test -f require_secret=true

gh run list --repo alex-harvey-z3q/github-actions-example
```

The matrix accepts one to three distinct release versions and always uses Python `3.11` and `3.12`, so it creates two to six combinations. Each combination has a unique artifact name. `fail-fast: false` lets the other combinations finish if one fails.

## Run locally

Python 3.11 or newer is recommended; there are no third-party dependencies.

```bash
python3 -m unittest discover -s tests -v
python3 app.py build --message 'Hello locally' --release 1.0.0
python3 dist/app.py deploy --target dev
cat deployment/receipt.json
```

To demonstrate a required secret locally, set an inert example value only for that process:

```bash
DEMO_TOKEN=local-demo-only python3 dist/app.py deploy --target test --require-secret true
```

Generated files are ignored by Git. This local dummy is not a credential.

## Jenkins example

The XML is illustrative and has not been imported into a live Jenkins server. To run it in a disposable Jenkins instance, import it as a freestyle job, provide a Python 3 agent and the Git/Credentials Binding plugins, and create a **Secret text** credential with ID `demo-token`. If this GitHub repository is private, configure SCM credentials too. Then use **Build with Parameters**. Nothing needs to change on the University's Jenkins server.

## Suggested five-minute walkthrough

1. **One minute:** show the Jenkins XML parameters and three shell commands.
2. **One minute:** show pipeline 01 calling the reusable template; explain job-level `uses` versus step-level `uses`.
3. **One minute:** dispatch pipeline 01 with inputs; show job dependencies, logs, summary and artifacts.
4. **One minute:** show secret passing and the checkbox; values remain hidden.
5. **One minute:** dispatch pipeline 02 and show the expanded matrix. Change the release list to show the fan-out changes without copying jobs.

Run the examples once before presenting so completed runs are available while a live run queues.

## GitHub documentation

- [Reusable workflows and their inputs/secrets](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
- [Triggering workflows and manual inputs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- [Matrix strategies](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)
