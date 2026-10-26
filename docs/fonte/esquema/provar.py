# -*- coding: utf-8 -*-
"""Executa os dois esquemas num SQLite limpo, aplica a semente e roda as provas.

Uso: python provar.py  -> imprime um JSON com o resultado de cada prova (vai para o documento).
"""
import json
import sqlite3
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def abrir(nome):
    con = sqlite3.connect(":memory:")
    con.executescript((AQUI / nome).read_text(encoding="utf-8"))
    return con


def tenta(con, sql, params=()):
    try:
        con.execute(sql, params)
        con.commit()
        return "ok"
    except sqlite3.Error as ex:
        con.rollback()
        return f"{type(ex).__name__}: {ex}"


provas = []

# ---------- campanha viva ----------
c = abrir("campanha.sql")
c.execute("insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao) values ('cp1','Teste','av-porao',1,'semente-abc','adulto')")
c.execute("insert into sessao (id, campanha_id, numero) values ('s1','cp1',1)")
c.execute("insert into diario (campanha_id, sessao_id, tipo, origem, dados) values ('cp1','s1','rolagem','E01','{}')")
seq = c.execute("select max(seq) from diario").fetchone()[0]
c.execute("insert into rolagem (seq, campanha_id, contador, expressao, modo, dados, modificadores, total, motivo) values (?, 'cp1', 1, '1d20+3', 'normal', '[14]', '{\"destreza\":3}', 17, 'teste de Atletismo')", (seq,))
c.commit()

provas.append({"tentativa": "Alterar um registro do diário (update diario set dados = ...)",
               "resposta": tenta(c, "update diario set dados = '{\"x\":1}' where seq = ?", (seq,))})
provas.append({"tentativa": "Apagar um registro do diário (delete from diario)",
               "resposta": tenta(c, "delete from diario where seq = ?", (seq,))})
c.execute("insert into diario (campanha_id, sessao_id, tipo, origem, dados) values ('cp1','s1','rolagem','E01','{}')")
c.commit()
seq2 = c.execute("select max(seq) from diario").fetchone()[0]
provas.append({"tentativa": "Gravar uma segunda rolagem com o mesmo contador da campanha",
               "resposta": tenta(c, "insert into rolagem (seq, campanha_id, contador, expressao, modo, dados, modificadores, total, motivo) values (?, 'cp1', 1, '1d20', 'normal', '[9]', '{}', 9, 'repetida')", (seq2,))})
provas.append({"tentativa": "Gravar uma rolagem informada em dado físico (contador nulo)",
               "resposta": tenta(c, "insert into rolagem (seq, campanha_id, contador, expressao, modo, dados, modificadores, total, motivo, informada) values (?, 'cp1', null, '1d20', 'normal', '[9]', '{}', 9, 'dado físico', 1)", (seq2,))})
c.execute("insert into diario (campanha_id, sessao_id, tipo, origem, dados) values ('cp1','s1','desvio','F02','{}')")
c.commit()
seq3 = c.execute("select max(seq) from diario").fetchone()[0]
c.execute("insert into desvio (seq, campanha_id, o_que_mudou, motivo, regra) values (?, 'cp1', 'taverneiro foge', 'reação do jogador', 'RN-02')", (seq3,))
c.commit()
provas.append({"tentativa": "Marcar um desvio como revisado (update desvio set revisado = 1)",
               "resposta": tenta(c, "update desvio set revisado = 1 where seq = ?", (seq3,))})
provas.append({"tentativa": "Reescrever o motivo de um desvio já registrado",
               "resposta": tenta(c, "update desvio set motivo = 'outro' where seq = ?", (seq3,))})
provas.append({"tentativa": "Criar campanha sem semente de rolagens",
               "resposta": tenta(c, "insert into campanha (id, nome, aventura_id, modulo_versao, semente, classificacao) values ('cp2','x','av',1,null,'livre')")})
