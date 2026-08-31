We need to correct and extend the current Scout architecture in the `qantly_sales` repository.

Project:

* Repository: `qantly_sales`
* Django project: `scout`
* Core app: `prospecting`

Scout is intended to be an automated sales prospecting engine for Qantly.

The core requirement is:

> Scout must discover relevant companies and job opportunities automatically from configurable search criteria. The user should NOT have to manually find companies first.

This task must fix the current Greenhouse-centered approach and make the search configuration database-driven so Scout can later expand beyond healthcare/statistics into other industries/domains.

---

# 1. Fix the Greenhouse architecture

Current problem:

The existing Greenhouse implementation depends on:

```env
GREENHOUSE_BOARDS_JSON=[]
```

This means the user has to manually find companies and provide Greenhouse board tokens.

That defeats the main purpose of Scout if it is treated as the primary discovery mechanism.

Do NOT remove the existing Greenhouse support.

Keep:

```python
GreenhouseBoard
GreenhouseJobBoardProvider
greenhouse_boards_from_json()
```

But change its role.

Greenhouse must be treated as:

* an optional provider
* a source-specific ATS adapter
* a development/testing source for explicitly known boards

It must NOT be the main discovery engine.

Document clearly that:

```env
GREENHOUSE_BOARDS_JSON=[]
```

is optional.

Scout should still work even when this remains empty.

---

# 2. Correct target architecture

The intended discovery pipeline is:

```text
SearchProfile
    ↓
Build search queries
    ↓
General public-web/job discovery
    ↓
Discover job URLs and companies automatically
    ↓
Detect ATS/source
    ↓
Use source-specific adapter when available
    ↓
Normalize to DiscoveredJob
    ↓
Parse
    ↓
Deduplicate
    ↓
Create/update Company
    ↓
Create/update JobPosting
    ↓
Later: qualify as Prospect
```

The user should configure WHAT to search for, not WHICH companies to search.

Example:

```text
Search for:
- Biostatisticians
- Statistical Analysts
- Clinical Data Analysts

In:
- USA
- UK
- Canada

Freshness:
- last 7 days
```

Scout should then discover companies itself.

---

# 3. Make search criteria database-driven

Do NOT hard-code domain-specific roles, keywords, skills, methods, industries, or countries in Python.

The current code contains hard-coded values such as:

```python
SKILL_PATTERNS
METHOD_PATTERNS
ANALYTICS_KEYWORDS
```

These should be replaced with database-driven configuration.

The reason:

Scout may later search for completely different domains such as:

* healthcare
* finance
* ecommerce
* SaaS
* manufacturing
* research
* consulting
* education

The application should not require source-code changes when the target domain changes.

---

# 4. Add SearchProfile

Create a model similar to:

```python
SearchProfile
```

Suggested fields:

```text
name
description
is_active
freshness_days
created_at
updated_at
```

A SearchProfile represents one prospecting strategy.

Examples:

```text
Qantly Healthcare Analytics
Financial Analytics
Ecommerce Data Teams
SaaS BI Hiring
```

Do not make this unnecessarily complex.

---

# 5. Add database-driven roles

Create something like:

```python
SearchRole
```

Suggested fields:

```text
search_profile
name
weight
is_active
created_at
```

Example roles for the initial Qantly profile:

```text
Biostatistician
Statistical Analyst
Clinical Data Analyst
Research Analyst
Data Analyst
Epidemiologist
Statistical Programmer
Data Scientist
Quantitative Analyst
```

These must be database records.

Do NOT hard-code them in the query-generation code.

---

# 6. Add database-driven search signals / keywords

Create something like:

```python
SearchSignal
```

or:

```python
SearchKeyword
```

Use whichever naming is clearer.

Suggested fields:

```text
search_profile
value
category
weight
is_active
created_at
```

Suggested categories:

```text
skill
method
software
industry
domain_signal
technology
qualification
```

Example initial values:

