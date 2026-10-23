"""Refresh the two profile stat cards.

Public numbers come from the GitHub API. Private numbers come from the API
when STATS_TOKEN is set, and otherwise from assets/private.json. The README
project list is not rewritten.
"""

import json
import os
import urllib.error
import urllib.request

USERNAME = os.environ.get("GH_USERNAME", "uiber3015")
PUBLIC_ORGS = ("DeepCodingInTuringAcademy", "UIBER2023")
SKIP_NAMES = {".github", USERNAME, "uibe3015", "uiber3015"}
LANG_COLOR = {
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "C++": "#f34b7d",
    "TypeScript": "#3178c6",
    "Shell": "#89e051",
    "Vue": "#41b883",
    "JavaScript": "#f1e05a",
    "CSS": "#563d7c",
    "SQL": "#e38c00",
}
FONT = "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
CARD_W = 424
CARD_H = 292
GAP = 32
WIDTH = CARD_W * 2 + GAP
HEIGHT = CARD_H


def api(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:
        return json.load(response), response.headers.get("Link") or ""


def paginate(url, token):
    items = []
    while url:
        page, link = api(url, token)
        if not isinstance(page, list):
            break
        items.extend(page)
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part[part.find("<") + 1 : part.find(">")]
    return items


def keep(repo):
    return not repo.get("fork") and repo.get("name") not in SKIP_NAMES


def languages(repos, token):
    totals = {}
    for repo in repos:
        try:
            data, _ = api(repo["languages_url"], token)
        except urllib.error.HTTPError:
            continue
        if not isinstance(data, dict):
            continue
        for name, count in data.items():
            totals[name] = totals.get(name, 0) + count
    return totals


def group_from_repos(title, repos, token):
    code = languages(repos, token)
    ranked = {
        name: count
        for name, count in sorted(code.items(), key=lambda item: item[1], reverse=True)
        if sum(code.values()) and count / sum(code.values()) >= 0.01
    }
    return {
        "title": title,
        "repos": len(repos),
        "stars": sum(repo.get("stargazers_count", 0) for repo in repos),
        "bytes": sum(code.values()),
        "languages": ranked,
    }


def load_public(token):
    try:
        if token:
            repos = paginate(
                "https://api.github.com/user/repos?affiliation=owner,organization_member&per_page=100",
                token,
            )
        else:
            repos = paginate(
                f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner",
                "",
            )
            for org in PUBLIC_ORGS:
                repos.extend(
                    paginate(
                        f"https://api.github.com/orgs/{org}/repos?per_page=100&type=public",
                        "",
                    )
                )
        selected = [repo for repo in repos if keep(repo) and not repo.get("private")]
        return group_from_repos("公开", selected, token)
    except urllib.error.HTTPError as error:
        print(f"public api skipped: {error.code}")
        with open("assets/public.json", encoding="utf-8") as handle:
            return json.load(handle)


def load_private(token):
    if not token:
        with open("assets/private.json", encoding="utf-8") as handle:
            return json.load(handle)
    repos = paginate(
        "https://api.github.com/user/repos?affiliation=owner,organization_member&per_page=100",
        token,
    )
    selected = [repo for repo in repos if keep(repo) and repo.get("private")]
    group = group_from_repos("私有", selected, token)
    with open("assets/private.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(group, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return group


def size(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f} MB"
    if num >= 1_000:
        return f"{num / 1_000:.1f} KB"
    return f"{num} B"


def summary(group):
    parts = [f"{group['repos']} 个仓库"]
    if group.get("stars") is not None:
        parts.append(f"{group['stars']} Star")
    parts.append(size(group["bytes"]))
    return " · ".join(parts)


def ranked(group):
    total = group.get("bytes") or sum(group["languages"].values()) or 1
    rows = []
    for name, count in group["languages"].items():
        pct = count / total * 100
        if pct < 1:
            continue
        rows.append((name, pct, LANG_COLOR.get(name, "#8b949e")))
    return rows[:5]


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def card_svg(groups, theme):
    dark = theme == "dark"
    page = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    title = "#e6edf3" if dark else "#1f2328"
    muted = "#8b949e" if dark else "#656d76"
    track = "#21262d" if dark else "#eaeef2"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{page}"/>',
    ]
    for index, group in enumerate(groups):
        x = index * (CARD_W + GAP)
        parts.append(
            f'<rect x="{x + 0.5}" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="16" fill="{page}" stroke="{border}"/>'
        )
        parts.append(
            f'<text x="{x + 28}" y="40" fill="{title}" font-size="18" font-weight="600" font-family="{FONT}">{esc(group["title"])}</text>'
        )
        parts.append(
            f'<text x="{x + 28}" y="66" fill="{muted}" font-size="13" font-family="{FONT}">{esc(summary(group))}</text>'
        )
        bar_width = CARD_W - 56
        for row, (name, pct, color) in enumerate(ranked(group)):
            y = 102 + row * 36
            parts.append(
                f'<text x="{x + 28}" y="{y}" fill="{title}" font-size="13" font-family="{FONT}">{esc(name)}</text>'
            )
            parts.append(
                f'<text x="{x + CARD_W - 28}" y="{y}" fill="{muted}" font-size="13" font-family="{FONT}" text-anchor="end">{pct:.1f}%</text>'
            )
            bar_y = y + 8
            parts.append(
                f'<rect x="{x + 28}" y="{bar_y}" width="{bar_width}" height="8" rx="4" fill="{track}"/>'
            )
            fill = max(4, round(bar_width * pct / 100))
            parts.append(
                f'<rect x="{x + 28}" y="{bar_y}" width="{fill}" height="8" rx="4" fill="{color}"/>'
            )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    token = os.environ.get("STATS_TOKEN", "").strip()
    groups = [load_public(token), load_private(token)]
    os.makedirs("assets", exist_ok=True)
    for theme, name in (("light", "assets/stats.svg"), ("dark", "assets/stats-dark.svg")):
        with open(name, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(card_svg(groups, theme))
    print(" ".join(f"{group['title']}={group['repos']}" for group in groups))


if __name__ == "__main__":
    main()
