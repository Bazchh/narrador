# -*- coding: utf-8 -*-
"""Gera o HTML do documento Casos de Uso a partir de casos-de-uso.json.

Uso: python gerar_casos_de_uso.py [casos-de-uso.json] [Casos-de-Uso.html]
Todos os números da capa, do índice, dos cartões de regra ("aplicada em N casos")
e do fechamento são calculados a partir dos dados; nada é digitado à mão.
"""
import json
import sys
from html import escape as e
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ENTRADA = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "casos-de-uso.json"
SAIDA = Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI / "Casos-de-Uso.html"

D = json.loads(ENTRADA.read_text(encoding="utf-8"))

PRIORIDADE_CLASSE = {"Essencial": "ess", "Importante": "imp", "Desejável": "des"}
FASE_CLASSE = {1: "p1", 2: "p2", 3: "p3"}
TIPO_CLASSE = {"ator": "st-ator", "sistema": "st-sis", "llm": "st-llm", "motor": "st-motor",
               "fim": "st-fim", "atencao": "st-aten", "falha": "st-falha"}

CSS = """
  :root { --ink:#0f1b33; --text:#222a38; --muted:#5b6577; --line:#d7dde8; --accent:#1f4fd1;
    --bg-soft:#f3f5f9; --f1:#1f4fd1; --f2:#e08a1e; --f3:#1f9d55; --red:#c53030; --amber:#c77d0a; --green:#1f9d55; }
  * { box-sizing:border-box; }
  html, body { margin:0; padding:0; background:#fff; color:var(--text);
    font-family:"Segoe UI", Arial, sans-serif; font-size:10pt; line-height:1.42; }
  h1,h2,h3,.big { font-family:"Segoe UI", Arial, sans-serif; font-weight:700; color:var(--ink); margin:0; letter-spacing:-0.02em; }
  h1 { font-size:38pt; line-height:1; margin:2px 0 10px; }
  h2 { font-size:21pt; line-height:1.1; margin:0 0 6px; }
  h3 { font-size:12pt; margin:0 0 3px; }
  p { margin:0 0 6px; }
  .mono { font-family:Consolas, "Cascadia Mono", monospace; }
  .kicker { font-family:Consolas, monospace; font-size:8.5pt; letter-spacing:0.14em; color:var(--accent); text-transform:uppercase; margin-bottom:6px; }
  .lead { font-size:11pt; max-width:150mm; margin-bottom:12px; }
  .capa { background:var(--bg-soft); margin:-16mm -16mm 0; padding:16mm 16mm 12mm; }
  .cap { break-before:page; }
  .stats { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:14px 0; }
  .stat { background:#fff; border:1px solid var(--line); border-radius:8px; padding:10px 12px; }
  .stat .big { font-size:26pt; line-height:1; }
  .stat .stl { font-size:9pt; color:var(--muted); margin-top:4px; }
  .grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
  .grid2 { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; }
  .card { background:#fff; border:1px solid var(--line); border-radius:8px; padding:10px 12px; border-top:3px solid var(--line); }
  .card .code { font-family:Consolas, monospace; font-size:8pt; letter-spacing:0.12em; color:var(--muted); text-transform:uppercase; }
  .card .meta { font-family:Consolas, monospace; font-size:8pt; color:var(--accent); margin:2px 0 5px; }
  .card p { font-size:9.2pt; margin:0; }
  .f1 { border-top-color:var(--f1); } .f2 { border-top-color:var(--f2); } .f3 { border-top-color:var(--f3); }
  .pill { display:inline-block; font-family:Consolas, monospace; font-size:7.5pt; padding:1px 7px; border-radius:10px; border:1px solid; margin-left:3px; vertical-align:middle; white-space:nowrap; }
  .pill.p1 { color:var(--f1); border-color:var(--f1); background:#eaf0ff; }
  .pill.p2 { color:var(--f2); border-color:var(--f2); background:#fff4e5; }
  .pill.p3 { color:var(--f3); border-color:var(--f3); background:#e8f7ee; }
  .pill.ess { color:var(--red); border-color:var(--red); background:#fdecec; }
  .pill.imp { color:var(--amber); border-color:var(--amber); background:#fff6e0; }
  .pill.des { color:var(--muted); border-color:var(--line); background:#f3f5f9; }
  .pill.ator { color:var(--ink); border-color:var(--ink); background:#fff; }
  .pill.rn { color:var(--muted); border-color:var(--line); background:#fff; }
  table { width:100%; border-collapse:collapse; font-size:9.2pt; }
  th { text-align:left; font-family:Consolas, monospace; font-size:7.5pt; letter-spacing:0.1em; color:var(--muted); text-transform:uppercase; background:#e9edf4; padding:6px 8px; }
  td { padding:5px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
  td.code { font-family:Consolas, monospace; color:var(--accent); white-space:nowrap; }
  tr.mod td { background:var(--ink); color:#fff; font-weight:700; font-size:10pt; padding:6px 8px; }
  tr { break-inside:avoid; }
  .leg { display:grid; grid-template-columns:150px 1fr; gap:4px 12px; font-size:9.3pt; }
  .leg b { color:var(--ink); }
  .leg div { padding:5px 0; border-bottom:1px solid var(--line); }
  .cores { background:var(--bg-soft); border-radius:8px; padding:8px 12px; font-size:8.8pt; margin-top:10px; }
  .sw { display:inline-block; width:14px; height:10px; border:1px solid var(--line); border-radius:2px; vertical-align:middle; margin:0 4px 0 10px; }
  .actors { display:grid; grid-template-columns:1fr 1fr; gap:6px 18px; }
  .actor { display:grid; grid-template-columns:34px 1fr; gap:8px; padding:7px 0; border-bottom:1px solid var(--line); break-inside:avoid; }
  .actor .ico { width:30px; height:30px; border-radius:6px; background:var(--bg-soft); border:1px solid var(--line); display:flex; align-items:center; justify-content:center; }
  .actor b { display:block; font-size:10pt; color:var(--ink); }
  .actor .m { font-family:Consolas, monospace; font-size:7.8pt; color:var(--accent); }
  .actor p { font-size:9pt; margin:2px 0 0; }
  .rules { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  .rule { border:1px solid var(--line); border-radius:8px; padding:8px 10px; display:grid; grid-template-columns:44px 1fr; gap:8px; break-inside:avoid; }
  .rule .tag { font-family:Consolas, monospace; font-size:8pt; background:var(--ink); color:#fff; padding:2px 5px; border-radius:3px; height:fit-content; }
  .rule b { display:block; font-size:9.8pt; color:var(--ink); }
  .rule p { font-size:8.8pt; margin:2px 0 0; }
  .rule .where { font-family:Consolas, monospace; font-size:7.5pt; color:var(--accent); margin-top:3px; }
  .diag { border:1px solid var(--line); border-radius:10px; padding:10px 12px 6px; margin:8px 0 14px; break-inside:avoid; }
  .diag .cap-txt { font-size:8.8pt; color:var(--muted); margin-top:4px; }
  /* ficha */
  .ficha { border:1px solid var(--line); border-radius:10px; margin:0 0 14px; break-inside:avoid; overflow:hidden; }
  .ficha .head { background:#eef2f8; padding:8px 12px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--line); }
  .ficha .head .code { font-family:Consolas, monospace; color:var(--accent); font-size:9.5pt; }
  .ficha .head h3 { font-size:12.5pt; flex:1; margin:0; }
  .ficha .body { padding:8px 12px 10px; }
  .obj { font-size:9.6pt; margin-bottom:6px; } .obj b { color:var(--ink); }
  .flow { display:flex; align-items:flex-start; justify-content:center; gap:0; margin:4px 0 10px; }
  .flow .col { display:flex; flex-direction:column; align-items:center; max-width:118px; }
  .flow .step { border:1px solid #9aa4b5; border-radius:4px; padding:5px 7px; font-size:7.6pt; line-height:1.25; text-align:center; background:#fff; min-width:86px; color:var(--ink); }
  .flow .arrow { align-self:flex-start; margin-top:12px; color:var(--muted); font-size:11pt; padding:0 3px; }
  .flow .branch { font-family:Consolas, monospace; font-size:6.8pt; color:var(--red); margin:2px 0 1px; }
  .flow .vline { width:0; border-left:1px dashed var(--red); height:8px; }
  .st-ator { background:#e9edf4 !important; border-color:#6b7588 !important; }
  .st-sis { background:#fff; }
  .st-llm { border-color:var(--green) !important; }
  .st-motor { border-color:var(--ink) !important; border-width:2px !important; }
  .st-fim { background:#e8f7ee !important; border-color:var(--green) !important; }
  .st-aten { background:#fff6e0 !important; border-color:var(--amber) !important; }
  .st-falha { background:#fdecec !important; border-color:var(--red) !important; }
  .cols { display:grid; grid-template-columns:1fr 1fr; gap:14px; border-top:1px solid var(--line); padding-top:8px; }
  .lbl { font-family:Consolas, monospace; font-size:7.5pt; letter-spacing:0.12em; color:var(--muted); text-transform:uppercase; margin:6px 0 3px; }
  .lbl:first-child { margin-top:0; }
  ul.pre { margin:0 0 0 14px; padding:0; font-size:9pt; } ul.pre li { margin:1px 0; }
  ol.main { margin:0 0 0 18px; padding:0; font-size:9pt; } ol.main li { margin:2px 0; padding-left:2px; }
  ol.main li::marker { color:var(--accent); font-family:Consolas, monospace; font-size:8.5pt; }
  .alt, .exc { font-size:8.8pt; margin:3px 0 4px; display:grid; grid-template-columns:26px 1fr; gap:6px; }
  .alt .b, .exc .b { font-family:Consolas, monospace; font-size:7.5pt; color:#fff; border-radius:3px; padding:1px 4px; height:fit-content; text-align:center; }
  .alt .b { background:var(--accent); } .exc .b { background:var(--red); }
  .alt b, .exc b { display:block; color:var(--ink); font-size:9.2pt; }
  .none { font-size:8.8pt; color:var(--muted); font-style:italic; }
  .res { border-top:1px solid var(--line); margin-top:8px; padding-top:6px; display:flex; align-items:baseline; gap:8px; font-size:9pt; }
  .res .lbl { margin:0; white-space:nowrap; } .res .txt { flex:1; }
  .seq { background:var(--bg-soft); border-top:1px solid var(--line); padding:8px 12px; }
  .seq .cap-txt { font-size:8.8pt; color:var(--muted); margin-top:2px; }
  .phase { border:1px solid var(--line); border-left:4px solid var(--line); border-radius:8px; padding:9px 12px; margin-bottom:8px; break-inside:avoid; }
  .phase.p1 { border-left-color:var(--f1); } .phase.p2 { border-left-color:var(--f2); } .phase.p3 { border-left-color:var(--f3); }
  .phase h3 { display:flex; justify-content:space-between; }
  .phase h3 span { font-family:Consolas, monospace; font-size:8pt; color:var(--accent); font-weight:normal; }
  .phase p { font-size:9.2pt; margin:2px 0 4px; }
  .chip { display:inline-block; font-size:8.2pt; border:1px solid var(--line); border-radius:10px; padding:1px 8px; margin:2px 2px 0 0; background:#fff; }
  .chip .mono { color:var(--accent); font-size:7.6pt; }
  .callout { background:var(--ink); color:#fff; border-radius:8px; padding:12px 14px; font-size:9.6pt; break-inside:avoid; }
  .note { background:var(--bg-soft); border-radius:8px; padding:10px 12px; font-size:9.2pt; break-inside:avoid; }
  .pend { display:grid; grid-template-columns:70px 90px 1fr; gap:8px; font-size:9pt; padding:6px 0; border-bottom:1px solid var(--line); }
"""

