"""Generate profile charts from public GitHub data. Python standard library only."""

import json
import math
import os
import re
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = "cristian7712"
COLORS = ["#B6FF6C", "#68E8DC", "#A999FF", "#F0C58B", "#FF8FA8", "#65ACFF"]


def fetch(url, api=False):
    headers = {"User-Agent": f"{USER}-profile-charts"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=45) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if api else raw


class Calendar(HTMLParser):
    """Join GitHub calendar cells to their accessible tooltip counts."""

    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.target = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and attrs.get("data-date"):
            self.cells[attrs["id"]] = attrs["data-date"]
        if tag == "tool-tip":
            self.target = attrs.get("for")
            self.parts = []

    def handle_data(self, data):
        if self.target:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.target:
            text = "".join(self.parts).strip()
            match = re.match(r"([\d,]+) contributions? on ", text)
            if match:
                self.counts[self.target] = int(match[1].replace(",", ""))
            elif text.startswith("No contributions on "):
                self.counts[self.target] = 0
            self.target = None

    def days(self):
        if len(self.cells) < 350 or self.cells.keys() - self.counts.keys():
            raise ValueError("GitHub calendar markup changed; preserving previous charts.")
        return sorted((date.fromisoformat(day), self.counts[key]) for key, day in self.cells.items())


def text(x, y, value, size=16, color="#A6B2CC", weight=400, **attrs):
    extra = " ".join(f'{key.rstrip("_").replace("_", "-")}="{escape(str(val), quote=True)}"' for key, val in attrs.items())
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" {extra}>{escape(str(value))}</text>'


