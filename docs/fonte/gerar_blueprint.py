# -*- coding: utf-8 -*-
"""Gera o HTML do Blueprint Técnico a partir de blueprint.json.

Uso: python gerar_blueprint.py [blueprint.json] [Blueprint.html]
Os números da capa são calculados dos dados. Blocos suportados: escopo_diagrama,
callout, tabela, camadas, pacotes, escolhas, lista, codigo, sequencia, cards (entregas seguintes).
"""
import json
import sys
from html import escape as e
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ENTRADA = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "blueprint.json"
SAIDA = Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI / "Blueprint.html"
D = json.loads(ENTRADA.read_text(encoding="utf-8"))

CSS = """
  :root { --ink:#0f1b33; --text:#222a38; --muted:#5b6577; --line:#d7dde8; --accent:#1f4fd1;
    --bg-soft:#f3f5f9; --f1:#1f4fd1; --f2:#e08a1e; --f3:#1f9d55; --red:#c53030; --amber:#c77d0a; --green:#1f9d55; }
  * { box-sizing:border-box; }
  html, body { margin:0; padding:0; background:#fff; color:var(--text); font-family:"Segoe UI", Arial, sans-serif; font-size:10pt; line-height:1.42; }
  h1,h2,h3 { font-weight:700; color:var(--ink); margin:0; letter-spacing:-0.02em; }
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
  .stat .big { font-size:26pt; line-height:1; font-weight:700; color:var(--ink); }
  .stat .stl { font-size:9pt; color:var(--muted); margin-top:4px; }
  .box { background:#fff; border:1px solid var(--line); border-radius:8px; padding:10px 14px; margin:8px 0; break-inside:avoid; }
  .box h3 { font-size:11.5pt; margin-bottom:3px; }
  .box p { font-size:9.4pt; margin:0; }
  .callout { border-radius:8px; padding:10px 14px; margin:10px 0; break-inside:avoid; font-size:9.4pt; border-left:4px solid var(--line); background:var(--bg-soft); }
  .callout .k { font-family:Consolas, monospace; font-size:7.5pt; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); margin-bottom:3px; }
  .callout.azul { border-left-color:var(--accent); background:#fff; border:1px solid var(--line); border-left:4px solid var(--accent); }
  .callout.amarelo { border-left-color:var(--amber); background:#fff6e0; }
  .callout.verde { border-left-color:var(--green); background:#e8f7ee; }
  .callout.vermelho { border-left-color:var(--red); background:#fdecec; }
  .callout.escuro { background:var(--ink); color:#fff; border-left-color:var(--ink); } .callout.escuro .k { color:#c9d2e3; }
  table { width:100%; border-collapse:collapse; font-size:9.2pt; }
  th { text-align:left; font-family:Consolas, monospace; font-size:7.5pt; letter-spacing:0.1em; color:var(--muted); text-transform:uppercase; background:#e9edf4; padding:6px 8px; }
  td { padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
  tr { break-inside:avoid; }
  td.code, .code { font-family:Consolas, monospace; color:var(--accent); white-space:nowrap; }
  .diag { border:1px solid var(--line); border-radius:10px; padding:12px 14px 8px; margin:8px 0 14px; break-inside:avoid; }
  .diag .cap-txt { font-size:8.8pt; color:var(--muted); margin-top:6px; }
  .diag .cap-txt b { color:var(--ink); }
  .camadas { display:grid; grid-template-columns:70px repeat(3,1fr); gap:6px 10px; align-items:stretch; }
  .camadas .rot { font-family:Consolas, monospace; font-size:7pt; letter-spacing:0.1em; color:var(--muted); text-transform:uppercase; align-self:center; }
  .camadas .cx { border:1px solid #9aa4b5; border-radius:5px; padding:6px 8px; text-align:center; background:#fff; }
  .camadas .cx b { display:block; font-size:9pt; color:var(--ink); }
  .camadas .cx span { font-size:7.6pt; color:var(--muted); }
  .camadas .cx.laranja { background:#fff4e5; border-color:var(--f2); }
  .camadas .cx.verde { background:#e8f7ee; border-color:var(--green); }
  .camadas .cx.cinza { background:var(--bg-soft); border-style:dashed; }
  .camadas .seta { text-align:center; color:#9aa4b5; font-size:11pt; line-height:1; }
  .pacotes { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
  .pac { border:1px solid var(--line); border-radius:8px; padding:9px 11px; break-inside:avoid; }
  .pac .k { font-family:Consolas, monospace; font-size:7.5pt; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); }
  .pac h3 { font-family:Consolas, monospace; font-size:11pt; color:var(--ink); margin:2px 0 4px; }
  .pac p { font-size:8.9pt; margin:0; }
  .escopo { display:grid; grid-template-columns:90px 1fr; gap:8px 12px; align-items:center; }
  .escopo .rot { font-family:Consolas, monospace; font-size:7pt; letter-spacing:0.1em; color:var(--muted); text-transform:uppercase; }
  .escopo .fila { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
  .escopo .cx { border:1px solid #9aa4b5; border-radius:6px; padding:7px 9px; text-align:center; background:#fff; }
  .escopo .cx b { display:block; font-size:9pt; color:var(--ink); } .escopo .cx span { font-size:7.8pt; color:var(--muted); }
  .escopo .cx.alvo { background:#fff4e5; border-color:var(--f2); border-width:2px; }
  .escopo .setas { display:grid; grid-template-columns:repeat(3,1fr); text-align:center; color:var(--accent); font-size:14pt; line-height:1; }
  .prox { display:grid; grid-template-columns:90px 1fr; gap:6px 12px; font-size:9.2pt; padding:6px 0; border-bottom:1px solid var(--line); }
  .prox b { font-family:Consolas, monospace; color:var(--accent); font-weight:normal; font-size:8.5pt; }
  .escolhas td:first-child { font-weight:700; color:var(--ink); white-space:nowrap; }
  .escolhas .alt { color:var(--muted); font-size:8.6pt; display:block; margin-top:3px; }
  .escolhas .alt b { color:var(--muted); font-weight:700; }
  .prop { display:inline-block; font-family:Consolas, monospace; font-size:7.5pt; padding:1px 7px; border-radius:10px; border:1px solid var(--amber); color:var(--amber); background:#fff6e0; vertical-align:middle; margin-left:6px; }
  ul.clean { margin:4px 0 0 16px; padding:0; font-size:9.3pt; } ul.clean li { margin:2px 0; }
  pre.cod { background:#0f1b33; color:#e6ecf5; border-radius:8px; padding:10px 12px; font-family:Consolas, "Cascadia Mono", monospace; font-size:8.2pt; line-height:1.4; white-space:pre-wrap; margin:6px 0 10px; break-inside:auto; }
  pre.cod.curto { break-inside:avoid; }
  .etapa { border:1px solid var(--line); border-radius:10px; margin:14px 0 10px; overflow:hidden; break-before:page; break-inside:auto; }
  .etapa-h, .etapa-r { break-after:avoid; }
  .etapa-h { color:#fff; padding:8px 12px; display:flex; align-items:center; gap:10px; }
  .etapa-h .k { font-family:Consolas, monospace; font-size:7.5pt; letter-spacing:0.12em; text-transform:uppercase; opacity:0.85; }
  .etapa-h b { font-size:13pt; flex:1; }
  .etapa-h .n { font-family:Consolas, monospace; font-size:8pt; opacity:0.9; }
  .etapa-r { background:var(--bg-soft); padding:7px 12px; font-size:9.2pt; border-bottom:1px solid var(--line); }
  .card-n { padding:9px 12px 10px; border-bottom:1px solid var(--line); break-inside:avoid; }
  .card-n:last-child { border-bottom:none; }
  .card-h { display:flex; align-items:center; gap:8px; margin-bottom:4px; flex-wrap:wrap; }
  .card-h .cid { color:#fff; font-family:Consolas, monospace; font-size:8.5pt; padding:2px 7px; border-radius:3px; }
  .card-h h3 { font-size:11.5pt; margin:0; flex:1; min-width:55%; }
  .pills { display:flex; gap:4px; flex-wrap:wrap; }
  .pill-c { font-family:Consolas, monospace; font-size:7.2pt; padding:1px 6px; border-radius:10px; border:1px solid var(--line); color:var(--muted); background:#fff; white-space:nowrap; }
  .pill-c.uc { color:var(--green); border-color:var(--green); background:#e8f7ee; }
  .card-b { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .card-b p { font-size:9pt; margin:0 0 2px; }
  .card-b ul.clean { font-size:8.8pt; margin-top:2px; }
  .card-b .lbl { font-family:Consolas, monospace; font-size:7.2pt; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); margin:4px 0 2px; }
  .aceite { background:#e8f7ee; border:1px solid #bfe3cc; border-radius:8px; padding:8px 10px; align-self:start; }
  .aceite p { font-size:9pt; }
  .cod-k { font-family:Consolas, monospace; font-size:7.5pt; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); margin:8px 0 2px; break-after:avoid; }
"""

