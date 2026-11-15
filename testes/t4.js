// Campanha como kit de mestre: A Ponte do Corvo.
require('../dist/motor.js'); const C = globalThis.Cronica; const assert = require('assert');
const CLS = ['guerreiro', 'clerigo', 'ladino', 'mago'];
function nova(sem, n, dif) { return C.novo({ av: 'ponte', semente: sem, dificuldade: dif || 'tranquilo', herois: Array.from({ length: n || 1 }, (_, i) => C.criarPC({ nome: 'H' + i, classe: CLS[i], especie: 'humano', antecedente: 'soldado' })) }); }
const txt = (S, n) => S.log.slice(n || 0).map(l => l.x).join('\n');
const quem = S => C.infoCena(S).vez || (S.herois.find(x => !x.morto) || S.herois[0]).id;
const ok = S => assert(C.validar(JSON.parse(JSON.stringify(C.compactar(S, 150, 80)))), 'estado inválido');
function lutar(S) { let g = 0; while (S.combate && !S.fim && g++ < 400) { const h = quem(S), ops = C.opcoes(S, h); const a = ops.find(o => / em /.test(o.rot)) || ops.find(o => /Encerrar/.test(o.rot)) || ops[0]; C.agir(S, a.cmd, h); } }
const imp = (o) => Object.assign({ tipo: 'improviso', veredito: 'decara', sucesso: 'Acontece.', falha: 'Não acontece.', motivo: '', fato: '' }, o);
const teste = (cd, ef, o) => imp(Object.assign({ veredito: 'teste', pericia: 'persuasao', cd: cd, efeitos: ef }, o));
// força um teste a dar certo: tenta em campanhas com sementes diferentes até passar
function comSucesso(prep, r, checa, max) { for (let i = 0; i < (max || 60); i++) { const S = prep(i); const n = S.log.length; assert(C.aplicarIA(S, 'tento ' + i, quem(S), r, 'agir')); if (/→ sucesso/.test(txt(S, n))) return checa(S); } assert(false, 'nenhum sucesso em ' + (max || 60) + ' tentativas'); }

// ---------- 1. IA desonesta: nada sem base no kit entra ----------
let S = nova('x1'), h = quem(S), antes = JSON.stringify(S.k || {});
const ruins = [
  imp({ efeitos: [{ revelar: 'osric' }] }),                       // segredo de outro lugar
  imp({ efeitos: [{ revelar: 'luz' }] }),                         // segredo daqui, mas sem teste nem confiança
  imp({ efeitos: [{ revelar: 'inventado' }] }),
  imp({ efeitos: [{ marca: 'acordo' }, { marca: 'osric_livre' }, { marca: 'tobin_confessa' }, { marca: 'suborno' }] }),
  imp({ efeitos: [{ final: 'resgate' }, { final: 'acordo' }, { final: 'tarde' }, { final: 'x' }] }),
  imp({ efeitos: [{ relogio: 5 }, { relogio: -1 }, { relogio: 'a' }] }),
  imp({ efeitos: [{ atitude: { quem: 'tobin', para: 'rendido' } }, { atitude: { quem: 'halda', para: 'amigavel' } }, { atitude: { quem: 'halda', para: 'escrava' } }] }),
  imp({ efeitos: [{ ouro: 500 }, { item: 'espada +3' }, 'x', null, 7, { luta: 'bando' }] }),
  imp({ efeitos: 'tudo' }), imp({ efeitos: { revelar: 'luz' } })
];
ruins.forEach((r, i) => { const o = S.ouro; assert(C.aplicarIA(S, 'tento algo ' + i, h, r, 'agir'), 'improviso ' + i + ' deveria narrar'); assert.strictEqual(S.ouro, o); assert(!S.fim && !S.combate, 'ruim ' + i + ' mudou o jogo'); });
assert.strictEqual(JSON.stringify(S.k.rev), '{}'); assert.strictEqual(JSON.stringify(S.k.f), '{}'); assert.strictEqual(S.k.rel, 0); assert.strictEqual(JSON.stringify(S.k.at), '{}');
assert(/não aceitou/.test(txt(S)), 'recusa não foi registrada');
assert(!C.aplicarIA(S, 'luto', h, { tipo: 'luta', alvos: ['bando'] }, 'agir') && !S.combate, 'luta contra grupo de outro lugar');
assert(!C.aplicarIA(S, 'bato na menina', h, { tipo: 'luta', alvos: ['mira'] }, 'agir') && !S.combate, 'criança atacável');
// relógio: um passo por ação, no máximo
C.aplicarIA(S, 'perco tempo', h, imp({ efeitos: [{ relogio: 1 }, { relogio: 1 }] }), 'agir'); assert.strictEqual(S.k.rel, 1);
ok(S);

