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
  pre.cod { background:#0f1b33; color:#e6ecf5; border-radius:8px; padding:10px 12px; font-family:Consolas, "Cascadia Mono", monospace; font-size:8.2pt; line-height:1.4; white-space:pre-wrap; margin:6px 0 10px; break-inside:avoid; }
  .cod-k { font-family:Consolas, monospace; font-size:7.5pt; letter-spacing:0.12em; text-transform:uppercase; color:var(--muted); margin:8px 0 2px; }
"""

# ---------- contagens ----------
n_caps = len(D["capitulos"])
n_escolhas = sum(len(b["linhas"]) for c in D["capitulos"] for b in c["blocos"] if b["tipo"] == "escolhas")
n_pacotes = sum(sum(1 for i in b["itens"] if i["rotulo"] == "Pacote") for c in D["capitulos"] for b in c["blocos"] if b["tipo"] == "pacotes")
n_cards = sum(len(b.get("cards", [])) for c in D["capitulos"] for b in c["blocos"] if b["tipo"] == "cards")
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
        return (f'<div class="cod-k">{e(b["titulo"])}</div>' if b.get("titulo") else "") + f'<pre class="cod">{e(b["texto"])}</pre>'
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
    raise ValueError("bloco desconhecido: " + t)


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
<p style="font-size:8.8pt;color:var(--muted);margin-top:12px;border-top:1px solid var(--line);padding-top:8px">{e(D["produto"])} · mestre por inteligência artificial para D&amp;D 5e, regras de 2024, SRD 5.2 em CC-BY-4.0 · acompanha o Mapa do Projeto (revisão 4) e os Casos de Uso (56 fichas)</p>
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
