"""Refresh the profile showcase.

Public repositories are listed by name. Private repositories contribute only
to the totals drawn on the stats image. A STATS_TOKEN secret is required for
those totals and for organization repositories the public API cannot see.
"""

import html
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

README = "README.md"
START = "<!-- SHOWCASE:START -->"
END = "<!-- SHOWCASE:END -->"
USERNAME = os.environ.get("GH_USERNAME", "uiber3015")
PUBLIC_ORGS = ("DeepCodingInTuringAcademy", "UIBER2023")
WIDTH = 840
BAR = 776
LANG_COLOR = {
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "C++": "#f34b7d",
    "TypeScript": "#3178c6",
    "Shell": "#89e051",
    "JavaScript": "#f1e05a",
    "CSS": "#563d7c",
    "C": "#555555",
    "CMake": "#DA3434",
    "Batchfile": "#C1F12E",
}
BLURBS = {
    "uiber3015/BioTRACE": "从生物医学论文表格抽取知识链",
    "uiber3015/EduInteractivateGame": "教育互动游戏",
    "uiber3015/EducationalSeriousGame_Demo": "教育游戏的网页演示",
    "UIBER2023/FinanceAI": "NLPCC 2026 金融共享任务",
    "UIBER2023/CycleGAN-Photo2Monet": "照片转 Monet 风格的课程项目",
    "DeepCodingInTuringAcademy/Habbit": "C++ 桌面时间管理",
    "DeepCodingInTuringAcademy/Minesweeper": "扫雷",
}
ORG_BLURBS = {
    "DeepCodingInTuringAcademy": "桌面小程序",
    "UIBER2023": "竞赛和课程项目",
}
FONT = "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"


def api(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response), response.headers.get("Link") or ""
    except urllib.error.HTTPError as error:
        if error.code in {404, 409}:
            return {}, ""
        detail = error.read().decode("utf-8", "replace")
        raise SystemExit(f"GitHub API {error.code}: {url}\n{detail}") from error


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


def size(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f} MB"
    if num >= 1_000:
        return f"{num / 1_000:.1f} KB"
    return f"{num} B"


def keep(repo):
    return (
        not repo.get("fork")
        and repo.get("name") not in {".github", USERNAME}
        and (repo.get("language") or repo.get("stargazers_count") or repo.get("description"))
    )


def load_repos(token):
    if token:
        repos = paginate(
            "https://api.github.com/user/repos?affiliation=owner,organization_member&per_page=100",
            token,
        )
        return [repo for repo in repos if keep(repo)]

    repos = paginate(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner",
        "",
    )
    for org in PUBLIC_ORGS:
        repos.extend(
            paginate(f"https://api.github.com/orgs/{org}/repos?per_page=100&type=public", "")
        )
    return [repo for repo in repos if keep(repo) and not repo.get("private")]


def languages(repos, token):
    totals = {}
    for repo in repos:
        data, _ = api(repo["languages_url"], token)
        if not isinstance(data, dict):
            continue
        for name, count in data.items():
            totals[name] = totals.get(name, 0) + count
    return totals


def ranked_languages(totals):
    total = sum(totals.values())
    ranked = []
    for name, count in sorted(totals.items(), key=lambda item: item[1], reverse=True):
        pct = (count / total * 100) if total else 0
        if pct < 1:
            continue
        ranked.append((name, pct, LANG_COLOR.get(name, "#8b949e")))
    return ranked, total


def esc(text):
    return html.escape(str(text), quote=True)


