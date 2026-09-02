# Qantly Sales Scout

Scout discovers relevant public job postings, turns their companies into prospects, and supports evidence-based qualification before a human-reviewed outreach process.

## Run locally

From `D:\qantly_sales\scout`:

```powershell
..\venv\Scripts\python.exe manage.py runserver
..\venv\Scripts\celery.exe -A scout worker -l info
```

From `D:\qantly_sales\frontend`:

```powershell
npm run dev
```

Open the dashboard at `http://127.0.0.1:5173`. Use a Django staff account.

## Phase 2 workflow

1. Run discovery and refresh the dashboard when the task completes.
2. In **Qualification queue**, select a prospect, run **Research**, then **Assess**.
3. Review the recorded public sources, confirmed current capabilities, and clearly separate customization gaps.
4. Create a draft only after assessment. Draft generation never sends email.
5. Use Django admin for the existing submit-for-approval, approval, and delivery process.

For a safe bounded qualification backfill:

```powershell
..\venv\Scripts\python.exe manage.py qualify_prospects --status discovered --limit 20
```

The command researches and assesses only; it never creates or sends outreach. See `PHASE2_TASKS.md` for the delivery tracker and guardrails.
