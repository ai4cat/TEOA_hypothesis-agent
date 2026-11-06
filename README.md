# TEOA hypothesis agent

Evidence-grounded hypothesis generation and experimental proposal design for investigating the role of triethanolamine (TEOA) in cobalt-mediated carbon dioxide reduction.

This repository contains the Python implementation, statistical input snapshots, prompts, retrieval settings and one frozen inference run, `reviewed_gpt54_repeat1`. It also provides DOI lists identifying the literature collections. The experimental cards are **research proposals, not executed experiments or validated mechanisms**.

## Contents

- [Overview](#overview)
- [Repository layout](#repository-layout)
- [Requirements and installation](#requirements-and-installation)
- [Inspect the frozen results](#inspect-the-frozen-results)
- [Literature data and copyright](#literature-data-and-copyright)
- [Reproduction prerequisites](#reproduction-prerequisites)
- [Configure your API access](#configure-your-api-access)
- [Run a new analysis](#run-a-new-analysis)
- [Verification and tests](#verification-and-tests)
- [Troubleshooting](#troubleshooting)
- [Reproducibility and interpretation](#reproducibility-and-interpretation)
- [Contributing](#contributing)
- [Citation](#citation)
- [License](#license)

## Overview

The workflow uses a fixed research brief and imported consensus statistics to retrieve literature passages, assess evidence, propose catalytic platforms and hypotheses, generate experimental cards, and review their scientific support and coverage. Recorded requests, responses, source quotations and decisions connect the final proposals to their inputs.

The frozen run contains:

| Item | Count |
| --- | ---: |
| Hypotheses | 5 |
| Experimental candidate cards | 29 |
| Retained evidence passages | 64 |
| Exact quotation spans | 188 |
| Shortlisted cards | 22 |
| Cards requiring revision | 5 |
| Rejected cards | 2 |

These counts describe the archived run. New inference can produce different results.

## Repository layout

```text
database/
  LIB1/doi_list_1988_lib1.txt       Literature identifiers for the main collection
  LIB2/doi_list_395_lib2.txt        Literature identifiers for the system collection
engine/
  agent.py                        Command-line entry point
  requirements.txt                Python dependencies
  statistics/
    verified_results/             Imported summary and three ranking tables
    SOURCE_MANIFEST.json          Statistical input provenance
  library/
    LIBRARY_VALIDATION.json        Historical corpus/index validation record
    index.sqlite                  Local-only full-text index; ignored by Git
  app/
    spec/
      research_prompt.txt         Default research brief
      retrieval.json              Retrieval and evidence-selection settings
      runtime.json                Default provider/model/runtime configuration
    latest.json                   Pointer to the recorded run
    runs/reviewed_gpt54_repeat1/   Frozen outputs and inference audit trail
    test_*.py                     Offline regression test source
OPEN_REPORT.cmd                   Windows shortcut to the saved HTML report
VERIFY.cmd                        Windows shortcut to complete frozen verification
LICENSE                           Existing Apache License 2.0
environment.yml                   Alternative Conda environment definition
```

`index.sqlite` may exist in a local delivery but is not a public repository asset. See the prerequisites below before attempting verification or generation from a fresh clone.

## Requirements and installation

The original delivery records validation on **Windows with Python 3.13.9**. The Python entry point can also be invoked directly on other operating systems, but this release has not been validated on them. SQLite must support FTS5 for retrieval.

```bash
git clone https://github.com/ai4cat/TEOA_hypothesis-agent.git
cd TEOA_hypothesis-agent
python -m venv .venv
```

Activate the environment in your shell:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux/macOS
source .venv/bin/activate
```

Then install the declared dependencies:

```bash
python -m pip install -r engine/requirements.txt
```

The requirements specify compatible ranges for `jsonschema` and `tiktoken`, not a complete lockfile. For a new study, record `python --version` and `python -m pip freeze` alongside the run. The `.cmd` shortcuts are Windows-only; all commands below assume the repository root and an activated environment.

### Alternative: Conda

Instead of the virtual-environment steps above, run these commands from the repository root:

```bash
conda env create -f environment.yml
conda activate teoa-hypothesis-agent
```

`environment.yml` installs Python 3.13 and the existing `engine/requirements.txt`. It is an environment definition, not a solver lockfile or an API-credential file. Use either Conda or `.venv` for a session, rather than activating both. The Windows `.cmd` shortcuts prefer a local `.venv` if one exists; when using Conda, invoke `python engine/agent.py ...` directly to select the active interpreter.

## Inspect the frozen results

Open this existing file directly in a browser:

```text
engine/app/runs/reviewed_gpt54_repeat1/report.html
```

On Windows, double-click `OPEN_REPORT.cmd`. Reading the saved report requires **no API key and makes no inference requests**. Historical links to local PDFs may not resolve on another computer.

Important archived files include:

| File inside the frozen run | Purpose |
| --- | --- |
| `candidates_final.json` | Final hypotheses, platforms and experimental cards |
| `candidates.csv` | Tabular candidate export |
| `04_evidence.json` | Retained evidence and exact quotations |
| `research_prompt.snapshot.txt` | Exact research brief used for this run |
| `retrieval_settings.snapshot.json` | Recorded retrieval settings |
| `generation_inputs.json` | Statistical and research-brief input snapshot |
| `calls/` | Inference requests, responses and per-call audit records |
| `rejected_stage_attempts/` | Rejected intermediate attempts retained for traceability |
| `GENERATION_FROZEN.json` | Final output/evidence hashes and freeze status |
| `source_manifest.json` | Input file hashes, including the original index |
| `RECORDS_SHA256.json` | Complete frozen record checksums |

Do not delete failed calls, rejected attempts, intermediate JSON files or supervisor records from this directory. They are part of the frozen audit trail, not disposable regression-test output. Do not use the `report` command on this frozen run merely to view it: that command renders and writes the report. Open the existing HTML instead.

## Literature data and copyright

The `database/` directory provides DOI lists rather than the source PDF corpus. Obtain the publications yourself through the DOI links, publisher websites, institutional access or legitimate open-access copies, subject to the applicable access and redistribution conditions. This repository does not provide a bulk PDF downloader or subscription credentials.

The historical input comprised 1,988 main-collection and 395 system-collection memberships. The recorded retrieval index contains 2,291 PDF-hash records and 131,045 text chunks. Collection memberships, unique DOI counts, publications and byte-distinct PDF records are different quantities and must not be treated as interchangeable.

The local `engine/library/index.sqlite` contains extracted full text. Excluding PDFs alone does not make that index suitable for unrestricted redistribution. It is ignored by Git and retained locally for the original delivery's verification. Historical request/response records also contain source quotations; review the permissions applicable to these materials before publishing a release. The software license does not grant rights to third-party publications or excerpts.

## Reproduction prerequisites

There are three distinct activities:

1. **Inspect archived scientific output:** open the saved report or JSON files. No corpus index or API access is required.
2. **Verify the original frozen run completely:** obtain the exact original local index and unchanged frozen records. Verification checks the index hash and quotation character offsets, so a different PDF edition or a newly extracted index will not satisfy the original manifest.
3. **Generate a new analysis:** provide a compatible local index, statistical inputs, settings and your own API access. This is a new run, not a byte-for-byte replay of the archived result.

**Current release limitation:** this package contains retrieval code but no production PDF-ingestion/index-building command. Downloading the DOI-listed PDFs does not, by itself, enable a fresh public clone to run the full pipeline. The original index is necessary for exact frozen verification; a compatible independently built index can support new analyses, but its construction is not implemented in this release. A complete public source-to-index reproduction workflow therefore remains a release prerequisite.

The code expects the local database at:

```text
engine/library/index.sqlite
```

Retrieval uses `papers`, `chunks` and an FTS5 `search` table. Table names alone are not an indexing specification: extraction, chunk boundaries, identifiers, deduplication and tokenizer settings affect the result. Do not substitute a generic SQLite database and expect historical quotation verification to pass.

Statistical inputs are imported from a separate consensus release. `python engine/agent.py statistics` displays their provenance; it does not recompute the upstream consensus analysis. Preserve the supplied snapshots when checking the recorded run.

## Configure your API access

API access is required only for new inference. Supply your own provider account and key. No credential is required to read archived results or perform offline verification.

The code reads **`OPENAI_API_KEY` from the process environment**. Set it for the current terminal session. In PowerShell 7:

```powershell
$env:OPENAI_API_KEY = Read-Host 'Enter your provider API key' -MaskInput
```

On Bash, enter it without echoing the value:

```bash
read -r -s -p "Enter your provider API key: " OPENAI_API_KEY
export OPENAI_API_KEY
printf '\n'
```

Do not put keys in README files, committed configuration files, issue reports or screenshots. Remove the variable after use with `Remove-Item Env:OPENAI_API_KEY` in PowerShell or `unset OPENAI_API_KEY` in Bash.

Before starting a new run, inspect `engine/app/spec/runtime.json` and set the provider and model for your account:

| Setting | Meaning |
| --- | --- |
| `base_url` | Provider API root, ending in `/v1` |
| `service_name` | Descriptive provider label |
| `model` | Requested model identifier |
| `timeout_seconds` | Response/read timeout |
| `connect_timeout_seconds` | Connection timeout |
| `max_output_tokens`, `minimum_output_tokens` | Output-token settings used by the transport |
| `allow_unreported_model` | Whether responses without model identity are accepted |
| `auto_reconnect` | Retry/reconnection behavior |

The recorded configuration uses model `gpt-5.4` and the third-party endpoint `https://superai05.com/v1`. The implementation allows only `api.openai.com`, `api.tiantoken.com` and `superai05.com`, over HTTPS at `/v1`; an arbitrary compatible endpoint will be rejected. It sends requests to the provider's `/responses` route. Provider/model availability and account permissions must be checked with that provider. Use the key issued for the endpoint you select; do not send a provider's credential to a different service.

Changing `OPENAI_BASE_URL` alone does not configure this application: the endpoint comes from the runtime JSON. For official OpenAI access, configure `base_url` as `https://api.openai.com/v1` and choose a model supported by your account and the request format. The historical configuration is a record, not a claim that a model is currently available or that another endpoint will reproduce identical results.

Do not edit runtime snapshots inside the frozen run. Changes to the default runtime configuration affect newly created runs. On resume, the existing run's provider/model configuration is retained. Historical unlimited-budget authorization text in the template does not authorize a new run: the CLI requires an explicit budget choice.

## Run a new analysis

First satisfy the index prerequisite above. Review the research brief in `engine/app/spec/research_prompt.txt`, the input tables in `engine/statistics/verified_results/` and retrieval settings in `engine/app/spec/retrieval.json`.

Use a unique name, never the frozen run's name:

```bash
python engine/agent.py generate --name my_teoa_run --budget 10
```

This command makes live, potentially billable inference requests. `10` is a user-selected **estimated-cost ceiling**, not a guaranteed invoice limit. The configuration explicitly says provider prices are unverified; token estimates, provider pricing and retry behavior can affect actual charges. Choose a ceiling appropriate to your account and configure provider-side spending controls where available.

The CLI requires either a finite positive `--budget` or explicit `--unlimited-budget`. A run can stop before completion if the estimated budget is exhausted. To deliberately resume an interrupted, unfrozen run:

```bash
python engine/agent.py generate --name my_teoa_run --budget 10 --resume
```

Resume uses the existing run configuration and recorded state; it is not a fresh independent replicate. Never remove freeze markers to force regeneration over archived evidence.

Outputs are written to `engine/app/runs/my_teoa_run/`. After a successful run:

```bash
python engine/agent.py verify --run my_teoa_run --full
python engine/agent.py report --run my_teoa_run --open
```

The second command writes a readable report for your new run. Review the scientific decisions and unresolved issues before using a card experimentally.

## Verification and tests

With dependencies installed and the **exact original local index** present:

```bash
python engine/agent.py verify --run reviewed_gpt54_repeat1 --full
```

On Windows, `VERIFY.cmd` runs the same verification, using `.venv` when available. It validates input hashes, output hashes, evidence quotations and offsets, model identities, final-card origins, and the complete frozen record manifest without inference requests. A public clone without the index cannot complete this command.

Offline regression tests are retained as reproducibility source files:

```bash
cd engine
python -m unittest discover -s app
cd ..
```

The original delivery records 59 passing tests. That historical count is not a claim that every environment or subsequent change has passed. Test source files are retained; redundant top-level test-result logs and obsolete delivery checksums have been removed. Frozen-run manifests and historical decisions remain unchanged.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `OPENAI_API_KEY is not configured` | Set the variable in the same shell used to start Python. |
| Invalid/unapproved API base URL | Use an allowed HTTPS `/v1` endpoint in the runtime JSON. |
| Provider rejects model or request | Confirm model access and Responses-format support with your provider. |
| Missing/unopenable SQLite database | Restore a compatible local index at the required path. DOI files are not a retrieval database. |
| Frozen input hash or quotation mismatch | Restore the exact original input/index; do not rewrite manifests to conceal the mismatch. |
| Run exists/is frozen | Choose a new name; use `--resume` only for a deliberate continuation of an unfrozen run. |
| Budget guard stops generation | Review the run ledger and actual provider charges before authorizing continuation. |
| Broken links to original PDFs | Historical local paths are provenance; acquire lawful local copies separately. |
| Network timeouts | Inspect the run's recorded failure and retry history before resuming. |

## Reproducibility and interpretation

- Frozen output inspection, integrity verification and new inference answer different questions. A hash match establishes file integrity, not scientific validity.
- Repeated live inference is not guaranteed to be deterministic, even with the same model name and inputs. Preserve model responses, settings and software versions for each replicate.
- The research brief supplies the Co(II)–bipyridine context and a preliminary TEA/TEOA comparison. Literature statistics do not independently establish a catalytic mechanism or document every historical experimental decision.
- Ranking and evidence-assessment scores are ordinal model judgments. Experimental cards retain transfer assumptions, controls, limitations and unresolved review decisions.
- Records can contain original absolute paths. Runtime paths are package-relative, but historical metadata should be reviewed before sharing outside the original research setting.

## Contributing

Use [GitHub issues](https://github.com/ai4cat/TEOA_hypothesis-agent/issues) for reproducible problems or proposals, and pull requests for changes. Include your Python version, command, relevant settings and a redacted error trace. Never attach API keys or publications you are not permitted to redistribute.

Keep changes to software separate from archived scientific records. Add an appropriate regression check when changing behavior; do not modify the frozen run to make tests pass. A production PDF-to-index ingestion workflow is an outstanding reproducibility contribution.

## Citation

When using this software, cite the associated research article once its bibliographic record is available and identify the repository URL and exact release or commit used. No article DOI or archived software DOI is assigned in this README. For the recorded analysis, identify `reviewed_gpt54_repeat1` and its freeze manifest. Cite the underlying publications separately where their findings are used.

## License

The software is distributed under the existing [Apache License 2.0](LICENSE). The license file has been retained unchanged. Third-party publications, extracted text and quotations remain subject to their respective rights and access conditions.
