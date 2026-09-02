# Scout deployment checklist

Use a production host with PostgreSQL, Redis, Gunicorn, Nginx, a Celery worker, and Celery Beat.

## Required processes

Run Django through Gunicorn (replace the path and module for the host):

```bash
gunicorn --chdir /srv/qantly_sales/scout scout.wsgi:application --bind 127.0.0.1:8000 --workers 3
celery -A scout worker --loglevel=INFO
celery -A scout beat --loglevel=INFO
```

Nginx should terminate TLS, serve the React build from `frontend/dist`, proxy `/api/` to Gunicorn, and set the production allowed/CSRF origins.

## Before launch

- Set `DJANGO_DEBUG=False` and a unique `DJANGO_SECRET_KEY`.
- Set `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS`, and `DJANGO_CSRF_TRUSTED_ORIGINS` to real HTTPS domains.
- Use managed PostgreSQL backups and a password-protected Redis instance.
- Run migrations, `python manage.py check --deploy`, and `npm run build`.
- Confirm the Celery worker and Beat have distinct supervised services and persist logs.
- Test one approval and SMTP delivery using a real internal recipient before any customer outreach.

## Operational limits

Keep discovery schedules and provider rate limits conservative. Review provider errors in task results, review every email before approval, and never configure automatic approval or automatic sending.
