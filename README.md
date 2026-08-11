# Garden City Reports 📬

A GitHub Actions monitor for the five Facebook share links you provided.

## What it does

- Checks all configured links every 30 minutes.
- Saves a fingerprint of the public metadata it can see.
- Sends an email **only when a previously seen page changes**.
- Sends no email when nothing changed.
- The first run creates a baseline and intentionally sends no email.

## Important Facebook limitation

Facebook share links can redirect to pages that require login or otherwise limit automated access. This project only uses information that is publicly returned to the GitHub Actions runner. If Facebook does not expose a post publicly, the monitor cannot read that post.

## Configure email

In GitHub, open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `SMTP_HOST` — your email provider's SMTP server
- `SMTP_PORT` — usually `465` for SMTP over SSL
- `SMTP_USERNAME` — the sending email account
- `SMTP_PASSWORD` — an SMTP/app password for that account
- `ALERT_EMAIL` — the address that should receive alerts

Never put an email password directly in `pages.json`, `monitor.py`, or the workflow file.

## Add or remove pages

Edit `pages.json`, commit the change, and the next scheduled run will use the new list.

## Run it manually

Go to **Actions → Garden City Reports → Run workflow**.

## Files

- `pages.json` — monitored URLs
- `monitor.py` — checker and email sender
- `.github/workflows/monitor.yml` — 30-minute schedule
- `state.json` — automatically generated monitoring state
