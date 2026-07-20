# Sprint 5 — Data/ML/Database Tasks

## Sprint Goal

Finalise the Data/ML/Database contribution by addressing report feedback, validating the production data pipeline and ML outputs, supporting the final demonstration and interview, and preparing clean release artefacts.

## S5-DATA-01: Revise the Data/ML/Database report sections based on Version 1 feedback

- Review all Version 1 feedback related to data sources, database design, data quality, ML methodology, evaluation and deployment.
- Update the assigned report sections and supporting figures or tables.
- Ensure that metrics, dataset versions, API contracts and technical terminology match the implemented system.
- Record how each relevant feedback item was addressed.

**Definition of done:** All relevant Version 1 feedback has been addressed or documented as not applicable, and the revised sections are ready for team review.

**Deliverable:** Revised Data/ML/Database sections and feedback-resolution notes.

## S5-DATA-02: Verify core Data/ML/Database features and resolve critical issues

- Validate data ingestion, cleaning, transformation and database-loading workflows.
- Verify database schema, migrations, seed data, constraints and API-facing data contracts.
- Check ML model loading, inference, output schema and fallback behaviour.
- Run relevant automated tests and targeted end-to-end checks.
- Confirm reproducibility using the documented setup and deployment process.
- Record defects and resolve all blocker or critical Data/ML/Database issues before external user testing.
- Re-test fixes and save final verification evidence.

**Definition of done:** Core data and ML workflows pass; database and API contracts remain aligned; no blocker or critical Data/ML/Database defect remains open.

**Deliverable:** Test evidence, defect log and validated Data/ML/Database release candidate.

## S5-DATA-03: Prepare and support the Data/ML/Database part of the final demonstration

- Select a concise workflow that demonstrates how source data becomes a user-facing result.
- Prepare stable demonstration data and expected ML/database outputs.
- Verify the demonstration environment, database state and model availability.
- Prepare backup screenshots, outputs or a recording in case the live pipeline fails.
- Rehearse the Data/ML/Database explanation within the allocated speaking time.
- Capture feedback relevant to the Data/ML/Database work.

**Definition of done:** The Data/ML/Database contribution can be clearly demonstrated with stable live and backup materials.

**Deliverable:** Demonstration script, prepared data and backup evidence.

## S5-DATA-04: Prepare for and attend the individual project interview

- Summarise individual Data/ML/Database responsibilities and contributions.
- Review key decisions concerning data selection, data quality, schema design, modelling, evaluation and deployment.
- Prepare evidence such as commits, tests, experiment results, diagrams and documentation.
- Be ready to explain limitations, trade-offs, challenges and lessons learned.
- Attend the scheduled individual interview.

**Definition of done:** The individual contribution and technical reasoning can be clearly explained and supported by evidence.

**Deliverable:** Completed interview and individual preparation notes.

## S5-DATA-05: Revise the Data/ML/Database report sections based on Version 2 feedback

- Review Version 2 feedback relevant to the Data/ML/Database work.
- Update the assigned sections, results, figures, tables and limitations.
- Re-check all reported metrics against final test and evaluation artefacts.
- Resolve inconsistencies with the architecture, backend and frontend sections.
- Complete a final proofread of citations, captions, terminology and formatting.

**Depends on:** Receipt of Version 2 feedback.

**Definition of done:** All relevant Version 2 feedback is addressed and the final Data/ML/Database sections match the released implementation and evidence.

**Deliverable:** Final Data/ML/Database report sections.

## S5-DATA-06: Clean Data/ML/Database files and prepare the final release

- Identify obsolete notebooks, temporary exports, duplicate datasets, generated outputs and superseded model artefacts.
- Confirm obsolete items before removal; retain required reproducibility and assessment evidence.
- Organise source code, migrations, schemas, tests, documentation, model artefacts and approved sample data.
- Remove secrets, credentials, local paths and environment-specific configuration from tracked files.
- Update `.gitignore` for generated data, caches, local environments and large reproducible outputs.
- Update Data/ML/Database documentation with setup, data provenance, pipeline execution, testing and deployment instructions.
- Run the final Data/ML/Database tests from a clean checkout.
- Confirm that required artefacts are included in or retrievable by the final release.

**Depends on:** S5-DATA-02 and S5-DATA-05.

**Definition of done:** The Data/ML/Database area is clean, documented and reproducible from a clean checkout, with no secrets or obsolete release artefacts.

**Deliverable:** Clean Data/ML/Database directories, updated documentation and final verification evidence.

## Recommended Order

1. S5-DATA-01 — Version 1 report revisions
2. S5-DATA-02 — Core verification and critical fixes
3. S5-DATA-03 and S5-DATA-04 — Demonstration and interview preparation
4. S5-DATA-05 — Version 2 report revisions
5. S5-DATA-06 — Clean-up and final release preparation

## Completion Checklist

- [ ] Version 1 Data/ML/Database feedback has been resolved.
- [ ] Data ingestion and transformation workflows have passed verification.
- [ ] Database schema, migrations and contracts have passed verification.
- [ ] ML inference and output contracts have passed verification.
- [ ] No blocker or critical Data/ML/Database defects remain open.
- [ ] Demonstration data and backup materials are ready.
- [ ] Individual interview evidence is ready.
- [ ] Version 2 Data/ML/Database feedback has been resolved.
- [ ] Final reported metrics match the saved evaluation evidence.
- [ ] Data/ML/Database files are clean, documented and reproducible.