# ---------- contagens ----------
n_caps = len(D["capitulos"])
n_escolhas = sum(len(b["linhas"]) for c in D["capitulos"] for b in c["blocos"] if b["tipo"] == "escolhas")
n_pacotes = sum(sum(1 for i in b["itens"] if i["rotulo"] == "Pacote") for c in D["capitulos"] for b in c["blocos"] if b["tipo"] == "pacotes")
n_cards = sum(len(et["cards"]) for c in D["capitulos"] for b in c["blocos"] if b["tipo"] == "cards" for et in b["etapas"])
n_ferramentas = sum(len(b.get("linhas", [])) for c in D["capitulos"] for b in c["blocos"] if b["tipo"] == "ferramentas")


def bloco(b):
    t = b["tipo"]
    if t == "callout":
        return f'<div class="callout {e(b.get("cor",""))}">{"<div class=k>" + e(b["titulo"]) + "</div>" if b.get("titulo") else ""}{e(b["texto"])}</div>'
    if t == "tabela":
        head = "".join(f"<th>{e(c)}</th>" for c in b["colunas"])
        rows = "".join("<tr>" + "".join(f'<td{" class=code" if i == 0 and b.get("primeira_mono") else ""}>{e(x)}</td>' for i, x in enumerate(r)) + "</tr>" for r in b["linhas"])
        tit = f'<h3 style="margin:10px 0 4px">{e(b["titulo"])}</h3>' if b.get("titulo") else ""
        return f'{tit}<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'
    if t == "lista":
        tit = f'<h3 style="margin:10px 0 2px">{e(b["titulo"])}</h3>' if b.get("titulo") else ""
        return tit + '<ul class="clean">' + "".join(f"<li>{e(i)}</li>" for i in b["itens"]) + "</ul>"
    if t == "codigo":
        curto = " curto" if b["texto"].count(chr(10)) < 40 else ""
        return (f'<div class="cod-k">{e(b["titulo"])}</div>' if b.get("titulo") else "") + f'<pre class="cod{curto}">{e(b["texto"])}</pre>'
    if t == "escopo_diagrama":
        acima = "".join(f'<div class="cx"><b>{e(c["t"])}</b><span>{e(c["s"])}</span></div>' for c in b["acima"])
        return (f'<div class="diag"><div class="escopo"><div class="rot">Sem isto não existe</div><div class="fila">{acima}</div>'
                f'<div></div><div class="setas">&#8595;&#8595;&#8595;</div>'
                f'<div class="rot">O que o jogador vê</div><div class="cx alvo"><b>{e(b["abaixo"]["t"])}</b><span>{e(b["abaixo"]["s"])}</span></div></div>'
                f'<div class="cap-txt">{e(b["legenda"])}</div></div>')
    if t == "camadas":
        h = ['<div class="diag"><div class="camadas">']
        for i, l in enumerate(b["linhas"]):
            if i:
                h.append('<div></div>' + ''.join('<div class="seta">&#8595;</div>' for _ in range(3)))
            h.append(f'<div class="rot">{e(l["rotulo"])}</div>')
            for c in l["caixas"]:
                h.append(f'<div class="cx {e(c.get("cor",""))}"><b>{e(c["t"])}</b><span>{e(c["s"])}</span></div>')
        h.append(f'</div><div class="cap-txt">{e(b["legenda"])}</div></div>')
        return "".join(h)
    if t == "pacotes":
        tit = f'<h3 style="margin:12px 0 6px">{e(b["titulo"])}</h3>' if b.get("titulo") else ""
        return tit + '<div class="pacotes">' + "".join(f'<div class="pac"><div class="k">{e(i["rotulo"])}</div><h3>{e(i["nome"])}</h3><p>{e(i["desc"])}</p></div>' for i in b["itens"]) + "</div>"
    if t == "escolhas":
        rows = "".join(f'<tr><td>{e(l["escolha"])}</td><td>{e(l["proposta"])}</td><td>{e(l["porque"])}<span class="alt"><b>Alternativa considerada:</b> {e(l["alternativa"])}</span></td></tr>' for l in b["linhas"])
        return (f'<h3 style="margin:14px 0 4px">{e(b["titulo"])}<span class="prop">proposta</span></h3><p style="font-size:9pt;color:var(--muted);margin-bottom:6px">{e(b["nota"])}</p>'
                f'<table class="escolhas"><thead><tr><th>Escolha</th><th>O que propomos</th><th>Por quê</th></tr></thead><tbody>{rows}</tbody></table>')
    if t == "provas":
        rows = "".join(f'<tr><td>{e(p["tentativa"])}</td><td class="mono" style="font-size:8.2pt;color:var(--ink)">{e(p["resposta"])}</td></tr>' for p in b["linhas"])
        return (f'<h3 style="margin:12px 0 4px">{e(b["titulo"])}</h3>'
                f'<table><thead><tr><th>O que tentamos fazer</th><th>O que o banco respondeu</th></tr></thead><tbody>{rows}</tbody></table>')
    if t == "ferramentas":
        rows = "".join(f'<tr><td class="code">{e(l["nome"])}</td><td>{e(l["quem"])}</td><td>{e(l["faz"])}</td><td>{e(l["devolve"])}</td><td class="code" style="font-size:7.8pt">{e(l["casos"])}</td></tr>' for l in b["linhas"])
        return (f'<h3 style="margin:12px 0 4px">{e(b["titulo"])}</h3>' + (f'<p style="font-size:9pt;color:var(--muted)">{e(b["nota"])}</p>' if b.get("nota") else "")
                + f'<table><thead><tr><th>Ferramenta</th><th>Quem chama</th><th>O que faz</th><th>O que devolve</th><th>Casos</th></tr></thead><tbody>{rows}</tbody></table>')
    if t == "sequencia":
        return f'<div class="diag">{sequencia_svg(b)}<div class="cap-txt"><b>{e(b["titulo"])}.</b> {e(b["legenda"])}</div></div>'
    if t == "estados":
        return f'<div class="diag">{estados_svg(b)}<div class="cap-txt"><b>{e(b["titulo"])}.</b> {e(b["legenda"])}</div></div>'
    if t == "transicoes":
        rows = "".join(f'<tr><td class="code">{e(l[0])}</td><td class="code">{e(l[1])}</td><td class="code" style="color:var(--green)">{e(l[2])}</td><td>{e(l[3])}</td></tr>' for l in b["linhas"])
        return (f'<h3 style="margin:12px 0 4px">{e(b["titulo"])}</h3>' + (f'<p style="font-size:9pt;color:var(--muted)">{e(b["nota"])}</p>' if b.get("nota") else "")
                + f'<table><thead><tr><th>Estado atual</th><th>Evento</th><th>Novo estado</th><th>O que acontece junto</th></tr></thead><tbody>{rows}</tbody></table>')
    if t == "grade":
        cols = b.get("colunas", 2)
        cards = "".join(f'<div class="box"><h3>{e(i["t"])}</h3><p>{e(i["s"])}</p></div>' for i in b["itens"])
        return (f'<h3 style="margin:12px 0 2px">{e(b["titulo"])}</h3>' if b.get("titulo") else "") + f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:8px">{cards}</div>'
    if t == "cards":
        return cards_html(b)
    raise ValueError("bloco desconhecido: " + t)