def panel(height, title, description, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#12192D"/><stop offset="1" stop-color="#080B14"/></linearGradient><linearGradient id="accent"><stop stop-color="#B6FF6C"/><stop offset="1" stop-color="#68E8DC"/></linearGradient></defs>
<style>text{{font-family:Segoe UI,Arial,sans-serif}}.mono{{font-family:Consolas,monospace}}</style>
<rect x="1" y="1" width="1198" height="{height-2}" rx="22" fill="url(#bg)" stroke="#2C3650"/>
{body}</svg>\n'''


def overview(profile, repos, days, stamp):
    original = [r for r in repos if not r["fork"]]
    metrics = [
        (len(repos), "REPOSITORIOS PÚBLICOS", "Ideas que se convierten en código"),
        (sum(r["stargazers_count"] for r in original), "ESTRELLAS RECIBIDAS", "En repositorios propios públicos"),
        (profile["followers"], "SEGUIDORES", "Conexiones alrededor del código"),
        (sum(n for _, n in days), "CONTRIBUCIONES", "En el calendario público anual"),
    ]
    body = text(36, 39, "GITHUB / EN NÚMEROS", 12, COLORS[0], 600, letter_spacing=2)
    body += text(1164, 39, f"ACTUALIZADO {stamp} UTC", 11, text_anchor="end", class_="mono")
    for i, (value, label, detail) in enumerate(metrics):
        x = 36 + i * 295
        if i:
            body += f'<path d="M{x-18}73V184" stroke="#2C3650"/>'
        body += text(x, 116, f"{value:,}".replace(",", "."), 49, COLORS[i], 750)
        body += text(x, 148, label, 11, "#ECF1FD", 600, letter_spacing=1)
        body += text(x, 174, detail, 12)
    return panel(210, "Mi GitHub en números", "; ".join(f"{v} {label.lower()}" for v, label, _ in metrics) + f". Datos públicos al {stamp} UTC.", body)


def activity(days):
    total = sum(n for _, n in days)
    active = sum(n > 0 for _, n in days)
    best = max(n for _, n in days)
    body = text(36, 40, "01 / RITMO DE CONSTRUCCIÓN", 12, COLORS[0], 600, letter_spacing=2)
    body += text(36, 84, "La constancia también deja huella.", 30, "#F4F6FD", 700)
    body += text(36, 114, f"{days[0][0]:%d/%m/%Y} — {days[-1][0]:%d/%m/%Y} · Calendario público de contribuciones", 15)
    start = days[0][0].toordinal() - (days[0][0].weekday() + 1) % 7
    peak = max(best, 1)
    shades = ["#1B2638", "#294D43", "#43866A", "#79C985", "#B6FF6C"]
    month = None
    months = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    for day, count in days:
        offset = day.toordinal() - start
        x, y = 68 + offset // 7 * 20, 161 + offset % 7 * 20
        if month != (day.year, day.month):
            if day.day <= 7:
                body += text(x, 147, months[day.month-1], 10)
            month = (day.year, day.month)
        level = 0 if count == 0 else min(4, 1 + int((count / peak) * 3))
        body += f'<rect x="{x}" y="{y}" width="15" height="15" rx="3" fill="{shades[level]}"><title>{day.isoformat()}: {count} contribuciones</title></rect>'
    for row, label in [(1, "L"), (3, "M"), (5, "V")]:
        body += text(39, 173 + row*20, label, 10)
    body += text(68, 327, f"{active} días activos", 15, COLORS[0], 600)
    body += text(267, 327, f"{best} contribuciones en el mejor día", 15)
    body += text(916, 326, "Menos", 11)
    for i, color in enumerate(shades):
        body += f'<rect x="{963+i*22}" y="314" width="15" height="15" rx="3" fill="{color}"/>'
    body += text(1080, 326, "Más", 11)
    body += '<path d="M36 350H1164" stroke="#2C3650"/>'
    # The 12 latest calendar weeks; first/last bars may cover partial weeks.
    weeks = defaultdict(int)
    for day, count in days:
        weeks[(day.toordinal()-start)//7] += count
    recent = sorted(weeks.items())[-12:]
    maximum = max(1, max(n for _, n in recent))
    body += text(36, 384, "PULSO SEMANAL", 12, COLORS[1], 600, letter_spacing=2)
    body += text(36, 411, "12 semanas", 21, "#F4F6FD", 650)
    body += text(36, 438, "Extremos: semanas parciales", 12)
    for i, (week, count) in enumerate(recent):
        x = 348 + i*67
        h = count/maximum*63
        body += f'<rect x="{x}" y="{443-h:.2f}" width="39" height="{max(h, 1):.2f}" rx="4" fill="{COLORS[1]}" opacity="{.45+i*.045:.2f}"/>'
        body += text(x+19.5, 433-h, count, 11, "#ECF1FD", text_anchor="middle")
        body += text(x+19.5, 464, date.fromordinal(start+week*7).strftime("%d/%m"), 10, text_anchor="middle")
    return panel(490, "Actividad anual y tendencia semanal", f"{total} contribuciones; {active} días activos; máximo diario de {best}. Cada celda representa un día. Las barras muestran las últimas doce semanas.", body)


def languages(repos):
    original = [r for r in repos if not r["fork"]]
    counts = Counter(r["language"] for r in original if r["language"])
    total = sum(counts.values())
    groups = counts.most_common(5)
    remainder = total - sum(n for _, n in groups)
    if remainder:
        groups.append(("Otros", remainder))
    body = text(36, 40, "02 / MAPA TECNOLÓGICO", 12, COLORS[2], 600, letter_spacing=2)
    body += text(36, 84, "Distintas herramientas. Una misma curiosidad.", 30, "#F4F6FD", 700)
    body += text(36, 115, "Lenguaje principal de cada repositorio propio público", 15)
    circumference = 2 * math.pi * 98
    body += '<circle cx="190" cy="271" r="98" fill="none" stroke="#1B2638" stroke-width="27"/>'
    offset = 0
    for i, (lang, count) in enumerate(groups):
        length = count / total * circumference
        body += f'<circle cx="190" cy="271" r="98" fill="none" stroke="{COLORS[i]}" stroke-width="27" stroke-dasharray="{max(0,length-4):.3f} {circumference:.3f}" stroke-dashoffset="{-offset:.3f}" transform="rotate(-90 190 271)"><title>{escape(lang)}: {count} repositorios</title></circle>'
        offset += length
        y = 170 + i*38
        body += f'<circle cx="376" cy="{y-5}" r="4" fill="{COLORS[i]}"/>'
        body += text(394, y, lang, 16, "#ECF1FD", 600)
        body += f'<rect x="590" y="{y-12}" width="370" height="9" rx="4" fill="#1B2638"/>'
        body += f'<rect x="590" y="{y-12}" width="{count/total*370:.2f}" height="9" rx="4" fill="{COLORS[i]}"/>'
        body += text(989, y, f"{count} repos", 14)
        body += text(1157, y, f"{count/total:.1%}", 15, COLORS[i], 600, text_anchor="end")
    body += text(190, 273, len(counts), 47, "#F4F6FD", 750, text_anchor="middle")
    body += text(190, 300, "LENGUAJES", 11, letter_spacing=2, text_anchor="middle")
    body += text(36, 420, f"Base: {total} repositorios con lenguaje detectado · {len(original)-total} sin clasificar · Forks excluidos", 13)
    body += text(36, 447, "La distribución refleja repositorios, no volumen de código ni nivel de dominio.", 13)
    return panel(474, "Distribución de lenguajes por repositorio", "; ".join(f"{lang}: {count} repositorios" for lang,count in counts.most_common()) + ". Porcentaje sobre repositorios propios públicos con lenguaje detectado, excluyendo forks.", body)


def main():
    profile = fetch(f"https://api.github.com/users/{USER}", api=True)
    repos = []
    page = 1
    while True:
        batch = fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}", api=True)
        repos.extend(r for r in batch if not r.get("private"))
        if len(batch) < 100:
            break
        page += 1
    calendar = Calendar()
    calendar.feed(fetch(f"https://github.com/users/{USER}/contributions"))
    days = calendar.days()
    stamp = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    charts = {"github-overview.svg": overview(profile, repos, days, stamp), "github-activity.svg": activity(days), "github-languages.svg": languages(repos)}
    # Render and validate everything before replacing any existing assets.
    import xml.etree.ElementTree as ET
    for chart in charts.values():
        ET.fromstring(chart)
    destination = ROOT / "assets" / "stats"
    destination.mkdir(parents=True, exist_ok=True)
    for name, chart in charts.items():
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination, delete=False) as temp:
            temp.write(chart)
        os.replace(temp.name, destination / name)
    print(f"Updated {len(charts)} charts: {len(repos)} repositories, {sum(n for _,n in days)} contributions.")


if __name__ == "__main__":
    main()
