#!/usr/bin/env python3
"""
Export last 3 months of GitHub activity (commits, PRs, issues) for a user
within the springernature organisation to a CSV file.

Usage: github-activity-export.py <github-username> [output.csv]

Requires the gh CLI to be authenticated: gh auth status
"""

import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

ORG = "springernature"
DAYS_BACK = 90
PER_PAGE = 100


def gh_api(endpoint, extra_headers=None):
    cmd = ["gh", "api", endpoint]
    for header in (extra_headers or []):
        cmd.extend(["--header", header])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def search_pages(url_template, extra_headers=None):
    """Fetch all pages from a GitHub search endpoint."""
    items = []
    page = 1
    while True:
        url = url_template.format(page=page)
        try:
            data = gh_api(url, extra_headers=extra_headers)
        except RuntimeError as e:
            msg = str(e)
            if "rate limit" in msg.lower():
                print("  Rate limited — waiting 60s...", file=sys.stderr)
                time.sleep(60)
                continue
            print(f"  API error: {msg}", file=sys.stderr)
            break

        batch = data.get("items", [])
        items.extend(batch)
        total = data.get("total_count", 0)

        if total > 1000:
            print(
                f"  Warning: {total} results exceed GitHub's 1000-item search cap."
                " Results will be incomplete.",
                file=sys.stderr,
            )

        sys.stderr.write(f"\r  {len(items)}/{min(total, 1000)}")
        sys.stderr.flush()

        if len(batch) < PER_PAGE or len(items) >= min(total, 1000):
            break

        page += 1
        time.sleep(1)  # Stay within the 30 req/min search rate limit

    sys.stderr.write("\n")
    return items


def since_date_str():
    dt = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    return dt.strftime("%Y-%m-%d")


def fetch_commits(username, since):
    q = quote(f"author:{username} org:{ORG} author-date:>={since}", safe="")
    url = f"/search/commits?q={q}&per_page={PER_PAGE}&page={{page}}"
    # Accept header required for the commits search endpoint
    return search_pages(url, extra_headers=["Accept: application/vnd.github.cloak-preview"])


def fetch_prs(username, since):
    q = quote(f"author:{username} org:{ORG} is:pr created:>={since}", safe="")
    url = f"/search/issues?q={q}&per_page={PER_PAGE}&page={{page}}"
    return search_pages(url)


def fetch_issues(username, since):
    q = quote(f"author:{username} org:{ORG} is:issue created:>={since}", safe="")
    url = f"/search/issues?q={q}&per_page={PER_PAGE}&page={{page}}"
    return search_pages(url)


def commit_rows(commits, username):
    rows = []
    for c in commits:
        repo = c.get("repository", {}).get("full_name", "")
        msg = c.get("commit", {}).get("message", "")
        description = msg.split("\n")[0].strip()
        dt = c.get("commit", {}).get("author", {}).get("date", "")
        link = c.get("html_url", "")
        rows.append({
            "username": username,
            "datetime": dt,
            "repo": repo,
            "link": link,
            "description": description,
        })
    return rows


def issue_pr_rows(items, username):
    rows = []
    for item in items:
        repo_url = item.get("repository_url", "")
        repo = repo_url.removeprefix("https://api.github.com/repos/")
        dt = item.get("created_at", "")
        link = item.get("html_url", "")
        title = item.get("title", "")
        rows.append({
            "username": username,
            "datetime": dt,
            "repo": repo,
            "link": link,
            "description": title,
        })
    return rows


def check_gh_installed():
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: gh CLI is not installed or not authenticated.", file=sys.stderr)
        print("Install: https://cli.github.com/", file=sys.stderr)
        print("Auth:    gh auth login", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <github-username> [output.csv]", file=sys.stderr)
        sys.exit(1)

    username = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else f"{username}-github-activity.csv"
    since = since_date_str()

    check_gh_installed()

    print(f"Fetching {ORG} activity for @{username} since {since}...")

    print("Commits:")
    commits = fetch_commits(username, since)
    print(f"  {len(commits)} commits")

    print("Pull requests:")
    prs = fetch_prs(username, since)
    print(f"  {len(prs)} pull requests")

    print("Issues:")
    issues = fetch_issues(username, since)
    print(f"  {len(issues)} issues")

    rows = (
        commit_rows(commits, username)
        + issue_pr_rows(prs, username)
        + issue_pr_rows(issues, username)
    )
    rows.sort(key=lambda r: r["datetime"], reverse=True)

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["username", "datetime", "repo", "link", "description"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} events to {output}")


if __name__ == "__main__":
    main()