// ---------- 2. IA honesta: efeitos com base entram ----------
comSucesso(i => nova('y' + i), teste(10, [{ revelar: 'luz' }]), S2 => { assert(S2.k.rev.luz && /Descoberto: Nas noites/.test(txt(S2))); });
// falha: só relógio ou hostilidade
(function () { for (let i = 0; i < 60; i++) { const S2 = nova('z' + i); C.aplicarIA(S2, 'forço a menina a falar', quem(S2), teste(25, [{ revelar: 'luz' }], { efeitos_falha: [{ revelar: 'luz' }, { relogio: 1 }, { atitude: { quem: 'halda', para: 'amigavel' } }] }), 'agir'); if (/→ falha/.test(txt(S2))) { assert(!S2.k.rev.luz && S2.k.rel === 1 && !S2.k.at.halda); return; } } assert(false); })();
// confissão exige pista e teste difícil o bastante
function naPonte(i, comLuz) { const S2 = nova('p' + i); if (comLuz) { S2.k = S2.k || { rev: {}, rel: 0, at: {}, f: {} }; S2.k.rev.luz = true; } C.agir(S2, '#ir:ponte', quem(S2)); return S2; }
S = naPonte(0, false); C.aplicarIA(S, 'aperto o tobin', quem(S), teste(5, [{ marca: 'tobin_confessa' }]), 'agir'); assert(!S.k.f.tobin_confessa, 'confissão sem pista');
(function () { for (let i = 0; i < 40; i++) { const S2 = naPonte(i, true); C.aplicarIA(S2, 'aperto o tobin de leve', quem(S2), teste(5, [{ marca: 'tobin_confessa' }]), 'agir'); assert(!S2.k.f.tobin_confessa, 'confissão com teste fácil demais'); } })();
comSucesso(i => naPonte(i, true), teste(12, [{ marca: 'tobin_confessa' }], { pericia: 'intimidacao' }), S2 => { assert(S2.k.f.tobin_confessa && S2.k.rev.trilha && S2.k.rev.osric && S2.k.at.tobin === 'rendido'); assert(C.opcoes(S2, quem(S2)).some(o => /trilha escondida/.test(o.rot)), 'trilha não abriu'); ok(S2); });
// atacar Tobin (culpado) não vira a vila; atacar Halda (inocente) vira
S = naPonte(1, false); assert(C.aplicarIA(S, 'ataco o cobrador', quem(S), { tipo: 'luta', alvos: ['tobin'], narracao: 'Aço.' }, 'agir') && S.combate); lutar(S); assert(!S.k.f.vila_hostil && S.f.mortos.tobin && !/Tobin/.test(C.infoCena(S).presentes.join()));
S = nova('h1'); C.aplicarIA(S, 'ataco a taverneira', quem(S), { tipo: 'luta', alvos: ['halda'] }, 'agir'); lutar(S); assert(S.k.f.vila_hostil);
assert(C.opcoes(S, quem(S)).some(o => /Deixar Vau do Corvo/.test(o.rot)) && !C.opcoes(S, quem(S)).some(o => /Mira|Passar a noite/.test(o.rot)), C.opcoes(S, quem(S)).map(o => o.rot).join());
C.agir(S, C.opcoes(S, quem(S)).find(o => /Deixar/.test(o.rot)).cmd, quem(S)); assert(S.fim && S.fim.final === 'foragido'); ok(S);
// o pedido ao mestre só mostra segredos do lugar
S = nova('q1'); let pr = C.promptIA(S, 'oi', quem(S), 'agir'); assert(/- luz:/.test(pr) && !/- cofre:/.test(pr) && !/- osric:/.test(pr) && /"efeitos"/.test(pr));
// relógio enche com noites: o bando parte e o final amargo aparece
S = nova('r1'); for (let i = 0; i < 3; i++) C.agir(S, '#a:longo', quem(S)); assert(S.k.f.tarde && S.k.f.bando_partiu && /coluna de fumaça/.test(txt(S)));
assert(C.opcoes(S, quem(S)).some(o => /já se foi/.test(o.rot))); C.agir(S, C.opcoes(S, quem(S)).find(o => /já se foi/.test(o.rot)).cmd, quem(S)); assert(S.fim.final === 'tarde'); ok(S);

// ---------- 3. sem IA: um bot joga até o fim, em grupos de 1 a 4, nos dois modos ----------
const fins = {}; let total = 0, presos = 0;
for (const dif of ['tranquilo', 'classico']) for (let n = 1; n <= 4; n++) for (let i = 0; i < 25; i++) {
  S = nova('b' + dif + n + '-' + i, n, dif); total++;
  let g = 0, rnd = i * 31 + n * 7 + 3, voltas = 0;
  while (!S.fim && g++ < 900) {
    const hid = quem(S), ops = C.opcoes(S, hid); assert(ops.length, 'sem opções em ' + S.cena + ' · ' + JSON.stringify(S.k));
    rnd = (rnd * 1103515245 + 12345) & 0x7fffffff;
    const pref = ops.filter(o => /Falar com|confiança|rastros|Revistar|Confrontar|trilha escondida|Enfrentar| em |sulcos|Espiar|Atacar o bando|Levar Osric|Entregar Osric|já se foi|Voltar à vila|Voltar à ponte|Voltar pela trilha|Ir até a ponte/.test(o.rot));
    const r1 = Math.floor(rnd / 65536), r2 = Math.floor(rnd / 256); const a = pref.length && r1 % 10 < 8 ? pref[r2 % pref.length] : ops[r2 % ops.length];
    C.agir(S, a.cmd, hid);
    if (S.fim && S.fim.tipo !== 'vitoria' && S.ckpt && voltas++ < 6) { const N = C.voltarPontoSeguro(S); if (N) S = N; }
  }
  ok(S);
  if (S.fim) fins[S.fim.final || S.fim.tipo] = (fins[S.fim.final || S.fim.tipo] || 0) + 1; else presos++;
}
console.log('finais sem IA em', total, 'partidas:', JSON.stringify(fins), '· sem terminar:', presos);
assert(presos <= total * 0.05, 'partidas demais sem fim'); assert(fins.resgate > 0 && fins.tarde > 0, 'faltou variedade de finais');
console.log('t4: tudo certo');