CORES_ETAPA = {"cinza": "#6b7588", "azul": "#1f4fd1", "verde": "#1f9d55", "laranja": "#e08a1e", "roxo": "#6f42c1", "marinho": "#0f1b33"}


def grafo_svg(etapas):
    cols = len(etapas)
    maxn = max(len(e["cards"]) for e in etapas)
    W = 700
    cw = W / cols
    bw, bh, gy = 74, 26, 36
    H = 40 + maxn * gy
    pos = {}
    for i, e in enumerate(etapas):
        for j, c in enumerate(e["cards"]):
            pos[c["id"]] = (cw * i + cw / 2, 44 + j * gy)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">',
           '<defs><marker id="ag" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 Z" fill="#9aa4b5"/></marker></defs>']
    for i, e in enumerate(etapas):
        cor = CORES_ETAPA.get(e["cor"], "#6b7588")
        out.append(f'<rect x="{cw*i + 8}" y="6" width="{cw - 16}" height="20" rx="4" fill="{cor}"/>')
        out.append(f'<text x="{cw*i + cw/2}" y="20" text-anchor="middle" font-size="8" font-weight="700" fill="#fff">{e["id"]} · {e_(e["nome"])}</text>')
    for e in etapas:
        for c in e["cards"]:
            x2, y2 = pos[c["id"]]
            for d in c["depois"]:
                x1, y1 = pos[d]
                if abs(x1 - x2) < 1:
                    out.append(f'<line x1="{x1}" y1="{y1 + bh/2}" x2="{x2}" y2="{y2 - bh/2}" stroke="#9aa4b5" stroke-width="0.9" marker-end="url(#ag)"/>')
                else:
                    out.append(f'<path d="M{x1 + bw/2},{y1} C{(x1 + x2)/2},{y1} {(x1 + x2)/2},{y2} {x2 - bw/2},{y2}" fill="none" stroke="#9aa4b5" stroke-width="0.9" marker-end="url(#ag)"/>')
    for e in etapas:
        cor = CORES_ETAPA.get(e["cor"], "#6b7588")
        for c in e["cards"]:
            x, y = pos[c["id"]]
            out.append(f'<rect x="{x - bw/2}" y="{y - bh/2}" width="{bw}" height="{bh}" rx="4" fill="#fff" stroke="{cor}" stroke-width="1.2"/>')
            out.append(f'<text x="{x}" y="{y + 3.5}" text-anchor="middle" font-size="8.5" font-family="Consolas, monospace" fill="#0f1b33">{c["id"]}</text>')
    out.append('</svg>')
    return "".join(out)


