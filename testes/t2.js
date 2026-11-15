'use strict';
const C = require('../dist/motor.js');
let falhas = 0;
function ok(c, m) { if (!c) { falhas++; if (falhas < 40) console.log('FALHA: ' + m); } }
function rnd(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = Math.imul(s ^ (s >>> 15), s | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const K = Object.keys, pick = (r, l) => l[Math.floor(r() * l.length)];
function embaralhar(r, l) { l = l.slice(); for (let i = l.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [l[i], l[j]] = [l[j], l[i]]; } return l; }
function fichaAleatoria(r, n) {
  const classe = pick(r, K(C.CLASSES)), cl = C.CLASSES[classe], ant = pick(r, K(C.ANTECEDENTES));
  const f = { nome: 'H' + n, classe, antecedente: ant, especie: pick(r, K(C.ESPECIES)), kit: pick(r, K(cl.kits)), cor: pick(r, C.CORES) };
  if (r() < 0.6) { const v = embaralhar(r, C.CONJUNTO); f.atr = {}; C.ATR_ORDEM.forEach((a, i) => f.atr[a] = v[i]); }
  if (r() < 0.5) f.bonus = r() < 0.3 ? { modo: '1+1+1' } : { modo: '2+1', a: pick(r, C.ANTECEDENTES[ant].atr), b: pick(r, C.ANTECEDENTES[ant].atr) };
  f.pericias = embaralhar(r, cl.listaPericias).slice(0, 4); f.periciaExtra = pick(r, C.PERICIAS_ORDEM); f.dobro = embaralhar(r, C.PERICIAS_ORDEM).slice(0, 3);
  if (cl.conj) { f.truques = embaralhar(r, cl.listaTruques); f.magias = embaralhar(r, cl.listaMagias).slice(0, 4); }
  if (r() < 0.1) return { nome: '<b>x</b>', classe: 'nada', atr: { for: 99 }, magias: 'x', pericias: 5 };
  return f;
}
function invariantes(S, ctx) {
  ok(C.validar(S), ctx + ' estado inválido');
  ok(Number.isInteger(S.ouro) && S.ouro >= 0 && Number.isInteger(S.pocoes) && S.pocoes >= 0, ctx + ' ouro/poções');
  const ids = new Set();
  S.herois.forEach(h => {
    ids.add(h.id);
    ok(Number.isInteger(h.pv) && h.pv >= 0 && h.pv <= h.pvMax, ctx + ' pv ' + h.pv + '/' + h.pvMax);
    ok(h.espacos >= 0 && h.espacos <= h.espacosMax && h.dv >= 0 && h.dv <= h.dvTotal && h.folego >= 0 && h.surto >= 0 && h.canalizar >= 0 && h.implacavel >= 0, ctx + ' recursos');
    ok(Number.isFinite(C.ca(h)) && C.ca(h) >= 8 && C.ca(h) <= 23, ctx + ' CA ' + C.ca(h));
    ok(!(h.morto && h.pv > 0), ctx + ' morto com PV');
    if (!S.combate && !S.fim) ok(h.morto || h.pv > 0, ctx + ' herói caído fora de combate');
    C.PERICIAS_ORDEM.forEach(p => ok(Number.isFinite(C.bonusPericia(h, p)), ctx + ' bônus'));
  });
  ok(ids.size === S.herois.length, ctx + ' ids repetidos');
  if (!S.fim) {
    ok(S.herois.some(h => !h.morto && h.pv > 0), ctx + ' ninguém de pé e sem fim');
    const quem = C.quemAge(S, null);
    ok(!!quem, ctx + ' sem herói para agir');
    const ops = C.opcoes(S, quem);
    ok(ops.length > 0, ctx + ' sem opções');
    ok(new Set(ops.map(o => o.cmd)).size === ops.length, ctx + ' opções duplicadas ' + ops.map(o => o.cmd).join(','));
    if (S.combate) { ok(C.vez(S) === quem, ctx + ' vez inconsistente'); ok(S.inimigos[S.combate.grupo].some(e => e.vivo), ctx + ' combate sem inimigos'); }
  }
  for (let i = Math.max(0, S.log.length - 40); i < S.log.length; i++) { const x = S.log[i].x; ok(typeof x === 'string' && x.length > 0 && !/undefined|NaN|\[object|null/.test(x), ctx + ' texto ruim: ' + x); }
}

/* 1. clicador aleatório com grupos de 1 a 4 */
(function fuzz() {
  let passos = 0, vit = 0, mortes = 0;
  const N = +process.env.FUZZ || 200;
  for (let n = 0; n < N; n++) {
    const r = rnd(n * 7 + 3), tam = 1 + (n % 4), av = n % 5 === 0 ? 'treino' : 'sino';
    let S = C.novo({ av, herois: Array.from({ length: tam }, (_, i) => fichaAleatoria(r, i)), semente: 'f' + n, dificuldade: n % 3 ? 'tranquilo' : 'classico' });
    ok(S.herois.length === tam, 'tamanho do grupo');
    for (let i = 0; i < 500; i++) {
      const ctx = '[fuzz ' + n + ' passo ' + i + ']';
      if (S.fim) { if (S.fim.tipo === 'vitoria') { vit++; break; } mortes++; const N2 = C.voltarPontoSeguro(S); ok(N2 && !N2.fim && !N2.combate, ctx + ' ponto seguro'); if (!N2) break; S = N2; continue; }
      const hid = r() < 0.7 ? C.quemAge(S, null) : pick(r, S.herois).id;
      const ops = C.opcoes(S, hid);
      if (!ops.length) { ok(false, ctx + ' sem opções para ' + hid); break; }
      let o = pick(r, ops);
      if (r() < 0.25) { const prefer = ops.filter(x => /^#ir:|atacar|#c:atk|#c:mag|contar|abrir|janela|lutar|concluir/.test(x.cmd)); if (prefer.length) o = pick(r, prefer); }
      try { C.agir(S, o.cmd, hid); } catch (e) { ok(false, ctx + ' exceção em ' + o.cmd + ': ' + e.stack); break; }
      invariantes(S, ctx + ' ' + o.cmd);
      passos++;
      if (i % 41 === 7) { const T = C.importar(C.exportar(S)); ok(T && JSON.stringify(T) === JSON.stringify(S), ctx + ' exportar/importar'); S = T; ok(C.validar(C.compactar(S)), ctx + ' compactar'); ok(JSON.stringify(C.compactar(S)).length < 200000, ctx + ' mesa grande demais: ' + JSON.stringify(C.compactar(S)).length); }
      if (i % 53 === 11 && !S.fim) { const e = C.entrarHeroi(S, fichaAleatoria(r, 9)); ok(e === null || typeof e === 'string', ctx + ' entrarHeroi'); invariantes(S, ctx + ' entrarHeroi'); }
      if (i % 97 === 50 && !S.fim) { C.sairHeroi(S, pick(r, S.herois).id); if (!S.fim) invariantes(S, ctx + ' sairHeroi'); }
    }
  }
  console.log('fuzz: ' + passos + ' ações, ' + vit + ' vitórias, ' + mortes + ' derrotas totais');
})();

/* 2. jogador sensato */
function escolher(S, modoFinal) {
  const hid = C.quemAge(S, null), ops = C.opcoes(S, hid), h = S.herois.find(x => x.id === hid);
  const tem = p => ops.find(o => o.cmd === p), comeca = p => ops.filter(o => o.cmd.startsWith(p));
  if (S.combate) {
    const ini = S.inimigos[S.combate.grupo].filter(e => e.vivo);
    const caido = S.herois.find(x => !x.morto && x.pv <= 0);
    if (caido) { const c = tem('#c:mag:palavra:' + caido.id) || tem('#c:pocao:' + caido.id) || tem('#c:mag:curar:' + caido.id) || tem('#c:mag:poupar:' + caido.id); if (c) return c.cmd; }
    if (h.pv <= h.pvMax * 0.5) { const c = tem('#c:folego') || tem('#c:mag:palavra:' + h.id) || tem('#c:pocao:' + h.id) || (h.pv <= h.pvMax * 0.35 && (tem('#c:mag:curar:' + h.id) || tem('#c:centelha:' + h.id))); if (c) return c.cmd; }
    if (tem('#c:surto')) return '#c:surto';
    const ivo = ini.find(e => e.id === 'ivo');
    if (S.combate.grupo === 'camara' && h.classe !== 'mago' && tem('#c:mov:ivo')) return '#c:mov:ivo';
    if (S.combate.grupo === 'camara' && modoFinal === 'abafar' && tem('#c:abafar') && ivo && ivo.zona !== 'longe') return '#c:abafar';
    if (tem('#c:expulsar') && S.combate.grupo === 'cripta' && ini.every(e => e.expulso <= 0 && e.zona !== 'longe')) return '#c:expulsar';
    if (tem('#c:mag:bencao') && S.herois.length > 1) return '#c:mag:bencao';
    if (tem('#c:mag:maos')) return '#c:mag:maos';
    if (tem('#c:mag:onda')) return '#c:mag:onda';
    const pri = e => (e.id === 'ivo' ? -100 : 0) + (e.zona === 'perto' ? -10 : 0) + e.hp;
    for (const e of ini.slice().sort((a, b) => pri(a) - pri(b))) {
      const ms = comeca('#c:mag:').filter(o => o.cmd.endsWith(':' + e.id));
      const slot = ms.find(o => /misseis|raioguia|orbe|infligir/.test(o.cmd)), truque = ms.find(o => /fogo|chama|gelo|choque/.test(o.cmd));
      const atks = comeca('#c:atk:').filter(o => o.cmd.endsWith(':' + e.id));
      if (slot && e.hp > 6) return slot.cmd;
      if (h.classe === 'mago' && truque) return truque.cmd;
      if (atks.length) return atks[0].cmd;
      if (truque) return truque.cmd;
    }
    const mov = comeca('#c:mov:');
    if (mov.length && h.classe !== 'mago') return (mov.find(o => o.cmd.endsWith(':ivo')) || mov[0]).cmd;
    if (tem('#c:esconder_b')) return '#c:esconder_b';
    return '#c:fim';
  }
  const pior = S.herois.filter(x => !x.morto).sort((a, b) => a.pv / a.pvMax - b.pv / b.pvMax)[0];
  if (pior.pv < pior.pvMax * 0.6) {
    const c = tem('#p:curto') || tem('#p:pocao:' + pior.id) || tem('#p:mag:curar:' + pior.id);
    if (c) return c.cmd;
    if (pior.pv < pior.pvMax * 0.5 && !S.f.ivo && S.av === 'sino') { const volta = { trilha: '#ir:estalagem', capela: '#ir:trilha', cripta: '#ir:capela', camara: '#ir:cripta' }[S.cena]; if (volta && tem(volta)) return volta; }
    if (tem('#a:longo')) return '#a:longo';
    if (tem('#a:descansar_banco')) return '#a:descansar_banco';
  }
  if (tem('#p:mag:armadura')) return '#p:mag:armadura';
  if (S.av === 'treino') { for (const c of ['#a:falar_dorval', '#a:saltar_fosso', '#a:trave', '#a:portao']) if (tem(c) && !S.vereditos[c.slice(3)]) return c; return tem('#a:lutar_bonecos') ? '#a:lutar_bonecos' : '#a:concluir'; }
  const ordem = ['#a:contar_marga', '#a:falar_marga', '#a:pedir_adiantamento', '#a:falar_bento', '#a:pagar_bebida', '#a:atacar_goblins', '#a:revistar_goblins', '#a:vasculhar_sacristia', '#a:ler_diario', '#a:examinar_marcas', '#a:abrir_chave', '#a:arrombar', '#a:janela', '#a:atacar_mortos', '#a:revistar_nichos', '#a:quebrar_sino'];
  if (S.cena === 'camara' && !S.f.ivo) return modoFinal === 'conversa' && !Object.keys(S.tentou).some(k => k.startsWith('convencer_ivo')) ? '#a:convencer_ivo' : '#a:atacar_ivo';
  for (const c of ordem) if (tem(c) && (/atacar_/.test(c) || !S.vereditos[c.slice(3)]) && !(c === '#a:arrombar' && !h.ferramentas)) return c;
  const rota = S.f.ivo ? { camara: '#ir:estalagem', cripta: '#ir:capela', capela: '#ir:trilha', trilha: '#ir:estalagem' }[S.cena] : { estalagem: '#ir:trilha', trilha: '#ir:capela', capela: '#ir:cripta', cripta: '#ir:camara' }[S.cena];
  if (rota && tem(rota)) return rota;
  return ops[0].cmd;
}
const GRUPOS = { solo_guerreiro: ['guerreiro'], solo_ladino: ['ladino'], solo_clerigo: ['clerigo'], solo_mago: ['mago'], dupla: ['guerreiro', 'mago'], trio: ['guerreiro', 'clerigo', 'ladino'], quarteto: ['guerreiro', 'clerigo', 'ladino', 'mago'] };
(function sensato() {
  const N = +process.env.BOT || 60, dif = process.env.DIF || 'tranquilo';
  for (const av of ['treino', 'sino']) for (const modoFinal of av === 'sino' ? ['luta', 'abafar', 'conversa'] : ['luta']) for (const nome of K(GRUPOS)) {
    let vit = 0, semQueda = 0, derrotas = 0, mortos = 0, passos = 0, travou = 0;
    for (let n = 0; n < N; n++) {
      const r = rnd(n + 99);
      let S = C.novo({ av, herois: GRUPOS[nome].map((c, i) => ({ nome: c[0].toUpperCase() + i, classe: c, especie: pick(r, K(C.ESPECIES)), antecedente: pick(r, K(C.ANTECEDENTES)), kit: pick(r, K(C.CLASSES[c].kits)) })), semente: av + modoFinal + nome + n, dificuldade: dif });
      let d = 0, i = 0;
      for (; i < 2500; i++) {
        if (S.fim) { if (S.fim.tipo === 'vitoria') break; d++; S = C.voltarPontoSeguro(S); continue; }
        const cmd = escolher(S, modoFinal);
        C.agir(S, cmd, null);
        if (i % 7 === 0) invariantes(S, '[sensato ' + nome + ' ' + n + ' ' + cmd + ']');
      }
      if (S.fim && S.fim.tipo === 'vitoria') { vit++; if (!d && !S.fatos.some(f => /derrotado|Você caiu/.test(f.x))) semQueda++; } else travou++;
      derrotas += d; passos += i; mortos += S.herois.filter(h => h.morto).length;
    }
    ok(travou === 0, 'sensato ' + av + '/' + modoFinal + '/' + nome + ': ' + travou + ' não fecharam');
    console.log((av + ' ' + modoFinal).padEnd(15) + nome.padEnd(16) + 'vitórias ' + vit + '/' + N + ' · sem cair ' + Math.round(100 * semQueda / N) + '% · derrotas totais/partida ' + (derrotas / N).toFixed(2) + ' · heróis mortos ' + mortos + ' · ações ' + Math.round(passos / N));
  }
})();

/* 3. texto livre, perguntas, IA e determinismo */
(function texto() {
  const mk = () => C.novo({ av: 'sino', herois: [{ nome: 'Ana', classe: 'ladino', antecedente: 'criminoso' }], semente: 'texto' });
  const roteiro = ['o que é o sino?', 'falo com a dona marga', 'posso pedir um adiantamento?', 'peço um adiantamento', 'converso com o velho bento', 'pago uma cerveja para ele', 'observo a sala', 'quero voar até a capela', '/ir trilha'];
  const A = mk(), B = mk();
  roteiro.forEach(t => { C.agir(A, t, 'h1'); C.agir(B, t, 'h1'); });
  ok(JSON.stringify(A) === JSON.stringify(B), 'mesma semente, resultados diferentes');
  ok(A.f.gancho && A.f.falouBento && A.f.sabeTrilha && A.cena === 'trilha', 'roteiro em texto livre: ' + JSON.stringify(A.f) + ' ' + A.cena);
  ok(A.log.some(l => /impossível/.test(l.x)), 'voar deveria ser impossível');
  const S = C.novo({ av: 'sino', herois: [{ nome: 'Ana', classe: 'mago' }, { nome: 'Beto', classe: 'guerreiro' }], semente: 'perg' });
  const foto = s => JSON.stringify(Object.assign({}, s, { log: null, nLog: 0, ckpt: null }));
  let antes = foto(S);
  ['posso falar com a marga?', 'e se eu observar a sala?', 'quem é ivo?', 'o que tem na trilha?', 'onde fica a capela?', 'como eu jogo?', 'xyzzy?'].forEach(q => C.agir(S, q, 'h2'));
  ok(foto(S) === antes && S.nRol === 0, 'pergunta alterou a campanha ou rolou dado');
  ok(C.agir(S, '/ficha', 'h1').abrir === 'ficha' && C.agir(S, '/diario').abrir === 'diario', 'comandos de painel');
  ['/resumo', '/sair', '/descansar', '/ir', '/ir lua', '/bobagem', '   ', '<script>alert(1)</script>', 'ç'.repeat(1000)].forEach(t => { C.agir(S, t, 'h1'); invariantes(S, '[cmd]'); });
  // IA: o roteiro não entende -> devolve {ia:true} sem mexer em nada
  antes = JSON.stringify(S);
  const r1 = C.agir(S, 'assobio uma canção de ninar bem baixinho', 'h1', { ia: true });
  ok(r1.ia === true && JSON.stringify(S) === antes, 'pedido de IA não deveria mudar o estado');
  const prompt = C.promptIA(S, 'assobio uma canção', 'h1');
  ok(/AÇÕES PREVISTAS/.test(prompt) && /falar_marga/.test(prompt) && prompt.length < 9000 && !/Lívia/.test(prompt.replace(/Lívia\. Trate/, '')), 'prompt da IA: tamanho ' + prompt.length);
  const lixo = [null, 'x', 42, [], {}, { tipo: 'acao', id: 'nao_existe' }, { tipo: 'acao', id: 'ir:lua' }, { tipo: 'pergunta', resposta: '' }, { tipo: 'improviso', veredito: 'teste', pericia: 'culinaria', cd: 10, sucesso: 'a', falha: 'b' }, { tipo: 'improviso', veredito: 'teste', pericia: 'percepcao', cd: 99, sucesso: 'a', falha: 'b' }, { tipo: 'improviso', veredito: 'teste', pericia: 'percepcao', cd: 10, sucesso: 'a' }, { tipo: 'improviso', veredito: 'decara' }, { tipo: 'outro' }];
  lixo.forEach(x => { const a = JSON.stringify(S); ok(C.aplicarIA(S, 'assobio', 'h1', x) === false && JSON.stringify(S) === a, 'resposta inválida da IA deveria ser recusada: ' + JSON.stringify(x)); });
  ok(C.aplicarIA(S, 'quero falar com a moça do balcão', 'h1', { tipo: 'acao', id: 'falar_marga' }) && S.f.gancho, 'IA -> ação prevista');
  const nr = S.nRol;
  ok(C.aplicarIA(S, 'o que a Marga acha do Bento?', 'h1', { tipo: 'pergunta', resposta: 'Ela dá de ombros.' }) && S.nRol === nr, 'IA -> pergunta');
  ok(C.aplicarIA(S, 'assobio uma canção', 'h1', { tipo: 'improviso', veredito: 'teste', pericia: 'atuacao', cd: 10, sucesso: 'A sala relaxa um pouco.', falha: 'Ninguém repara.', fato: 'Ana assobiou na estalagem.' }) && S.nRol === nr + 1, 'IA -> improviso com teste');
  const f0 = S.fatos.length;
  ok(C.aplicarIA(S, 'assobio uma canção', 'h1', { tipo: 'improviso', veredito: 'teste', pericia: 'atuacao', cd: 10, sucesso: 'x', falha: 'y' }) && S.nRol === nr + 1 && S.fatos.length === f0, 'improviso repetido não rola de novo');
  ok(C.aplicarIA(S, 'derrubo a estalagem com um soco', 'h2', { tipo: 'improviso', veredito: 'impossivel', motivo: 'As paredes são de pedra.' }), 'IA -> impossível');
  ok(C.aplicarIA(S, 'vou para a trilha', 'h2', { tipo: 'acao', id: 'ir:trilha' }) && S.cena === 'trilha' || S.combate, 'IA -> saída');
  C.semIA(S, 'faço qualquer coisa', 'h1'); invariantes(S, '[semIA]');
  // combate por texto com grupo
  let T = null;
  for (let n = 0; n < 300 && !T; n++) { const X = C.novo({ av: 'sino', herois: [{ nome: 'Gui', classe: 'guerreiro' }, { nome: 'Lia', classe: 'clerigo', kit: 'taumaturgo' }], semente: 'cb' + n }); C.agir(X, 'subo a trilha', 'h1'); if (X.combate) T = X; }
  ok(!!T, 'não achei emboscada');
  if (T) {
    const frases = ['quantos são?', 'ataco o goblin 1', 'avanço sobre o goblin 2', 'ataco goblin 2', 'arremesso a azagaia no goblin 3', 'esquivo', 'recuo', 'bebo a poção', 'curar ferimentos em gui', 'chama sagrada no goblin 1', 'retomar o fôlego', 'ataco', 'passo', 'danço', 'me escondo', 'desengajo', 'vou para a linha de frente', 'bênção'];
    let g = 0;
    while (T.combate && g < 400) { C.agir(T, frases[g % frases.length], null); invariantes(T, '[texto combate ' + g + ']'); g++; if (T.fim) break; }
    ok(!T.combate || T.fim, 'combate por texto não terminou');
  }
  ok(C.importar('lixo') === null && C.importar('{}') === null && C.importar('{"v":2}') === null, 'importação inválida');
  // fichas: tudo o que vier errado é corrigido
  const h = C.criarPC({ nome: '  <i>Zé</i>  '.repeat(9), classe: 'mago', especie: 'anao', atr: { for: 15, des: 15, con: 15, int: 15, sab: 15, car: 15 }, magias: ['curar', 'sono', 'sono'], truques: ['chama', 'gelo'], kit: 'escudo' });
  ok(h.nome.length <= 24 && h.classe === 'mago' && h.magias.length === 6 && h.magias.includes('sono') && h.magias.includes('gelo') && !h.magias.includes('curar') && h.kit === 'cajado', 'ficha corrigida: ' + JSON.stringify(h.magias) + h.kit);
  ok(C.ATR_ORDEM.reduce((s, a) => s + h.atr[a], 0) === 72 + 3, 'atributos do conjunto padrão + bônus: ' + JSON.stringify(h.atr));
  K(C.CLASSES).forEach(c => K(C.CLASSES[c].kits).forEach(k => K(C.ESPECIES).forEach(e => K(C.ANTECEDENTES).forEach(a => {
    const f = C.normalizarFicha({ classe: c, kit: k, especie: e, antecedente: a }), x = C.criarPC(f), y = C.criarPC(C.normalizarFicha(f));
    ok(JSON.stringify(x) === JSON.stringify(y), 'normalizarFicha não é estável para ' + [c, k, e, a]);
    ok(new Set(x.pericias).size === x.pericias.length && x.pericias.length === 2 + C.CLASSES[c].nPericias + (e === 'humano' ? 1 : 0) + (e === 'elfo' && !x.pericias.slice(0, 2).includes('percepcao') ? 1 : 0), 'perícias de ' + [c, k, e, a] + ': ' + x.pericias);
  }))));
})();
console.log(falhas ? '\n' + falhas + ' FALHA(S)' : '\nTudo certo: nenhuma falha.');
process.exit(falhas ? 1 : 0);