# ---------- índices e contagens ----------
atores = {a["id"]: a for a in D["atores"]}
casos_todos = [(m, c) for m in D["modulos"] for c in m["casos"]]
total_casos = len(casos_todos)
casos_detalhados = [(m, c) for m, c in casos_todos if m["detalhado"]]
regras = {r["codigo"]: r for r in D["regras"]}
uso_rn = {r: [] for r in regras}
for m, c in casos_detalhados:
    for r in c.get("regras", []):
        uso_rn[r].append(c["codigo"])
principal_de = {a: [] for a in atores}
apoio_de = {a: [] for a in atores}
for m, c in casos_todos:
    principal_de[c["ator"]].append(c["codigo"])
    for ap in c.get("apoio", []):
        apoio_de[ap].append(c["codigo"])
ess = sum(1 for m, c in casos_todos if c["prioridade"] == "Essencial")
por_fase = {f: sum(1 for m, c in casos_todos if c["fase"] == f) for f in (1, 2, 3)}


def rotulo_ator(a):
    return atores[a].get("rotulo", a)


def pill_fase(f):
    return f'<span class="pill {FASE_CLASSE[f]}">Fase {f}</span>'


def pill_pri(p):
    return f'<span class="pill {PRIORIDADE_CLASSE[p]}">{e(p)}</span>'


