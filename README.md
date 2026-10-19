# Fortnite-hub

## Complete hub setup

Run `pip install -r requirements.txt`, then `gunicorn app:app`.
Run the isolated test suite with `python -m unittest discover -s tests -v`.

Production environment:

- `SECRET_KEY`: stable random session secret.
- `FORTNITE_API_KEY`: required for authenticated player statistics and any restricted API endpoints.
- `DATABASE_PATH`: path on a persistent Render disk (for example `/var/data/fortnite_hub.db`). Without a persistent disk, accounts and favorites can disappear after a deployment. The current default remains `fortnite_hub.db` to preserve existing installations; do not change paths without copying the database first.
- `CRON_SECRET`: same random secret in Render and GitHub Actions; the scheduled workflow calls the deployed app using the `X-Cron-Secret` header.
- `RESEND_API_KEY` and `RESEND_FROM_EMAIL`: configure a verified sender for production email delivery. Each user must opt in on the Notifications page.

The tracker runs against the web server database, includes bundle contents, and records successful alerts per user/item/shop date to prevent repeated sends. No email credentials or live API calls are needed for tests. As with most email providers, a process failure between delivery and writing the log can still cause a duplicate on retry.

Players require public account statistics. New cosmetics are API additions, not confirmed release dates. The map provides POIs, not chest positions. A 3D viewer is not included because the current data source does not supply usable character models.
