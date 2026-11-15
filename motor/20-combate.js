  /* ------------------------------------------------------------------ combate por zonas, em grupo */
  function vivos(S) { return S.combate ? S.inimigos[S.combate.grupo].filter(function (e) { return e.vivo; }) : []; }
  function estadoInimigo(e) {
    var f = e.hp / e.hpMax;
    return f >= 1 ? 'ileso' : f > 0.5 ? 'ferido' : f > 0.25 ? 'muito ferido' : 'por um fio';
  }
  /* ---------- luta que o jogador começa contra alguém da cena ---------- */
  function estaMorto(S, pid) { return !!(S.f.mortos && S.f.mortos[pid]); }
  function pessoasDaCena(S) {
    var c = AV(S).cenas[S.cena];
    return (c.pessoas ? c.pessoas(S) : []).filter(function (p) { return !estaMorto(S, p.id); });
  }
  function grupoBriga(S) {
    var b = S.briga || {}, onde = b.cena || S.cena;
    return {
      zonas: {}, zonaPadrao: 'perto', alerta: 'brigaAlerta', onde: 'numa briga que começou por escolha própria',
      fugaPara: onde, acordaEm: onde,
      textoFuga: 'Você recua até a porta e sai para a rua. Ninguém vem atrás, mas todos viram.',
      textoQueda: function (S2) {
        var perdeu = Math.floor(S2.ouro / 2); S2.ouro -= perdeu;
        return 'Você acorda no chão, com gosto de sangue na boca' + (perdeu ? ' e ' + perdeu + ' po a menos na bolsa' : '') + '. Deixaram você viver, e deixaram claro que não foi por simpatia. ' + (S2.herois.length > 1 ? 'Quem resistiu está' : 'Você está') + ' com 1 ponto de vida.';
      },
      aoVencer: function (S2) {
        var l = S2.inimigos._briga || [], nomes = l.map(function (e) { return e.nome; }).join(' e '), c = AV(S2).cenas[S2.cena];
        S2.f.mortos = S2.f.mortos || {};
        l.forEach(function (e) { e.vivo = false; if (e.pid) S2.f.mortos[e.pid] = true; });
        out(S2, 'narra', c.aposBriga ? c.aposBriga(S2, nomes) : 'O silêncio que fica é pior que o barulho. Quem viu não vai esquecer.');
        fato(S2, nomes + (l.length > 1 ? ' morreram' : ' morreu') + ' pelas mãos ' + (S2.herois.length > 1 ? 'do grupo' : 'do herói') + ' em ' + c.nome + '.');
        desvio(S2, 'Os moradores não seriam feridos.', (S2.herois.length > 1 ? 'O grupo matou ' : 'O herói matou ') + nomes + '.', 'decisão do jogador');
        S2.briga = null;
      }
    };
  }
  function grupoDe(S, id) { return id === '_briga' ? grupoBriga(S) : AV(S).grupos[id]; }
  function iniciarBriga(S, h, alvos) {
    var c = AV(S).cenas[S.cena];
    checkpoint(S);
    S.briga = { cena: S.cena, quem: h ? h.id : null };
    S.inimigos._briga = alvos.map(function (p, i) { var e = mk('p' + (i + 1), p.tipo, p.nome, p.hp); e.pid = p.id; return e; });
    if (c.aoBriga) c.aoBriga(S, alvos); else S.f.malvisto = true;
    if (c.aoAtacar) out(S, 'narra', c.aoAtacar(S, alvos));
    iniciarCombate(S, '_briga', {});
  }

  function mk(id, tipo, nome, hp) {
    var m = MONSTROS[tipo];
    hp = hp || m.hp;
    return { id: id, tipo: tipo, nome: nome, hp: hp, hpMax: hp, vivo: true, zona: 'medio', drenado: false, lento: false, aflito: false, guiado: false, chocado: false, expulso: 0, dorme: 0, passo: false };
  }
  function varios(n, prefixo, tipo, nome, hp) {
    var l = [];
    for (var i = 1; i <= n; i++) l.push(mk(prefixo + i, tipo, n > 1 ? nome + ' ' + i : nome, hp));
    return l;
  }
  function inimigo(S, id) {
    var l = S.inimigos[S.combate.grupo];
    for (var i = 0; i < l.length; i++) if (l[i].id === id) return l[i];
    return null;
  }
  function vez(S) {
    var c = S.combate;
    if (!c) return null;
    var id = c.ordem[c.i];
    return id && id.charAt(0) === 'h' ? heroi(S, id) : null;
  }
  function novoTurno() { return { mov: false, acao: false, bonus: false, espaco: false, furtivo: false }; }
  function linhaInicial(h) { return (h.classe === 'mago' || (h.classe === 'guerreiro' && h.kit === 'arco')) ? 'tras' : 'frente'; }
  function frente(S) { return ativos(S).filter(function (h) { return h.linha === 'frente'; }); }
  function garantirFrente(S, calado) {
    var a = ativos(S);
    if (!a.length || frente(S).length) return;
    a.forEach(function (h) { h.linha = 'frente'; });
    if (!calado && S.herois.length > 1) out(S, 'combate', 'Sem ninguém na linha de frente, os inimigos alcançam ' + lista(a.map(function (h) { return h.nome; })) + '.');
  }
  function limparFx(S) { S.herois.forEach(function (h) { h.fx = {}; h.linha = 'frente'; }); }
  function algumPerto(S) { return vivos(S).some(function (e) { return e.zona === 'perto'; }); }
  function modoLiquido(vant, desv) { return vant && !desv ? 'vantagem' : desv && !vant ? 'desvantagem' : null; }

  function iniciarCombate(S, grp, o) {
    o = o || {};
    var g = grupoDe(S, grp), inis = S.inimigos[grp];
    inis.forEach(function (e) {
      if (!e.vivo) return;
      e.zona = (o.zonas && o.zonas[e.id]) || g.zonas[e.id] || g.zonaPadrao || 'medio';
      e.drenado = e.lento = e.aflito = e.guiado = e.chocado = false; e.expulso = 0; e.dorme = 0; e.passo = false;
    });
    S.herois.forEach(function (h) { h.fx = {}; h.linha = linhaInicial(h); });
    garantirFrente(S, true);
    S.combate = { grupo: grp, rodada: 1, ordem: [], i: 0, turno: novoTurno() };
    S.f[g.alerta] = true;
    var ini = [];
    ativos(S).forEach(function (h) {
      var r = d20(S, 'Iniciativa de ' + h.nome, mod(h.atr.des), o.ini || null, null, null, h);
      ini.push({ id: h.id, nome: h.nome, v: r.total, d: 50 + mod(h.atr.des) });
    });
    inis.forEach(function (e) {
      if (!e.vivo) return;
      var r = d20(S, 'Iniciativa de ' + e.nome, MONSTROS[e.tipo].ini, null, null, null);
      ini.push({ id: e.id, nome: e.nome, v: r.total, d: MONSTROS[e.tipo].ini });
    });
    ini.sort(function (a, b) { return b.v - a.v || b.d - a.d; });
    S.combate.ordem = ini.map(function (x) { return x.id; });
    out(S, 'combate', 'Combate! Iniciativa' + (o.ini ? ' (heróis com ' + o.ini + ')' : '') + ': ' + ini.map(function (x) { return x.nome + ' ' + x.v; }).join(', ') + '.');
    posicoes(S);
    avancar(S, true);
  }
  function posicoes(S) {
    var v = vivos(S);
    if (!v.length) return;
    var t = 'Posições: ' + v.map(function (e) { return e.nome + ' ' + (e.zona === 'longe' ? 'longe' : e.zona === 'perto' ? 'em corpo a corpo' : 'a média distância') + (e.hp < e.hpMax ? ' (' + estadoInimigo(e) + ')' : ''); }).join('; ') + '.';
    if (S.herois.length > 1) {
      var fr = frente(S).map(function (h) { return h.nome; }), tr = ativos(S).filter(function (h) { return h.linha === 'tras'; }).map(function (h) { return h.nome; });
      t += ' Na linha de frente: ' + lista(fr) + '.' + (tr.length ? ' Atrás: ' + lista(tr) + '.' : '');
    }
    out(S, 'combate', t);
  }

  // Um teste contra a morte. Devolve true se o herói voltou a si.
  function testeMorte(S, h) {
    var g = S.combate ? grupoDe(S, S.combate.grupo) : null;
    var r = d20(S, 'Teste contra a morte de ' + h.nome, 0, null, 10, 'CD', h), c = h.caido;
    if (r.d20 === 20) { fecharD20(S, r, true, '20 natural: volta a si'); h.pv = 1; h.caido = null; out(S, 'combate', h.nome + ' abre os olhos e se levanta com 1 PV.'); return true; }
    if (r.d20 === 1) { c.f += 2; fecharD20(S, r, false, '1 natural: duas falhas (' + Math.min(c.f, 3) + ' de 3)'); }
    else if (r.total >= 10) { c.s++; fecharD20(S, r, true, 'sucesso (' + c.s + ' de 3)'); }
    else { c.f++; fecharD20(S, r, false, 'falha (' + Math.min(c.f, 3) + ' de 3)'); }
    if (c.s >= 3) { c.estavel = true; out(S, 'combate', h.nome + ' está estável: inconsciente, mas fora de perigo.'); }
    else if (c.f >= 3) {
      if (S.dificuldade === 'classico' && !(g && g.semMorte)) { h.morto = true; h.caido = null; out(S, 'combate', h.nome + ' não resiste.'); fato(S, h.nome + ' morreu ' + (g ? g.onde : 'na aventura') + '.'); }
      else { c.estavel = true; out(S, 'combate', h.nome + ' fica por um fio, mas resiste (modo Tranquilo): está estável.'); }
    }
    return false;
  }

  // Avança a ordem até chegar a vez de um herói consciente (ou o combate acabar).
  function avancar(S, primeiro) {
    var guarda = 0;
    while (S.combate && !S.fim && guarda++ < 400) {
      var c = S.combate;
      if (!primeiro) {
        c.i++;
        if (c.i >= c.ordem.length) {
          c.i = 0; c.rodada++;
          var g = grupoDe(S, c.grupo);
          if (g.aoRodada) g.aoRodada(S, c.rodada);
          if (!S.combate) return;
        }
      }
      primeiro = false;
      var id = c.ordem[c.i];
      if (id.charAt(0) === 'h') {
        var h = heroi(S, id);
        if (!h || h.morto) continue;
        if (h.pv <= 0) {
          if (h.caido && !h.caido.estavel) { if (!testeMorte(S, h)) continue; }
          else continue;
        }
        c.turno = novoTurno();
        h.fx.esquiva = false; h.fx.deseng = false;
        out(S, 'combate', 'Rodada ' + c.rodada + ' · vez de ' + h.nome + '. PV ' + h.pv + '/' + h.pvMax + '.');
        return;
      }
      var e = inimigo(S, id);
      if (!e || !e.vivo) continue;
      turnoInimigo(S, e);
      if (verificarFim(S)) return;
    }
  }

  function turnoInimigo(S, e) {
    var m = MONSTROS[e.tipo], g = grupoDe(S, S.combate.grupo);
    e.chocado = false;
    if (e.dorme > 0) { e.dorme--; out(S, 'combate', e.nome + (e.dorme > 0 ? ' continua dormindo.' : ' dorme, mas já começa a se mexer.')); return; }
    if (e.expulso > 0) {
      e.expulso--;
      if (e.zona !== 'longe') { e.zona = ZONAS[ZONAS.indexOf(e.zona) + 1]; out(S, 'combate', e.nome + ' recua, expulso pela fé.'); }
      else out(S, 'combate', e.nome + ' se encolhe ao longe, expulso.');
      return;
    }
    if (g.ia && g.ia[e.tipo]) { if (g.ia[e.tipo](S, e)) return; }
    var estavaLento = e.lento;
    e.lento = false;
    if (e.zona !== 'perto') {
      if (m.parado) return;
      if (estavaLento) { out(S, 'combate', e.nome + ' tenta avançar, mas não consegue sair do lugar neste turno.'); return; }
      if (m.lerdo) {
        e.passo = !e.passo;
        if (e.passo) { out(S, 'combate', e.nome + ' se arrasta para a frente, devagar.'); return; }
      }
      e.zona = ZONAS[ZONAS.indexOf(e.zona) - 1];
      out(S, 'combate', e.nome + ' avança' + (e.zona === 'perto' ? ' e chega ao corpo a corpo.' : ' até a média distância.'));
      if (e.zona !== 'perto') return;
    }
    garantirFrente(S);
    var alvos = frente(S), visiveis = alvos.filter(function (h) { return !h.fx.escondido; });
    if (!alvos.length) return;
    ataqueInimigo(S, e, sortear(S, visiveis.length ? visiveis : alvos), false);
  }

  function ferirHeroi(S, h, dn, quem) {
    var g = S.combate ? grupoDe(S, S.combate.grupo) : null, nota = '';
    if (S.dificuldade !== 'classico') { dn = Math.max(1, Math.floor(dn / 2)); nota = ' (metade, pelo modo Tranquilo)'; }
    h.pv = Math.max(0, h.pv - dn);
    h.fx.escondido = false;
    if (h.pv <= 0 && h.implacavel > 0) {
      h.implacavel--; h.pv = 1;
      out(S, 'combate', quem + ' acerta ' + h.nome + ': ' + dn + ' de dano' + nota + '. Deveria cair, mas a Resistência Implacável o mantém de pé com 1 PV.');
      return;
    }
    out(S, 'combate', quem + ' acerta ' + h.nome + ': ' + dn + ' de dano' + nota + '. PV ' + h.pv + '/' + h.pvMax + '.');
    if (h.pv <= 0) {
      h.caido = { s: 0, f: 0, estavel: !!(g && g.semMorte) };
      out(S, 'combate', h.nome + ' cai, inconsciente.');
      garantirFrente(S);
    }
  }

  function ataqueInimigo(S, e, h, oportunidade) {
    var m = MONSTROS[e.tipo], a = m.atq;
    var desv = !!(h.fx.esquiva || e.drenado || h.fx.escondido);
    e.drenado = false;
    var r = d20(S, e.nome + ' ataca ' + h.nome + ' com ' + a.nome + (oportunidade ? ' (ataque de oportunidade)' : ''), a.bonus, desv ? 'desvantagem' : null, ca(h), 'CA');
    var crit = r.d20 === 20, acerto = crit || (r.d20 !== 1 && r.total >= ca(h));
    fecharD20(S, r, acerto, acerto ? (crit ? 'acerto crítico' : 'acerta') : 'erra');
    if (!acerto) return;
    var dn = rolarSoma(S, 'Dano de ' + e.nome, [{ n: a.n, l: a.l }], a.b, { crit: crit, sufixo: TIPO_DANO[a.tipo] });
    ferirHeroi(S, h, dn, e.nome);
  }

  function ferir(S, e, q, tipo, o) {
    o = o || {};
    var m = MONSTROS[e.tipo], nota = '';
    if (m.vuln && m.vuln.indexOf(tipo) >= 0) { q *= 2; nota = ' (vulnerável: dano dobrado)'; }
    e.hp -= q;
    if (q > 0) { e.expulso = 0; if (e.dorme > 0) { e.dorme = 0; nota += ' (acorda)'; } }
    if (e.tipo === 'ivo') S.f.ivoGolpe = o.corpo ? 'corpo' : 'dist';
    if (e.hp <= 0) {
      if (m.fortitude && tipo !== 'radiante' && !o.crit) {
        var r = d20(S, 'Fortitude de morto-vivo de ' + e.nome, m.salv.con, null, 5 + q, 'CD');
        fecharD20(S, r, r.total >= 5 + q, r.total >= 5 + q ? 'continua de pé' : 'cai');
        if (r.total >= 5 + q) { e.hp = 1; out(S, 'combate', e.nome + ' sofre ' + q + ' de dano' + nota + ' e deveria cair, mas se recusa: fica por um fio.'); return; }
      }
      e.hp = 0; e.vivo = false;
      out(S, 'combate', e.nome + ' sofre ' + q + ' de dano' + nota + ' e ' + (e.tipo === 'ivo' ? 'desaba.' : (m.mortoVivo || e.tipo === 'boneco') ? 'desmonta no chão.' : 'cai.'));
      return;
    }
    out(S, 'combate', e.nome + ' sofre ' + q + ' de dano' + nota + ' (' + estadoInimigo(e) + ').');
  }

  function atacarArma(S, h, w, e) {
    var c = S.combate;
    if (c.turno.acao) return aviso(S, h.nome + ' já usou a ação neste turno.');
    var junto = e.zona === 'perto' && h.linha === 'frente';
    if (w.alcance === 'perto' && !junto) return aviso(S, e.zona !== 'perto' ? e.nome + ' está longe demais para um ataque com ' + w.nome.toLowerCase() + '. Avance sobre ele primeiro ou use outro ataque.' : h.nome + ' está na linha de trás. Vá para a linha de frente para atacar corpo a corpo.');
    var corpo = junto && w.alcance !== 'dist';
    var vant = e.aflito || e.guiado || h.fx.escondido || e.dorme > 0;
    var desv = !corpo && ((h.linha === 'frente' && algumPerto(S)) || (w.alcance === 'arremesso' && e.zona === 'longe'));
    var modo = modoLiquido(vant, desv);
    e.aflito = false; e.guiado = false; h.fx.escondido = false;
    var bz = bencao(S, h), bonus = bonusArma(h, w) + bz;
    var r = d20(S, 'Ataque de ' + h.nome + ' com ' + w.nome.toLowerCase() + ' em ' + e.nome + (bz ? ' (Bênção +' + bz + ')' : ''), bonus, modo, MONSTROS[e.tipo].ca, 'CA', h);
    var crit = r.d20 === 20, acerto = crit || (r.d20 !== 1 && r.total >= MONSTROS[e.tipo].ca);
    fecharD20(S, r, acerto, acerto ? (crit ? 'acerto crítico' : 'acerta') : 'erra');
    c.turno.acao = true;
    var mestre = temMaestria(h) && w.maestria, md = modArma(h, w);
    if (!acerto) {
      if (mestre === 'raspar' && md > 0) { out(S, 'combate', 'Maestria: mesmo errando, a lâmina pesada raspa o alvo.'); ferir(S, e, md, w.tipo, { corpo: corpo }); }
      return true;
    }
    var partes = [{ n: w.n, l: w.l }], rot = 'Dano de ' + h.nome + ' (' + w.nome.toLowerCase() + ')';
    var aliado = e.zona === 'perto' && frente(S).some(function (x) { return x !== h; });
    if (h.classe === 'ladino' && !c.turno.furtivo && modo !== 'desvantagem' && (modo === 'vantagem' || aliado)) { partes.push({ n: 1, l: 6 }); c.turno.furtivo = true; rot = 'Dano de ' + h.nome + ' (' + w.nome.toLowerCase() + ' + Ataque Furtivo)'; }
    var dn = rolarSoma(S, rot, partes, md, { crit: crit, sufixo: TIPO_DANO[w.tipo], min3: h.classe === 'guerreiro' && h.kit === 'grande' && corpo });
    ferir(S, e, dn, w.tipo, { crit: crit, corpo: corpo });
    if (e.vivo && mestre) {
      if (mestre === 'drenar') { e.drenado = true; out(S, 'combate', 'Maestria: o golpe desequilibra ' + e.nome + ', que terá desvantagem no próximo ataque.'); }
      if (mestre === 'lentidao') { e.lento = true; out(S, 'combate', 'Maestria: ' + e.nome + ' não consegue avançar no próximo turno.'); }
      if (mestre === 'afligir') { e.aflito = true; out(S, 'combate', 'Maestria: o próximo ataque contra ' + e.nome + ' terá vantagem.'); }
    }
    return true;
  }

  function podeEspaco(S, h, mg) {
    if (mg.truque) return true;
    if (h.espacos <= 0) { aviso(S, h.nome + ' não tem mais espaços de magia. Um descanso longo os devolve.'); return false; }
    if (S.combate && S.combate.turno.espaco) { aviso(S, 'Só uma magia com espaço por turno.'); return false; }
    return true;
  }
  function gastar(S, h, mg) {
    if (!mg.truque) { h.espacos--; if (S.combate) S.combate.turno.espaco = true; }
    if (S.combate) { if (mg.acao === 'bonus') S.combate.turno.bonus = true; else S.combate.turno.acao = true; }
  }

  // alvo: id de inimigo (em combate) ou id de herói (curas e proteções). Devolve true se a magia aconteceu.
  function conjurar(S, h, id, alvo) {
    var mg = MAGIAS[id], c = S.combate, tipo = c ? 'combate' : 'narra';
    if (!mg || !temMagia(h, id)) return aviso(S, h.nome + ' não conhece essa magia.');
    if (c) {
      if (mg.acao === 'acao' && c.turno.acao) return aviso(S, h.nome + ' já usou a ação neste turno.');
      if (mg.acao === 'bonus' && c.turno.bonus) return aviso(S, h.nome + ' já usou a ação bônus neste turno.');
    } else if (!mg.fora) return aviso(S, 'Não há por que conjurar ' + mg.nome + ' agora.');
    var m5 = mod(h.atr[conj(h)]), cd = cdMagia(h), ah, e;
    if (mg.modo === 'cura') {
      ah = alvo ? heroi(S, alvo) : h;
      if (!ah || ah.morto) return aviso(S, 'Esse aliado não pode ser curado.');
      if (ah.pv >= ah.pvMax) return aviso(S, ah.nome + ' já está com todos os pontos de vida.');
      if (!podeEspaco(S, h, mg)) return false;
      gastar(S, h, mg);
      var q = rolarSoma(S, mg.nome + ' de ' + h.nome, [{ n: mg.n, l: mg.l }], m5, { sufixo: 'PV' });
      var estava = ah.pv <= 0, gq = curar(ah, q);
      out(S, tipo, 'Uma luz morna fecha os ferimentos de ' + ah.nome + ': +' + gq + ' PV. PV ' + ah.pv + '/' + ah.pvMax + '.' + (estava ? ' ' + ah.nome + ' volta a si.' : ''));
      return true;
    }
    if (mg.modo === 'armadura') {
      if (h.armaduraArcana) return aviso(S, 'A Armadura Arcana já está ativa.');
      if (!podeEspaco(S, h, mg)) return false;
      gastar(S, h, mg);
      h.armaduraArcana = true;
      out(S, tipo, 'Um brilho fino cobre a pele de ' + h.nome + ' e some. CA ' + ca(h) + ' até o próximo descanso longo.');
      return true;
    }
    if (!c) return aviso(S, 'Não há alvo para ' + mg.nome + ' agora.');
    if (mg.modo === 'poupar') {
      ah = alvo ? heroi(S, alvo) : null;
      if (!ah || ah.morto || ah.pv > 0 || !ah.caido || ah.caido.estavel) return aviso(S, 'Poupar os Moribundos só serve para um aliado caído que ainda corre perigo.');
      gastar(S, h, mg);
      ah.caido.estavel = true;
      out(S, 'combate', h.nome + ' toca ' + ah.nome + ', que para de piorar: está estável.');
      return true;
    }
    if (mg.modo === 'bencao') {
      if (ativos(S).every(function (x) { return x.fx.bencao; })) return aviso(S, 'O grupo já está abençoado.');
      if (!podeEspaco(S, h, mg)) return false;
      gastar(S, h, mg);
      ativos(S).forEach(function (x) { x.fx.bencao = true; });
      out(S, 'combate', h.nome + ' abençoa ' + (S.herois.length > 1 ? 'o grupo' : 'a si mesmo') + ': +1d4 nos ataques e salvaguardas até o fim do combate.');
      return true;
    }
    if (mg.modo === 'escudofe') {
      ah = alvo ? heroi(S, alvo) : h;
      if (!ah || !consc(ah)) return aviso(S, 'Esse aliado não pode receber o Escudo da Fé agora.');
      if (ah.fx.escudoFe) return aviso(S, ah.nome + ' já está protegido pelo Escudo da Fé.');
      if (!podeEspaco(S, h, mg)) return false;
      gastar(S, h, mg);
      ah.fx.escudoFe = true;
      out(S, 'combate', 'Um escudo de luz gira em volta de ' + ah.nome + ': CA ' + ca(ah) + ' até o fim do combate.');
      return true;
    }
    if (mg.modo === 'area') {
      if (h.linha !== 'frente') return aviso(S, mg.nome + ' sai das mãos de quem conjura: ' + h.nome + ' precisa estar na linha de frente.');
      var alvos = vivos(S).filter(function (x) { return x.zona === 'perto'; });
      if (!alvos.length) return aviso(S, mg.nome + ' só alcança quem está em corpo a corpo, e não há ninguém tão perto.');
      if (!podeEspaco(S, h, mg)) return false;
      gastar(S, h, mg);
      var total = rolarSoma(S, mg.nome + ' de ' + h.nome, [{ n: mg.n, l: mg.l }], 0, { sufixo: TIPO_DANO[mg.tipo] });
      out(S, 'combate', mg.tipo === 'fogo' ? 'Um leque de fogo sai das mãos de ' + h.nome + '.' : 'Um estrondo parte de ' + h.nome + ' e varre quem está perto.');
      alvos.forEach(function (x) {
        var r = d20(S, 'Salvaguarda de ' + ATR[mg.salv] + ' de ' + x.nome, MONSTROS[x.tipo].salv[mg.salv], null, cd, 'CD');
        var passou = r.total >= cd;
        fecharD20(S, r, passou, passou ? 'passa, metade do dano' : 'falha');
        ferir(S, x, passou ? Math.floor(total / 2) : total, mg.tipo, {});
        if (!passou && mg.empurra && x.vivo) { x.zona = 'medio'; out(S, 'combate', x.nome + ' é arremessado para a média distância.'); }
      });
      return true;
    }
    e = alvo ? inimigo(S, alvo) : null;
    if (!e || !e.vivo) return aviso(S, 'Escolha um alvo para ' + mg.nome + '.');
    if (mg.toque && !(e.zona === 'perto' && h.linha === 'frente')) return aviso(S, mg.nome + ' exige tocar o alvo: ' + h.nome + ' precisa estar na linha de frente, com ' + e.nome + ' em corpo a corpo.');
    if (!podeEspaco(S, h, mg)) return false;
    if (mg.modo === 'sono') {
      gastar(S, h, mg);
      var grupoSono = [e].concat(vivos(S).filter(function (x) { return x !== e && x.zona === e.zona; })).slice(0, 2);
      out(S, 'combate', h.nome + ' sopra um punhado de areia fina na direção de ' + lista(grupoSono.map(function (x) { return x.nome; })) + '.');
      grupoSono.forEach(function (x) {
        if (MONSTROS[x.tipo].mortoVivo || x.tipo === 'boneco') { out(S, 'combate', x.nome + ' não dorme: é imune.'); return; }
        var r = d20(S, 'Salvaguarda de Sabedoria de ' + x.nome, MONSTROS[x.tipo].salv.sab, null, cd, 'CD');
        var passou = r.total >= cd;
        fecharD20(S, r, passou, passou ? 'resiste' : 'adormece');
        if (!passou) { x.dorme = 2; out(S, 'combate', x.nome + ' desaba, dormindo. Ataques contra ele têm vantagem; qualquer dano o acorda.'); }
      });
      return true;
    }
    if (mg.modo === 'auto') {
      gastar(S, h, mg);
      var dn = rolarSoma(S, mg.nome + ' de ' + h.nome + ' (três dardos)', [{ n: 3, l: 4 }], 3, { sufixo: TIPO_DANO[mg.tipo] });
      out(S, 'combate', 'Três dardos de luz dobram no ar e acertam ' + e.nome + ' sem errar.');
      ferir(S, e, dn, mg.tipo, {});
      return true;
    }
    if (mg.modo === 'salv') {
      gastar(S, h, mg);
      var rs = d20(S, mg.nome + ' de ' + h.nome + ': salvaguarda de ' + ATR[mg.salv] + ' de ' + e.nome, MONSTROS[e.tipo].salv[mg.salv], null, cd, 'CD');
      var ok = rs.total >= cd;
      fecharD20(S, rs, ok, ok ? (mg.meio ? 'passa, metade do dano' : 'passa, sem dano') : 'falha');
      if (!ok || mg.meio) {
        var d1 = rolarSoma(S, 'Dano de ' + mg.nome, [{ n: mg.n, l: mg.l }], 0, { sufixo: TIPO_DANO[mg.tipo] });
        ferir(S, e, ok ? Math.floor(d1 / 2) : d1, mg.tipo, { corpo: !!mg.toque });
      } else out(S, 'combate', e.nome + ' escapa do clarão.');
      return true;
    }
    // ataque mágico (à distância ou de toque)
    gastar(S, h, mg);
    var vant = e.aflito || e.guiado || h.fx.escondido || e.dorme > 0, desv = !mg.toque && h.linha === 'frente' && algumPerto(S);
    var modo = modoLiquido(vant, desv);
    e.aflito = false; e.guiado = false; h.fx.escondido = false;
    var bz = bencao(S, h);
    var r2 = d20(S, mg.nome + ' de ' + h.nome + ' em ' + e.nome + (bz ? ' (Bênção +' + bz + ')' : ''), atqMagia(h) + bz, modo, MONSTROS[e.tipo].ca, 'CA', h);
    var crit = r2.d20 === 20, acerto = crit || (r2.d20 !== 1 && r2.total >= MONSTROS[e.tipo].ca);
    fecharD20(S, r2, acerto, acerto ? (crit ? 'acerto crítico' : 'acerta') : 'erra');
    if (acerto) {
      var d2 = rolarSoma(S, 'Dano de ' + mg.nome, [{ n: mg.n, l: mg.l }], 0, { crit: crit, sufixo: TIPO_DANO[mg.tipo] });
      ferir(S, e, d2, mg.tipo, { crit: crit, corpo: !!mg.toque });
      if (e.vivo && mg.guia) { e.guiado = true; out(S, 'combate', 'Uma luz fraca fica presa a ' + e.nome + ': o próximo ataque contra ele tem vantagem.'); }
      if (e.vivo && mg.lento) { e.lento = true; out(S, 'combate', 'O frio trava as pernas de ' + e.nome + ': ele não avança no próximo turno.'); }
      if (e.vivo && mg.choque) { e.chocado = true; out(S, 'combate', e.nome + ' fica atordoado pelo choque e não faz ataques de oportunidade até o próximo turno dele.'); }
    }
    return true;
  }

  function beberPocao(S, h, alvo) {
    var c = S.combate, ah = alvo ? heroi(S, alvo) : h;
    if (S.pocoes <= 0) return aviso(S, 'O grupo não tem poções de cura.');
    if (!ah || ah.morto) return aviso(S, 'Esse aliado não pode ser curado.');
    if (ah.pv >= ah.pvMax) return aviso(S, ah.nome + ' já está com todos os pontos de vida.');
    if (c && c.turno.bonus) return aviso(S, h.nome + ' já usou a ação bônus neste turno.');
    S.pocoes--;
    var q = rolarSoma(S, 'Poção de cura', [{ n: 2, l: 4 }], 2, { sufixo: 'PV' });
    var estava = ah.pv <= 0, g = curar(ah, q);
    out(S, c ? 'combate' : 'narra', (ah === h ? h.nome + ' bebe a poção de um gole' : h.nome + ' dá a poção a ' + ah.nome) + ': +' + g + ' PV. PV ' + ah.pv + '/' + ah.pvMax + '.' + (estava ? ' ' + ah.nome + ' volta a si.' : '') + ' Poções restantes: ' + S.pocoes + '.');
    if (c) c.turno.bonus = true;
    return true;
  }

  function oportunidades(S, h) {
    if (h.fx.deseng) return;
    vivos(S).forEach(function (e) {
      if (e.zona === 'perto' && e.expulso <= 0 && e.dorme <= 0 && !e.chocado && consc(h)) ataqueInimigo(S, e, h, true);
    });
  }
  function ardiloso(h) { return h.classe === 'ladino' && h.nivel >= 2; }

  // Executa um comando de combate do herói da vez. Devolve true se algo aconteceu.
  function execCombate(S, k, a1, a2) {
    var c = S.combate, h = vez(S), t = c.turno, e, ah, feito = false;
    if (!h) return false;
    switch (k) {
      case 'fim': out(S, 'combate', h.nome + ' encerra o turno.'); avancar(S); return true;
      case 'atk': {
        var w = armas(h).filter(function (x) { return x.id === a1; })[0];
        e = inimigo(S, a2);
        if (!w || !e || !e.vivo) return aviso(S, 'Esse ataque não é possível agora.');
        feito = atacarArma(S, h, w, e); break;
      }
      case 'mag': feito = conjurar(S, h, a1, a2 || null); break;
      case 'mov': {
        e = inimigo(S, a1);
        if (!e || !e.vivo) return aviso(S, 'Esse alvo não está mais em combate.');
        if (t.mov) return aviso(S, h.nome + ' já se moveu neste turno.');
        if (e.zona === 'perto' && h.linha === 'frente') return aviso(S, h.nome + ' já está em corpo a corpo com ' + e.nome + '.');
        if (e.zona !== 'perto') e.zona = ZONAS[ZONAS.indexOf(e.zona) - 1];
        h.linha = 'frente'; t.mov = true;
        out(S, 'combate', h.nome + ' avança: ' + e.nome + ' agora está ' + (e.zona === 'perto' ? 'em corpo a corpo.' : 'a média distância.'));
        feito = true; break;
      }
      case 'frente':
        if (t.mov) return aviso(S, h.nome + ' já se moveu neste turno.');
        if (h.linha === 'frente') return aviso(S, h.nome + ' já está na linha de frente.');
        h.linha = 'frente'; t.mov = true;
        out(S, 'combate', h.nome + ' passa para a linha de frente.');
        feito = true; break;
      case 'tras':
        if (t.mov) return aviso(S, h.nome + ' já se moveu neste turno.');
        if (h.linha !== 'frente') return aviso(S, h.nome + ' já está atrás.');
        if (!frente(S).some(function (x) { return x !== h; })) return aviso(S, 'Alguém precisa segurar a linha de frente. Sem outro herói ali, o jeito é o grupo todo recuar.');
        out(S, 'combate', h.nome + ' recua para trás dos companheiros.');
        oportunidades(S, h);
        t.mov = true;
        if (consc(h)) h.linha = 'tras';
        feito = true; break;
      case 'afastar': {
        if (t.mov) return aviso(S, h.nome + ' já se moveu neste turno.');
        if (!vivos(S).some(function (x) { return x.zona !== 'longe'; })) return aviso(S, 'Os inimigos já estão longe.');
        out(S, 'combate', S.herois.length > 1 ? h.nome + ' puxa o grupo para trás.' : h.nome + ' recua.');
        if (h.linha === 'frente') oportunidades(S, h);
        t.mov = true;
        if (consc(h)) vivos(S).forEach(function (x) { if (x.zona !== 'longe') x.zona = ZONAS[ZONAS.indexOf(x.zona) + 1]; });
        feito = true; break;
      }
      case 'esquiva':
        if (t.acao) return aviso(S, h.nome + ' já usou a ação neste turno.');
        t.acao = true; h.fx.esquiva = true;
        out(S, 'combate', h.nome + ' se concentra em se defender: até o próximo turno, ataques contra ' + h.nome + ' têm desvantagem.');
        feito = true; break;
      case 'deseng': case 'deseng_b':
        if (k === 'deseng_b') { if (!ardiloso(h)) return aviso(S, h.nome + ' não tem Ação Ardilosa.'); if (t.bonus) return aviso(S, h.nome + ' já usou a ação bônus neste turno.'); t.bonus = true; }
        else { if (t.acao) return aviso(S, h.nome + ' já usou a ação neste turno.'); t.acao = true; }
        h.fx.deseng = true;
        out(S, 'combate', h.nome + ' se desengaja: neste turno, pode recuar ou fugir sem sofrer ataques de oportunidade.');
        feito = true; break;
      case 'esconder': case 'esconder_b': {
        if (k === 'esconder_b') { if (!ardiloso(h)) return aviso(S, h.nome + ' não tem Ação Ardilosa.'); if (t.bonus) return aviso(S, h.nome + ' já usou a ação bônus neste turno.'); }
        else if (t.acao) return aviso(S, h.nome + ' já usou a ação neste turno.');
        if (h.linha === 'frente' && algumPerto(S)) return aviso(S, 'Não dá para se esconder com um inimigo em corpo a corpo.');
        if (h.fx.escondido) return aviso(S, h.nome + ' já está escondido.');
        if (k === 'esconder_b') t.bonus = true; else t.acao = true;
        var rh = teste(S, 'Furtividade de ' + h.nome + ' para se esconder', bonusPericia(h, 'furtividade'), null, 15, h);
        if (rh.ok) { h.fx.escondido = true; out(S, 'combate', h.nome + ' some nas sombras: o próximo ataque de ' + h.nome + ' tem vantagem, e ataques contra ' + h.nome + ' têm desvantagem até lá.'); }
        else out(S, 'combate', 'Os inimigos não perdem ' + h.nome + ' de vista.');
        feito = true; break;
      }
      case 'disparada':
        if (!ardiloso(h)) return aviso(S, h.nome + ' não tem Ação Ardilosa.');
        if (t.bonus) return aviso(S, h.nome + ' já usou a ação bônus neste turno.');
        if (!t.mov) return aviso(S, 'Use a Disparada depois do movimento normal: ela dá um movimento a mais.');
        t.bonus = true; t.mov = false;
        out(S, 'combate', 'Disparada: ' + h.nome + ' pode se mover mais uma vez neste turno.');
        feito = true; break;
      case 'pocao': feito = beberPocao(S, h, a1 || null); break;
      case 'folego': {
        if (h.classe !== 'guerreiro') return aviso(S, 'Só o guerreiro tem Retomar o Fôlego.');
        if (h.folego <= 0) return aviso(S, 'Sem usos de Retomar o Fôlego. Um descanso devolve.');
        if (t.bonus) return aviso(S, h.nome + ' já usou a ação bônus neste turno.');
        if (h.pv >= h.pvMax) return aviso(S, h.nome + ' já está com todos os pontos de vida.');
        h.folego--; t.bonus = true;
        var q = rolarSoma(S, 'Retomar o Fôlego de ' + h.nome, [{ n: 1, l: 10 }], h.nivel, { sufixo: 'PV' });
        out(S, 'combate', h.nome + ' respira fundo e segue: +' + curar(h, q) + ' PV. PV ' + h.pv + '/' + h.pvMax + '.');
        feito = true; break;
      }
      case 'surto':
        if (h.surto <= 0) return aviso(S, 'Surto de Ação indisponível.');
        if (!t.acao) return aviso(S, 'Use a ação normal primeiro; o Surto dá uma ação a mais.');
        h.surto--; t.acao = false;
        out(S, 'combate', 'Surto de Ação: ' + h.nome + ' ganha mais uma ação neste turno.');
        feito = true; break;
      case 'expulsar': {
        if (h.classe !== 'clerigo' || h.canalizar <= 0) return aviso(S, 'Canalizar Divindade indisponível.');
        if (t.acao) return aviso(S, h.nome + ' já usou a ação neste turno.');
        var alvos = vivos(S).filter(function (x) { return MONSTROS[x.tipo].mortoVivo && x.zona !== 'longe'; });
        if (!alvos.length) return aviso(S, 'Não há mortos-vivos ao alcance (corpo a corpo ou média distância).');
        h.canalizar--; t.acao = true;
        out(S, 'combate', h.nome + ' ergue o símbolo sagrado e ordena que os mortos recuem.');
        alvos.forEach(function (x) {
          var r = d20(S, 'Salvaguarda de Sabedoria de ' + x.nome, MONSTROS[x.tipo].salv.sab, null, cdMagia(h), 'CD');
          var ok = r.total >= cdMagia(h);
          fecharD20(S, r, ok, ok ? 'resiste' : 'é expulso');
          if (!ok) { x.expulso = 10; out(S, 'combate', x.nome + ' vira o rosto e foge. O efeito acaba se ele sofrer dano.'); }
        });
        feito = true; break;
      }
      case 'centelha': {
        if (h.classe !== 'clerigo' || h.canalizar <= 0) return aviso(S, 'Canalizar Divindade indisponível.');
        if (t.acao) return aviso(S, h.nome + ' já usou a ação neste turno.');
        ah = a1 ? heroi(S, a1) : h;
        if (!ah || ah.morto) return aviso(S, 'Esse aliado não pode ser curado.');
        if (ah.pv >= ah.pvMax) return aviso(S, ah.nome + ' já está com todos os pontos de vida.');
        h.canalizar--; t.acao = true;
        var qc = rolarSoma(S, 'Centelha Divina de ' + h.nome, [{ n: 1, l: 8 }], mod(h.atr.sab), { sufixo: 'PV' });
        var estava = ah.pv <= 0;
        out(S, 'combate', 'A centelha fecha os cortes de ' + ah.nome + ': +' + curar(ah, qc) + ' PV. PV ' + ah.pv + '/' + ah.pvMax + '.' + (estava ? ' ' + ah.nome + ' volta a si.' : ''));
        feito = true; break;
      }
      case 'abafar': {
        var g = grupoDe(S, c.grupo);
        if (!g.abafar) return aviso(S, 'Não há nada para abafar aqui.');
        feito = g.abafar(S, h); break;
      }
      case 'fugir': {
        if (t.acao) return aviso(S, h.nome + ' já usou a ação neste turno; fugir exige a ação.');
        t.acao = true;
        out(S, 'combate', S.herois.length > 1 ? h.nome + ' dá o sinal e o grupo corre.' : h.nome + ' dá as costas e corre.');
        vivos(S).forEach(function (x) {
          var fr = frente(S);
          if (x.zona !== 'perto' || x.expulso > 0 || x.dorme > 0 || x.chocado || !fr.length) return;
          var alvo = sortear(S, fr);
          if (!alvo.fx.deseng) ataqueInimigo(S, x, alvo, true);
        });
        if (!ativos(S).length) { verificarFim(S); return true; }
        var gr = grupoDe(S, c.grupo);
        S.combate = null;
        levantarCaidos(S); limparFx(S);
        out(S, 'narra', gr.textoFuga);
        fato(S, (S.herois.length > 1 ? 'O grupo fugiu' : 'Você fugiu') + ' do combate ' + gr.onde + '. Os inimigos que sobraram continuam lá.');
        entrarCena(S, gr.fugaPara, {});
        return true;
      }
      default: return aviso(S, 'Não entendi essa ação de combate.');
    }
    if (!feito) return false;
    if (verificarFim(S)) return true;
    var atual = vez(S);
    if (S.combate && (!atual || !consc(atual) || (S.combate.turno.acao && !bonusDisponivel(S, atual)))) avancar(S);
    return true;
  }

  function feridos(S) { return vivosH(S).filter(function (x) { return x.pv < x.pvMax; }); }
  function bonusDisponivel(S, h) {
    var t = S.combate.turno;
    if (h.surto > 0 && t.acao) return true;
    if (t.bonus) return false;
    if (S.pocoes > 0 && feridos(S).length) return true;
    if (h.classe === 'guerreiro' && h.folego > 0 && h.pv < h.pvMax) return true;
    if (h.espacos > 0 && !t.espaco && ((temMagia(h, 'palavra') && feridos(S).length) || (temMagia(h, 'escudofe') && ativos(S).some(function (x) { return !x.fx.escudoFe; })))) return true;
    if (ardiloso(h)) return true;
    return false;
  }

  function levantarCaidos(S) {
    S.herois.forEach(function (h) {
      if (h.morto || h.pv > 0) return;
      h.pv = 1; h.caido = null;
      out(S, 'narra', h.nome + ' volta a si, amparado pelos companheiros, com 1 ponto de vida.');
    });
  }

  function verificarFim(S) {
    var c = S.combate;
    if (!c) return true;
    if (!ativos(S).length) { derrota(S); return true; }
    var g = grupoDe(S, c.grupo);
    var acabou = g.fimSe ? g.fimSe(S) : vivos(S).length === 0;
    if (acabou) {
      S.combate = null;
      out(S, 'combate', 'Fim do combate.');
      g.aoVencer(S);
      levantarCaidos(S); limparFx(S);
      checkpoint(S);
      return true;
    }
    return false;
  }

  // Ninguém de pé: o motor resolve os testes contra a morte que faltam.
  function derrota(S) {
    var g = grupoDe(S, S.combate.grupo), guarda = 0;
    S.combate = { grupo: S.combate.grupo, rodada: S.combate.rodada, ordem: [], i: 0, turno: novoTurno() };
    out(S, 'narra', (S.herois.length > 1 ? 'O último herói cai.' : 'O mundo escurece.') + ' O motor rola os testes contra a morte: três sucessos e o herói resiste, três falhas e ' + (S.dificuldade === 'classico' && !g.semMorte ? 'a história dele acaba aqui.' : 'fica por um fio.'));
    S.herois.forEach(function (h) {
      guarda = 0;
      while (!h.morto && h.pv <= 0 && h.caido && !h.caido.estavel && guarda++ < 20) testeMorte(S, h);
    });
    S.combate = null;
    limparFx(S);
    var sobrou = vivosH(S);
    if (!sobrou.length) {
      S.fim = { tipo: 'morte' };
      out(S, 'narra', 'O frio sobe devagar e depois não há mais frio. ' + (S.herois.length > 1 ? 'Ninguém do grupo volta.' : S.herois[0].nome + ' não volta.') + '\n\nVocê pode voltar ao último ponto seguro ou começar uma nova campanha.');
      return;
    }
    sobrou.forEach(function (h) { if (h.pv <= 0) { h.pv = 1; h.caido = null; } });
    out(S, 'narra', g.textoQueda(S));
    fato(S, (S.herois.length > 1 ? 'O grupo foi derrotado ' : 'Você caiu ') + g.onde + (sobrou.length < S.herois.length ? ', e nem todos resistiram.' : ', mas resistiu.') + ' Quem sobreviveu acordou com 1 PV.');
    entrarCena(S, g.acordaEm, { calado: true });
  }

  /* ------------------------------------------------------------------ descansos */
  function precisaCurto(h) {
    return (h.classe === 'guerreiro' && (h.folego < 2 || (h.nivel >= 2 && h.surto < 1))) || (h.classe === 'clerigo' && h.nivel >= 2 && h.canalizar < 2) || (h.classe === 'mago' && h.recArcana > 0 && h.espacos < h.espacosMax);
  }
  function valeCurto(S) { return vivosH(S).some(function (h) { return (h.pv < h.pvMax && h.dv > 0) || precisaCurto(h); }); }
  function descansoCurto(S) {
    var cena = AV(S).cenas[S.cena];
    if (!cena.seguro(S)) return aviso(S, 'Aqui não é seguro para descansar. ' + (cena.motivoInseguro || 'Há perigo por perto.'));
    out(S, 'narra', S.herois.length > 1 ? 'O grupo encosta, afrouxa as correias e deixa uma hora passar.' : 'Você encosta, afrouxa as correias e deixa uma hora passar.');
    var linhas = ['Descanso curto: uma hora parado, recuperando as forças.'];
    vivosH(S).forEach(function (h) {
      var gastou = 0, partes = [];
      while (h.dv > 0 && (h.pvMax - h.pv >= 3 || (gastou === 0 && h.pv < h.pvMax && h.pv <= h.pvMax / 2))) {
        h.dv--; gastou++;
        curar(h, rolarSoma(S, 'Dado de Vida de ' + h.nome, [{ n: 1, l: CLASSES[h.classe].dv }], mod(h.atr.con), { sufixo: 'PV' }));
      }
      if (gastou) partes.push('gastou ' + gastou + ' Dado' + (gastou > 1 ? 's' : '') + ' de Vida');
      if (h.classe === 'guerreiro') { if (h.folego < 2) { h.folego++; partes.push('Retomar o Fôlego +1'); } if (h.nivel >= 2 && h.surto < 1) { h.surto = 1; partes.push('Surto de Ação de volta'); } }
      if (h.classe === 'clerigo' && h.nivel >= 2 && h.canalizar < 2) { h.canalizar++; partes.push('Canalizar Divindade +1'); }
      if (h.classe === 'mago' && h.recArcana > 0 && h.espacos < h.espacosMax) { h.recArcana--; h.espacos++; partes.push('Recuperação Arcana: +1 espaço de magia'); }
      linhas.push(h.nome + ': PV ' + h.pv + '/' + h.pvMax + (partes.length ? ' · ' + partes.join(' · ') : ''));
    });
    out(S, 'sistema', linhas.join('\n'));
    checkpoint(S);
    return true;
  }
  function descansoLongo(S) {
    var cena = AV(S).cenas[S.cena];
    if (!cena.longo) return aviso(S, 'Um descanso longo pede cama e porta trancada. ' + (AV(S).ondeLongo || 'Aqui não dá.'));
    S.dia++;
    vivosH(S).forEach(function (h) {
      h.pv = h.pvMax; h.caido = null; h.dv = h.dvTotal; h.espacos = h.espacosMax; h.armaduraArcana = false;
      if (h.classe === 'guerreiro') { h.folego = 2; if (h.nivel >= 2) h.surto = 1; }
      if (h.classe === 'clerigo' && h.nivel >= 2) h.canalizar = 2;
      if (h.classe === 'mago') h.recArcana = 1;
      if (h.especie === 'orc') h.implacavel = 1;
    });
    out(S, 'narra', cena.longo(S));
    out(S, 'sistema', 'Descanso longo: PV, Dados de Vida, espaços de magia e habilidades recuperados.');
    checkpoint(S);
    return true;
  }