# ---------- SVG: boneco e diagrama de casos de uso ----------
def boneco(x, y, nome):
    return (f'<g transform="translate({x},{y})">'
            f'<circle cx="0" cy="-22" r="6" fill="none" stroke="#333" stroke-width="1.3"/>'
            f'<line x1="0" y1="-16" x2="0" y2="4" stroke="#333" stroke-width="1.3"/>'
            f'<line x1="-10" y1="-8" x2="10" y2="-8" stroke="#333" stroke-width="1.3"/>'
            f'<line x1="0" y1="4" x2="-8" y2="18" stroke="#333" stroke-width="1.3"/>'
            f'<line x1="0" y1="4" x2="8" y2="18" stroke="#333" stroke-width="1.3"/>'
            f'<text x="0" y="32" text-anchor="middle" font-size="8" fill="#333">{e(nome)}</text></g>')


def caixa_sistema(x, y, nome):
    return (f'<g transform="translate({x},{y})"><rect x="-46" y="-14" width="92" height="28" rx="4" fill="#e9edf4" stroke="#9aa4b5"/>'
            f'<text x="0" y="4" text-anchor="middle" font-size="8" fill="#333">{e(nome)}</text></g>')


def diagrama_modulo(m):
    casos = m["casos"]
    pessoas = [a for a in atores if atores[a]["tipo"] == "pessoa" and any(
        c["ator"] == a or a in c.get("apoio", []) for c in casos)]
    sistemas = [a for a in atores if atores[a]["tipo"] == "sistema" and any(
        c["ator"] == a or a in c.get("apoio", []) for c in casos)]
    W = 700
    linhas = (len(casos) + 1) // 2
    H = 60 + linhas * 64 + 40
    pos = {}
    for i, c in enumerate(casos):
        col, row = i % 2, i // 2
        pos[c["codigo"]] = (260 + col * 180, 70 + row * 64)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">']
    # borda do módulo
    out.append(f'<rect x="150" y="18" width="400" height="{H - 30}" rx="8" fill="none" stroke="#9aa4b5" stroke-dasharray="4 3"/>')
    out.append(f'<text x="350" y="38" text-anchor="middle" font-size="9" font-weight="700" fill="#0f1b33">Módulo {e(m["letra"])} · {e(m["nome"])}</text>')
    # posições de atores
    py = {a: 60 + i * ((H - 120) / max(1, len(pessoas) - 1) if len(pessoas) > 1 else 0) for i, a in enumerate(pessoas)}
    if len(pessoas) == 1:
        py[pessoas[0]] = H / 2
    sy = {s: 60 + i * ((H - 120) / max(1, len(sistemas) - 1) if len(sistemas) > 1 else 0) for i, s in enumerate(sistemas)}
    if len(sistemas) == 1:
        sy[sistemas[0]] = H / 2
    # linhas
    for c in casos:
        cx, cy = pos[c["codigo"]]
        for a in [c["ator"]] + c.get("apoio", []):
            if a in py:
                out.append(f'<line x1="80" y1="{py[a]:.0f}" x2="{cx - 70}" y2="{cy}" stroke="#b9c2d0" stroke-width="0.8"/>')
            elif a in sy:
                out.append(f'<line x1="{cx + 70}" y1="{cy}" x2="{574}" y2="{sy[a]:.0f}" stroke="#b9c2d0" stroke-width="0.8"/>')
    # elipses
    for c in casos:
        cx, cy = pos[c["codigo"]]
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="72" ry="24" fill="#dfe7ff" stroke="#1f4fd1" stroke-width="1.2"/>')
        out.append(f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" font-size="6.5" fill="#1f4fd1" font-family="Consolas, monospace">{e(c["codigo"])}</text>')
        nome = c["nome"]
        palavras, l1, l2 = nome.split(), "", ""
        for w in palavras:
            if len(l1) + len(w) < 24 and not l2:
                l1 = (l1 + " " + w).strip()
            else:
                l2 = (l2 + " " + w).strip()
        if l2 and len(l2) > 26:
            l2 = l2[:24] + "…"
        if l2:
            out.append(f'<text x="{cx}" y="{cy + 2}" text-anchor="middle" font-size="7" font-weight="700" fill="#0f1b33">{e(l1)}</text>')
            out.append(f'<text x="{cx}" y="{cy + 11}" text-anchor="middle" font-size="7" font-weight="700" fill="#0f1b33">{e(l2)}</text>')
        else:
            out.append(f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="7" font-weight="700" fill="#0f1b33">{e(l1)}</text>')
    for a in pessoas:
        out.append(boneco(60, py[a], rotulo_ator(a)))
    for s in sistemas:
        out.append(caixa_sistema(620, sy[s], s))
    out.append('</svg>')
    return "".join(out)


def mapa_geral():
    pessoas = [a for a in atores if atores[a]["tipo"] == "pessoa"]
    sistemas = [a for a in atores if atores[a]["tipo"] == "sistema"]
    mods = D["modulos"]
    W, rowh = 700, 58
    H = 50 + len(mods) * rowh + 30
    cor = {1: "#1f4fd1", 2: "#e08a1e", 3: "#1f9d55"}
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">']
    out.append('<text x="60" y="22" font-size="7.5" fill="#5b6577" font-family="Consolas, monospace" letter-spacing="1.5">ATORES</text>')
    out.append('<text x="350" y="22" text-anchor="middle" font-size="7.5" fill="#5b6577" font-family="Consolas, monospace" letter-spacing="1.5">MÓDULOS DO SISTEMA</text>')
    out.append('<text x="640" y="22" text-anchor="end" font-size="7.5" fill="#5b6577" font-family="Consolas, monospace" letter-spacing="1.5">SISTEMAS EXTERNOS</text>')
    py = {a: 60 + i * ((H - 120) / max(1, len(pessoas) - 1)) for i, a in enumerate(pessoas)}
    sy = {s: 60 + i * ((H - 120) / max(1, len(sistemas) - 1)) for i, s in enumerate(sistemas)}
    my = {m["letra"]: 40 + i * rowh for i, m in enumerate(mods)}
    for m in mods:
        y = my[m["letra"]]
        usados_p = {a for c in m["casos"] for a in [c["ator"]] + c.get("apoio", []) if a in py}
        usados_s = {a for c in m["casos"] for a in [c["ator"]] + c.get("apoio", []) if a in sy}
        for a in usados_p:
            out.append(f'<line x1="80" y1="{py[a]:.0f}" x2="230" y2="{y + 24}" stroke="#b9c2d0" stroke-width="0.8"/>')
        for s in usados_s:
            out.append(f'<line x1="470" y1="{y + 24}" x2="{574}" y2="{sy[s]:.0f}" stroke="#b9c2d0" stroke-width="0.8"/>')
    for m in mods:
        y = my[m["letra"]]
        out.append(f'<rect x="230" y="{y}" width="240" height="48" rx="6" fill="#fff" stroke="{cor[m["fase"]]}" stroke-width="1.3"/>')
        out.append(f'<text x="350" y="{y + 18}" text-anchor="middle" font-size="9" font-weight="700" fill="#0f1b33">Módulo {e(m["letra"])} · {e(m["nome"])}</text>')
        out.append(f'<text x="350" y="{y + 32}" text-anchor="middle" font-size="7" fill="#1f4fd1" font-family="Consolas, monospace">{len(m["casos"])} casos de uso · fase {m["fase"]}</text>')
        cods = " · ".join(c["codigo"] for c in m["casos"][:5]) + (" · …" if len(m["casos"]) > 5 else "")
        out.append(f'<text x="350" y="{y + 43}" text-anchor="middle" font-size="6.5" fill="#5b6577" font-family="Consolas, monospace">{e(cods)}</text>')
    for a in pessoas:
        out.append(boneco(60, py[a], rotulo_ator(a)))
    for s in sistemas:
        out.append(caixa_sistema(620, sy[s], s))
    out.append('</svg>')
    return "".join(out)


def sequencia_svg(seq):
    cols = seq["colunas"]
    W = 640
    cw = W / len(cols)
    H = 40 + len(seq["passos"]) * 30 + 16
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">']
    xs = [cw * i + cw / 2 for i in range(len(cols))]
    for i, c in enumerate(cols):
        out.append(f'<rect x="{xs[i] - 60}" y="4" width="120" height="22" rx="4" fill="#e9edf4" stroke="#9aa4b5"/>')
        out.append(f'<text x="{xs[i]}" y="19" text-anchor="middle" font-size="8" font-weight="700" fill="#0f1b33">{e(c)}</text>')
        out.append(f'<line x1="{xs[i]}" y1="26" x2="{xs[i]}" y2="{H - 6}" stroke="#b9c2d0" stroke-dasharray="3 3"/>')
    for k, p in enumerate(seq["passos"]):
        y = 48 + k * 30
        x1, x2 = xs[p["de"]], xs[p["para"]]
        dash = ' stroke-dasharray="4 3"' if p.get("tracejado") else ""
        if x1 == x2:
            out.append(f'<path d="M{x1},{y - 6} h26 v12 h-26" fill="none" stroke="#1f4fd1" stroke-width="1.2"/>')
            out.append(f'<text x="{x1 + 30}" y="{y + 3}" font-size="7" fill="#333">{e(p["t"])}</text>')
        else:
            out.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#1f4fd1" stroke-width="1.2"{dash}/>')
            tip = x2 - 6 if x2 > x1 else x2 + 6
            out.append(f'<path d="M{x2},{y} L{tip},{y - 3} L{tip},{y + 3} Z" fill="#1f4fd1"/>')
            out.append(f'<text x="{(x1 + x2) / 2}" y="{y - 4}" text-anchor="middle" font-size="7" fill="#333">{e(p["t"])}</text>')
    out.append('</svg>')
    return "".join(out)


# ---------- ficha ----------
def ficha(c):
    h = [f'<div class="ficha" id="{c["codigo"]}"><div class="head"><span class="code">UC-{e(c["codigo"])}</span><h3>{e(c["nome"])}</h3>'
         f'<span class="pill ator">{e(rotulo_ator(c["ator"]))}</span>{pill_fase(c["fase"])}{pill_pri(c["prioridade"])}</div><div class="body">']
    h.append(f'<div class="obj"><b>Objetivo.</b> {e(c["objetivo"])}</div>')
    # fluxo
    h.append('<div class="flow">')
    for i, s in enumerate(c["fluxo"]):
        if i:
            h.append('<span class="arrow">&#8594;</span>')
        h.append(f'<div class="col"><div class="step {TIPO_CLASSE[s["tipo"]]}">{e(s["t"])}</div>')
        if "desvio" in s:
            d = s["desvio"]
            h.append(f'<div class="vline"></div><div class="branch">{e(d["rotulo"])}</div><div class="step {TIPO_CLASSE[d["tipo"]]}">{e(d["t"])}</div>')
        h.append('</div>')
    h.append('</div>')
    # colunas
    h.append('<div class="cols"><div>')
    h.append('<div class="lbl">Pré-condições</div><ul class="pre">' + "".join(f'<li>{e(p)}</li>' for p in c["pre"]) + '</ul>')
    h.append('<div class="lbl">Fluxo principal</div><ol class="main">' + "".join(f'<li>{e(p)}</li>' for p in c["principal"]) + '</ol>')
    h.append('</div><div>')
    h.append(f'<div class="lbl">Gatilho</div><div style="font-size:9pt">{e(c["gatilho"])}</div>')
    if c.get("apoio"):
        h.append('<div class="lbl">Atores de apoio</div><div style="font-size:9pt">' + ", ".join(e(a) for a in c["apoio"]) + '</div>')
    h.append('<div class="lbl">Fluxos alternativos</div>')
    if c.get("alternativos"):
        for i, a in enumerate(c["alternativos"], 1):
            h.append(f'<div class="alt"><span class="b">A{i}</span><div><b>{e(a["t"])}</b>{e(a["d"])}</div></div>')
    else:
        h.append('<div class="none">Sem desvios previstos: o fluxo principal cobre o caso.</div>')
    if c.get("excecoes"):
        h.append('<div class="lbl">Exceções</div>')
        for i, x in enumerate(c["excecoes"], 1):
            h.append(f'<div class="exc"><span class="b">E{i}</span><div><b>{e(x["t"])}</b>{e(x["d"])}</div></div>')
    h.append('</div></div>')
    rns = "".join(f'<span class="pill rn">{e(r)}</span>' for r in c.get("regras", []))
    h.append(f'<div class="res"><span class="lbl">Resultado</span><span class="txt">{e(c["resultado"])}</span><span>{rns}</span></div>')
    h.append('</div>')
    if c.get("sequencia"):
        h.append(f'<div class="seq">{sequencia_svg(c["sequencia"])}<div class="cap-txt">{e(c["sequencia"]["legenda"])}</div></div>')
    h.append('</div>')
    return "".join(h)


# ---------- páginas ----------
def capa():
    cards = "".join(
        f'<div class="card f{m["fase"]}"><div class="code">Módulo {e(m["letra"])}</div><h3>{e(m["nome"])}</h3>'
        f'<div class="meta">{len(m["casos"])} casos · fase {m["fase"]}{"" if m["detalhado"] else " · a detalhar"}</div><p>{e(m["resumo"])}</p></div>'
        for m in D["modulos"])
    return f'''<section class="capa"><div class="kicker">{e(D["kicker"])}</div><h1>{e(D["titulo"])}</h1>
<p class="lead">{e(D["intro"])}</p>
<div class="note" style="max-width:150mm"><b>{e(D["entrega"].split(":")[0])}:</b>{e(D["entrega"].split(":",1)[1])}</div>
<div class="stats"><div class="stat"><div class="big">{total_casos}</div><div class="stl">casos de uso especificados</div></div>
<div class="stat"><div class="big">{len(D["modulos"])}</div><div class="stl">módulos funcionais</div></div>
<div class="stat"><div class="big">{len(atores)}</div><div class="stl">atores identificados</div></div>
<div class="stat"><div class="big">{len(regras)}</div><div class="stl">regras de negócio</div></div></div>
<div class="grid3">{cards}</div>
<p style="font-size:8.8pt;color:var(--muted);margin-top:12px;border-top:1px solid var(--line);padding-top:8px">{e(D["produto"])} · mestre por inteligência artificial para D&amp;D 5e, regras de 2024 · fase 1 com {por_fase[1]} casos de uso, fase 2 com {por_fase[2]} e fase 3 com {por_fase[3]} · {ess} classificados como essenciais · {len(casos_detalhados)} detalhados nesta entrega</p>
</section>'''


def como_ler():
    return '''<section class="cap"><div class="kicker">Como ler este documento</div><h2>Cada caso de uso é uma ficha com desenho, passos e desvios</h2>
<p class="lead">A mesma estrutura sempre, para que qualquer pessoa, do desenvolvedor ao jogador que testa, encontre a informação no mesmo lugar.</p>
<div class="grid2"><div class="leg">
<div><b>Código e nome</b></div><div>Identificador fixo, como UC-A02. O código não muda, mesmo que o nome seja ajustado.</div>
<div><b>Objetivo</b></div><div>O que o ator quer obter. Se o objetivo não for alcançado, o caso de uso falhou.</div>
<div><b>Pré-condições</b></div><div>O que já precisa ser verdade antes de começar.</div>
<div><b>Fluxo principal</b></div><div>Os passos numerados do caminho sem problema.</div>
<div><b>Exceções</b></div><div>O que fazer quando algo falha, sempre com a ação de recuperação.</div>
<div><b>Regras aplicadas</b></div><div>As regras de negócio que valem ali, listadas no capítulo próprio.</div>
</div><div class="leg">
<div><b>Etiquetas</b></div><div>Ator principal, fase de entrega (1, 2 ou 3) e prioridade (essencial, importante ou desejável).</div>
<div><b>Desenho do fluxo</b></div><div>O caminho feliz em blocos, da esquerda para a direita. Seta tracejada para baixo é desvio.</div>
<div><b>Gatilho</b></div><div>O evento que dispara o caso de uso.</div>
<div><b>Fluxos alternativos</b></div><div>Caminhos válidos e diferentes, que também terminam bem.</div>
<div><b>Resultado</b></div><div>O estado do mundo depois que o caso de uso termina.</div>
<div><b>Sequência</b></div><div>Em casos com troca de mensagens, um diagrama de sequência fecha a ficha.</div>
</div></div>
<div class="cores"><b>Cores dos desenhos</b>
<span class="sw" style="background:#e9edf4;border-color:#6b7588"></span>início pelo ator
<span class="sw" style="background:#fff"></span>passo da plataforma
<span class="sw" style="background:#fff;border-color:#1f9d55"></span>serviço de linguagem (mestre)
<span class="sw" style="background:#fff;border-color:#0f1b33;border-width:2px"></span>motor de regras
<span class="sw" style="background:#e8f7ee;border-color:#1f9d55"></span>resultado esperado
<span class="sw" style="background:#fff6e0;border-color:#c77d0a"></span>atenção
<span class="sw" style="background:#fdecec;border-color:#c53030"></span>falha ou recusa</div>
</section>'''


def pag_atores():
    icons = {"pessoa": "&#9823;", "sistema": "&#9881;"}
    rows = []
    for a in D["atores"]:
        n_p, n_a = len(principal_de[a["id"]]), len(apoio_de[a["id"]])
        partes = []
        if n_p:
            partes.append(f"ator principal em {n_p} caso{'s' if n_p != 1 else ''}")
        if n_a:
            partes.append(f"participa de {n_a} caso{'s' if n_a != 1 else ''}")
        rows.append(f'<div class="actor"><div class="ico">{icons[a["tipo"]]}</div><div><b>{e(a.get("rotulo", a["id"]))}</b><div class="m">{e(" · ".join(partes))}</div><p>{e(a["desc"])}</p></div></div>')
    return f'''<section class="cap"><div class="kicker">Atores</div><h2>Os {len(atores)} atores do sistema</h2>
<p class="lead">Ator é quem inicia ou recebe alguma coisa da plataforma. Pessoas e a rotina da plataforma ficam à esquerda dos diagramas; sistemas externos e dados embutidos ficam à direita, em caixas.</p>
<div class="actors">{"".join(rows)}</div></section>'''


def pag_mapa():
    return f'''<section class="cap"><div class="kicker">Visão geral</div><h2>O mapa dos {total_casos} casos de uso</h2>
<p class="lead">Cada linha liga um ator ao módulo em que ele atua. A cor da borda indica a fase em que o módulo entra: azul na fase 1, laranja na fase 2 e verde na fase 3.</p>
<div class="diag">{mapa_geral()}<div class="cap-txt">Quem usa o quê. Os módulos A a G sustentam a mesa solo da fase 1; H traz o grupo; I solta a campanha livre.</div></div></section>'''


def pag_indice():
    rows = []
    for m in D["modulos"]:
        rows.append(f'<tr class="mod"><td colspan="5">Módulo {e(m["letra"])} · {e(m["nome"])}{"" if m["detalhado"] else " · a detalhar na próxima entrega"}</td></tr>')
        for c in m["casos"]:
            rows.append(f'<tr><td class="code">UC-{e(c["codigo"])}</td><td>{e(c["nome"])}</td><td>{e(rotulo_ator(c["ator"]))}</td><td>{pill_fase(c["fase"])}</td><td>{pill_pri(c["prioridade"])}</td></tr>')
    return f'''<section class="cap"><div class="kicker">Índice</div><h2>Os {total_casos} casos de uso em uma tabela</h2>
<p class="lead">A lista completa, com código fixo desde já. Use a coluna de fase para planejar as entregas e a de prioridade para decidir o que corta primeiro.</p>
<table><thead><tr><th>Código</th><th>Caso de uso</th><th>Ator principal</th><th>Fase</th><th>Prioridade</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>'''


def pag_regras():
    cards = []
    for r in D["regras"]:
        n = len(uso_rn[r["codigo"]])
        onde = (f'aplicada em {n} caso{"s" if n != 1 else ""} de uso detalhado{"s" if n != 1 else ""}'
                if n else "ainda sem caso detalhado que a aplique")
        cards.append(f'<div class="rule"><span class="tag">{e(r["codigo"])}</span><div><b>{e(r["titulo"])}</b><p>{e(r["texto"])} Obtemos: {e(r["obtemos"])}</p><div class="where">{e(onde)}</div></div></div>')
    return f'''<section class="cap"><div class="kicker">Regras de negócio</div><h2>{len(regras)} regras que valem em todos os casos de uso</h2>
<p class="lead">São as decisões que não se repetem em cada ficha, as mesmas do Mapa do Projeto, com a numeração preservada. Quando uma regra aparece listada em um caso de uso, é aqui que ela está explicada. A contagem considera só os casos detalhados nesta entrega.</p>
<div class="rules">{"".join(cards)}</div></section>'''


def cap_modulo(m):
    fichas = "".join(ficha(c) for c in m["casos"])
    return f'''<section class="cap"><div class="kicker">Módulo {e(m["letra"])} · fase {m["fase"]}</div><h2>{e(m["nome"])}</h2>
<p class="lead">{e(m["resumo"])}</p>
<div class="diag">{diagrama_modulo(m)}<div class="cap-txt">Diagrama de casos de uso do módulo {e(m["letra"])}. As pessoas ficam à esquerda, os sistemas externos à direita e cada elipse é um caso de uso detalhado nas páginas seguintes.</div></div>
{fichas}</section>'''


def fechamento():
    blocos = []
    for f in (1, 2, 3):
        fase = D["fases"][str(f)]
        chips = "".join(f'<span class="chip"><span class="mono">UC-{e(c["codigo"])}</span> {e(c["nome"])}</span>' for m, c in casos_todos if c["fase"] == f)
        blocos.append(f'<div class="phase {FASE_CLASSE[f]}"><h3>Fase {f} · {e(fase["nome"])}<span>{por_fase[f]} casos de uso</span></h3><p>{e(fase["resumo"])}</p>{chips}</div>')
    pend = "".join(f'<div class="pend"><span class="mono" style="color:var(--accent)">{e(p["codigo"])}</span><span class="pill {"des" if p["estado"]=="resolvida" else "imp"}" style="margin:0;height:fit-content">{e(p["estado"])}</span><span>{e(p["texto"])}</span></div>' for p in D["pendencias"])
    return f'''<section class="cap"><div class="kicker">Fechamento</div><h2>O que entra em cada fase</h2>
<p class="lead">A fase 1 é a mesa jogável solo. A fase 2 traz a mesa longa e o grupo. A fase 3 solta a campanha livre.</p>
{"".join(blocos)}
<div class="kicker" style="margin-top:14px">Lacunas e decisões tocadas por esta entrega</div>
{pend}
<div class="callout" style="margin-top:14px"><b>Como usar este documento no dia a dia.</b> Cada caso de uso vira um item do backlog, com o código como identificador permanente. O critério de aceite de um item é o fluxo principal funcionando de ponta a ponta, mais cada exceção listada tratada e testada. Quando surgir uma necessidade nova, ela entra como um caso de uso novo, com código próprio, em vez de crescer dentro de um existente: assim o escopo continua visível e negociável.</div>
</section>'''


html = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{e(D["titulo"])} · {e(D["produto"])}</title><style>{CSS}</style></head><body>
{capa()}{como_ler()}{pag_atores()}{pag_mapa()}{pag_indice()}{pag_regras()}
{"".join(cap_modulo(m) for m in D["modulos"] if m["detalhado"])}
{fechamento()}
</body></html>'''
SAIDA.write_text(html, encoding="utf-8")
print(f"ok {SAIDA.name}: {total_casos} casos ({len(casos_detalhados)} detalhados), {len(regras)} regras, {len(atores)} atores")
