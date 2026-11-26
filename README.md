# SurveyQA Autopilot + AI Notary

**100% Automated Survey Math, Quota Verification & Cryptographic SHA-256 Proof for GitHub.**

Run deterministic survey QA inside your GitHub Actions on every Pull Request and data export — zero external servers, zero respondent PII leaves your repository.

## Quick Start (`.github/workflows/surveyqa.yml`)

```yaml
name: SurveyQA + AI Notary Gate
on: [pull_request, push]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: apumiaaifund/surveyqa-autopilot@v1
        with:
          spec_path: 'specs/questionnaire.docx'
          survey_path: 'surveys/survey.xml'
          notary_api_url: 'https://ainotary.io'
          notary_api_key: ${{ secrets.NOTARY_API_KEY }}
```

## What It Verifies
- **Deterministic Quota Math:** Extracts target quotas from `.docx` specs and verifies actual/simulated distributions using exact `Decimal` arithmetic (`±2.5%` tolerance).
- **Pre-Launch Synthetic Simulation:** Simulates `N=500` respondents across your `.xml` survey script and runs Chi-square uniformity tests on randomized blocks.
- **Tamper-Proof Certification:** Generates a SHA-256 hash of your spec, survey script, and audit report, stamping an immutable timestamp certificate via **AI Notary**.
