# Qantly Sales — Phase 2 Tracker

Phase 2 extends Scout from discovery/relevance into evidence-based sales qualification and human-approved outreach. It preserves the existing discovery, relevance, approval, and delivery workflows.

## Phase 2A — Models and migrations

- [x] Inspect existing Prospect, JobPosting, Contact, OutreachEmail, and ProspectEvent models
- [x] Add ProspectResearch
- [x] Add ProspectAssessment
- [x] Add score validation, controlled account/classification/CTA choices, and audit event types
- [x] Create and apply migration
- [x] Add model tests

## Phase 2B — Public research

- [x] Add research schemas and provider abstraction
- [x] Implement cached public-evidence research with forced refresh
- [x] Store evidence URLs and confidence without fabricated facts
- [x] Add research tests

## Phase 2C–D — Capability comparison and strategic assessment

- [x] Load active QantlyCapability records dynamically
- [x] Separate current Qantly match from customization gaps
- [x] Store five independent strategic scores, account type, classification, reasons, and CTA
- [x] Add claim-safety tests
- [x] Add strategic-assessment tests

## Phase 2E–F — Sales strategy and outreach drafts

- [x] Add account-type strategy selection
- [x] Generate evidence-based, draft-only OutreachEmail records
- [x] Keep approval mandatory and add generation tests

## Phase 2G–L — Product workflow and verification

- [x] Add prospect qualification API actions and detail serialization
- [x] Add admin support
- [x] Add React prospect review screens
- [x] Add safe batch qualification
- [x] Verify delivery, audit behavior, discovery compatibility, and documentation

## Guardrails

- Never fabricate research, contacts, evidence URLs, or Qantly capabilities.
- Potential customization is never presented as an existing Qantly feature.
- No LinkedIn login/scraping, browser automation, LangGraph, CRM integration, or autonomous sending.

## Operating the workflow

1. Run discovery from the Scout dashboard after starting Celery.
2. Open the **Qualification queue**, select a prospect, then use **Research** and **Assess**. Research records only stored public URLs; assessment is deterministic and evidence-based.
3. Use **Create draft** only after assessment. It creates an `OutreachEmail` in `draft` status and never sends mail.
4. Review/edit the draft and submit/approve it in Django admin. Only approved outreach can be sent by the existing delivery workflow.
5. For a bounded backfill, run `python manage.py qualify_prospects --status discovered --limit 20`. It only researches/assesses and explicitly never creates or sends an email. Add `--force` to refresh cached research.