def e_(s):
    return e(s)


def cards_html(b):
    etapas = b["etapas"]
    h = []
    # visão geral
    rows = "".join(f'<tr><td><span style="display:inline-block;background:{CORES_ETAPA.get(et["cor"],"#6b7588")};color:#fff;font-family:Consolas,monospace;font-size:7.5pt;padding:1px 6px;border-radius:3px">{et["id"]}</span></td><td><b>{e(et["nome"])}</b></td><td>{e(et["resumo"])}</td><td class="code">{len(et["cards"])} cards</td></tr>' for et in etapas)
    h.append(f'<table><thead><tr><th>Etapa</th><th></th><th>O que muda no fim dela</th><th>Cards</th></tr></thead><tbody>{rows}</tbody></table>')
    h.append(f'<div class="callout azul"><div class="k">Como usar estes cards</div>{e(b["nota"])}</div>')
    h.append(f'<div class="diag" style="margin-top:12px">{grafo_svg(etapas)}<div class="cap-txt"><b>Quem depende de quem.</b> As setas mostram o que precisa estar pronto antes. Cards na mesma coluna sem seta entre si podem ser feitos em paralelo. As etapas S0 e S1 são sequenciais de verdade; a partir de S2, os cards de mesa e os de importação podem andar lado a lado.</div></div>')
    for et in etapas:
        cor = CORES_ETAPA.get(et["cor"], "#6b7588")
        h.append(f'<div class="etapa" style="border-color:{cor}"><div class="etapa-h" style="background:{cor}"><span class="k">Etapa {et["id"]}</span><b>{e(et["nome"])}</b><span class="n">{len(et["cards"])} cards</span></div><div class="etapa-r">{e(et["resumo"])}</div>')
        for c in et["cards"]:
            entra = "".join(f"<li>{e(i)}</li>" for i in c["entra"])
            dep = f'<span class="pill-c">depois de {e(", ".join(c["depois"]))}</span>' if c["depois"] else '<span class="pill-c">sem dependência</span>'
            casos = f'<span class="pill-c uc">{e(c["casos"])}</span>' if c["casos"] else ""
            h.append(f'''<div class="card-n"><div class="card-h"><span class="cid" style="background:{cor}">{c["id"]}</span><h3>{e(c["nome"])}</h3><span class="pills">{dep}{casos}</span></div>
<div class="card-b"><div><div class="lbl">Por que este card existe</div><p>{e(c["porque"])}</p><div class="lbl">O que entra no repositório</div><ul class="clean">{entra}</ul></div>
<div class="aceite"><div class="lbl" style="color:var(--green)">Critério de aceite</div><p><b>Dado</b> {e(c["aceite"]["dado"])}, <b>quando</b> {e(c["aceite"]["quando"])}, <b>então</b> {e(c["aceite"]["entao"])}</p></div></div></div>''')
        h.append('</div>')
    return "".join(h)


