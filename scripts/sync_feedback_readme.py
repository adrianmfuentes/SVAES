#!/usr/bin/env python3
"""Sync published user feedback (name, rating, comment — never email) into the
README between the FEEDBACK:START / FEEDBACK:END markers. Run by
.github/workflows/feedback-sync.yml.
"""
import json
import os
import re
import sys
import urllib.request

README_PATH = os.environ.get("README_PATH", "README.md")
MAX_ENTRIES = 12
MAX_COMMENT_LEN = 240

START_MARKER = "<!-- FEEDBACK:START -->"
END_MARKER = "<!-- FEEDBACK:END -->"

EMPTY_MESSAGE = (
    "_Todavía no hay feedback publicado. "
    "Sé el primero en dejar tu opinión desde la landing page._"
)


def fetch_feedback(api_url: str, sync_key: str) -> list[dict]:
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/v1/feedback/public",
        headers={"X-Feedback-Sync-Key": sync_key},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def stars(rating: int) -> str:
    rating = max(0, min(5, rating))
    return "★" * rating + "☆" * (5 - rating)


def sanitize(text: str) -> str:
    text = " ".join(text.split())
    if len(text) > MAX_COMMENT_LEN:
        text = text[: MAX_COMMENT_LEN - 1].rstrip() + "…"
    return text.replace("|", "/").replace("`", "'")


def render(entries: list[dict]) -> str:
    if not entries:
        return EMPTY_MESSAGE

    lines = []
    for entry in entries[:MAX_ENTRIES]:
        comment = sanitize(entry["comments"])
        name = sanitize(entry["name"]) or "Anónimo"
        lines.append(f'> {stars(entry["rating"])} "{comment}"')
        lines.append(f"> — {name}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> None:
    api_url = os.environ["FEEDBACK_API_URL"]
    sync_key = os.environ["FEEDBACK_SYNC_KEY"]

    entries = fetch_feedback(api_url, sync_key)
    block = render(entries)

    with open(README_PATH, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if not pattern.search(content):
        print(f"Markers not found in {README_PATH}", file=sys.stderr)
        sys.exit(1)

    new_content = pattern.sub(f"{START_MARKER}\n{block}\n{END_MARKER}", content, count=1)

    if new_content == content:
        print("No changes to feedback section.")
        return

    with open(README_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)
    print(f"Updated {min(len(entries), MAX_ENTRIES)} feedback entries in {README_PATH}.")


if __name__ == "__main__":
    main()
