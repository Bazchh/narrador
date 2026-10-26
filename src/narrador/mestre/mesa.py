"""A mesa: a sessão em andamento, com a máquina de estados, o executor, o contexto do turno
e o adaptador do serviço (casos C02, C03, C05, C09, F05, G05). É o que o terminal usa."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from narrador.campanha import banco as campanha_banco
from narrador.campanha import combate as campanha_combate
from narrador.campanha import personagens, sessoes
from narrador.mestre import registro, servico, tratadores_narracao
from narrador.mestre.protocolo import Contexto, Executor
from narrador.modulo import banco as modulo_banco
from narrador.modulo import canonico
from narrador.motor import combate as motor_combate
from narrador.motor import entrada as motor_entrada
from narrador.motor import sessao as motor_sessao
from narrador.motor.combate import EstadoCombate

SISTEMA_FIXO = (
    "Você é o mestre de uma mesa de D&D 5e, regras de 2024, em português do Brasil. "
    "Você narra e decide a história; o motor decide toda regra e todo dado. "
    "Use as ferramentas: pergunta não é ação; toda tentativa tem veredito; fato estabelecido não se contradiz; "
    "segredo só sai pela história; todo desvio do módulo é registrado com motivo. "
    "Termine todo turno com a ferramenta narrar."
)


@dataclass
class Mesa:
    caminho_campanha: Path
    caminho_aventura: Path
    con: sqlite3.Connection = field(init=False)
    con_aventura: sqlite3.Connection = field(init=False)
    campanha_id: str = field(init=False)
    modulo: canonico.ModuloCanonico = field(init=False)
    contexto: Contexto = field(init=False)
    executor: Executor = field(init=False)
    estado: motor_sessao.EstadoSessao = "fechada"
    sessao: sessoes.SessaoAberta | None = None
    turnos: int = 0
    falhas_seguidas: int = 0
    trava: sessoes.Trava = field(init=False)

    # ---------------------------------------------------------------- abrir e encerrar

    def abrir(self) -> sessoes.SessaoAberta:
        """C02 e F05. Retomada não é estado: é abrir e cair direto em 'em combate' se o diário disser."""
        self.estado = motor_sessao.transicao(self.estado, "abrir")
        self.trava = sessoes.Trava(self.caminho_campanha)
        self.trava.adquirir()
        self.con = campanha_banco.criar(self.caminho_campanha)
        self.con_aventura = modulo_banco.criar(self.caminho_aventura)
        self.campanha_id = sessoes.campanha_unica(self.con)
        aventura_id, versao = self.con.execute(
            "select aventura_id, modulo_versao from campanha where id = ?", (self.campanha_id,)
        ).fetchone()
        self.modulo = canonico.carregar(self.con_aventura, aventura_id, versao)
        try:
            self.sessao = sessoes.abrir_sessao(self.con, self.campanha_id)
        except sessoes.CampanhaInconsistenteError:
            self.estado = motor_sessao.transicao(self.estado, "inconsistencia")
            self.con.close()
            self.con_aventura.close()
            self.trava.liberar()
            raise
        inst = self.sessao.instantaneo
        self.contexto = Contexto(
            self.con,
            self.campanha_id,
            self.sessao.sessao_id,
            None,
            {
                "modulo": self.modulo,
                "cena_atual": inst.cena_atual,
                "personagem_id": inst.personagem_id,
                "pv_atual": inst.pontos_de_vida,
            },
        )
        if self.sessao.em_combate and self.sessao.combate is not None:
            self.contexto.extras["combate"] = self.sessao.combate
            self.estado = motor_sessao.transicao(self.estado, "contexto_pronto_em_combate")
        else:
            self.estado = motor_sessao.transicao(self.estado, "contexto_pronto")
        self.executor = Executor(self.contexto, registro.TODOS)
        return self.sessao

    def encerrar(self, pendencias: list[str] | None = None) -> None:
        """C09: tudo já está salvo a cada fato; aqui só se marca o fim e se libera a trava."""
        assert self.sessao is not None
        self.estado = motor_sessao.transicao(self.estado, "encerrar")
        sessoes.encerrar_sessao(self.con, self.campanha_id, self.sessao.sessao_id, pendencias)
        self.estado = motor_sessao.transicao(self.estado, "resumo_gravado")
        self.con.close()
        self.con_aventura.close()
        self.trava.liberar()

    # ---------------------------------------------------------------- turno

    def _novo_turno(self) -> str:
        self.turnos += 1
        turno = f"t-{self.sessao.numero if self.sessao else 0}-{self.turnos}"
        self.contexto.turno_atual = turno
        return turno

    def contexto_do_turno(self, entrada_do_jogador: str, turno: str) -> servico.ContextoDoTurno:
        """Os seis blocos do capítulo 6, montados pela plataforma."""
        assert self.sessao is not None
        inst = self.sessao.instantaneo
        classificacao, tom, configuracao = self.con.execute(
            "select classificacao, tom, configuracao from campanha where id = ?", (self.campanha_id,)
        ).fetchone()
        regras = [
            t
            for (t,) in self.con.execute(
                "select texto from regra_de_mesa where campanha_id = ? and ativa = 1", (self.campanha_id,)
            )
        ]
        cena: dict[str, Any] = {}
        if inst.cena_atual and inst.cena_atual in self.modulo.itens:
            recorte = self.executor.executar(
                _chamada_interna("consultar_cena", {"cena_id": inst.cena_atual}, turno)
            )
            cena = recorte.saida or {}
        personagem: dict[str, Any] = {}
        if inst.personagem_id:
            gravada, d = personagens.consultar(self.con, self.campanha_id, inst.personagem_id)
            personagem = {
                "nome": gravada.ficha.nome,
                "classe": d.classe.nome_pt,
                "nivel": gravada.ficha.nivel,
                "pv": inst.pontos_de_vida
                if inst.pontos_de_vida is not None
                else d.pontos_de_vida_maximos.total,  # zero é zero: "or" escondia a queda
                "pv_max": d.pontos_de_vida_maximos.total,
                "ca": d.classe_armadura.total,
            }
        combate = self.contexto.extras.get("combate")
        if combate is not None and combate.estado != "encerrado":
            personagem["combate"] = {
                "rodada": combate.rodada,
                "turno_de": combate.atual.id if combate.atual else None,
            }
        classe = motor_entrada.classificar(entrada_do_jogador)
        return servico.ContextoDoTurno(
            turno=turno,
            sistema=SISTEMA_FIXO,
            mesa=f"classificação {classificacao}; tom {tom}; configuração {configuracao}; regras de mesa: {regras or 'nenhuma'}",
            campanha=f"sessão {self.sessao.numero}" + (" (retomada)" if self.sessao.retomada_de else ""),
            cena=cena,
            personagem=personagem,
            entrada=f"[{classe}] {entrada_do_jogador}",
        )

    def rodar_turno(self, entrada_do_jogador: str, mestre: servico.ServicoDeLinguagem) -> servico.Turno:
        """Um turno completo: contexto, chamadas pelo executor, narração aprovada ou falha classificada (G05)."""
        if self.estado not in ("em_cena", "em_combate"):
            raise motor_sessao.TransicaoInvalidaError(f"não dá para jogar em '{self.estado}'")
        turno = self._novo_turno()
        ctx = self.contexto_do_turno(entrada_do_jogador, turno)
        resultado = mestre.rodar_turno(ctx, self.executor.disponiveis(), self.executor.executar)
        self.contexto.turno_atual = None
        if resultado.falha is not None:
            self.falhas_seguidas += 1
            sessoes.registrar_evento(
                self.con,
                self.campanha_id,
                ctx_sessao(self),
                "G05",
                "falha do serviço",
                {"tipo": resultado.falha.tipo, "detalhe": resultado.falha.detalhe, "turno": turno},
            )
            if resultado.falha.tipo == "indisponivel" and self.falhas_seguidas >= 2:
                self.estado = motor_sessao.transicao(self.estado, "falha_servico")
            return resultado
        self.falhas_seguidas = 0
        self._sincronizar_estado()
        return resultado

    def texto_literal(self) -> str:
        """A alternativa mecânica quando o mestre falha (C03 E1): a descrição do módulo."""
        return tratadores_narracao.texto_literal_da_cena(self.contexto)

    def retomar_servico(self, em_combate: bool | None = None) -> None:
        evento = (
            "servico_voltou_em_combate"
            if (em_combate if em_combate is not None else self._em_combate())
            else "servico_voltou"
        )
        self.estado = motor_sessao.transicao(self.estado, evento)
        self.falhas_seguidas = 0

    def _em_combate(self) -> bool:
        combate = self.contexto.extras.get("combate")
        return combate is not None and combate.estado != "encerrado"

    def _sincronizar_estado(self) -> None:
        """O combate é dado do contexto; a máquina da sessão segue o que o combate diz."""
        em_combate = self._em_combate()
        if self.estado == "em_cena" and em_combate:
            self.estado = motor_sessao.transicao(self.estado, "combate_iniciado")
        elif self.estado == "em_combate" and not em_combate:
            self.estado = motor_sessao.transicao(self.estado, "combate_encerrado")
        combate = self.contexto.extras.get("combate")
        if combate is not None and self.sessao is not None:
            pv = combate.jogador.pontos_de_vida
            self.contexto.extras["pv_atual"] = pv  # o próximo combate parte da vida real
            inst = self.sessao.instantaneo
            if pv != inst.pontos_de_vida:
                novo = sessoes.Instantaneo(
                    sessoes.ultimo_seq(self.con, self.campanha_id),
                    inst.cena_atual,
                    inst.relogio_minutos,
                    inst.personagem_id,
                    inst.sessao_numero,
                    pv,
                    inst.extras,
                )
                sessoes.gravar_instantaneo(self.con, self.campanha_id, novo)
                self.sessao = sessoes.SessaoAberta(
                    self.sessao.sessao_id,
                    self.sessao.numero,
                    novo,
                    self.sessao.retomada_de,
                    em_combate,
                    combate if em_combate else None,
                    False,
                )

    def ir_para(self, cena_id: str, minutos: int = 0) -> None:
        assert self.sessao is not None
        if cena_id not in self.modulo.itens:
            raise canonico.CenaInexistenteError(cena_id, self.modulo.cenas())
        sessoes.mudar_cena(self.con, self.campanha_id, self.sessao.sessao_id, cena_id, minutos)
        self.contexto.extras["cena_atual"] = cena_id
        self.sessao = sessoes.SessaoAberta(
            self.sessao.sessao_id,
            self.sessao.numero,
            sessoes.ultimo_instantaneo(self.con, self.campanha_id) or self.sessao.instantaneo,
            self.sessao.retomada_de,
            self.sessao.em_combate,
            self.sessao.combate,
            self.sessao.narracao_pendente,
        )

    def combate_atual(self) -> EstadoCombate | None:
        return self.contexto.extras.get("combate")

    # ---------------------------------------------------------------- combate pelo lado da plataforma

    def _combate_vivo(self) -> EstadoCombate:
        combate = self.combate_atual()
        if combate is None or combate.estado == "encerrado":
            raise motor_combate.AcaoNaoPermitidaError("não há combate em andamento")
        return combate

    def _guardar_combate(self, estado: EstadoCombate, origem: str) -> None:
        self.contexto.extras["combate"] = estado
        assert self.sessao is not None
        campanha_combate.gravar(self.con, self.campanha_id, self.sessao.sessao_id, estado, origem)
        self._sincronizar_estado()

    def agir_pelo_jogador(self, decl: motor_combate.Declaracao) -> EstadoCombate:
        """D02: a declaração do jogador no turno dele, resolvida pelo motor e gravada.
        Gasta a ação? O turno encerra sozinho, como no turno das criaturas."""
        combate = self._combate_vivo()
        assert self.sessao is not None
        pj_id = self.sessao.instantaneo.personagem_id or ""
        rolar = campanha_combate.rolador(self.con, self.campanha_id, self.sessao.sessao_id, "D02")
        estado = motor_combate.agir(combate, pj_id, decl, rolar)
        ainda_dele = estado.estado == "turno_pj" and estado.atual is not None and estado.atual.id == pj_id
        if ainda_dele and not estado.economia.acao:
            estado = motor_combate.encerrar_turno(estado)
        self._guardar_combate(estado, "D02")
        return estado

    def agir_padrao_da_criatura(self, criatura_id: str) -> EstadoCombate:
        """D03 E1: o mestre falhou no turno da criatura; a ficha age por ela e o turno encerra."""
        combate = self._combate_vivo()
        assert self.sessao is not None
        rolar = campanha_combate.rolador(self.con, self.campanha_id, self.sessao.sessao_id, "D03")
        estado = motor_combate.acao_padrao(combate, criatura_id, rolar)
        if estado.estado == "turno_cri" and estado.atual is not None and estado.atual.id == criatura_id:
            estado = motor_combate.encerrar_turno(estado)
        self._guardar_combate(estado, "D03")
        return estado


def ctx_sessao(mesa: Mesa) -> str | None:
    return mesa.sessao.sessao_id if mesa.sessao else None


def _chamada_interna(ferramenta: str, entrada: dict[str, Any], turno: str) -> Any:
    from narrador.mestre.protocolo import Chamada

    return Chamada(id=f"{turno}-plataforma", ferramenta=ferramenta, entrada=entrada, turno=turno)
