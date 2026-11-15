// Luta contra moradores e modos de fala.
require('../dist/motor.js'); const C = globalThis.Cronica; const assert = require('assert');
function nova(sem, n, dif) { const cls = ['guerreiro','clerigo','ladino','mago']; return C.novo({ av: 'sino', semente: sem, dificuldade: dif || 'tranquilo', herois: Array.from({length:n||1}, (_, i) => C.criarPC({ nome: 'H' + i, classe: cls[i], especie: 'humano', antecedente: 'soldado' })) }); }
function txt(S, n) { return S.log.slice(n).map(l => l.x).join('\n'); }
function lutar(S, re) { let g = 0; while (S.combate && !S.fim && g++ < 300) { const t = C.vez ? null : null; const hid = (C.infoCena(S).vez) || S.herois[0].id; const ops = C.opcoes(S, hid); const a = ops.find(o => re.test(o.rot)) || ops.find(o => / em /.test(o.rot)) || ops.find(o => /Encerrar/.test(o.rot)) || ops[0]; C.agir(S, a.cmd, hid); } }
let S, h, n;
// 1. sem IA: frase de ataque com o nome começa a luta; frase de conversa não
S = nova('a1'); h = S.herois[0].id; n = S.log.length;
C.agir(S, 'falo com dona marga', h); assert(!S.combate && /serve uma caneca/.test(txt(S, n)), 'conversa virou luta');
n = S.log.length; C.agir(S, 'quero atacar Dona Marga com minha espada', h); assert(S.combate && S.combate.grupo === '_briga', 'ataque não começou luta'); assert(S.ckpt, 'sem ponto seguro antes da briga');
lutar(S, / em Dona Marga/); assert(!S.combate && S.f.mortos.marga && S.f.malvisto);
assert(!/Dona Marga/.test(C.infoCena(S).presentes.join()), 'morta ainda presente');
assert(!C.opcoes(S, h).some(o => /Marga|Bento|Passar a noite/.test(o.rot)), 'ações de morador sobraram: ' + C.opcoes(S, h).map(o => o.rot));
assert(C.infoCena(S).seguro === false);
// pergunta sobre atacar não começa luta
S = nova('a2'); h = S.herois[0].id; C.agir(S, 'posso atacar a marga?', h); assert(!S.combate, 'pergunta começou luta');
// modo falar nunca começa luta; modo perguntar nunca muda estado
S = nova('a3'); h = S.herois[0].id; C.agir(S, 'eu vou te matar, marga', h, { modo: 'falar' }); assert(!S.combate, 'fala começou luta');
n = S.log.length; const antes = JSON.stringify([S.f, S.ouro, S.cena]); C.agir(S, 'falar com dona marga', h, { modo: 'perguntar' }); assert.strictEqual(JSON.stringify([S.f, S.ouro, S.cena]), antes, 'pergunta mudou o estado'); assert(/\(ao mestre\)/.test(txt(S, n)));
n = S.log.length; C.agir(S, 'bom dia', h, { modo: 'falar' }); assert(/“bom dia”/.test(txt(S, n)), txt(S, n));
// 2. IA: luta só contra quem está na lista; modos respeitados
S = nova('b1'); h = S.herois[0].id;
assert(!C.aplicarIA(S, 'x', h, { tipo: 'luta', alvos: ['ivo'] }, 'agir'), 'alvo fora da cena aceito');
assert(!C.aplicarIA(S, 'x', h, { tipo: 'luta', alvos: ['marga'] }, 'falar'), 'fala iniciou luta');
assert(C.aplicarIA(S, 'x', h, { tipo: 'luta', alvos: ['marga'] }, 'perguntar') === false && !S.combate, 'pergunta iniciou luta');
assert(C.aplicarIA(S, 'o que tem aqui', h, { tipo: 'improviso', veredito: 'decara', sucesso: 'Uma sala baixa.' }, 'perguntar') && /Uma sala baixa/.test(txt(S, 0)) && !S.combate);
assert(C.aplicarIA(S, 'ataco os dois', h, { tipo: 'luta', alvos: ['marga', 'bento'], narracao: 'Aço fora da bainha.' }, 'agir') && S.combate);
assert(C.validar(JSON.parse(JSON.stringify(C.compactar(S, 150, 80)))), 'estado em briga não valida');
assert(/PODEM SER ATACADOS: marga = Dona Marga; bento = Bento/.test(C.promptIA(nova('b2'), 'oi', nova('b2').herois[0].id, 'agir')));
// 3. fugir da briga e cair na briga
let fugiu = 0, caiu = 0;
for (let i = 0; i < 40; i++) {
  S = nova('c' + i, 1, 'classico'); h = S.herois[0].id; C.agir(S, 'ataco o bento', h); assert(S.combate);
  if (i % 2) { let g = 0; while (S.combate && !S.fim && g++ < 50) { const ops = C.opcoes(S, h); C.agir(S, (ops.find(o => /Fugir/.test(o.rot)) || ops.find(o => /Encerrar/.test(o.rot)) || ops[0]).cmd, h); } if (!S.fim) { fugiu++; assert(S.cena === 'estalagem' && S.f.malvisto && !S.f.mortos); } }
  else { let g = 0; while (S.combate && !S.fim && g++ < 200) { const ops = C.opcoes(S, h); C.agir(S, (ops.find(o => /Encerrar/.test(o.rot)) || ops.find(o => /Esquivar/.test(o.rot)) || ops[0]).cmd, h); } if (!S.combate && !S.fim && !(S.f.mortos || {}).bento) caiu++; }
  assert(C.validar(JSON.parse(JSON.stringify(C.compactar(S, 150, 80)))));
}
// 4. a aventura termina mesmo malvisto: jogo inteiro com bot depois de matar Marga, em grupos de 1 a 4
let fins = 0, total = 0;
for (let n2 = 1; n2 <= 4; n2++) for (let i = 0; i < 12; i++) {
  S = nova('d' + n2 + '-' + i, n2); h = S.herois[0].id; C.agir(S, 'ataco dona marga', h); lutar(S, / em Dona Marga/); total++;
  let g = 0, rnd = i * 7 + 1;
  while (!S.fim && g++ < 1500) {
    const hid = C.infoCena(S).vez || S.herois.find(x => !x.morto).id; const ops = C.opcoes(S, hid); assert(ops.length, 'sem opções em ' + S.cena);
    assert(!ops.some(o => /Marga/.test(o.rot)), 'ação com Marga morta: ' + ops.map(o => o.rot));
    const pref = ops.filter(o => /Deixar Pedra|Subir a trilha|Seguir|Descer à cripta|Atacar| em |Quebrar|Voltar para Pedra|Avançar sobre Ivo|corredor/.test(o.rot));
    rnd = (rnd * 1103515245 + 12345) & 0x7fffffff; const a = pref.length && rnd % 10 < 8 ? pref[rnd % pref.length] : ops[rnd % ops.length];
    C.agir(S, a.cmd, hid);
    if (S.fim && S.fim.tipo !== 'vitoria' && S.ckpt) { const N = C.voltarPontoSeguro(S); if (N) S = N; }
  }
  if (S.fim && S.fim.tipo === 'vitoria') { fins++; assert(/Ninguém conta moedas/.test(txt(S, 0)), 'epílogo errado'); assert(!/Dona Marga conta trinta/.test(txt(S, 0))); }
}
console.log('fugas ok:', fugiu, '· quedas na briga:', caiu, '· aventuras concluídas malvisto:', fins + '/' + total);
assert(fins >= total * 0.6, 'poucas aventuras terminam malvisto');
console.log('t3: tudo certo');
