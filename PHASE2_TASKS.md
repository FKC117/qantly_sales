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
- [ ] Keep approval mandatory and add generation tests

## Phase 2G–L — Product workflow and verification

- [ ] Add prospect qualification API actions and detail serialization
- [ ] Add admin support and React prospect review screens
- [ ] Add safe batch qualification
- [ ] Verify delivery, audit behavior, discovery compatibility, and documentation

## Guardrails

- Never fabricate research, contacts, evidence URLs, or Qantly capabilities.
- Potential customization is never presented as an existing Qantly feature.
- No LinkedIn login/scraping, browser automation, LangGraph, CRM integration, or autonomous sending.
