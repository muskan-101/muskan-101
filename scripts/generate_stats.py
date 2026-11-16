"""Generate dark/pink GitHub stat cards (SVG) for a profile README.

Uses only the public GitHub REST API and the standard library.
Set GITHUB_TOKEN to avoid rate limits (the Actions workflow does this).
"""
import json, os, urllib.request, urllib.parse
from html import escape

USER = os.environ.get("GH_USER", "muskan-101")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

BG, BORDER, TITLE, TEXT, MUTED, ACCENT = "#0b0610", "#2a1220", "#d68ab0", "#e6d6e0", "#9a8594", "#c2749a"
FONT = "'Segoe UI', Helvetica, Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"


def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-stats-generator")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch():
    user = api(f"/users/{USER}")
    repos, page = [], 1
    while True:
        chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in own)
    langs = {}
    for r in own:
        try:
            for k, v in api(f"/repos/{USER}/{r['name']}/languages").items():
                langs[k] = langs.get(k, 0) + v
        except Exception:
            pass
    def count(path):
        try:
            return api(path)["total_count"]
        except Exception:
            return 0
    commits = count(f"/search/commits?q=author:{USER}&per_page=1")
    prs = count(f"/search/issues?q=author:{USER}+type:pr&per_page=1")
    return {"repos": user["public_repos"], "followers": user["followers"],
            "stars": stars, "commits": commits, "prs": prs, "langs": langs}


def card(title, body, h=170):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{h}" viewBox="0 0 420 {h}" role="img" aria-label="{escape(title)}">
  <rect x=".5" y=".5" width="419" height="{h-1}" rx="8" fill="{BG}" stroke="{BORDER}"/>
  <text x="24" y="34" font-family="{SERIF}" font-size="17" letter-spacing="1.5" fill="{TITLE}">{escape(title.upper())}</text>
  <rect x="24" y="44" width="48" height="1.5" fill="{ACCENT}"/>
{body}
</svg>'''


def stats_svg(d):
    rows = [("Public repositories", d["repos"]), ("Stars earned", d["stars"]),
            ("Total commits", d["commits"]), ("Pull requests", d["prs"]), ("Followers", d["followers"])]
    body = ""
    for i, (k, v) in enumerate(rows):
        y = 72 + i * 20
        body += (f'  <text x="24" y="{y}" font-family="{FONT}" font-size="13" fill="{MUTED}">{k}</text>\n'
                 f'  <text x="396" y="{y}" text-anchor="end" font-family="{FONT}" font-size="13" font-weight="600" fill="{TEXT}">{v}</text>\n')
    return card("GitHub Statistics", body)


def langs_svg(d):
    total = sum(d["langs"].values()) or 1
    top = sorted(d["langs"].items(), key=lambda x: -x[1])[:5]
    shades = ["#f0a8cc", "#d68ab0", "#c2749a", "#9c5878", "#6e3d56"]
    body, x = "", 24.0
    width = 372
    # stacked bar
    for (name, v), c in zip(top, shades):
        w = width * v / total
        body += f'  <rect x="{x:.1f}" y="58" width="{max(w,1):.1f}" height="8" fill="{c}"/>\n'
        x += w
    for i, ((name, v), c) in enumerate(zip(top, shades)):
        col, row = i % 2, i // 2
        cx, cy = 24 + col * 190, 92 + row * 22
        body += (f'  <circle cx="{cx+4}" cy="{cy-4}" r="4" fill="{c}"/>\n'
                 f'  <text x="{cx+16}" y="{cy}" font-family="{FONT}" font-size="12.5" fill="{TEXT}">{escape(name)} '
                 f'<tspan fill="{MUTED}">{100*v/total:.1f}%</tspan></text>\n')
    return card("Most Used Languages", body)


if __name__ == "__main__":
    data = fetch()
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "stats.svg"), "w").write(stats_svg(data))
    open(os.path.join(OUT, "languages.svg"), "w").write(langs_svg(data))
    print({k: v for k, v in data.items() if k != "langs"}, list(data["langs"])[:6])