def card_svg(groups, theme):
    dark = theme == "dark"
    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    title = "#8b949e" if dark else "#656d76"
    value = "#e6edf3" if dark else "#1f2328"
    track = "#21262d" if dark else "#eaeef2"
    height = 36 + len(groups) * 132
    label = "，".join(
        f"{group['title']}仓库 {group['repos']} 个，{group['stars']} 个 Star，代码 {group['code']}"
        for group in groups
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{esc(label)}">',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="16" fill="{bg}" stroke="{border}"/>',
    ]
    for index, group in enumerate(groups):
        y = 28 + index * 132
        clip = f"bar{index}"
        parts.append(
            f'<text x="32" y="{y + 8}" fill="{title}" font-size="14" font-family="{FONT}">{esc(group["title"])}</text>'
        )
        for column, (number, caption) in enumerate(
            ((group["repos"], "仓库"), (group["stars"], "Star"), (group["code"], "代码量"))
        ):
            x = 32 + column * 210
            parts.append(
                f'<text x="{x}" y="{y + 52}" fill="{value}" font-size="32" font-weight="650" font-family="{FONT}">{esc(number)}</text>'
            )
            parts.append(
                f'<text x="{x}" y="{y + 74}" fill="{title}" font-size="13" font-family="{FONT}">{caption}</text>'
            )
        bar_y = y + 94
        parts.append(f'<clipPath id="{clip}"><rect x="32" y="{bar_y}" width="{BAR}" height="8" rx="4"/></clipPath>')
        parts.append(f'<rect x="32" y="{bar_y}" width="{BAR}" height="8" rx="4" fill="{track}"/>')
        parts.append(f'<g clip-path="url(#{clip})">')
        cursor = 32
        for _name, pct, color in group["languages"]:
            segment = round(BAR * pct / 100)
            if segment <= 0:
                continue
            parts.append(f'<rect x="{cursor}" y="{bar_y}" width="{segment}" height="8" fill="{color}"/>')
            cursor += segment
        parts.append("</g>")
        legend_x = 32
        for name, pct, color in group["languages"]:
            parts.append(f'<circle cx="{legend_x + 4}" cy="{bar_y + 28}" r="4" fill="{color}"/>')
            caption = f"{name} {pct:.1f}%"
            parts.append(
                f'<text x="{legend_x + 14}" y="{bar_y + 32}" fill="{title}" font-size="13" font-family="{FONT}">{esc(caption)}</text>'
            )
            legend_x += 14 + int(len(caption) * 7.2) + 22
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def write_cards(groups):
    os.makedirs("assets", exist_ok=True)
    for theme in ("light", "dark"):
        name = "assets/stats.svg" if theme == "light" else "assets/stats-dark.svg"
        with open(name, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(card_svg(groups, theme))


def blurb(repo):
    text = (repo.get("description") or "").strip()
    if text:
        return text.replace("|", "/")
    preset = BLURBS.get(repo["full_name"])
    if preset:
        return preset
    language = repo.get("language") or "代码"
    return f"{language} 项目"


def project_rows(repos):
    ranked = sorted(
        repos,
        key=lambda repo: (-repo.get("stargazers_count", 0), repo["full_name"].lower()),
    )
    rows = ["| 项目 | 内容 |", "| --- | --- |"]
    for repo in ranked:
        name = repo["name"].replace("|", "/")
        stars = repo.get("stargazers_count", 0)
        detail = blurb(repo)
        if stars:
            detail = f"{detail} · {stars} Star"
        rows.append(f"| [{name}]({repo['html_url']}) | {detail} |")
    if len(rows) == 2:
        rows.append("| 暂无 |  |")
    return rows


def org_rows(repos):
    owners = []
    seen = set()
    for repo in repos:
        owner = repo.get("owner") or {}
        login = owner.get("login") or ""
        if owner.get("type") != "Organization" or login in seen:
            continue
        seen.add(login)
        owners.append(login)
    if not owners:
        return ["暂无组织仓库。"]
    return [
        f"- [{login}](https://github.com/{login})：{ORG_BLURBS.get(login, '组织项目')}"
        for login in owners
    ]


def group_from(title, repos, token):
    totals = languages(repos, token)
    ranked, total = ranked_languages(totals)
    return {
        "title": title,
        "repos": str(len(repos)),
        "stars": str(sum(repo.get("stargazers_count", 0) for repo in repos)),
        "code": size(total),
        "languages": ranked,
    }


def main():
    token = os.environ.get("STATS_TOKEN", "").strip()
    repos = load_repos(token)
    public = [repo for repo in repos if not repo.get("private")]
    private = [repo for repo in repos if repo.get("private")]
    groups = [group_from("公开", public, token)]
    if token:
        groups.append(group_from("私有", private, token))
    write_cards(groups)

    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    body = [
        "<p align=\"center\">",
        "  <picture>",
        "    <source media=\"(prefers-color-scheme: dark)\" srcset=\"assets/stats-dark.svg\">",
        "    <img alt=\"仓库统计\" src=\"assets/stats.svg\">",
        "  </picture>",
        "</p>",
        "",
        "## 公开项目",
        "",
        *project_rows(public),
        "",
        "## 组织",
        "",
        *org_rows(public),
        "",
        f"<!-- updated {today} -->",
    ]
    block = START + "\n" + "\n".join(body) + "\n" + END + "\n"
    with open(README, encoding="utf-8") as handle:
        text = handle.read()
    begin = text.find(START)
    finish = text.find(END)
    if begin == -1 or finish == -1 or finish < begin:
        raise SystemExit("README.md 里没有展示标记。")
    updated = text[:begin] + block + text[finish + len(END) :]
    if not updated.endswith("\n"):
        updated += "\n"
    with open(README, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)
    print(f"public={len(public)} private={len(private)} token={'yes' if token else 'no'}")


if __name__ == "__main__":
    main()