def sequencia_svg(seq):
    cols = seq["colunas"]
    W = 680
    cw = W / len(cols)
    H = 40 + len(seq["passos"]) * 28 + 16
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">']
    xs = [cw * i + cw / 2 for i in range(len(cols))]
    for i, c in enumerate(cols):
        out.append(f'<rect x="{xs[i] - cw/2 + 6}" y="4" width="{cw - 12}" height="22" rx="4" fill="#e9edf4" stroke="#9aa4b5"/>')
        out.append(f'<text x="{xs[i]}" y="19" text-anchor="middle" font-size="8" font-weight="700" fill="#0f1b33">{e(c)}</text>')
        out.append(f'<line x1="{xs[i]}" y1="26" x2="{xs[i]}" y2="{H - 6}" stroke="#b9c2d0" stroke-dasharray="3 3"/>')
    for k, p in enumerate(seq["passos"]):
        y = 46 + k * 28
        if p.get("nota"):
            x = xs[p["de"]]
            out.append(f'<rect x="{x - 90}" y="{y - 9}" width="180" height="16" rx="3" fill="#fff6e0" stroke="#c77d0a"/>')
            out.append(f'<text x="{x}" y="{y + 3}" text-anchor="middle" font-size="7" fill="#333">{e(p["t"])}</text>')
            continue
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