```text
SPSS
SAS
Stata
R
Python
SQL
survival analysis
Kaplan-Meier
Cox regression
regression
hypothesis testing
clinical research
clinical trial
machine learning
```

These must be database-driven.

Do not hard-code these values into parsing logic.

---

# 7. Make geography configurable

Countries/regions must also be database-driven or stored as configuration associated with SearchProfile.

Use the simplest clean design.

For example:

```python
SearchLocation
```

with:

```text
search_profile
country
region
is_active
```

Alternatively, a JSON/list field on SearchProfile is acceptable if cleaner for the MVP.

The important part is:

Do NOT hard-code the target countries in Python.

---

# 8. Optional industries

Make industries configurable as well.

This may be:

```python
SearchIndustry
```

or a simple related/config field.

Examples:

```text
Healthcare
Pharmaceutical
CRO
Research
University
Clinical Research
Analytics Consulting
```

Keep the MVP simple.

---

# 9. Initial Qantly SearchProfile

Create an initial database SearchProfile representing the current Qantly use case.

Example:

```text
Name:
Qantly Healthcare & Statistical Analytics
```

Populate it with the initial roles/signals/industries.

Do this using either:

* data migration
* fixture
* management command

Use whichever is cleanest.

Do NOT place these initial values permanently in runtime Python constants.

---

# 10. Query generation

Create a query-generation layer.

Conceptually:

```python
build_search_queries(search_profile)
```

The query builder should read:

```text
roles
signals
locations
industries
freshness settings
```

from the database.

Example output might conceptually resemble:

```text
"Biostatistician" "SPSS" jobs
"Clinical Data Analyst" healthcare jobs
"Statistical Analyst" SAS research
```

Do not generate an excessive Cartesian product of every role × keyword × country.

Keep query generation efficient and configurable.

---

# 11. SearchProvider remains the main abstraction

Keep or improve the existing abstraction:

```python
class SearchProvider(Protocol):
    def search_jobs(self, query: str) -> list[DiscoveredJob]:
        ...
```

This should become the main discovery interface.

Greenhouse should NOT implement the entire discovery strategy.

Suggested structure:

```text
prospecting/
    discovery/
        __init__.py
        schemas.py
        services.py
        query_builder.py

        providers/
            __init__.py
            base.py
            greenhouse.py
            generic_web.py
```

Do not reorganize purely for aesthetics if it adds risk.

But keep provider responsibilities separated.

---

# 12. Build a general public discovery provider

Implement a provider such as:

```python
class PublicWebSearchProvider:
    def search_jobs(self, query: str) -> list[DiscoveredJob]:
        ...
```

Its role is to discover candidate job postings and companies from general search criteria.

Important constraints:

* do not automate LinkedIn login
* do not scrape authenticated LinkedIn pages
* do not use browser automation
* do not use Selenium
* do not use Playwright
* only use publicly accessible/indexed content

If broad public web discovery cannot be implemented reliably without an external search API/provider:

DO NOT fake it.

Instead:

1. build the abstraction cleanly
2. document the limitation
3. add placeholder configuration for a future external search provider
4. keep the current deterministic/test provider usable

Never fabricate discovered companies/jobs.

---

# 13. Source / ATS detection

Add lightweight source detection:

```python
detect_job_source(url)
```

Examples:

```text
Greenhouse → greenhouse
Lever → lever
Ashby → ashby
generic company careers page → generic
```

Handle at minimum:

```text
boards.greenhouse.io
job-boards.greenhouse.io
jobs.lever.co
jobs.ashbyhq.com
```

Greenhouse support already exists.

Do NOT implement full Lever/Ashby integrations unless straightforward.

Source detection should make future adapters easy to add.

---

# 14. Preserve the existing DiscoveredJob schema

All providers should normalize results into:

```python
DiscoveredJob
```

The database ingestion layer should not care whether the source was:

```text
Greenhouse
Lever
Ashby
generic web
future search API
```

This normalization boundary is important.

---

# 15. Preserve the existing ingestion pipeline

The current ingestion code already provides useful functionality including:

