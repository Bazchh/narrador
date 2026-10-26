"""Carrega o subconjunto do SRD 5.2.1 do esqueleto (card N-04) para o pacote.

Fonte de verdade: o PDF oficial em dados/srd/SRD_CC_v5.2.1.pdf (CC-BY-4.0). Acelerador: os
arquivos JSON abertos do projeto open5e para o SRD 2024, baixados sob demanda para uma
pasta temporária e NÃO versionados (licença dos arquivos derivados não declarada). Cada
registro só entra se a página do PDF que o contém for encontrada; a saída é
src/narrador/srd/dados/esqueleto.json.

Uso: python ferramentas/carregar_srd.py [--open5e PASTA]
Ferramenta de desenvolvimento: usa rede quando precisa baixar; nunca roda em teste.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import urllib.request
import warnings
from pathlib import Path
from typing import Any

import pymupdf

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from narrador.srd.atribuicao import ATRIBUICAO  # noqa: E402
from narrador.srd.modelo import (  # noqa: E402
    VERSAO_SRD,
    Arma,
    Armadura,
    Ataque,
    Atributo,
    Classe,
    Condicao,
    Criatura,
    Especie,
    Pericia,
    Srd,
    Traco,
)

PDF = RAIZ / "dados" / "srd" / "SRD_CC_v5.2.1.pdf"
SAIDA = RAIZ / "src" / "narrador" / "srd" / "dados" / "esqueleto.json"
OPEN5E = "https://raw.githubusercontent.com/open5e/open5e-api/staging/data/v2/wizards-of-the-coast/srd-2024/{}.json"
MODELOS = [
    "Creature",
    "CreatureAction",
    "CreatureTrait",
    "Weapon",
    "WeaponProperty",
    "WeaponPropertyAssignment",
    "Armor",
    "SkillDescription",
    "ConditionDescription",
    "Species",
    "SpeciesTrait",
    "CharacterClass",
    "ClassFeature",
]

# ---- o subconjunto do esqueleto e os nomes em português ----------------------------------

CRIATURAS = {"Giant Rat": "Rato gigante"}
ESPECIES = {"Human": "Humano"}
CLASSES = {"Fighter": "Guerreiro"}
TRACOS_NIVEL_1 = {"Fighter": ["Fighting Style", "Second Wind", "Weapon Mastery"]}
ARMAS = {
    "Battleaxe": "Machado de batalha",
    "Blowgun": "Zarabatana",
    "Club": "Clava",
    "Dagger": "Adaga",
    "Dart": "Dardo",
    "Flail": "Mangual",
    "Glaive": "Glaive",
    "Greataxe": "Machado grande",
    "Greatclub": "Clava grande",
    "Greatsword": "Espada grande",
    "Halberd": "Alabarda",
    "Hand Crossbow": "Besta de mão",
    "Handaxe": "Machadinha",
    "Heavy Crossbow": "Besta pesada",
    "Javelin": "Azagaia",
    "Lance": "Lança de justa",
    "Light Crossbow": "Besta leve",
    "Light Hammer": "Martelo leve",
    "Longbow": "Arco longo",
    "Longsword": "Espada longa",
    "Mace": "Maça",
    "Maul": "Malho",
    "Morningstar": "Estrela-da-manhã",
    "Musket": "Mosquete",
    "Pike": "Pique",
    "Pistol": "Pistola",
    "Quarterstaff": "Bordão",
    "Rapier": "Rapieira",
    "Scimitar": "Cimitarra",
    "Shortbow": "Arco curto",
    "Shortsword": "Espada curta",
    "Sickle": "Foice",
    "Sling": "Funda",
    "Spear": "Lança",
    "Trident": "Tridente",
    "War Pick": "Picareta de guerra",
    "Warhammer": "Martelo de guerra",
    "Whip": "Chicote",
}
ARMADURAS: dict[str, tuple[str, str]] = {
    "Padded Armor": ("Armadura acolchoada", "leve"),
    "Leather Armor": ("Armadura de couro", "leve"),
    "Studded Leather Armor": ("Couro batido", "leve"),
    "Hide Armor": ("Armadura de peles", "media"),
    "Chain Shirt": ("Camisa de malha", "media"),
    "Scale Mail": ("Brunea", "media"),
    "Breastplate": ("Peitoral", "media"),
    "Half Plate Armor": ("Meia armadura", "media"),
    "Ring Mail": ("Cota de anéis", "pesada"),
    "Chain Mail": ("Cota de malha", "pesada"),
    "Splint Armor": ("Armadura de talas", "pesada"),
    "Plate Armor": ("Armadura de placas", "pesada"),
    "Shield": ("Escudo", "escudo"),
}
FORCA_MINIMA = {"Chain Mail": 13, "Splint Armor": 15, "Plate Armor": 15}
FURTIVIDADE_DESVANTAGEM = {
    "Padded Armor",
    "Scale Mail",
    "Half Plate Armor",
    "Ring Mail",
    "Chain Mail",
    "Splint Armor",
    "Plate Armor",
}
PERICIAS: dict[str, tuple[str, Atributo]] = {
    "Acrobatics": ("Acrobacia", "dex"),
    "Animal Handling": ("Lidar com Animais", "wis"),
    "Arcana": ("Arcanismo", "int"),
    "Athletics": ("Atletismo", "str"),
    "Deception": ("Enganação", "cha"),
    "History": ("História", "int"),
    "Insight": ("Intuição", "wis"),
    "Intimidation": ("Intimidação", "cha"),
    "Investigation": ("Investigação", "int"),
    "Medicine": ("Medicina", "wis"),
    "Nature": ("Natureza", "int"),
    "Perception": ("Percepção", "wis"),
    "Performance": ("Atuação", "cha"),
    "Persuasion": ("Persuasão", "cha"),
    "Religion": ("Religião", "int"),
    "Sleight of Hand": ("Prestidigitação", "dex"),
    "Stealth": ("Furtividade", "dex"),
    "Survival": ("Sobrevivência", "wis"),
}
CONDICOES = {
    "Blinded": "Cego",
    "Charmed": "Enfeitiçado",
    "Deafened": "Surdo",
    "Exhaustion": "Exaustão",
    "Frightened": "Amedrontado",
    "Grappled": "Agarrado",
    "Incapacitated": "Incapacitado",
    "Invisible": "Invisível",
    "Paralyzed": "Paralisado",
    "Petrified": "Petrificado",
    "Poisoned": "Envenenado",
    "Prone": "Caído",
    "Restrained": "Impedido",
    "Stunned": "Atordoado",
    "Unconscious": "Inconsciente",
}
DANO_PT = {
    "acid": "ácido",
    "bludgeoning": "contundente",
    "cold": "frio",
    "fire": "fogo",
    "force": "energia",
    "lightning": "elétrico",
    "necrotic": "necrótico",
    "piercing": "perfurante",
    "poison": "veneno",
    "psychic": "psíquico",
    "radiant": "radiante",
    "slashing": "cortante",
    "thunder": "trovão",
}
PE_POR_ND = {"0": 10, "0.125": 25, "0.25": 50, "0.5": 100, "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800}

# ---- utilidades ------------------------------------------------------------------------


def slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")


def sem_espacos(texto: str) -> str:
    return re.sub(r"\s+", "", texto)


def baixar_open5e(pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for modelo in MODELOS:
        destino = pasta / f"{modelo}.json"
        if destino.exists():
            continue
        print(f"baixando {modelo}.json")
        with urllib.request.urlopen(OPEN5E.format(modelo), timeout=60) as resp:
            destino.write_bytes(resp.read())


def carregar_open5e(pasta: Path) -> dict[str, list[dict[str, Any]]]:
    return {m: json.loads((pasta / f"{m}.json").read_text(encoding="utf-8")) for m in MODELOS}


class Pdf:
    """Localiza a página do PDF que contém todas as marcas pedidas."""

    def __init__(self, caminho: Path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.doc = pymupdf.open(str(caminho))
        self.textos = [self.doc[i].get_text() for i in range(self.doc.page_count)]
        self.sha256 = hashlib.sha256(caminho.read_bytes()).hexdigest()

    def pagina(self, *marcas: str, a_partir_de: int = 1) -> int:
        for i in range(a_partir_de - 1, len(self.textos)):
            if all(m in self.textos[i] for m in marcas):
                return i + 1
        raise LookupError(f"não achei no PDF uma página com {marcas!r}")


def campos(itens: list[dict[str, Any]], nome: str) -> dict[str, Any]:
    for it in itens:
        if it["fields"].get("name") == nome:
            f = dict(it["fields"])
            f["pk"] = it["pk"]
            return f
    raise LookupError(f"open5e não tem {nome!r}")


def filhos(itens: list[dict[str, Any]], pai: str) -> list[dict[str, Any]]:
    return [it["fields"] for it in itens if it["fields"].get("parent") == pai]


ATAQUE = re.compile(
    r"(?P<tipo>Melee|Ranged) Attack Roll: \+(?P<bonus>\d+), (?:reach|range) (?P<alcance>\d+)[^.]*\.\s*"
    r"(?:Hit: )?\d+ \((?P<dados>\d+d\d+(?:\s*[+-]\s*\d+)?)\) (?P<dano>\w+) damage",
    re.IGNORECASE,
)


def montar_criatura(nome: str, nome_pt: str, dados: dict[str, list[dict[str, Any]]], pdf: Pdf) -> Criatura:
    c = campos(dados["Creature"], nome)
    tracos = [Traco(nome=t["name"], descricao=t["desc"]) for t in filhos(dados["CreatureTrait"], c["pk"])]
    ataques, acoes = [], []
    for a in filhos(dados["CreatureAction"], c["pk"]):
        m = ATAQUE.search(a["desc"])
        if m:
            ataques.append(
                Ataque(
                    nome=a["name"],
                    tipo="corpo_a_corpo" if m["tipo"].lower() == "melee" else "distancia",
                    bonus=int(m["bonus"]),
                    alcance_pes=int(m["alcance"]),
                    dano_dados=re.sub(r"\s+", "", m["dados"]),
                    dano_tipo=DANO_PT.get(m["dano"].lower(), m["dano"].lower()),
                    descricao=a["desc"],
                )
            )
        else:
            acoes.append(Traco(nome=a["name"], descricao=a["desc"]))
    primeira_marca = tracos[0].nome if tracos else (ataques[0].nome if ataques else nome)
    pagina = pdf.pagina(nome, primeira_marca, a_partir_de=250)
    extras = {
        k: int(v)
        for k, v in (("escalar", c.get("climb")), ("nadar", c.get("swim")), ("voar", c.get("fly")))
        if v
    }
    nd = str(c["challenge_rating"])
    return Criatura(
        id=f"srd:criatura:{slug(nome)}",
        nome=nome,
        nome_pt=nome_pt,
        pagina=pagina,
        tamanho=c["size"],
        tipo=c["type"],
        tendencia=c["alignment"],
        classe_armadura=int(c["armor_class"]),
        pontos_de_vida=int(c["hit_points"]),
        dados_de_vida=c["hit_dice"],
        velocidade_pes=int(c["walk"] or 0),
        velocidades_extras=extras,
        atributos={
            a: int(c[f"ability_score_{n}"])
            for a, n in zip(
                ("str", "dex", "con", "int", "wis", "cha"),
                ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"),
                strict=True,
            )
        },
        bonus_iniciativa=int(c["initiative_bonus"]),
        percepcao_passiva=int(c["passive_perception"]),
        nivel_de_desafio=nd,
        pontos_de_experiencia=int(c.get("experience_points_integer") or PE_POR_ND[nd]),
        bonus_proficiencia=2,
        tracos=tracos,
        ataques=ataques,
        acoes_texto=acoes,
    )


def montar_armas(dados: dict[str, list[dict[str, Any]]], pdf: Pdf) -> list[Arma]:
    pagina = pdf.pagina("Longsword", "Greatsword", "Battleaxe", "Glaive", "Blowgun")
    props = {p["pk"]: p["fields"] for p in dados["WeaponProperty"]}
    saida = []
    for nome, nome_pt in ARMAS.items():
        w = campos(dados["Weapon"], nome)
        atribuidas = [
            props[a["fields"]["property"]]
            for a in dados["WeaponPropertyAssignment"]
            if a["fields"]["weapon"] == w["pk"]
        ]
        maestria = next((p["name"] for p in atribuidas if p.get("type") == "Mastery"), None)
        propriedades = sorted(p["name"] for p in atribuidas if p.get("type") != "Mastery")
        saida.append(
            Arma(
                id=f"srd:arma:{slug(nome)}",
                nome=nome,
                nome_pt=nome_pt,
                pagina=pagina,
                simples=bool(w["is_simple"]),
                dano_dados=w["damage_dice"],
                dano_tipo=DANO_PT.get(w["damage_type"], w["damage_type"]),
                propriedades=propriedades,
                maestria=maestria,
                alcance_pes=int(w["range"] or 0),
                alcance_longo_pes=int(w["long_range"] or 0),
            )
        )
    return saida


def montar_armaduras(dados: dict[str, list[dict[str, Any]]], pdf: Pdf) -> list[Armadura]:
    pagina = pdf.pagina("Chain Mail", "Splint", "Breastplate", "Padded")
    saida = []
    for nome, (nome_pt, categoria) in ARMADURAS.items():
        a = campos(dados["Armor"], nome)
        saida.append(
            Armadura(
                id=f"srd:armadura:{slug(nome)}",
                nome=nome,
                nome_pt=nome_pt,
                pagina=pagina,
                categoria=categoria,  # type: ignore[arg-type]
                classe_armadura_base=int(a["ac_base"]),
                soma_destreza=bool(a["ac_add_dexmod"]),
                teto_destreza=a["ac_cap_dexmod"],
                forca_minima=FORCA_MINIMA.get(nome),
                desvantagem_furtividade=nome in FURTIVIDADE_DESVANTAGEM,
            )
        )
    return saida


def montar_pericias(dados: dict[str, list[dict[str, Any]]], pdf: Pdf) -> list[Pericia]:
    pagina = pdf.pagina("Acrobatics", "Sleight of Hand", "Survival", "Example Uses")
    por_chave = {s["fields"]["describes"]: s["fields"] for s in dados["SkillDescription"]}
    saida = []
    for nome, (nome_pt, atributo) in PERICIAS.items():
        s = (
            por_chave[slug(nome).replace("-", "_")]
            if slug(nome).replace("-", "_") in por_chave
            else por_chave[slug(nome)]
        )
        saida.append(
            Pericia(
                id=f"srd:pericia:{slug(nome)}",
                nome=nome,
                nome_pt=nome_pt,
                pagina=pagina,
                atributo=atributo,
                descricao=s["desc"],
            )
        )
    return saida


def montar_condicoes(dados: dict[str, list[dict[str, Any]]], pdf: Pdf) -> list[Condicao]:
    por_chave = {c["fields"]["describes"]: c["fields"] for c in dados["ConditionDescription"]}
    saida = []
    for nome, nome_pt in CONDICOES.items():
        pagina = pdf.pagina(f"{nome} [Condition]", a_partir_de=170)
        saida.append(
            Condicao(
                id=f"srd:condicao:{slug(nome)}",
                nome=nome,
                nome_pt=nome_pt,
                pagina=pagina,
                descricao=por_chave[slug(nome)]["desc"],
            )
        )
    return saida


def montar_especies(dados: dict[str, list[dict[str, Any]]], pdf: Pdf) -> list[Especie]:
    saida = []
    for nome, nome_pt in ESPECIES.items():
        e = campos(dados["Species"], nome)
        tracos = [Traco(nome=t["name"], descricao=t["desc"]) for t in filhos(dados["SpeciesTrait"], e["pk"])]
        por_nome = {t.nome: t.descricao for t in tracos}
        velocidade = int(re.search(r"(\d+) feet", por_nome.get("Speed", "30 feet")).group(1))  # type: ignore[union-attr]
        pagina = pdf.pagina(
            f"As a {nome}, you have these special traits.", tracos[2].nome if len(tracos) > 2 else nome
        )
        saida.append(
            Especie(
                id=f"srd:especie:{slug(nome)}",
                nome=nome,
                nome_pt=nome_pt,
                pagina=pagina,
                tamanho=por_nome.get("Size", ""),
                velocidade_pes=velocidade,
                tracos=tracos,
            )
        )
    return saida


DIVERGENCIAS: list[str] = []
NOME_ATRIBUTO: dict[str, Atributo] = {
    "strength": "str",
    "dexterity": "dex",
    "constitution": "con",
    "intelligence": "int",
    "wisdom": "wis",
    "charisma": "cha",
}
SALVAGUARDAS = re.compile(r"Saving Throw\s*Proficiencies\s*([A-Za-z]+) and ([A-Za-z]+)")


def salvaguardas_do_pdf(texto: str, classe: str) -> list[Atributo]:
    """Lê 'Saving Throw Proficiencies: X and Y' do bloco Core <Classe> Traits do PDF."""
    bloco = texto[texto.find(f"Core {classe} Traits") :]
    m = SALVAGUARDAS.search(bloco)
    if not m:
        return []
    return sorted([NOME_ATRIBUTO[m.group(1).lower()], NOME_ATRIBUTO[m.group(2).lower()]])


def montar_classes(dados: dict[str, list[dict[str, Any]]], pdf: Pdf) -> list[Classe]:
    saida = []
    for nome, nome_pt in CLASSES.items():
        c = campos(dados["CharacterClass"], nome)
        feats = filhos(dados["ClassFeature"], c["pk"])
        basicos = next((f["desc"] for f in feats if f["name"] == f"Core {nome} Traits"), "")
        vistos: set[str] = set()
        nivel1 = []
        for f in feats:
            if (
                f["name"] in TRACOS_NIVEL_1[nome]
                and f["name"] not in vistos
                and not f["desc"].startswith("[Column")
            ):
                vistos.add(f["name"])
                nivel1.append(Traco(nome=f["name"], descricao=f["desc"]))
        pagina = pdf.pagina(f"Core {nome} Traits", "Second Wind")
        # O PDF é a fonte de verdade; o acelerador só entra se o PDF não disser.
        do_acelerador = sorted(c["saving_throws"])
        salvaguardas = salvaguardas_do_pdf(pdf.textos[pagina - 1], nome) or do_acelerador
        if salvaguardas != do_acelerador:
            DIVERGENCIAS.append(
                f"{nome}: salvaguardas no PDF {salvaguardas}, no acelerador {do_acelerador}; usado o PDF"
            )
        saida.append(
            Classe(
                id=f"srd:classe:{slug(nome)}",
                nome=nome,
                nome_pt=nome_pt,
                pagina=pagina,
                dado_de_vida=c["hit_dice"].lower(),
                salvaguardas=salvaguardas,
                atributos_primarios=["str", "dex"] if nome == "Fighter" else [],
                tracos_basicos=basicos,
                tracos_nivel_1=nivel1,
            )
        )
    return saida


def principal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--open5e", type=Path, default=Path(tempfile.gettempdir()) / "narrador-open5e-srd-2024"
    )
    args = parser.parse_args(argv)
    pdf = Pdf(PDF)
    if sem_espacos(ATRIBUICAO) not in sem_espacos(pdf.textos[0]):
        print("ERRO: o texto de atribuição do pacote não bate com a página 1 do PDF", file=sys.stderr)
        return 1
    baixar_open5e(args.open5e)
    dados = carregar_open5e(args.open5e)
    srd = Srd(
        versao=VERSAO_SRD,
        pdf_sha256=pdf.sha256,
        paginas_pdf=pdf.doc.page_count,
        criaturas=[montar_criatura(n, pt, dados, pdf) for n, pt in CRIATURAS.items()],
        armas=montar_armas(dados, pdf),
        armaduras=montar_armaduras(dados, pdf),
        pericias=montar_pericias(dados, pdf),
        condicoes=montar_condicoes(dados, pdf),
        especies=montar_especies(dados, pdf),
        classes=montar_classes(dados, pdf),
    )
    for d in DIVERGENCIAS:
        print("divergência do acelerador:", d)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(srd.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8")
    total = sum(
        len(x)
        for x in (
            srd.criaturas,
            srd.armas,
            srd.armaduras,
            srd.pericias,
            srd.condicoes,
            srd.especies,
            srd.classes,
        )
    )
    print(
        f"ok {SAIDA.relative_to(RAIZ)}: {total} registros, todos com página do PDF ({srd.paginas_pdf} páginas, sha256 {srd.pdf_sha256[:12]})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(principal())