def estados_svg(b):
    # estados em linhas (grade), setas rotuladas entre eles
    estados = b["estados"]            # [{id, nome, sub, cor}]
    cores = {"azul": ("#eaf0ff", "#1f4fd1"), "verde": ("#e8f7ee", "#1f9d55"), "laranja": ("#fff4e5", "#e08a1e"), "vermelho": ("#fdecec", "#c53030"), "cinza": ("#f3f5f9", "#6b7588")}
    por_linha = b.get("por_linha", 4)
    W = 680
    bw, bh = 118, 40
    gx = (W - 20) / por_linha
    pos = {}
    for i, s in enumerate(estados):
        r, c = divmod(i, por_linha)
        pos[s["id"]] = (10 + c * gx + gx / 2, 36 + r * 90)
    H = 36 + ((len(estados) - 1) // por_linha + 1) * 90
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">',
           '<defs><marker id="ar" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#1f4fd1"/></marker></defs>']
    rotulos = []
    def rotulo(x, y, txt):
        w = len(txt) * 3.9 + 6
        rotulos.append(f'<rect x="{x - w/2}" y="{y - 7}" width="{w}" height="10" rx="2" fill="#fff" fill-opacity="0.92"/>'
                       f'<text x="{x}" y="{y + 1}" text-anchor="middle" font-size="6.6" fill="#1f4fd1">{e(txt)}</text>')
    k_cross = 0
    for t in b["setas"]:                # [de, para, rotulo, estilo]
        (x1, y1), (x2, y2) = pos[t[0]], pos[t[1]]
        dash = ' stroke-dasharray="4 3"' if (len(t) > 3 and t[3] == "tracejada") else ""
        if abs(y1 - y2) < 1 and abs(x1 - x2) < 1:   # laço no mesmo estado
            out.append(f'<path d="M{x1 + 20},{y1 - bh/2} C{x1 + 40},{y1 - bh/2 - 26} {x1 - 40},{y1 - bh/2 - 26} {x1 - 20},{y1 - bh/2}" fill="none" stroke="#1f4fd1" stroke-width="1.2" marker-end="url(#ar)"{dash}/>')
            rotulo(x1, y1 - bh/2 - 24, t[2])
        elif abs(y1 - y2) < 1:          # mesma linha
            sx, ex = (x1 + bw / 2, x2 - bw / 2) if x2 > x1 else (x1 - bw / 2, x2 + bw / 2)
            dy = -3 if x2 > x1 else 3
            out.append(f'<line x1="{sx}" y1="{y1 + dy}" x2="{ex}" y2="{y2 + dy}" stroke="#1f4fd1" stroke-width="1.2" marker-end="url(#ar)"{dash}/>')
            rotulo((sx + ex) / 2, y1 + (dy - 8 if dy < 0 else dy + 9), t[2])
        else:
            sy, ey = (y1 + bh / 2, y2 - bh / 2) if y2 > y1 else (y1 - bh / 2, y2 + bh / 2)
            my = (sy + ey) / 2 + (k_cross % 3 - 1) * 9
            k_cross += 1
            out.append(f'<path d="M{x1},{sy} L{x1},{my} L{x2},{my} L{x2},{ey}" fill="none" stroke="#1f4fd1" stroke-width="1.2" marker-end="url(#ar)"{dash}/>')
            rotulo((x1 + x2) / 2 if abs(x1 - x2) > 60 else x1 + 70, my - 1, t[2])
    for s in estados:
        x, y = pos[s["id"]]
        fill, stroke = cores.get(s.get("cor", "cinza"), cores["cinza"])
        out.append(f'<rect x="{x - bw/2}" y="{y - bh/2}" width="{bw}" height="{bh}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')
        out.append(f'<text x="{x}" y="{y - 2}" text-anchor="middle" font-size="8.5" font-weight="700" fill="#0f1b33">{e(s["nome"])}</text>')
        out.append(f'<text x="{x}" y="{y + 10}" text-anchor="middle" font-size="6.6" fill="#5b6577">{e(s.get("sub",""))}</text>')
    out.extend(rotulos)
    out.append('</svg>')
    return "".join(out)