* Company creation
* JobPosting creation
* source/source_job_id duplicate detection
* URL duplicate detection
* fuzzy duplicate detection
* parsing
* requirements extraction
* analytics/search signals
* seniority
* department
* parsed timestamp
* status changes

Keep this logic unless there is a clear bug.

Refactor only where necessary to support database-driven SearchProfile signals.

---

# 16. Parsing must use the active SearchProfile

The current parser has hard-coded patterns.

Change it so parsing/matching can receive a SearchProfile.

Conceptually:

```python
parse_job_details(raw_content, search_profile)
```

The parser should compare the job content against the SearchProfile's active signals.

Example:

```text
SearchProfile:
Healthcare Analytics

Signals:
SPSS
SAS
survival analysis
clinical trial
```

If later we create:

```text
SearchProfile:
Financial Analytics
```

the same parser should work with:

```text
risk modeling
Bloomberg
financial forecasting
VaR
Python
```

without modifying Python constants.

---

# 17. Store why a job matched

Where appropriate, store the matched signals with the JobPosting.

The current:

```python
analytics_signals
```

field is too domain-specific if Scout becomes generic.

Rename it to something more general such as:

```python
matched_signals
```

or:

```python
search_signals
```

Preferred:

```python
matched_signals
```

This should contain the SearchProfile signals detected in the job.

If this field is renamed, create the proper migration and update all references/tests.

---

# 18. Consider renaming requirements only if necessary

The existing:

```python
requirements
```

field is acceptable and can remain.

The following are also acceptable:

```text
seniority
department
```

They are generic enough.

---

# 19. Rename two existing models

Rename:

```text
Outreach
→ OutreachEmail
```

Rename:

```text
ProspectActivity
→ ProspectEvent
```

Keep:

```text
Company
JobPosting
Prospect
Contact
```

Reason:

```text
OutreachEmail
```

makes it explicit that this model represents an email lifecycle.

```text
ProspectEvent
```

makes it explicit that the model represents audit/history events.

Update all references across:

* models
* serializers
* views
* services
* admin
* tests
* migrations
* related names where appropriate

Preserve data and behavior.

---

# 20. Keep Prospect and OutreachEmail states separate

Do not collapse them.

`Prospect.status` represents the overall sales opportunity lifecycle.

For example:

```text
discovered
qualified
awaiting_approval
approved
sent
replied
demo
trial
converted
lost
closed
```

`OutreachEmail.status` represents one specific email lifecycle:

```text
draft
awaiting_approval
approved
rejected
sent
failed
```

A Prospect may eventually have multiple OutreachEmail records.

Do not blindly mirror statuses between the two.

---

# 21. Conceptual domain model after this task

The model should conceptually look like:

```text
SearchProfile
    ├── SearchRole
    ├── SearchSignal
    ├── SearchLocation
    └── SearchIndustry

            ↓

        Discovery Run
            ↓

Company
    │
    ├── JobPosting
    │       ↓
    │    Prospect
    │       ├── Contact
    │       ├── OutreachEmail
    │       └── ProspectEvent
```

A dedicated `DiscoveryRun` model is optional for this task.

If adding it would materially improve auditability, add a minimal model.

Otherwise leave it for later.

Do not over-engineer.

---

# 22. Admin support

Register the new SearchProfile-related models in Django admin.

The admin should make it practical to:

* create SearchProfiles
* activate/deactivate them
* edit roles
* edit signals
* edit locations
* edit industries

Use simple inline admin where helpful.

Do not build a custom React configuration UI yet unless one already exists.

---

# 23. API support

Expose SearchProfile configuration through DRF only if it fits cleanly with the current API.

At minimum, support:

```text
list
retrieve
create
update
activate/deactivate
```

for SearchProfile.

Related roles/signals may either:

* have their own endpoints
* or be managed through nested/simple serializers

Prefer the least complex implementation.

---

# 24. Tests

Keep all existing tests.

Improve broad assertions such as:

```python
with self.assertRaises(Exception):
```

Use specific exceptions:

```python
IntegrityError
ValidationError
```

Add tests for:

* SearchProfile creation
* SearchRole creation
* SearchSignal creation
* SearchLocation/configuration
* SearchIndustry/configuration
* query generation from database values
* inactive roles/signals are excluded
* Greenhouse JSON is optional
* Scout works when `GREENHOUSE_BOARDS_JSON=[]`
* source detection
* Greenhouse normalization
* generic DiscoveredJob ingestion
* duplicate source_job_id protection
* duplicate URL protection
* fuzzy duplicate behavior
* parsing based on SearchProfile signals
* matched_signals storage
* OutreachEmail approval flow
* ProspectEvent creation
* cross-company validation
* authentication requirements

Do not weaken existing tests.

---

# 25. Environment configuration

Keep:

```env
GREENHOUSE_BOARDS_JSON=[]
```

but change the comments in `.env.example` to make clear that it is optional.

For example:

```env
# Optional: explicitly configured Greenhouse boards for development,
# testing, or monitoring known companies.
# General Scout discovery must not depend on this.
GREENHOUSE_BOARDS_JSON=[]
```

If a general search provider requires future credentials, add empty placeholders such as:

```env
SEARCH_PROVIDER=
SEARCH_API_KEY=
```

Only if actually required by the architecture.

Do not commit secrets.

---

# 26. Do not add LangGraph yet

Do NOT add LangGraph orchestration as part of this task.

We first need deterministic discovery to work properly.

Current order:

```text
SearchProfile
→ query generation
→ discovery
→ source detection
→ normalization
→ parsing
→ deduplication
→ persistence
```

Once this works reliably, the next phase will be:

```text
qualification
→ Qantly fit scoring
→ company research
→ contact discovery
→ outreach generation
→ LangGraph orchestration
```

---

# 27. Do not add unnecessary infrastructure

Do not add:

* Selenium
* Playwright
* LinkedIn login automation
* LinkedIn scraping
* vector database
* complex multi-agent system
* extra Django apps without need
* AI browser agents
* autonomous cold email sending
* excessive provider integrations

Keep Scout as a focused MVP.

---

# 28. Key product requirement

The completed system should be moving toward this behavior:

The user chooses:

```text
SearchProfile:
Qantly Healthcare & Statistical Analytics
```

Scout reads the database and sees:

```text
Roles:
Biostatistician
Clinical Data Analyst
Statistical Analyst
Epidemiologist

Signals:
SPSS
SAS
R
Stata
survival analysis
regression
clinical trial

Locations:
USA
UK
Canada

Freshness:
7 days
```

Scout then searches for relevant jobs and companies automatically.

The user should NOT have to first supply:

```text
Company A
Company B
Company C
```

or Greenhouse board tokens.

That manual company discovery is exactly what Scout is supposed to eliminate.

---

# 29. Keep it domain-agnostic

The architecture must support future SearchProfiles such as:

```text
Qantly Healthcare Analytics
Finance Analytics
Ecommerce Analytics
SaaS Analytics
Market Research
Manufacturing Data Teams
```

without changing the source code.

Only the database configuration should need to change.

---

# 30. Final validation

Before finishing this task:

1. Review the current repository before making changes.
2. Preserve working behavior wherever possible.
3. Create proper Django migrations.
4. Run `makemigrations`.
5. Run `migrate`.
6. Run `python manage.py check`.
7. Run the full Django test suite.
8. Fix all failures.
9. Confirm `GREENHOUSE_BOARDS_JSON=[]` does not break the app.
10. Confirm query generation uses database SearchProfile values.
11. Confirm no domain-specific search keywords remain hard-coded in runtime discovery/parsing code unless they are truly generic technical constants.
12. Summarize what was changed.
13. Explicitly state whether broad general-web discovery currently requires an external search API/provider.
14. Do not claim general web discovery works if only an interface/stub exists.

The main architectural rule is:

> Scout must be driven by search intent stored in the database, not by manually supplied companies and not by hard-coded domain keywords.
