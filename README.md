# SurveyQA Autopilot + AI Notary

[![Get Starter ($49)](https://img.shields.io/badge/Starter_License-Lava.top_%2449-10b981?style=for-the-badge)](https://app.lava.top/products/5c686e06-3d47-4f87-99ad-3c3c0e1526a3) [![Get Pro SPSS+PDF ($199)](https://img.shields.io/badge/Pro_(SPSS_%2B_PDF)-Lava.top_%24199-8b5cf6?style=for-the-badge)](https://app.lava.top/products/723f8cbd-ff84-4d4a-aa30-83c15cf46400) [![Live Interactive Stand](https://img.shields.io/badge/Live_Demo-Interactive_Stand-38bdf8?style=for-the-badge)](https://apumiaaifund.github.io/surveyqa-autopilot/)

[![Get Starter ($49)](https://img.shields.io/badge/Starter_License-Lava.top_%2449-10b981?style=for-the-badge)](https://app.lava.top/products/5c686e06-3d47-4f87-99ad-3c3c0e1526a3) [![Get Pro SPSS+PDF ($199)](https://img.shields.io/badge/Pro_(SPSS_%2B_PDF)-Lava.top_%24199-8b5cf6?style=for-the-badge)](https://app.lava.top/products/723f8cbd-ff84-4d4a-aa30-83c15cf46400) [![Live Interactive Stand](https://img.shields.io/badge/Live_Demo-Interactive_Stand-38bdf8?style=for-the-badge)](https://apumiaaifund.github.io/surveyqa-autopilot/)

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
          notary_api_url: 'https://ainotary-edge.apumia-notary.workers.dev/v1/stamp'
          notary_api_key: ${{ secrets.NOTARY_API_KEY }}
```

## What It Verifies
- **Deterministic Quota Math:** Extracts target quotas from `.docx` specs and verifies actual/simulated distributions using exact `Decimal` arithmetic (`±2.5%` tolerance).
- **Pre-Launch Synthetic Simulation:** Simulates `N=500` respondents across your `.xml` survey script and runs Chi-square uniformity tests on randomized blocks.
- **Tamper-Proof Certification:** Generates a SHA-256 hash of your spec, survey script, and audit report, stamping an immutable timestamp certificate via **AI Notary**.