def capa():
    stats = [(len(D["capitulos"]), "capítulos nesta entrega"), (49, "casos de uso da fase 1 cobertos"),
             (n_pacotes, "pacotes do código"), (n_escolhas, "escolhas de tecnologia propostas")]
    if n_cards:
        stats[3] = (n_cards, "cards na ordem de execução")
    st = "".join(f'<div class="stat"><div class="big">{v}</div><div class="stl">{e(l)}</div></div>' for v, l in stats)
    return f'''<section class="capa"><div class="kicker">{e(D["kicker"])}</div><h1>{e(D["titulo"])}</h1>
<p class="lead">{e(D["intro"])}</p>
<div class="callout amarelo" style="max-width:150mm"><div class="k">Estado desta versão</div>{e(D["entrega"])}</div>
<div class="stats">{st}</div>
<div class="box"><h3>Para quem escrevemos isto</h3><p>{e(D["para_quem"])}</p></div>
<div class="box"><h3>A regra que organiza todo o documento</h3><p>{e(D["regra"])}</p></div>
<p style="font-size:8.8pt;color:var(--muted);margin-top:12px;border-top:1px solid var(--line);padding-top:8px">{e(D["produto"])} · mestre por inteligência artificial para D&amp;D 5e, regras de 2024, SRD 5.2 em CC-BY-4.0 · acompanha o Mapa do Projeto (revisão 5) e os Casos de Uso (56 fichas)</p>
</section>'''


def capitulo(c):
    return f'<section class="cap"><div class="kicker">{e(c["kicker"])}</div><h2>{e(c["titulo"])}</h2><p class="lead">{e(c["lead"])}</p>' + "".join(bloco(b) for b in c["blocos"]) + "</section>"


def proximas():
    if not D.get("proximas"):
        return ""
    return ('<section class="cap"><div class="kicker">O que vem nas próximas entregas</div><h2>O resto do documento, já encomendado</h2>'
            '<p class="lead">Cada entrega passa pelo mesmo portão: o cliente lê, aprova ou corrige, e só então a seguinte começa.</p>'
            + "".join(f'<div class="prox"><b>{e(p["n"])}</b><span>{e(p["t"])}</span></div>' for p in D["proximas"]) + "</section>")


html = f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{e(D["titulo"])} · {e(D["produto"])}</title><style>{CSS}</style></head><body>{capa()}{"".join(capitulo(c) for c in D["capitulos"])}{proximas()}</body></html>'
SAIDA.write_text(html, encoding="utf-8")
print(f"ok {SAIDA.name}: {n_caps} capítulos, {n_escolhas} escolhas, {n_pacotes} pacotes, {n_cards} cards, {n_ferramentas} ferramentas")
