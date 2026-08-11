import hashlib
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from html import unescape
from urllib.parse import urljoin
from urllib.request import Request, urlopen

STATE_FILE = "state.json"
PAGES_FILE = "pages.json"
USER_AGENT = "GardenCityReports/1.0 (+https://github.com/b3434474-art/Garden-city-reports)"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_page(url):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        final_url = response.geturl()
        content_type = response.headers.get("content-type", "")
        body = response.read(2_000_000).decode("utf-8", errors="ignore")
    return final_url, content_type, body


def meta_value(html, name):
    needle = f'property="{name}"'
    needle2 = f'name="{name}"'
    lower = html.lower()
    for marker in (needle.lower(), needle2.lower()):
        pos = lower.find(marker)
        if pos == -1:
            continue
        tag_start = lower.rfind("<meta", 0, pos)
        tag_end = lower.find(">", pos)
        if tag_start == -1 or tag_end == -1:
            continue
        tag = html[tag_start:tag_end + 1]
        tag_lower = tag.lower()
        content_pos = tag_lower.find("content=")
        if content_pos == -1:
            continue
        quote = tag[content_pos + 8:].lstrip()[:1]
        if quote in ('"', "'"):
            rest = tag[content_pos + 8:].lstrip()[1:]
            end = rest.find(quote)
            if end >= 0:
                return unescape(rest[:end]).strip()
    return ""


def title_value(html):
    lower = html.lower()
    start = lower.find("<title")
    if start == -1:
        return ""
    start = lower.find(">", start)
    end = lower.find("</title>", start)
    if start == -1 or end == -1:
        return ""
    return unescape(html[start + 1:end]).strip()


def clean_text(text):
    return " ".join(text.replace("\n", " ").replace("\r", " ").split())


def describe(url):
    try:
        final_url, content_type, html = fetch_page(url)
        title = meta_value(html, "og:title") or title_value(html)
        description = meta_value(html, "og:description") or meta_value(html, "description")
        canonical = meta_value(html, "og:url") or final_url
        # Keep only stable public metadata. Facebook may require login or return a challenge page.
        fingerprint_source = "\n".join([canonical, title, description])
        fingerprint = hashlib.sha256(fingerprint_source.encode()).hexdigest()
        blocked = any(x in html.lower() for x in ["log in to facebook", "you must log in", "checkpoint"])
        return {
            "url": url,
            "final_url": final_url,
            "title": clean_text(title)[:300],
            "description": clean_text(description)[:1000],
            "fingerprint": fingerprint,
            "blocked": blocked,
            "content_type": content_type,
        }, None
    except Exception as exc:
        return None, str(exc)


def send_email(items):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["ALERT_EMAIL"]

    lines = ["Garden City Reports detected a change/new public page state:", ""]
    for item in items:
        lines.append(f"Page: {item['url']}")
        lines.append(f"Title: {item['title'] or '(no title found)'}")
        if item["description"]:
            lines.append(f"Description: {item['description']}")
        lines.append(f"Link: {item['final_url']}")
        lines.append("")

    message = EmailMessage()
    message["From"] = username
    message["To"] = recipient
    message["Subject"] = f"Garden City Reports: {len(items)} page change(s)"
    message.set_content("\n".join(lines))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
        server.login(username, password)
        server.send_message(message)


def main():
    config = load_json(PAGES_FILE, {"pages": []})
    state = load_json(STATE_FILE, {})
    new_state = dict(state)
    changes = []
    errors = []

    for url in config.get("pages", []):
        result, error = describe(url)
        if error:
            errors.append(f"{url}: {error}")
            continue

        old = state.get(url, {}).get("fingerprint")
        new_state[url] = result

        # First run creates a baseline and deliberately sends NO email.
        if old is not None and old != result["fingerprint"]:
            changes.append(result)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(new_state, f, indent=2, ensure_ascii=False)

    if changes:
        send_email(changes)
        print(f"Detected {len(changes)} change(s); email sent.")
    else:
        print("No new changes detected; no email sent.")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(error)


if __name__ == "__main__":
    main()