provas.append({"tentativa": "Veredito de teste com dificuldade 45, fora da escala do SRD",
               "resposta": tenta(c, "insert into diario (campanha_id, sessao_id, tipo, origem, dados) values ('cp1','s1','veredito','C05','{}')") and
                           tenta(c, "insert into veredito (seq, campanha_id, situacao, tipo, pericia, dificuldade) values ((select max(seq) from diario), 'cp1', 'escalar o muro', 'teste', 'Atletismo', 45)")})

# ---------- aventura e módulo canônico ----------
a = abrir("aventura.sql")
a.executescript((AQUI / "semente.sql").read_text(encoding="utf-8"))
n_itens = a.execute("select count(*) from item_canonico where aventura_id='av-porao' and versao=1").fetchone()[0]
n_lig = a.execute("select count(*) from ligacao where aventura_id='av-porao' and versao=1").fetchone()[0]
provas.append({"tentativa": "Aplicar a semente: a aventura original mínima, versão 1 publicada",
               "resposta": f"ok: {n_itens} itens canônicos e {n_lig} ligações gravados"})
provas.append({"tentativa": "Alterar um item de uma versão publicada do módulo",
               "resposta": tenta(a, "update item_canonico set nome = 'x' where id = 'cena-porao' and versao = 1")})
provas.append({"tentativa": "Acrescentar uma cena a uma versão publicada",
               "resposta": tenta(a, "insert into item_canonico (id, aventura_id, versao, tipo, nome, dados) values ('cena-nova','av-porao',1,'cena','Nova','{}')")})
provas.append({"tentativa": "Gravar um segredo sem condição de descoberta",
               "resposta": tenta(a, "insert into modulo_versao (aventura_id, versao, origem, impressao_texto) values ('av-porao', 2, 'importado', 'sha256:v2')") and
                           tenta(a, "insert into item_canonico (id, aventura_id, versao, tipo, nome, dados, segredo) values ('seg-x','av-porao',2,'segredo','Sem condição','{}',1)")})
provas.append({"tentativa": "Acrescentar uma cena ao rascunho da versão 2, ainda não publicada",
               "resposta": tenta(a, "insert into item_canonico (id, aventura_id, versao, tipo, nome, dados) values ('cena-nova','av-porao',2,'cena','Nova','{}')")})
provas.append({"tentativa": "Mapear uma criatura sem SRD, sem ficha própria e sem marca de pendente",
               "resposta": tenta(a, "insert into mapeamento_srd (aventura_id, versao, item_id, srd_versao) values ('av-porao', 2, 'cena-nova', '5.2.1')")})

caminho = a.execute("""
  with recursive passo(item, n) as (
    select 'cena-taverna', 0
    union all
    select l.para_item, n + 1 from ligacao l join passo p on l.de_item = p.item
    where l.aventura_id = 'av-porao' and l.versao = 1 and l.caminho_critico = 1 and n < 20)
  select group_concat(item, ' -> ') from passo""").fetchone()[0]
provas.append({"tentativa": "Percorrer o caminho crítico da semente a partir da primeira cena",
               "resposta": f"ok: {caminho}"})

tabelas_c = c.execute("select count(*) from sqlite_master where type='table' and name not like 'sqlite_%'").fetchone()[0]
gatilhos_c = c.execute("select count(*) from sqlite_master where type='trigger'").fetchone()[0]
tabelas_a = a.execute("select count(*) from sqlite_master where type='table' and name not like 'sqlite_%'").fetchone()[0]
gatilhos_a = a.execute("select count(*) from sqlite_master where type='trigger'").fetchone()[0]

resultado = {"sqlite": sqlite3.sqlite_version, "python": sys.version.split()[0],
             "campanha": {"tabelas": tabelas_c, "gatilhos": gatilhos_c},
             "aventura": {"tabelas": tabelas_a, "gatilhos": gatilhos_a},
             "provas": provas}
(AQUI / "provas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(resultado, ensure_ascii=False, indent=2))
