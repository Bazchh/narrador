  /* ================================================================== CAMPANHA COMO KIT DE MESTRE
     Uma aventura deste tipo não é roteiro: é material de mestre (lugares, pessoas, segredos, uma ameaça que
     avança, finais possíveis). O mestre por IA conduz a partir do kit. Ele só muda o jogo propondo EFEITOS de
     uma lista fechada, e o motor confere cada um antes de aplicar. Sem IA, o motor gera botões a partir do
     mesmo kit, e a aventura continua jogável de forma mais simples. */

  function tx(v, S) { return typeof v === 'function' ? v(S) : (v || ''); }
  function kitDe(S) { return AV(S).kit || null; }
  function kitS(S) { if (!S.k || typeof S.k !== 'object') S.k = { rev: {}, rel: 0, at: {}, f: {} }; return S.k; }
  function kf(S, nome) { return !!kitS(S).f[nome]; }
  function kRev(S, id) { return !!kitS(S).rev[id]; }
  // exige: lista de alternativas; cada alternativa é uma lista de condições ('marca', '!marca', 'rev:segredo')
  function cumpre(S, exige) {
    if (!exige || !exige.length) return true;
    return exige.some(function (alt) {
      return alt.every(function (t) {
        var nao = t.charAt(0) === '!', n = nao ? t.slice(1) : t;
        var v = n.indexOf('rev:') === 0 ? kRev(S, n.slice(4)) : kf(S, n);
        return nao ? !v : v;
      });
    });
  }
  function atitude(S, pid) { var k = kitDe(S); return kitS(S).at[pid] || (k && k.pessoas[pid] && k.pessoas[pid].atitude) || 'neutro'; }
  function presente(S, pid) {
    var k = kitDe(S), p = k && k.pessoas[pid];
    return !!p && p.onde === S.cena && !estaMorto(S, pid) && cumpre(S, p.se);
  }
  function grupoAtivo(S, gid) {
    var k = kitDe(S), G = k && k.grupos[gid], l = S.inimigos[gid];
    if (!G || !l || !l.some(function (e) { return e.vivo; })) return false;
    return !kf(S, gid + '_vencido') && !kf(S, gid + '_evitado') && !kf(S, gid + '_partiu') && !(G.cedeCom && kf(S, G.cedeCom));
  }
  var ROT_ATITUDE = { amigavel: 'do seu lado', neutro: 'neutro', hostil: 'hostil', rendido: 'rendido' };

  function relogioKit(S, n, motivo) {
    var k = kitDe(S), R = k && k.relogio, e = kitS(S);
    if (!R || e.f.tarde || (R.paraSe && cumpre(S, R.paraSe))) return;
    e.rel = Math.min(R.max, e.rel + n);
    out(S, 'sistema', 'Ameaça · ' + R.nome + ': ' + e.rel + ' de ' + R.max + (motivo ? ' (' + motivo + ')' : '') + '.');
    if (e.rel >= R.max) {
      e.f.tarde = true;
      (R.aoEncher.marcas || []).forEach(function (m) { e.f[m] = true; });
      out(S, 'narra', tx(R.aoEncher.texto, S));
      fato(S, R.aoEncher.fato);
    }
  }
  function revelarKit(S, id) {
    var k = kitDe(S), sg = k.segredos[id];
    if (!sg || kRev(S, id)) return false;
    kitS(S).rev[id] = true;
    fato(S, 'Descoberto: ' + sg.texto);
    return true;
  }
  function finalizarKit(S, fid) {
    var F = kitDe(S).finais[fid];
    out(S, 'narra', tx(F.texto, S));
    if (F.ouro) { var q = tx(F.ouro, S); if (q > 0) { S.ouro += q; out(S, 'sistema', 'O grupo recebe ' + q + ' po.'); } }
    fato(S, tx(F.fato, S));
    S.fim = { tipo: 'vitoria', final: fid };
    out(S, 'titulo', 'Fim da aventura');
    out(S, 'sistema', resumo(S));
  }

  /* Confere e aplica os efeitos propostos. ctx: { teste, cd, falha, confiavel }
     - confiavel: efeito vindo do próprio kit (botões do motor), não da IA.
     Devolve quantos foram recusados. */
  function aplicarEfeitos(S, lista, ctx) {
    var k = kitDe(S), e = kitS(S), recusados = 0, usouRelogio = false, i;
    if (!k || !Array.isArray(lista)) return 0;
    ctx = ctx || {};
    lista = lista.slice(0, 5);
    for (i = 0; i < lista.length && !S.fim && !S.combate; i++) {
      var ef = lista[i], ok = false;
      if (!ef || typeof ef !== 'object') { recusados++; continue; }
      if (typeof ef.revelar === 'string') {
        var sg = k.segredos[ef.revelar];
        var aqui = sg && ((sg.onde || []).indexOf(S.cena) >= 0 || (sg.quem || []).some(function (p) { return presente(S, p); }));
        var merece = sg && (ctx.confiavel || ctx.teste || sg.livre || (sg.quem || []).some(function (p) { return presente(S, p) && /amigavel|rendido/.test(atitude(S, p)); }));
        if (sg && !kRev(S, ef.revelar) && !ctx.falha && (ctx.confiavel || (aqui && merece))) ok = revelarKit(S, ef.revelar);
      } else if (typeof ef.marca === 'string') {
        var mk = k.marcas[ef.marca];
        if (mk && !e.f[ef.marca] && !ctx.falha && (!mk.lugar || mk.lugar.indexOf(S.cena) >= 0) && cumpre(S, mk.exige) && (!mk.quem || presente(S, mk.quem)) &&
            (ctx.confiavel || !mk.cd || (ctx.teste && ctx.cd >= mk.cd))) {
          e.f[ef.marca] = true; ok = true;
          fato(S, mk.texto);
          if (mk.ouro) { S.ouro += mk.ouro; out(S, 'sistema', 'O grupo recebe ' + mk.ouro + ' po.'); }
          if (mk.efeitos) aplicarEfeitos(S, mk.efeitos, { confiavel: true });
        }
      } else if (ef.atitude && typeof ef.atitude === 'object') {
        var quem = String(ef.atitude.quem || ''), para = String(ef.atitude.para || ''), p = k.pessoas[quem];
        var precisaTeste = para === 'amigavel' || para === 'rendido';
        if (p && presente(S, quem) && ROT_ATITUDE[para] && atitude(S, quem) !== para && !(para === 'rendido' && !p.rendivel) &&
            (ctx.confiavel || !precisaTeste || (ctx.teste && !ctx.falha))) {
          e.at[quem] = para; ok = true;
          fato(S, p.nome + ' agora está ' + ROT_ATITUDE[para] + '.');
        }
      } else if (ef.relogio !== undefined) {
        var n = Math.round(Number(ef.relogio));
        if (!usouRelogio && n >= 1 && n <= (ctx.confiavel ? 3 : 1) && k.relogio) { usouRelogio = true; ok = true; relogioKit(S, n, ef.motivo ? texto(ef.motivo, 60) : null); }
      } else if (typeof ef.luta === 'string' && ctx.confiavel) {
        if (grupoAtivo(S, ef.luta) && k.grupos[ef.luta].lugar === S.cena) { ok = true; out(S, 'narra', tx(k.grupos[ef.luta].intro, S)); iniciarCombate(S, ef.luta, {}); }
      } else if (typeof ef.final === 'string') {
        var F = k.finais[ef.final];
        if (F && !ctx.falha && F.lugar.indexOf(S.cena) >= 0 && cumpre(S, F.exige)) { ok = true; finalizarKit(S, ef.final); }
      }
      if (!ok) recusados++;
    }
    if (recusados && !ctx.confiavel) out(S, 'sistema', 'O motor não aceitou ' + (recusados > 1 ? recusados + ' mudanças propostas' : 'uma mudança proposta') + ' pelo mestre, por falta de base no material da campanha. O resto vale.');
    return recusados;
  }

  /* ---------- do kit para o formato que o motor já conhece ---------- */
  function cenaDeKit(kit, lid) {
    var L = kit.lugares[lid], acoes = [];
    function gente(S) { return Object.keys(kit.pessoas).filter(function (pid) { return presente(S, pid); }); }
    function hostilAqui(S) { return L.grupo && grupoAtivo(S, L.grupo); }
    function fechado(S) { return !!(L.fechaCom && kf(S, L.fechaCom)); }

    Object.keys(kit.pessoas).forEach(function (pid) {
      var p = kit.pessoas[pid];
      if (p.onde !== lid || !p.fala) return;
      acoes.push({
        id: 'falar_' + pid, rot: 'Falar com ' + p.nome, re: p.reFala || p.re,
        se: function (S) { return presente(S, pid) && atitude(S, pid) !== 'hostil' && !fechado(S); },
        fazer: function (S) { out(S, 'narra', tx(p.fala, S)); (p.conta || []).forEach(function (sid) { revelarKit(S, sid); }); }
      });
    });
    Object.keys(kit.segredos).forEach(function (sid) {
      var ps = kit.segredos[sid].pista;
      if (!ps || ps.lugar !== lid) return;
      acoes.push({
        id: 'pista_' + sid, rot: ps.rot, re: ps.re,
        se: function (S) { return !kRev(S, sid) && cumpre(S, ps.exige) && (!ps.quem || presente(S, ps.quem)) && !(ps.semHostis && hostilAqui(S)) && !fechado(S); },
        veredito: function () { return { tipo: 'teste', per: ps.per, cd: ps.cd, grupo: !!ps.grupo }; },
        fazer: function (S, r) {
          if (r.ok) { out(S, 'narra', tx(ps.ok, S)); revelarKit(S, sid); }
          else { out(S, 'narra', tx(ps.falha, S)); if (ps.falhaEfeitos) aplicarEfeitos(S, ps.falhaEfeitos, { confiavel: true }); }
        }
      });
    });
    (kit.acoes[lid] || []).forEach(function (a) {
      acoes.push({
        id: a.id, rot: a.rot, re: a.re, repetivel: !!a.repetivel,
        se: function (S) { return cumpre(S, a.exige) && (!a.quem || presente(S, a.quem)) && (!a.grupoAtivo || grupoAtivo(S, a.grupoAtivo)) && !fechado(S); },
        veredito: a.per ? function () { return { tipo: 'teste', per: a.per, cd: a.cd, grupo: !!a.grupo }; } : null,
        fazer: function (S, r) {
          var lado = r.ok ? a.ok : a.falha;
          out(S, 'narra', tx(lado.txt, S));
          if (lado.efeitos) aplicarEfeitos(S, lado.efeitos, { confiavel: true });
        }
      });
    });
    if (L.grupo) {
      var G = kit.grupos[L.grupo];
      acoes.push({
        id: 'enfrentar_' + L.grupo, rot: G.rotLuta, re: G.re,
        se: function (S) { return hostilAqui(S); },
        fazer: function (S) { out(S, 'narra', tx(G.intro, S)); iniciarCombate(S, L.grupo, {}); }
      });
    }
    Object.keys(kit.finais).forEach(function (fid) {
      var F = kit.finais[fid];
      if (F.lugar.indexOf(lid) < 0) return;
      acoes.push({ id: 'final_' + fid, rot: F.rot, re: F.re, livre: true, se: function (S) { return cumpre(S, F.exige); }, fazer: function (S) { finalizarKit(S, fid); } });
    });
    if (L.longo) acoes.push({ id: 'longo', rot: 'Passar a noite (descanso longo)', re: /descans|dorm|pernoit|passar a noite|quarto|cama/, se: function (S) { return !fechado(S); }, fazer: function (S) { descansoLongo(S); } });

    var cena = {
      kit: true, nome: L.nome, lugar: L.lugar,
      desc: function (S) {
        var d = tx(L.desc, S);
        (L.estados || []).forEach(function (e) { if (cumpre(S, e.se)) d += ' ' + tx(e.txt, S); });
        return d;
      },
      presentes: function (S) {
        var l = gente(S).map(function (pid) { var p = kit.pessoas[pid]; return p.nome + ', ' + p.papel + (atitude(S, pid) !== 'neutro' ? ' (' + ROT_ATITUDE[atitude(S, pid)] + ')' : ''); });
        if (hostilAqui(S)) l.push(tx(kit.grupos[L.grupo].presenca, S));
        return l;
      },
      pessoas: function (S) {
        return gente(S).filter(function (pid) { return kit.pessoas[pid].tipo && !kit.pessoas[pid].intocavel; }).map(function (pid) { var p = kit.pessoas[pid]; return { id: pid, nome: p.nome, tipo: p.tipo, hp: p.hp, re: p.re }; });
      },
      seguro: function (S) { return !!L.seguro && !hostilAqui(S) && !fechado(S); },
      motivoInseguro: L.motivoInseguro || 'Aqui não há como baixar a guarda.',
      entrar: function (S, o) {
        if (o.primeira) out(S, 'narra', tx(L.chegada, S));
        else if (!o.calado) out(S, 'narra', tx(L.volta, S));
        if (L.nivel) subirNivel(S, L.nivel);
      },
      acoes: acoes, topicos: [],
      saidas: function (S) {
        return Object.keys(L.liga).map(function (d) {
          var c = L.liga[d], bloqueio = null;
          if (c.exige && !cumpre(S, c.exige)) { if (c.oculta) return null; bloqueio = c.bloqueio; }
          if (c.atrasDoGrupo && hostilAqui(S)) bloqueio = tx(kit.grupos[L.grupo].bloqueio, S);
          return { para: d, rot: c.rot, re: c.re, bloqueio: bloqueio };
        }).filter(Boolean);
      },
      aoAtacar: function (S, alvos) { return 'O ar muda antes do primeiro golpe. ' + alvos.map(function (p) { return p.nome; }).join(' e ') + (alvos.length > 1 ? ' recuam' : ' recua') + ' um passo, sem para onde correr.'; },
      aposBriga: function (S, nomes) { return kf(S, 'vila_hostil') ? 'Quando acaba, o silêncio dura pouco. Uma porta bate, depois outra. Alguém corre para avisar os outros. ' + nomes + ' não vai se levantar, e este lugar não vai esquecer quem fez isso.' : 'Quando acaba, só se ouve o rio. ' + nomes + ' não vai se levantar.'; },
      // briga contra alguém do kit: quem ataca inocente perde o lugar; quem ataca culpado só ganha um inimigo
      aoBriga: function (S, alvos) {
        alvos.forEach(function (a) {
          var p = kit.pessoas[a.id];
          kitS(S).at[a.id] = 'hostil';
          if (p && p.inocente && !kf(S, 'vila_hostil')) { kitS(S).f.vila_hostil = true; fato(S, (S.herois.length > 1 ? 'O grupo atacou ' : 'O herói atacou ') + p.nome + ', que não tinha feito nada. ' + kit.lugares[kit.inicio].nome + ' se volta contra os heróis.'); }
        });
      },
      mapa: function (S) {
        return {
          tema: L.tema, grupo: L.grupo || null, neutro: false,
          mostra: function () { return hostilAqui(S); },
          npcs: function () { return gente(S).map(function (pid, i) { var p = kit.pessoas[pid], xy = p.pos || [4 + i * 2, 3]; return { n: p.nome, x: xy[0], y: xy[1] }; }); }
        };
      }
    };
    // um novo dia permite tentar de novo as pistas que falharam
    if (L.longo) cena.longo = function (S) { Object.keys(S.tentou).forEach(function (c) { if (c.indexOf('pista_') === 0) delete S.tentou[c]; }); relogioKit(S, (kit.relogio && kit.relogio.passos.longo) || 0, 'uma noite se passou'); return tx(L.longo, S); };
    return cena;
  }
  function gruposDeKit(kit) {
    var g = {};
    Object.keys(kit.grupos).forEach(function (gid) {
      var G = kit.grupos[gid];
      g[gid] = {
        zonas: {}, zonaPadrao: G.zona || 'medio', alerta: gid + 'Alerta', onde: G.onde, fugaPara: G.fugaPara, acordaEm: kit.inicio,
        textoFuga: G.textoFuga,
        textoQueda: function (S) {
          var perdeu = Math.floor(S.ouro / 2); S.ouro -= perdeu;
          relogioKit(S, 1, 'os heróis perderam tempo se recuperando');
          return tx(G.textoQueda, S) + (perdeu ? ' Faltam ' + perdeu + ' po na bolsa.' : '') + ' ' + (S.herois.length > 1 ? 'Quem resistiu está' : 'Você está') + ' com 1 ponto de vida.';
        },
        fimSe: G.chefe ? function (S) { var l = S.inimigos[gid]; return !l.some(function (e) { return e.vivo; }) || !l.filter(function (e) { return e.chefe; })[0].vivo; } : null,
        aoVencer: function (S) {
          S.inimigos[gid].forEach(function (e) { e.vivo = false; });
          kitS(S).f[gid + '_vencido'] = true;
          out(S, 'narra', tx(G.vitoria, S));
          fato(S, tx(G.fato, S));
          if (G.nivel) subirNivel(S, G.nivel);
          if (G.efeitos) aplicarEfeitos(S, G.efeitos, { confiavel: true });
        }
      };
    });
    return g;
  }
  function inimigosDeKit(kit) {
    return function (n) {
      var r = {};
      Object.keys(kit.grupos).forEach(function (gid) {
        var G = kit.grupos[gid], l = varios(G.n(n), G.pre, G.tipo, G.nomeUm, G.hp ? G.hp(n) : null);
        if (G.chefe) { var c = mk(G.pre + 'c', G.chefe.tipo, G.chefe.nome, G.chefe.hp(n)); c.chefe = true; l.unshift(c); }
        r[gid] = l;
      });
      return r;
    };
  }
  function aventuraDeKit(kit) {
    var cenas = {};
    Object.keys(kit.lugares).forEach(function (lid) { cenas[lid] = cenaDeKit(kit, lid); });
    return {
      id: kit.id, titulo: kit.titulo, duracao: kit.duracao, nivel: kit.nivel, tipo: kit.tipo, resumo: kit.resumo, kit: kit,
      inicio: kit.inicio, cenas: cenas, grupos: gruposDeKit(kit), inimigos: inimigosDeKit(kit), ondeLongo: kit.ondeLongo,
      notas: function () { return kit.tom; }
    };
  }

  /* ---------- o que o mestre por IA recebe do kit, só do lugar onde o grupo está ---------- */
  function promptKit(S) {
    var k = kitDe(S), e = kitS(S), L = k.lugares[S.cena], l = [], x;
    l.push('MATERIAL DO MESTRE (o jogador NÃO vê isto)');
    l.push('PREMISSA: ' + k.premissa);
    x = Object.keys(k.pessoas).filter(function (p) { return presente(S, p); }).map(function (pid) {
      var p = k.pessoas[pid];
      return '- ' + pid + ' = ' + p.nome + ', ' + p.papel + '. Atitude: ' + ROT_ATITUDE[atitude(S, pid)] + '. Quer: ' + p.quer + ' Sabe: ' + p.sabe + (p.rendivel ? ' Pode se render.' : '');
    });
    l.push('PESSOAS NESTA CENA:'); l = l.concat(x.length ? x : ['- (ninguém)']);
    if (L.grupo && grupoAtivo(S, L.grupo)) l.push('GRUPO HOSTIL AQUI: ' + L.grupo + ' = ' + tx(k.grupos[L.grupo].presenca, S) + '. ' + (k.grupos[L.grupo].nota || ''));
    x = Object.keys(k.segredos).filter(function (sid) {
      var sg = k.segredos[sid];
      return !kRev(S, sid) && ((sg.onde || []).indexOf(S.cena) >= 0 || (sg.quem || []).some(function (p) { return presente(S, p); }));
    }).map(function (sid) { var sg = k.segredos[sid]; return '- ' + sid + ': ' + sg.texto + ' [como se descobre: ' + sg.como + ']'; });
    l.push('SEGREDOS AINDA GUARDADOS que podem vir à tona NESTA cena:'); l = l.concat(x.length ? x : ['- (nenhum)']);
    x = Object.keys(e.rev).map(function (sid) { return '- ' + k.segredos[sid].texto; });
    if (x.length) { l.push('JÁ DESCOBERTO PELOS HERÓIS:'); l = l.concat(x); }
    x = Object.keys(k.marcas).filter(function (m) {
      var mk = k.marcas[m];
      return !e.f[m] && (!mk.lugar || mk.lugar.indexOf(S.cena) >= 0) && cumpre(S, mk.exige) && (!mk.quem || presente(S, mk.quem));
    }).map(function (m) { var mk = k.marcas[m]; return '- ' + m + ': ' + mk.quando + (mk.cd ? ' [só como resultado de um teste com CD ' + mk.cd + ' ou mais]' : ''); });
    l.push('MARCAS QUE PODEM ACONTECER AQUI:'); l = l.concat(x.length ? x : ['- (nenhuma)']);
    x = Object.keys(k.finais).filter(function (f) { return k.finais[f].lugar.indexOf(S.cena) >= 0 && cumpre(S, k.finais[f].exige); }).map(function (f) { return '- ' + f + ': ' + k.finais[f].quando; });
    if (x.length) { l.push('FINAIS QUE JÁ PODEM ACONTECER AQUI:'); l = l.concat(x); }
    if (k.relogio && !e.f.tarde) l.push('AMEAÇA: ' + k.relogio.nome + ', em ' + e.rel + ' de ' + k.relogio.max + '. ' + k.relogio.quando);
    if (e.f.tarde) l.push('AMEAÇA CUMPRIDA: ' + k.relogio.aoEncher.fato);
    if (kf(S, 'vila_hostil')) l.push('SITUAÇÃO: os heróis atacaram um inocente. A vila os teme e os quer longe; ninguém ali ajuda ou paga.');
    return l;
  }
  var REGRAS_KIT = [
    'CAMPANHA DE MESTRE: aqui você conduz. Narre com liberdade a partir do MATERIAL DO MESTRE: dê voz às pessoas conforme o que querem e sabem, deixe o jogador tentar o que quiser e mostre consequências.',
    'Para MUDAR o jogo, e só assim, acrescente "efeitos" a um improviso: uma lista com até 3 itens destes tipos:',
    '   {"revelar":"<id de SEGREDOS>"}  {"marca":"<id de MARCAS>"}  {"atitude":{"quem":"<id de PESSOAS>","para":"amigavel|neutro|hostil|rendido"}}  {"relogio":1}  {"final":"<id de FINAIS>"}',
    '   Em improviso com teste, "efeitos" valem só se o teste der sucesso; para a falha use "efeitos_falha" (só relogio ou atitude hostil).',
    '   O motor confere cada efeito contra o material e recusa o que não tiver base. Nunca invente ids.',
    'Não conte um segredo na narração sem o efeito "revelar" correspondente. Se o momento não justifica, o segredo continua guardado e a pessoa desconversa.',
    'Para lutar contra o GRUPO HOSTIL, responda {"tipo":"luta","alvos":["<id do grupo>"],"narracao":"..."}.',
    'Não dê ouro, itens, cura nem vitórias por narração: isso só acontece por efeitos, por combate ou por ações previstas.'
  ];

  /* ------------------------------------------------------------------ kit: A Ponte do Corvo */
  var KIT_PONTE = {
    id: 'ponte', titulo: 'A Ponte do Corvo', duracao: '30 a 60 minutos', nivel: 'Níveis 1 e 2', tipo: 'Campanha de mestre',
    resumo: 'Carroças somem na estrada do rio, sempre depois da ponte velha. Quatro lugares, gente com segredos, uma ameaça que não espera e vários finais. Feita para o mestre por IA: você tenta o que quiser e o mundo responde.',
    ondeLongo: 'Só na Taverna do Remo Partido, na vila.',
    inicio: 'vila',
    premissa: 'Na vila de Vau do Corvo, três carroças de mercadores sumiram em um mês, sempre depois da ponte velha. A verdade: Tobin, o cobrador do pedágio, avisa um bando de salteadores com uma lanterna verde quando passa carga rica. O bando desvia a carroça por uma trilha na mata, guardada por lobos famintos, até um moinho abandonado. O chefe, Garra, mantém vivo o mercador Osric para pedir resgate. O bando pretende ir embora em poucos dias.',
    tom: 'Fantasia clássica de estrada e fronteira: vila pequena à beira de um rio, gente comum com medo, bandidos que são gente e não monstros. Tom sóbrio, concreto, sem humor forçado.',
    lugares: {
      vila: {
        nome: 'Vau do Corvo', lugar: 'Taverna do Remo Partido', tema: 'taverna', seguro: true, fechaCom: 'vila_hostil',
        motivoInseguro: 'Depois do que aconteceu, ninguém em Vau do Corvo lhe abre a porta.',
        desc: 'Taverna de tábuas escuras à beira do rio, com um remo quebrado pregado sobre a lareira. Carroceiros parados bebem devagar, sem ter para onde ir.',
        estados: [{ se: [['vila_hostil']], txt: 'As janelas se fecham à sua passagem. Ninguém fala com você.' }],
        chegada: 'A estrada do rio termina, por hoje, na vila de Vau do Corvo: uma dúzia de casas, um vau raso e a Taverna do Remo Partido. Há carroças demais paradas no pátio e gente demais sem fazer nada.\n\nAtrás do balcão, uma mulher de mangas arregaçadas mede você de cima a baixo. Perto da porta, uma menina de uns dez anos finge varrer o chão e não tira os olhos da estrada.',
        volta: 'A Taverna do Remo Partido continua cheia de carroceiros que não se arriscam na estrada.',
        longo: function (S) { return 'Um quarto sob o telhado, com cheiro de rio e de lenha molhada. Amanhece o dia ' + S.dia + '.'; },
        liga: { ponte: { rot: 'Ir até a ponte velha', re: /ponte|pedagio|estrada|sair|saio|seguir|sigo/ } }
      },
      ponte: {
        nome: 'Ponte Velha', lugar: 'Estrada do rio, meia légua acima da vila', tema: 'trilha', seguro: false,
        desc: 'Ponte de pedra de um arco só, mais velha que a vila. Do lado de cá, a casa do pedágio: uma porta, uma janela, uma corrente atravessada na estrada.',
        chegada: 'A ponte velha aparece depois da curva: pedra escura, um arco só, o rio grosso de chuva por baixo. Uma corrente fecha a passagem. Da casa do pedágio sai um homem magro, limpando as mãos no avental, com o sorriso de quem cobra de todo mundo.',
        volta: 'A ponte velha continua onde sempre esteve, com a corrente atravessada na estrada.',
        liga: {
          vila: { rot: 'Voltar à vila', re: /vila|vau|taverna|voltar|volto/ },
          mata: { rot: 'Seguir a trilha escondida na mata', re: /trilha|mata|rastro|floresta|seguir|sigo/, exige: [['rev:trilha']], oculta: true }
        }
      },
      mata: {
        nome: 'Trilha da Mata', lugar: 'Mata fechada além da ponte', tema: 'trilha', seguro: false, grupo: 'lobos',
        desc: 'Trilha estreita de terra batida por rodas, escondida da estrada por uma cortina de galhos cortados. A mata é escura e quieta demais.',
        chegada: 'Os galhos que escondem a entrada foram cortados e postos ali de propósito. Depois deles, a trilha é larga o bastante para uma carroça, e há sulcos fundos de rodas na lama. A mata se fecha por cima. Em algum lugar à frente, alguma coisa rosna baixo.',
        volta: 'A trilha na mata continua escura. Os sulcos das rodas seguem para dentro.',
        liga: {
          ponte: { rot: 'Voltar à ponte', re: /ponte|voltar|volto|estrada/ },
          moinho: { rot: 'Seguir os sulcos até o fim da trilha', re: /moinho|sulco|seguir|sigo|adiante|frente|fim da trilha/, atrasDoGrupo: true }
        }
      },
      moinho: {
        nome: 'Moinho Afogado', lugar: 'Clareira no fim da trilha', tema: 'patio', seguro: false, grupo: 'bando', nivel: 'ao chegar ao moinho',
        desc: 'Moinho de água abandonado, com a roda parada e meio submersa. Três carroças sem cavalos estão encostadas na parede.',
        estados: [
          { se: [['bando_partiu']], txt: 'Não há ninguém. As cinzas de uma fogueira grande ainda estão mornas, e as carroças foram esvaziadas.' },
          { se: [['bando_vencido']], txt: 'O que sobrou do bando está amarrado ou caído.' },
          { se: [['acordo']], txt: 'O bando se foi pela mata, levando o que pôde carregar.' }
        ],
        chegada: function (S) { return kf(S, 'bando_partiu') ? 'A trilha termina numa clareira com um moinho de água abandonado. Três carroças vazias, uma fogueira apagada às pressas e nenhum som além do rio. Quem estava aqui foi embora.' : 'A trilha termina numa clareira. Um moinho de água abandonado, a roda parada e meio afogada, três carroças encostadas na parede. Há fumaça saindo de um buraco no telhado, vozes de homens e, por um instante, o som de alguém tossindo atrás de uma porta trancada por fora.'; },
        volta: 'O moinho afogado continua na clareira, no fim da trilha.',
        liga: { mata: { rot: 'Voltar pela trilha', re: /voltar|volto|trilha|mata|recuar|recuo/ } }
      }
    },
    pessoas: {
      halda: {
        nome: 'Halda', papel: 'taverneira que fala pela guilda dos carroceiros', onde: 'vila', tipo: 'plebeu', inocente: true, pos: [6.5, 3.6],
        re: /halda|taverneira|dona|mulher|guilda|balcao/,
        quer: 'as carroças de volta à estrada; paga 40 po, em nome da guilda, a quem descobrir o que acontece e der fim nisso.',
        sabe: 'três carroças sumiram em um mês, sempre depois da ponte velha e sempre as de carga mais rica; nenhum corpo apareceu; ela acha que são lobos ou coisa pior, e não desconfia de ninguém da vila.',
        fala: function (S) { return kf(S, 'ouviu_halda') ? '“Já lhe disse o que sei”, responde Halda. “Três carroças, sempre depois da ponte, sempre as melhores. Quarenta peças a quem acabar com isso.”' : (kitS(S).f.ouviu_halda = true, 'Halda põe um copo na sua frente antes de você pedir.\n\n“Três carroças em um mês. Todas somem depois da ponte velha, e nunca as de carga pobre. Nem roda, nem cavalo, nem corpo. Os carroceiros dizem que são lobos. Lobo não leva barril de vinho.” Ela bate com o dedo no balcão. “A guilda paga quarenta peças de ouro a quem descobrir o que é e der fim nisso. Comece pela ponte. E não conte com o cobrador do pedágio: Tobin nunca vê nada.”'); }
      },
      mira: {
        nome: 'Mira', papel: 'menina de uns dez anos, filha do ferreiro', onde: 'vila', intocavel: true, inocente: true, pos: [3, 5.5],
        re: /mira|menina|crianca|garota/,
        quer: 'que alguém acredite nela, mas tem medo de Tobin, que a ameaçou.',
        sabe: 'nas noites em que uma carroça some, uma luz verde acende na janela da casa do pedágio. Ela viu duas vezes, do telhado do pai.',
        fala: 'Mira para de varrer, olha para a porta, olha para você e volta a varrer mais depressa. “Eu não vi nada”, diz, sem que ninguém tenha perguntado.'
      },
      tobin: {
        nome: 'Tobin', papel: 'cobrador do pedágio', onde: 'ponte', tipo: 'plebeu', hp: 8, rendivel: true, pos: [7, 3], se: [['!tobin_fugiu']],
        re: /tobin|cobrador|homem|pedagio/,
        quer: 'que ninguém olhe o baú dele nem pergunte da lanterna; é covarde, e entrega o bando se achar que vai ser enforcado sozinho.',
        sabe: 'tudo: é ele quem avisa o bando com a lanterna verde; a trilha fica logo depois da ponte, atrás de galhos cortados; o moinho; e que o mercador Osric está vivo, preso para resgate.',
        fala: function (S) { return kf(S, 'tobin_confessa') ? 'Tobin está sentado no chão, de costas para a parede, e fala sem levantar os olhos. “A trilha é depois da ponte, atrás dos galhos. O moinho fica no fim. O mercador está vivo, eu juro que está vivo.”' : '“Duas moedas de cobre por pessoa, cinco por roda”, recita Tobin. “Carroças? Passam por aqui inteiras, eu cobro, elas seguem. O que acontece depois da ponte não é da minha conta. Lobos, dizem.” Ele sorri demais para quem não tem nada a esconder.'; }
      },
      osric: {
        nome: 'Osric', papel: 'mercador preso no moinho', onde: 'moinho', intocavel: true, inocente: true, pos: [9.5, 2], se: [['!bando_partiu', '!osric_livre']],
        re: /osric|mercador|prisioneiro|preso/,
        quer: 'sair vivo; promete tudo e mais um pouco a quem o soltar.',
        sabe: 'o bando fala em ir embora logo; Garra é o único que os outros obedecem; foi o cobrador da ponte quem os avisou da carga dele.'
      }
    },
    segredos: {
      luz: {
        texto: 'Nas noites em que uma carroça some, uma lanterna verde acende na janela da casa do pedágio.',
        como: 'Mira conta, se alguém ganhar a confiança dela (com jeito, não com pressão).', onde: [], quem: ['mira'],
        pista: { lugar: 'vila', quem: 'mira', rot: 'Ganhar a confiança da menina Mira', re: /mira|menina|crianca|confianc/, per: 'persuasao', cd: 10,
          ok: 'Você se abaixa para ficar da altura dela e não pergunta nada por um tempo. Mira decide sozinha.\n\n“Tem uma luz”, cochicha. “Verde. Na janela do Tobin. Só nas noites ruins. Eu vi do telhado, duas vezes. Ele disse que se eu contasse o lobo vinha me buscar.”',
          falha: 'Mira aperta a vassoura contra o peito e recua até a porta da cozinha. O que quer que ela saiba, não vai dizer agora.' }
      },
      cofre: {
        texto: 'O baú de Tobin guarda muito mais ouro do que um pedágio rende, e uma lanterna de vidro verde.',
        como: 'revistando a casa do pedágio; se Tobin perceber, avisa o bando na mesma noite.', onde: ['ponte'], quem: [],
        pista: { lugar: 'ponte', rot: 'Revistar a casa do pedágio', re: /revist|casa do pedagio|bau|vasculh|procur.*casa/, per: 'investigacao', cd: 12,
          ok: 'Debaixo do catre, um baú com fecho novo demais para a casa. Dentro: moedas de ouro em quantidade que nenhum pedágio de cobre explica e, embrulhada num pano, uma lanterna de vidro verde.',
          falha: 'Você revira prateleiras e tralha sem achar nada, e quando se vira Tobin está na porta, sem sorrir. Ele não diz nada. Não precisa.',
          falhaEfeitos: [{ relogio: 1, motivo: 'Tobin desconfiou' }] }
      },
      trilha: {
        texto: 'Logo depois da ponte, sulcos de rodas saem da estrada por uma trilha escondida atrás de galhos cortados.',
        como: 'procurando rastros além da ponte, ou arrancando de Tobin.', onde: ['ponte'], quem: ['tobin'],
        pista: { lugar: 'ponte', rot: 'Procurar rastros de carroça além da ponte', re: /rastro|pegada|sulco|marca|procur|trilha/, per: 'sobrevivencia', cd: 12,
          ok: 'Cinquenta passos depois da ponte, a lama conta a história: os sulcos fundos de uma carroça carregada saem da estrada e entram na mata, atrás de uma cortina de galhos cortados e postos ali à mão.',
          falha: 'A chuva lavou a estrada. Você vê marcas de roda demais, indo para todo lado, e nenhuma que diga alguma coisa.' }
      },
      osric: {
        texto: 'O bando mantém vivo no moinho um mercador, Osric, para pedir resgate à guilda.',
        como: 'espiando o moinho sem ser visto, ou arrancando de Tobin.', onde: ['moinho'], quem: ['tobin'],
        pista: { lugar: 'moinho', rot: 'Espiar o moinho antes de agir', re: /espi|observ|olh|rond|vigi/, per: 'furtividade', cd: 12, grupo: true, exige: [['!bando_vencido', '!acordo', '!bando_partiu']],
          ok: function (S) { return 'Pela fresta de uma tábua solta: ' + (S.inimigos.bando.length) + ' homens em volta do fogo, um deles de braço enfaixado em couro, a quem os outros pedem licença para falar. E, atrás de uma porta trancada por fora, um homem gordo de roupas boas e sujas, vivo, amarrado a uma viga.'; },
          falha: 'Um galho estala debaixo do seu pé. As vozes lá dentro param por um instante e depois continuam, mais baixas. Não dá para chegar mais perto sem ser visto.' }
      }
    },
    marcas: {
      tobin_confessa: {
        quando: 'Tobin, confrontado com a luz verde ou com o baú, quebra e confessa.', texto: 'Tobin confessou: é ele quem avisa o bando com a lanterna verde.',
        lugar: ['ponte'], quem: 'tobin', exige: [['rev:luz'], ['rev:cofre']], cd: 12,
        efeitos: [{ revelar: 'trilha' }, { revelar: 'osric' }, { atitude: { quem: 'tobin', para: 'rendido' } }]
      },
      acordo: {
        quando: 'Garra aceita soltar Osric e sumir da região, levando o que já roubou, em vez de lutar.', texto: 'Garra aceitou um acordo: solta o mercador e some da região com o que já roubou.',
        lugar: ['moinho'], exige: [['!bando_vencido', '!bando_partiu']], cd: 15,
        efeitos: [{ marca: 'osric_livre' }]
      },
      osric_livre: {
        quando: 'Osric é solto, depois de o bando ser vencido ou de um acordo.', texto: 'Osric está livre.',
        lugar: ['moinho'], exige: [['bando_vencido'], ['acordo']]
      },
      suborno: {
        quando: 'os heróis aceitam ouro de Tobin ou de Garra para dizer que foram só os lobos.', texto: 'Os heróis aceitaram ouro para olhar para o outro lado.',
        lugar: ['ponte', 'moinho'], exige: [['!bando_vencido', '!tobin_confessa', '!bando_partiu']], ouro: 25
      }
    },
    acoes: {
      ponte: [
        { id: 'pressionar_tobin', rot: 'Confrontar Tobin com o que você descobriu', re: /confront|pression|acus|interrog|confess|encurral/, quem: 'tobin', exige: [['rev:luz', '!tobin_confessa'], ['rev:cofre', '!tobin_confessa']], per: 'intimidacao', cd: 12,
          ok: { txt: 'Você diz a palavra “lanterna” e o sorriso de Tobin se desmancha. Ele olha para a mata, para a vila, faz as contas de quem o enforcaria primeiro.\n\n“Eu só acendia a luz”, diz, e depois não para mais de falar.', efeitos: [{ marca: 'tobin_confessa' }] },
          falha: { txt: '“Luz verde? Baú?” Tobin ri, alto demais. “Vá contar essa história na taverna.” Mas quando você se afasta, ele entra em casa e fecha a janela com força.', efeitos: [{ relogio: 1, motivo: 'Tobin vai avisar o bando' }] } }
      ],
      mata: [
        { id: 'evitar_lobos', rot: 'Contornar os lobos sem ser visto', re: /contorn|evit|esgueir|furtiv|escond|sem ser visto/, grupoAtivo: 'lobos', per: 'furtividade', cd: 13, grupo: true,
          ok: { txt: 'Contra o vento, pisando em raiz e não em folha, você dá a volta por fora da trilha. Os lobos farejam o ar, inquietos, e não acham nada.', efeitos: [{ marca: 'lobos_evitado' }] },
          falha: { txt: 'O vento vira. Três cabeças cinzentas se erguem ao mesmo tempo.', efeitos: [{ luta: 'lobos' }] } }
      ],
      moinho: [
        { id: 'negociar_garra', rot: 'Chamar o chefe do bando para conversar', re: /negoci|convers|falar|falo|chefe|garra|acordo|parlament/, grupoAtivo: 'bando', per: 'persuasao', cd: 15,
          ok: { txt: 'O homem do braço enfaixado sai sozinho, devagar, com as mãos à vista. Escuta até o fim.\n\n“A guilda manda mais gente depois de vocês”, admite Garra. “E eu já tenho o que carregar.” Ele cospe no chão. “O gordo é seu. A gente some antes de escurecer, e ninguém aqui viu ninguém.”', efeitos: [{ marca: 'acordo' }] },
          falha: { txt: 'O homem do braço enfaixado escuta metade e ri. “Conversa é coisa de quem não trouxe gente bastante.” Ele assobia, e a porta do moinho se abre.', efeitos: [{ luta: 'bando' }] } }
      ]
    },
    grupos: {
      lobos: {
        lugar: 'mata', tipo: 'lobo', nomeUm: 'Lobo', pre: 'l', n: function (n) { return n <= 1 ? 1 : n === 2 ? 2 : 3; }, zona: 'medio',
        onde: 'na trilha da mata', fugaPara: 'ponte', re: /lobo|atac|enfrent|lut/, rotLuta: 'Enfrentar os lobos',
        presenca: function (S) { var q = S.inimigos.lobos.filter(function (e) { return e.vivo; }).length; return q > 1 ? q + ' lobos magros, de guarda na trilha' : 'um lobo magro, de guarda na trilha'; },
        nota: 'O bando os mantém famintos e presos a correntes compridas, como guarda. Não são sobrenaturais.',
        bloqueio: 'Os lobos fecham a trilha. Não dá para passar sem enfrentá-los ou contorná-los.',
        intro: 'Eles saem do mato sem pressa, costelas à mostra, arrastando correntes compridas presas a estacas. Alguém os pôs ali de guarda e os deixou com fome.',
        textoFuga: 'Você recua pela trilha até a luz da estrada. As correntes esticam e os lobos param, rosnando, no limite delas.',
        textoQueda: 'Você acorda de manhã, na beira da estrada, arrastado até ali por alguém que não ficou para explicar.',
        vitoria: 'O último lobo cai. Nas estacas, as correntes ainda balançam. Quem prende lobos numa trilha não quer visitas.',
        fato: 'Os lobos que guardavam a trilha da mata estão mortos.', nivel: 'depois da trilha da mata'
      },
      bando: {
        lugar: 'moinho', tipo: 'bandido', nomeUm: 'Salteador', pre: 'b', n: function (n) { return n <= 1 ? 1 : n === 2 ? 2 : n === 3 ? 3 : 4; }, zona: 'medio', cedeCom: 'acordo',
        chefe: { tipo: 'chefe', nome: 'Garra', hp: function (n) { return 16 + 7 * (n - 1); } },
        onde: 'no moinho afogado', fugaPara: 'mata', re: /bando|bandido|salteador|garra|atac|invad|enfrent|lut/, rotLuta: 'Atacar o bando',
        presenca: function (S) { return 'Garra e ' + (S.inimigos.bando.filter(function (e) { return e.vivo && !e.chefe; }).length) + ' salteador(es), dentro do moinho'; },
        nota: 'Garra é prático e não morre por orgulho: aceita um acordo se achar que perde mais lutando. Se Garra cair, os outros se rendem.',
        intro: 'A porta do moinho se abre de uma vez. Homens de couro e lâmina curta se espalham pela clareira, e atrás deles vem um de braço enfaixado, sem pressa nenhuma.',
        textoFuga: 'Você recua para a trilha. Ninguém o persegue na mata: eles têm um moinho cheio de saque para guardar.',
        textoQueda: 'Você acorda na trilha, sem as botas, com a cabeça latejando. Deixaram você viver para que conte aos outros que não vale a pena.',
        vitoria: 'Garra cai de joelhos e depois de lado. Os que restam olham para ele, olham para você e largam as lâminas na lama.',
        fato: 'O bando do moinho foi vencido e Garra caiu.', efeitos: [{ marca: 'osric_livre' }]
      }
    },
    relogio: {
      nome: 'o bando levanta acampamento', max: 6, passos: { longo: 2 }, paraSe: [['bando_vencido'], ['acordo']],
      quando: 'Avança quando uma noite passa, quando Tobin desconfia ou quando os heróis perdem tempo. Ao encher, o bando vai embora com o saque e leva Osric.',
      aoEncher: {
        marcas: ['bando_partiu', 'tobin_fugiu'],
        texto: 'Rio acima, por cima das árvores, uma coluna de fumaça grossa sobe e se desfaz no vento: alguém queimou o que não quis carregar. O que quer que estivesse escondido naquela mata, não está mais.',
        fato: 'O bando foi embora da região com o saque, levando o mercador. O cobrador do pedágio sumiu na mesma noite.'
      }
    },
    finais: {
      resgate: {
        rot: 'Levar Osric a Halda e contar tudo', re: /halda|contar|conto|entreg|osric|recompensa|guilda/, lugar: ['vila'], exige: [['osric_livre', 'bando_vencido', '!vila_hostil']],
        quando: 'os heróis voltam à vila com Osric, depois de vencer o bando.',
        ouro: function (S) { return kf(S, 'tobin_confessa') ? 50 : 40; },
        texto: function (S) { return 'Osric entra na Taverna do Remo Partido pelos próprios pés e a sala inteira se levanta. Halda escuta a história de uma ponta à outra sem interromper.' + (kf(S, 'tobin_confessa') ? '\n\nQuando você chega à lanterna verde, dois carroceiros saem sem dizer nada, na direção da ponte. Voltam com Tobin entre eles. Halda acrescenta dez peças às quarenta, “pelo que a guilda ia continuar perdendo”.' : '\n\n“E como eles sabiam qual carroça valia a pena?”, pergunta Halda. Ninguém tem a resposta. Ela conta quarenta peças de ouro em cima do balcão, devagar, olhando para a estrada.') + '\n\nNa manhã seguinte, a primeira carroça em um mês cruza a ponte velha.'; },
        fato: 'O bando foi vencido, Osric voltou vivo e a estrada do rio está aberta.'
      },
      acordo: {
        rot: 'Entregar Osric e contar do acordo', re: /halda|contar|conto|entreg|osric|acordo|guilda/, lugar: ['vila'], exige: [['osric_livre', 'acordo', '!vila_hostil']],
        quando: 'os heróis voltam à vila com Osric, depois de um acordo com Garra.',
        ouro: 25,
        texto: 'Osric conta a parte dele aos gritos; você conta a sua sem enfeite. Halda ouve as duas.\n\n“Então eles foram embora ricos”, diz por fim. “E vivos.” Ela conta vinte e cinco peças e empurra pelo balcão. “O homem está aqui e a estrada está livre. O resto, a guilda cobra de outro jeito, noutro dia.”\n\nMetade da sala acha que você fez bem. A outra metade não bebe com você.',
        fato: 'Osric voltou vivo por um acordo. O bando escapou com o saque.'
      },
      tarde: {
        rot: 'Contar a Halda que o bando já se foi', re: /halda|contar|conto|tarde|guilda|foram embora/, lugar: ['vila'], exige: [['tarde', '!vila_hostil', '!osric_livre']],
        quando: 'o bando já partiu e os heróis voltam de mãos vazias.',
        ouro: function (S) { return Object.keys(kitS(S).rev).length >= 2 ? 10 : 0; },
        texto: 'Halda escuta de braços cruzados. Quando você termina, ela demora a falar.\n\n“Então era gente. E já foi.” Ela olha para as carroças paradas no pátio. “A estrada abre, pelo menos. O homem que eles levaram tinha mulher em Três Pontes. Alguém vai ter que escrever a ela.”\n\nNinguém discute pagamento em voz alta.',
        fato: 'Os heróis chegaram tarde: o bando partiu com o saque e com o mercador.'
      },
      comprado: {
        rot: 'Dizer a Halda que foram só os lobos', re: /halda|contar|conto|lobos|mentir|minto/, lugar: ['vila'], exige: [['suborno', '!vila_hostil']],
        quando: 'os heróis aceitaram suborno e mentem à guilda.',
        texto: 'Você diz que foram lobos. Halda olha para a sua bolsa, que pesa mais do que pesava, e não pergunta de onde vieram as moedas.\n\n“Lobos”, repete. Ela não paga nada, e você não cobra. Na semana seguinte, outra carroça some depois da ponte.',
        fato: 'Os heróis mentiram à guilda em troca de ouro. As carroças continuam sumindo.'
      },
      foragido: {
        rot: 'Deixar Vau do Corvo para trás', re: /partir|parto|ir embora|vou embora|deixar|deixo|fugir|fujo|estrada/, lugar: ['vila', 'ponte'], exige: [['vila_hostil']],
        quando: 'os heróis atacaram um inocente e não têm mais o que fazer ali.',
        texto: 'Não há mais nada para você em Vau do Corvo além de portas trancadas e de um nome que os carroceiros vão levar estrada afora. Você toma o caminho do rio antes que alguém resolva cobrar o que foi feito.\n\nAs carroças continuam sumindo depois da ponte velha. Ninguém mais vem perguntar por quê.',
        fato: 'Os heróis deixaram Vau do Corvo como foragidos. O mistério da ponte ficou sem resposta.'
      }
    }
  };
  KIT_PONTE.marcas.lobos_evitado = { quando: 'os heróis passam pelos lobos sem luta.', texto: 'Os heróis passaram pelos lobos sem serem vistos.', lugar: ['mata'], exige: [['!lobos_vencido']], cd: 13 };
  AVENTURAS.ponte = aventuraDeKit(KIT_PONTE);
