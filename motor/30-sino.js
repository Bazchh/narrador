  /* ------------------------------------------------------------------ aventura: O Sino de Pedra-Funda */
  function resolvido(S) { return !!S.f.ivo; }
  function goblinsOk(S) { return !!S.f.goblins; }
  function criptaLimpa(S) { return S.inimigos.cripta.every(function (e) { return !e.vivo; }); }
  var NUM = { 1: 'um', 2: 'dois', 3: 'três', 4: 'quatro', 5: 'cinco' };
  function qg(S) { return NUM[S.inimigos.goblins.length] || 'vários'; }
  function Qg(S) { var t = qg(S); return t.charAt(0).toUpperCase() + t.slice(1); }
  function V(S, um, grupo) { return S.herois.length > 1 ? grupo : um; }
  function sinoInimigos(n) {
    return {
      goblins: varios(n <= 1 ? 2 : n === 2 ? 3 : 4, 'g', 'goblin', 'Goblin'),
      cripta: varios(n >= 3 ? 2 : 1, 'e', 'esqueleto', 'Esqueleto').concat(varios(n >= 4 ? 2 : 1, 'z', 'zumbi', 'Zumbi', n <= 1 ? 10 : 15)),
      camara: [mk('ivo', 'ivo', 'Ivo', 14 + 8 * (n - 1))].concat(varios(n >= 3 ? 2 : 1, 'k', 'zumbi', 'Guardião', n <= 1 ? 12 : 15))
    };
  }

  var SINO_GRUPOS = {
    goblins: {
      zonas: {}, zonaPadrao: 'medio', alerta: 'goblinsAlerta', onde: 'na trilha do barranco',
      fugaPara: 'estalagem', acordaEm: 'estalagem',
      textoFuga: 'Você desce a trilha aos trancos, com os guinchos dos goblins ficando para trás.',
      textoQueda: function (S) {
        var perdeu = Math.floor(S.ouro / 2); S.ouro -= perdeu;
        return 'Chuva no rosto. Os goblins reviraram os bolsos' + (perdeu ? ' e levaram ' + perdeu + ' po' : '') + ', e depois perderam o interesse. ' + ((S.f.malvisto || estaMorto(S, 'bento')) ? 'Ninguém da vila sobe para ajudar: é por conta própria que se chega de volta à estalagem. ' + V(S, 'Você está com 1 ponto de vida.', 'Quem resistiu está com 1 ponto de vida.') : 'O velho Bento, que subiu atrás de lenha, ' + V(S, 'arrasta você até a estalagem. Você está com 1 ponto de vida.', 'vai e volta três vezes até trazer todo mundo para a estalagem. Quem resistiu está com 1 ponto de vida.'));
      },
      // Goblins são covardes: quando um cai, o outro foge.
      fimSe: function (S) { var l = S.inimigos.goblins; return l.filter(function (e) { return !e.vivo; }).length * 2 >= l.length; },
      aoVencer: function (S) {
        var fugiram = S.inimigos.goblins.filter(function (e) { return e.vivo; });
        S.inimigos.goblins.forEach(function (e) { e.vivo = false; });
        S.f.goblins = 'mortos';
        var fim = ' A trilha fica em silêncio, só a chuva. Lá em cima, o campanário da capela velha aparece entre as árvores.';
        if (fugiram.length) {
          out(S, 'narra', (fugiram.length === 1 ? fugiram[0].nome + ' olha os companheiros caídos, solta um guincho e some no mato sem olhar para trás.' : 'Os goblins que restam olham os companheiros caídos, guincham e somem no mato sem olhar para trás.') + fim);
          fato(S, V(S, 'Você derrubou', 'O grupo derrubou') + ' parte dos goblins da trilha do barranco e o resto fugiu.');
        } else {
          out(S, 'narra', 'Os goblins ficam caídos entre as pedras.' + fim);
          fato(S, V(S, 'Você derrotou', 'O grupo derrotou') + ' os goblins que emboscavam a trilha do barranco.');
        }
      }
    },
    cripta: {
      zonas: { e1: 'medio', e2: 'medio', z1: 'longe', z2: 'longe' }, alerta: 'mortosAlerta', onde: 'na antecâmara da cripta',
      fugaPara: 'capela', acordaEm: 'capela',
      textoFuga: 'Você sobe os degraus de dois em dois e bate a porta da cripta atrás de si. Do outro lado, algo arranha a madeira e desiste.',
      textoQueda: function (S) { return 'Os mortos não se interessam por quem para de se mexer. Horas depois, ' + V(S, 'você abre os olhos, rasteja degraus acima e desaba no chão da capela. Está com 1 ponto de vida.', 'um a um, vocês abrem os olhos, rastejam degraus acima e desabam no chão da capela. Quem resistiu está com 1 ponto de vida.'); },
      aoVencer: function (S) {
        out(S, 'narra', 'Os ossos param de tremer. A antecâmara volta a ser só uma sala de mortos quietos. No fundo, um corredor estreito desce, e de lá vem uma batida surda e lenta: pedra contra pedra.');
        fato(S, V(S, 'Você destruiu', 'O grupo destruiu') + ' os mortos-vivos da antecâmara da cripta.');
      }
    },
    camara: {
      zonas: { ivo: 'longe', k1: 'medio', k2: 'medio', r1: 'longe' }, alerta: 'ivoAlerta', onde: 'na câmara do sino',
      fugaPara: 'cripta', acordaEm: 'capela',
      textoFuga: 'Você recua pelo corredor. Atrás de você, o sino volta a bater, sem pressa.',
      textoQueda: function (S) { return V(S, 'Você acorda no chão da capela, enrolado numa manta que não é sua. Alguém arrastou você para fora da cripta e enfaixou o pior dos cortes.', 'O grupo acorda no chão da capela, cada um enrolado numa manta que não é sua. Alguém arrastou todos para fora da cripta e enfaixou o pior dos cortes.') + ' Lá embaixo, o sino continua. Quem resistiu está com 1 ponto de vida.'; },
      fimSe: function (S) { var ivo = S.inimigos.camara[0]; return !ivo.vivo || !!S.f.sinoAbafado; },
      aoRodada: function (S, rodada) {
        var ivo = S.inimigos.camara[0];
        if (rodada >= (S.herois.length > 1 ? 3 : 4) && !S.f.esqueletoErguido && ivo.vivo && !S.f.sinoAbafado) {
          S.f.esqueletoErguido = true;
          var e = mk('r1', 'esqueleto', 'Esqueleto');
          e.zona = 'longe';
          S.inimigos.camara.push(e);
          S.combate.ordem.push('r1');
          out(S, 'combate', 'O sino bate mais uma vez e um dos nichos da parede se abre por dentro: um esqueleto se levanta, do outro lado da câmara.');
        }
      },
      ia: {
        ivo: function (S, e) {
          if (e.zona === 'perto') return false; // ataca com a foice pelo fluxo normal
          out(S, 'combate', 'Ivo puxa a corda. O sino de pedra bate, surdo, e o som parece vir de dentro dos dentes de quem escuta.');
          return true;
        }
      },
      abafar: function (S, h) {
        var c = S.combate, ivo = S.inimigos.camara[0];
        if (c.turno.acao) return aviso(S, h.nome + ' já usou a ação neste turno.');
        if (ivo.zona === 'longe') return aviso(S, 'O sino está do outro lado da câmara, junto de Ivo. Avance sobre Ivo primeiro.');
        c.turno.acao = true;
        var modo = S.f.sabeSino ? 'vantagem' : null;
        out(S, 'veredito', 'Veredito: teste de Atletismo (Força), CD 13 · médio' + (modo ? ' · com vantagem (o grupo sabe como o sino funciona)' : '') + '.');
        var r = teste(S, 'Atletismo de ' + h.nome + ' para abafar o sino', bonusPericia(h, 'atletismo'), modo, 13, h);
        if (r.ok) {
          S.f.sinoAbafado = true;
          out(S, 'combate', h.nome + ' se joga contra o sino e o abraça com o corpo inteiro. A pedra vibra contra o peito, cada vez menos, e para.');
        } else out(S, 'combate', h.nome + ' agarra a borda do sino, mas ele escapa e balança de novo.');
        return true;
      },
      aoVencer: function (S) {
        var ivo = S.inimigos.camara[0];
        S.inimigos.camara.forEach(function (e) { if (e.tipo !== 'ivo') e.vivo = false; });
        if (S.f.sinoAbafado) {
          S.f.ivo = 'rendido';
          out(S, 'narra', 'Sem o som, os mortos desabam onde estão, como roupas largadas. Ivo solta a corda. Olha para a figura pequena no banco, que não se mexeu, e cai de joelhos.\n\n“Ela ia acordar”, ele diz, sem força. “Faltava pouco.”');
          fato(S, V(S, 'Você abafou', 'O grupo abafou') + ' o sino de pedra no meio do combate. Os mortos caíram e Ivo se rendeu.');
          desvio(S, 'derrotar Ivo em combate', 'o sino foi silenciado em vez de Ivo ser derrubado.', 'escolha do jogador.');
        } else if (!ivo.vivo && S.f.ivoGolpe === 'corpo') {
          S.f.ivo = 'rendido'; ivo.hp = 1;
          out(S, 'narra', 'O último golpe é contido no instante final: derruba, não mata. Ivo cai sentado, sem ar, vivo. A corda escapa da mão dele, o sino para, e os mortos desabam onde estão.\n\nEle olha para a figura pequena no banco, que não se mexeu. “Faltava pouco”, diz.');
          fato(S, 'Ivo foi derrubado sem ser morto. O sino parou e os mortos caíram.');
        } else {
          S.f.ivo = 'morto';
          out(S, 'narra', 'Ivo cai de costas, ainda segurando a corda. O sino dá meia batida e para. Os mortos desabam onde estão. Na câmara, só respiração ofegante e a figura pequena no banco, que não se mexeu.');
          fato(S, 'Ivo, o sacristão, morreu na câmara do sino. O sino parou.');
        }
        S.f.resolvido = true;
      }
    }
  };

  var SINO_CENAS = {
    /* ---------------------------------------------------------------- 1. estalagem */
    estalagem: {
      nome: 'Estalagem do Lampião', lugar: 'Vila de Pedra-Funda',
      desc: function (S) {
        if (S.f.malvisto) return 'A sala da estalagem se esvazia quando você entra. Quem fica, fica de costas. Ninguém lhe dirige a palavra, ninguém serve nada.';
        if (resolvido(S)) return 'A sala da estalagem está cheia e quieta. Todos esperam que você diga alguma coisa.';
        return 'Sala baixa, lareira acesa, meia dúzia de moradores falando baixo de costas para as janelas. Dona Marga cuida do balcão. O velho caçador Bento ocupa o canto perto do fogo.';
      },
      presentes: function (S) {
        var l = [];
        if (!estaMorto(S, 'marga')) l.push('Dona Marga, a estalajadeira');
        if (!estaMorto(S, 'bento')) l.push('Bento, o velho caçador');
        if (S.f.malvisto) l.push('moradores que evitam o seu olhar');
        return l;
      },
      pessoas: function () {
        return [
          { id: 'marga', nome: 'Dona Marga', tipo: 'plebeu', re: /marga|estalajadeira|dona|mulher/ },
          { id: 'bento', nome: 'Bento', tipo: 'cacador', re: /bento|cacador|velho/ }
        ];
      },
      aoAtacar: function (S, alvos) { return 'As conversas morrem de uma vez. Um banco cai. Os moradores se espremem contra as paredes e a porta, e ' + alvos.map(function (p) { return p.nome; }).join(' e ') + (alvos.length > 1 ? ' se põem' : ' se põe') + ' em guarda como ' + (alvos.length > 1 ? 'podem' : 'pode') + '.'; },
      aposBriga: function (S, nomes) { return 'Ninguém grita. É pior: a sala inteira olha para ' + nomes + ' no chão e depois para você, e um a um os moradores saem pela porta, sem dar as costas. Pedra-Funda não tem guarda, mas tem memória. Daqui em diante ninguém nesta vila lhe vende, lhe hospeda ou lhe paga.'; },
      motivoInseguro: 'Ninguém nesta vila lhe dá pouso depois do que aconteceu.',
      seguro: function (S) { return !S.f.malvisto; },
      longo: function (S) { return 'Dona Marga cede ' + V(S, 'o quarto dos fundos', 'os quartos dos fundos') + '. À meia-noite o sino bate lá em cima, três vezes, e o sono vem mesmo assim. Amanhece o dia ' + S.dia + '.'; },
      entrar: function (S, o) {
        if (o.primeira) {
          out(S, 'narra', 'Chove fino sobre Pedra-Funda quando você empurra a porta da Estalagem do Lampião. Meia dúzia de moradores fala baixo, de costas para as janelas. Atrás do balcão, Dona Marga conta as velas que restam. Num canto, o velho caçador Bento afia uma faca que não precisa de fio.\n\nLá fora, morro acima, um sino bate uma vez. A sala inteira se cala.\n\nVocê pode falar com Dona Marga, puxar conversa com Bento ou observar a sala.');
          return;
        }
        if (S.f.malvisto) { if (!o.calado) out(S, 'narra', 'Você entra na Estalagem do Lampião. As conversas morrem. Ninguém serve nada, ninguém pergunta nada.'); return; }
        if (resolvido(S)) { out(S, 'narra', 'A porta da estalagem se abre antes de você tocar nela. Dona Marga está de pé no meio da sala, com a vila inteira atrás. Ninguém pergunta nada: esperam você contar.'); return; }
        if (!o.calado) out(S, 'narra', 'Você volta à Estalagem do Lampião. O fogo continua aceso e as conversas param quando você entra.');
      },
      acoes: [
        {
          id: 'partir', rot: 'Deixar Pedra-Funda', livre: true, re: /partir|parto|ir embora|vou embora|deixar a vila|deixo a vila|estrada/,
          se: function (S) { return S.f.malvisto && resolvido(S); },
          fazer: function (S) { epilogoMalvisto(S); }
        },
        {
          id: 'contar_marga', rot: 'Contar a Dona Marga o que aconteceu', re: /marga|contar|conto|relat|recompensa|explic|voltei|aconteceu/,
          se: function (S) { return resolvido(S); },
          fazer: function (S) { epilogo(S); }
        },
        {
          id: 'pedir_adiantamento', rot: 'Pedir a Marga algo para a subida', re: /adiant|pocao|suprimento|para a subida|para a viagem|ajuda extra|pagamento antes|metade agora/,
          se: function (S) { return S.f.gancho && !S.f.pocaoMarga && !resolvido(S); },
          veredito: function () { return { tipo: 'teste', per: 'persuasao', cd: 12 }; },
          fazer: function (S, r) {
            if (r.ok) {
              S.f.pocaoMarga = true; S.pocoes++;
              out(S, 'narra', 'Marga pensa, some pela porta da cozinha e volta com um frasco de vidro grosso. “Era do meu marido. Ele não precisa mais. Você talvez precise.”');
              fato(S, 'Dona Marga lhe deu uma poção de cura antes da subida.');
            } else out(S, 'narra', '“Pago na volta”, diz Marga, sem maldade. “Já adiantei dinheiro a gente que subiu e não desceu.”');
          }
        },
        {
          id: 'falar_marga', rot: 'Falar com Dona Marga', re: /marga|estalajadeira|dona|balcao|trabalho|servico|contrato|oferta|aceito/,
          se: function (S) { return !resolvido(S); },
          fazer: function (S) {
            if (!S.f.gancho) {
              S.f.gancho = true;
              out(S, 'narra', 'Dona Marga serve uma caneca sem perguntar se você quer.\n\n“Faz três noites. O sino da capela velha toca à meia-noite. A capela está fechada há vinte anos, e aquele sino é de pedra: foi feito para nunca soar. O sacristão, Ivo, subiu na primeira noite para ver o que era. Não desceu.”\n\nEla empurra a caneca na sua direção. “Trinta peças de ouro e cama enquanto durar, para quem subir, descobrir o que é e fizer parar. A trilha do barranco sai dos fundos da vila.”');
              fato(S, 'Dona Marga contratou você por 30 po para descobrir por que o sino de pedra toca e fazê-lo parar.');
              fato(S, 'O sacristão Ivo subiu à capela velha há três noites e não voltou.');
            } else {
              out(S, 'narra', '“Já disse o que sei”, responde Marga. “O sino toca à meia-noite, Ivo subiu e não desceu, e eu pago trinta peças a quem resolver. Ivo cuidava do cemitério. Homem quieto. Ficou mais quieto desde o inverno.”');
            }
          }
        },
        {
          id: 'pagar_bebida', rot: 'Pagar uma bebida a Bento (1 po)', re: /bebida|cerveja|caneca|vinho|pago|pagar|rodada/,
          se: function (S) { return S.f.falouBento && !S.f.sabeTrilha && S.ouro >= 1 && !resolvido(S); },
          fazer: function (S) { pagar(S, 1); out(S, 'narra', 'Você põe uma moeda no balcão e uma caneca cheia na frente de Bento. Ele olha a caneca, depois você, e guarda a faca.'); bentoConta(S); }
        },
        {
          id: 'convencer_bento', rot: 'Convencer Bento a contar o que sabe', re: /bento|cacador|velho|convenc|insist|persuad/,
          se: function (S) { return S.f.falouBento && !S.f.sabeTrilha && !resolvido(S); },
          veredito: function () { return { tipo: 'teste', per: 'persuasao', cd: 10 }; },
          fazer: function (S, r) {
            if (r.ok) { out(S, 'narra', 'Você fala da subida como quem vai de qualquer jeito. Bento bufa, vencido.'); bentoConta(S); }
            else out(S, 'narra', 'Bento cospe no fogo. “Conselho de graça ninguém escuta.” Talvez uma bebida solte a língua dele.');
          }
        },
        {
          id: 'falar_bento', rot: 'Puxar conversa com Bento', re: /bento|cacador|velho|lareira/,
          se: function (S) { return !S.f.falouBento && !resolvido(S); },
          fazer: function (S) {
            S.f.falouBento = true;
            out(S, 'narra', 'Bento não levanta os olhos da faca. “Tem coisa pequena e ruim rondando a trilha desde que o sino começou. Eu não subo mais.” E se cala, como quem já falou demais.');
            fato(S, 'Bento, o caçador, diz que algo pequeno e ruim ronda a trilha desde que o sino começou.');
          }
        },
        {
          id: 'observar_sala', livre: true, rot: 'Observar a sala e as pessoas', re: /observ|olh|examin|repar|estud|sala|moradores|clima|escut|ouvir|ouco/,
          se: function (S) { return !S.f.obsSala && !resolvido(S); },
          veredito: function () { return { tipo: 'teste', per: 'intuicao', cd: 12 }; },
          fazer: function (S, r) {
            S.f.obsSala = true;
            if (r.ok) {
              S.f.sabeLuto = true;
              out(S, 'narra', 'Você escuta mais do que olha. Duas mulheres perto da janela falam de Ivo com pena, não com medo: “desde que enterrou a menina, no inverno”. Quando percebem você, mudam de assunto.');
              fato(S, 'Ivo enterrou uma filha no inverno passado. A vila fala dele com pena.');
            } else out(S, 'narra', 'Gente com medo e sem vontade de explicar o medo a um estranho. Daqui, você não tira mais do que isso.');
          }
        },
        {
          id: 'longo', rot: 'Passar a noite (descanso longo)', re: /descans|dorm|pernoit|passar a noite|quarto|cama/,
          se: function (S) { return !resolvido(S); },
          fazer: function (S) { descansoLongo(S); }
        }
      ],
      topicos: [
        { re: /sino/, txt: function () { return 'O que a vila sabe: o sino da capela velha é de pedra, feito para nunca soar, e mesmo assim toca à meia-noite há três noites.'; } },
        { re: /ivo|sacristao/, txt: function (S) { return 'Ivo é o sacristão: cuidava da capela e do cemitério. Subiu na primeira noite e não voltou.' + (S.f.sabeLuto ? ' Você ouviu que ele enterrou uma filha no inverno.' : ''); } },
        { re: /recompensa|pagamento|ouro|quanto/, txt: function () { return 'Dona Marga oferece 30 peças de ouro e pouso a quem fizer o sino parar.'; } },
        { re: /capela|cripta|trilha|caminho/, txt: function () { return 'A capela velha fica no alto do morro. A trilha do barranco, que sai dos fundos da vila, leva até lá.'; } }
      ],
      saidas: function (S) {
        return [{ para: 'trilha', rot: 'Subir a trilha do barranco', re: /trilha|barranco|capela|subir|subo|morro|sair|saio|partir|parto/ }];
      }
    },

    /* ---------------------------------------------------------------- 2. trilha */
    trilha: {
      nome: 'Trilha do Barranco', lugar: 'Entre a vila e a capela',
      desc: function (S) {
        if (S.f.goblins === 'evitados' && !resolvido(S)) return 'Trilha estreita entre pedras grandes e raízes, com o barranco de um lado. Os goblins seguem de tocaia lá embaixo, mas você conhece o caminho por cima. Para cima, a capela velha; para baixo, as luzes da vila.';
        if (goblinsOk(S)) return 'Trilha estreita entre pedras grandes e raízes, com o barranco de um lado. Quieta agora. Para cima, a capela velha; para baixo, as luzes da vila.';
        return 'Trilha estreita entre pedras grandes e raízes, com o barranco de um lado. ' + Qg(S) + ' goblins estão de tocaia no trecho das pedras.';
      },
      presentes: function (S) { return (goblinsOk(S) && !(S.f.goblins === 'evitados' && !resolvido(S))) ? [] : [Qg(S) + ' goblins de tocaia']; },
      seguro: function (S) { return goblinsOk(S); },
      motivoInseguro: 'Os goblins estão perto demais.',
      entrar: function (S, o) {
        if (!S.f.gancho && !S.f.malvisto) {
          S.f.gancho = true;
          out(S, 'narra', 'Quando você alcança a porta dos fundos, Dona Marga grita do balcão: “Trinta peças de ouro se você fizer aquele sino parar! E traga notícia do Ivo, o sacristão!”');
          fato(S, 'Dona Marga ofereceu 30 po para você fazer o sino de pedra parar e trazer notícia de Ivo.');
        }
        if (goblinsOk(S)) {
          if (!o.calado) out(S, 'narra', resolvido(S) ? 'A trilha desce quieta. Nenhum sinal dos goblins: sem o sino, não há mais quem pague por eles.' : S.f.goblins === 'evitados' ? 'Você refaz o caminho por cima do barranco, agarrado às raízes. Lá embaixo, os goblins continuam vigiando a trilha vazia.' : 'A trilha do barranco está quieta. A chuva escorre pelas pedras.');
          return;
        }
        if (S.f.goblinsAlerta) {
          out(S, 'narra', 'Os goblins não foram embora. Um assobio agudo corta a chuva assim que você pisa no trecho das pedras, e eles saltam para a trilha.');
          iniciarCombate(S, 'goblins', {});
          return;
        }
        if (S.f.viuGoblins) { out(S, 'narra', 'Os goblins continuam de tocaia entre as pedras, sem ter visto ninguém.'); return; }
        out(S, 'narra', 'A trilha sobe em curvas apertadas, com o barranco à esquerda e pedras do tamanho de carroças à direita. A chuva abafa os seus passos, e os de qualquer outra coisa.');
        var modo = S.f.sabeTrilha ? 'vantagem' : null;
        out(S, 'veredito', 'O mestre pede um teste de Percepção (Sabedoria), CD 13 · médio' + (modo ? ' · com vantagem (Bento avisou onde olhar)' : '') + '.');
        var hp = melhor(S, 'percepcao');
        var r = teste(S, 'Percepção de ' + hp.nome, bonusPericia(hp, 'percepcao'), modo, 13, hp);
        if (r.ok) {
          S.f.viuGoblins = true;
          out(S, 'narra', 'Você para antes da curva. Entre duas pedras, uma orelha pontuda se mexe. São ' + qg(S) + ' goblins de tocaia, virados para a trilha, e ainda não viram ninguém.\n\nDá para atacar primeiro, contornar pelo alto do barranco ou sair à vista e falar com eles.');
          fato(S, hp.nome + ' percebeu ' + qg(S) + ' goblins de tocaia na trilha antes de ser visto.');
        } else {
          out(S, 'narra', 'Uma pedrinha rola. Quando você vira o rosto, ' + qg(S) + ' goblins já estão pulando das pedras, com adagas na mão e os dentes à mostra.');
          fato(S, Qg(S) + ' goblins armaram uma emboscada na trilha do barranco.');
          iniciarCombate(S, 'goblins', { ini: 'desvantagem', zonas: { g1: 'perto', g2: 'medio' } });
        }
      },
      acoes: [
        {
          id: 'atacar_goblins', rot: 'Atacar os goblins de surpresa', re: /atac|ataq|luto|lutar|mato|matar|embosc|surpresa|flech|atir|golpe/,
          se: function (S) { return S.f.viuGoblins && !goblinsOk(S); },
          fazer: function (S) {
            out(S, 'narra', 'Você escolhe o momento e sai da curva já em movimento. Os goblins levam um susto.');
            iniciarCombate(S, 'goblins', { ini: 'vantagem', zonas: { g1: 'medio', g2: 'longe' } });
          }
        },
        {
          id: 'contornar_goblins', rot: 'Contornar pelo alto do barranco', re: /contorn|barranco|esgueir|furtiv|escond|passar sem|desvi|por cima|silencio/,
          se: function (S) { return S.f.viuGoblins && !goblinsOk(S); },
          veredito: function (S) { return { tipo: 'teste', per: 'furtividade', cd: 12, grupo: true, modo: S.f.sabeTrilha ? 'vantagem' : null, porque: 'Bento contou do caminho por cima' }; },
          fazer: function (S, r) {
            if (r.ok) {
              S.f.goblins = 'evitados';
              out(S, 'narra', 'Você sobe pelo barranco agarrado às raízes, passa por cima das pedras e desce do outro lado. Lá embaixo, os goblins continuam vigiando uma trilha vazia.');
              fato(S, 'Você passou pelos goblins da trilha sem ser visto.');
              desvio(S, 'combate contra os goblins na trilha', 'você contornou a emboscada sem lutar.', 'escolha do jogador, com sucesso em Furtividade.');
            } else {
              out(S, 'narra', 'Uma raiz cede. Você escorrega meio barranco numa chuva de terra, e rostos verdes se viram ao mesmo tempo.');
              iniciarCombate(S, 'goblins', {});
            }
          }
        },
        {
          id: 'intimidar_goblins', rot: 'Sair à vista e ameaçar os goblins', re: /intimid|ameac|assust|amedront|grit/,
          se: function (S) { return S.f.viuGoblins && !goblinsOk(S); },
          veredito: function () { return { tipo: 'teste', per: 'intimidacao', cd: 13 }; },
          fazer: function (S, r) {
            if (r.ok) { out(S, 'narra', 'Você sai da curva de arma na mão e fala baixo, devagar, o que vai acontecer se eles ficarem. Os goblins se entreolham. Um deles larga a adaga.'); acordoGoblins(S); }
            else { out(S, 'narra', 'Os goblins escutam a ameaça até o fim, contam quantos são vocês e riem.'); iniciarCombate(S, 'goblins', {}); }
          }
        },
        {
          id: 'pagar_goblins', rot: 'Oferecer 5 po para passarem a conversa', re: /fal|convers|negoci|ofere|suborn|pag|moeda|ouro|acordo|persuad|convenc/,
          se: function (S) { return S.f.viuGoblins && !goblinsOk(S); },
          veredito: function (S) {
            if (S.ouro < 5) return { tipo: 'impossivel', motivo: 'Goblins não aceitam promessa. Sem pelo menos 5 peças de ouro na mão, eles nem escutam.' };
            return { tipo: 'teste', per: 'persuasao', cd: 12 };
          },
          fazer: function (S, r) {
            if (r.ok) { pagar(S, 5); out(S, 'narra', 'Você mostra as moedas antes de mostrar o rosto. Os goblins farejam o ar, discutem em guinchos e estendem a mão.'); acordoGoblins(S); }
            else { out(S, 'narra', 'Os goblins olham as moedas, olham a sua bolsa e decidem que preferem a bolsa inteira.'); iniciarCombate(S, 'goblins', {}); }
          }
        },
        {
          id: 'revistar_goblins', rot: 'Revistar os goblins caídos', re: /revist|vasculh|procur|examin|bolso|corpo|saque/,
          se: function (S) { return S.f.goblins === 'mortos' && !S.f.revistouGoblins; },
          fazer: function (S) {
            S.f.revistouGoblins = true; S.f.pistaMoedas = true; S.ouro += 4;
            out(S, 'narra', 'Nos bolsos, quatro peças de ouro e um punhado de cobres velhos, todos com um pequeno sino cunhado: moedas da caixa de esmolas da capela. Alguém lá de cima andou pagando os goblins.');
            fato(S, 'Os goblins carregavam moedas da caixa de esmolas da capela: alguém os pagava.');
          }
        }
      ],
      topicos: [
        { re: /goblin/, txt: function (S) { return goblinsOk(S) ? 'Os goblins não são mais problema nesta trilha.' : S.f.viuGoblins ? 'São ' + qg(S) + ', pequenos, armados com adagas, vigiando a trilha. Ainda não viram você.' : 'Bento falou de coisa pequena e ruim na trilha.'; } },
        { re: /capela|sino|cima/, txt: function () { return 'A capela velha fica no fim desta trilha, no alto do morro.'; } }
      ],
      saidas: function (S) {
        var s = [{ para: 'estalagem', rot: 'Descer para a vila', re: /vila|estalagem|descer|desco|voltar|volto|pedra funda/ }];
        s.push({ para: 'capela', rot: 'Seguir até a capela velha', re: /capela|subir|subo|seguir|sigo|cima|morro|adiante|frente/, bloqueio: goblinsOk(S) ? null : (S.f.viuGoblins ? 'Os goblins vigiam justamente o trecho por onde a trilha segue. Você precisa lidar com eles antes: lutando, contornando ou conversando.' : 'Você ainda não passou pelo trecho das pedras.') });
        return s;
      }
    },

    /* ---------------------------------------------------------------- 3. capela */
    capela: {
      nome: 'Capela Velha', lugar: 'Alto do morro',
      desc: function (S) {
        return 'Metade do telhado caiu. O campanário está de pé, mas vazio: resta a corda cortada e marcas de arrasto no chão. Atrás do altar, a porta da cripta, de carvalho e ferro' + (S.f.criptaAberta ? ', agora aberta' : ', trancada') + '. Ao lado, uma sacristia pequena. Do lado de fora, uma janela baixa da cripta, meio soterrada.';
      },
      presentes: function () { return []; },
      seguro: function () { return true; },
      entrar: function (S, o) {
        if (o.primeira) {
          out(S, 'narra', 'A capela velha perdeu metade do telhado para vinte invernos. Você entra pisando em telha quebrada. O campanário continua de pé, mas não há sino nele: só uma corda cortada e, no chão de laje, marcas fundas de arrasto que vão do pé da torre até uma porta de carvalho e ferro atrás do altar. A porta da cripta. Trancada.\n\nAo lado do altar, uma sacristia com a porta encostada. Lá fora, rente ao chão, uma janela baixa da cripta, meio soterrada.\n\nDe algum lugar debaixo dos seus pés vem uma batida surda. Pedra contra pedra.');
          fato(S, 'O sino de pedra foi tirado do campanário e arrastado para dentro da cripta.');
          subirNivel(S, 'ao chegar à capela velha');
          return;
        }
        if (!o.calado) out(S, 'narra', 'Você está de volta à nave da capela velha. A chuva entra pelo telhado aberto.' + (resolvido(S) ? ' Pela primeira vez, não há batida nenhuma vindo de baixo.' : ''));
      },
      acoes: [
        {
          id: 'ler_diario', rot: 'Ler o caderno de Ivo', re: /ler|leio|caderno|diario|anotac|pagina/,
          se: function (S) { return S.f.achouDiario && !S.f.segredo; },
          fazer: function (S) {
            S.f.segredo = true;
            out(S, 'narra', 'A letra é miúda e cuidadosa no começo, e vai se desfazendo.\n\n“Lívia, nove anos. Febre do inverno. Enterrada no terceiro nicho.”\n\nPáginas depois: “O livro de registros da capela diz que o sino de pedra chama quem dorme ao alcance do som. Por isso o fizeram mudo.”\n\nE na última página escrita: “Toquei. Ela abriu os olhos. Não fala ainda, não me olha. Os outros também se levantam, mas não importa. Preciso tocar mais. Paguei os pequenos da trilha para ninguém subir.”');
            fato(S, 'Segredo descoberto: Ivo toca o sino de pedra para trazer de volta a filha morta, Lívia. O sino levanta todos os mortos da cripta.');
            fato(S, 'Ivo pagou os goblins da trilha com as esmolas da capela para manter a vila longe.');
          }
        },
        {
          id: 'vasculhar_sacristia', rot: 'Vasculhar a sacristia', re: /sacristia|vasculh|procur|revist|gaveta|armario|chave/,
          se: function (S) { return !S.f.vasculhou; },
          veredito: function () { return { tipo: 'teste', per: 'investigacao', cd: 12 }; },
          fazer: function (S, r) {
            S.f.vasculhou = true; S.f.achouDiario = true;
            var base = 'A sacristia tem uma cama de campanha desfeita, restos de comida e, sobre a mesa, um caderno de capa mole aberto com a lombada para cima. Alguém vive aqui há dias.';
            if (r.ok) {
              S.f.chave = true; S.pocoes++;
              out(S, 'narra', base + '\n\nVocê não para na mesa. Atrás de um missal na prateleira mais alta, uma chave de ferro comprida. No fundo falso da gaveta, um frasco de poção de cura ainda lacrado.');
              fato(S, 'Na sacristia você achou a chave da cripta, uma poção de cura e o caderno de Ivo.');
            } else {
              out(S, 'narra', base + '\n\nVocê revira gavetas e prateleiras, mas fora o caderno não encontra nada que sirva. Se há uma chave, está bem escondida.');
              fato(S, 'Na sacristia você achou o caderno de Ivo, mas nenhuma chave.');
            }
          }
        },
        {
          id: 'examinar_marcas', rot: 'Examinar o campanário e as marcas', re: /campanario|marca|arrasto|corda|torre|sino|rastro/,
          se: function (S) { return !S.f.viuMarcas; },
          veredito: function () { return { tipo: 'teste', per: 'arcanismo', cd: 13 }; },
          fazer: function (S, r) {
            S.f.viuMarcas = true;
            if (r.ok) {
              S.f.sabeSino = true;
              out(S, 'narra', 'Na base da torre, entalhada na pedra e quase apagada, uma inscrição fúnebre. Você reconhece a fórmula: o sino é uma relíquia de chamado. Cada batida acorda quem está enterrado ao alcance do som, e só enquanto o som durar. Quem abafar o sino quebra o chamado na hora.');
              fato(S, 'O sino de pedra chama os mortos enquanto soa. Abafá-lo quebra o chamado.');
            } else out(S, 'narra', 'Um homem sozinho arrastou esse sino, aos poucos, com alavanca e muita teimosia. Há uma inscrição gasta na base da torre, mas você não consegue tirar sentido dela.');
          }
        },
        {
          id: 'abrir_chave', rot: 'Abrir a cripta com a chave', re: /chave|abrir|abro|destranc|porta/,
          se: function (S) { return S.f.chave && !S.f.criptaAberta; },
          fazer: function (S) {
            S.f.criptaAberta = 'chave';
            out(S, 'narra', 'A chave gira com um estalo seco. A porta se abre para dentro, sem ranger: alguém andou passando óleo nas dobradiças. Degraus úmidos descem para o escuro.');
            fato(S, 'Você abriu a porta da cripta com a chave da sacristia.');
          }
        },
        {
          id: 'tentar_porta', rot: 'Examinar a porta da cripta', re: /porta|abrir|abro|macaneta|tranca/,
          se: function (S) { return !S.f.criptaAberta && !S.f.chave; },
          fazer: function (S) { out(S, 'narra', 'Carvalho grosso, ferragens antigas, fechadura de ferro. Trancada, e as dobradiças foram engraxadas há pouco. Caminhos possíveis: achar a chave (a sacristia é um bom lugar), abrir a fechadura com ferramentas de ladrão, forçar a porta no ombro ou entrar pela janela soterrada, do lado de fora.'); }
        },
        {
          id: 'arrombar', rot: 'Abrir a fechadura com ferramentas de ladrão', re: /arromb|fechadura|gazua|ferramenta|destranc/,
          se: function (S) { return !S.f.criptaAberta; },
          veredito: function (S, h) {
            if (!h.ferramentas) return { tipo: 'impossivel', motivo: 'Sem ferramentas de ladrão, essa fechadura de ferro não cede a um grampo ou a uma faca. Procure a chave, force a porta ou tente a janela soterrada.' };
            return { tipo: 'teste', per: 'prestidigitacao', cd: 15, modo: h.pericias.indexOf('prestidigitacao') >= 0 ? 'vantagem' : null, porque: 'treino na perícia e nas ferramentas' };
          },
          fazer: function (S, r) {
            if (r.ok) { S.f.criptaAberta = 'arrombada'; out(S, 'narra', 'Três pinos, o último teimoso. A fechadura cede com um clique que você sente mais do que ouve. Degraus úmidos descem para o escuro.'); fato(S, 'Você abriu a fechadura da cripta com ferramentas de ladrão.'); }
            else out(S, 'narra', 'A fechadura é velha e boa. Uma das gazuas entorta lá dentro e você desiste antes de quebrá-la. Ainda há a porta para forçar e a janela soterrada.');
          }
        },
        {
          id: 'forcar_porta', rot: 'Forçar a porta da cripta', re: /forc|ombro|derrub|chut|empurr|quebr/,
          se: function (S) { return !S.f.criptaAberta; },
          veredito: function () { return { tipo: 'teste', per: 'atletismo', cd: 15 }; },
          fazer: function (S, r) {
            if (r.ok) { S.f.criptaAberta = 'forcada'; S.f.barulho = true; out(S, 'narra', 'No terceiro tranco o batente racha e a porta bate na parede de dentro com um estrondo que desce a escada inteira. Se havia alguma chance de chegar em silêncio, acabou.'); fato(S, 'Você arrombou a porta da cripta à força. O barulho foi grande.'); }
            else out(S, 'narra', 'Carvalho e ferro. Seu ombro reclama, a porta não. Ainda há a janela soterrada, do lado de fora.');
          }
        },
        {
          id: 'janela', rot: 'Entrar pela janela soterrada', re: /janela|soterrad|cavar|cavo|fora|buraco|espremer/,
          se: function (S) { return !S.f.criptaAberta; },
          veredito: function () { return { tipo: 'teste', per: 'acrobacia', cd: 10 }; },
          repetivel: true,
          fazer: function (S, r, h) {
            S.f.criptaAberta = 'janela';
            if (r.ok) out(S, 'narra', 'Você tira a terra com as mãos, se espreme pela abertura e desce pendurado, soltando o corpo sem barulho sobre o chão da cripta. Por dentro, você destrava a porta: o caminho de volta fica aberto.');
            else {
              S.f.barulho = true;
              var dn = rolarSoma(S, 'Queda de ' + h.nome, [{ n: 1, l: 4 }], 0, { sufixo: 'de concussão' });
              h.pv = Math.max(1, h.pv - dn);
              out(S, 'narra', 'A borda cede quando você está na metade. Você cai de mau jeito sobre a laje, com uma chuva de pedra e terra: ' + dn + ' de dano em ' + h.nome + '. PV ' + h.pv + '/' + h.pvMax + '. O barulho ecoa pela cripta. Por dentro, você destrava a porta.');
            }
            fato(S, 'Você entrou na cripta pela janela soterrada e destravou a porta por dentro.');
            desvio(S, 'entrar pela porta da cripta', 'você entrou pela janela soterrada.', 'a porta estava trancada e o caminho da história não pode travar.');
          }
        }
      ],
      topicos: [
        { re: /sino/, txt: function (S) { return 'O campanário está vazio. As marcas no chão mostram que o sino foi arrastado até a porta da cripta.' + (S.f.sabeSino ? ' Você sabe que ele chama os mortos enquanto soa.' : ''); } },
        { re: /porta|cripta|entrar|fechadura/, txt: function (S) { return S.f.criptaAberta ? 'A cripta está aberta.' : 'A porta da cripta está trancada. Caminhos possíveis: achar a chave, abrir a fechadura com ferramentas, forçar a porta ou entrar pela janela soterrada.'; } },
        { re: /ivo|sacristao|livia|filha|menina/, txt: function (S) { return S.f.segredo ? 'Pelo caderno: Ivo toca o sino para trazer de volta a filha, Lívia, enterrada na cripta.' : 'Alguém vive na sacristia há dias. Deve ser Ivo, mas ele não está aqui em cima.'; } }
      ],
      saidas: function (S) {
        return [
          { para: 'trilha', rot: 'Descer pela trilha', re: /trilha|vila|descer|desco|voltar|volto|estalagem/ },
          { para: 'cripta', rot: 'Descer à cripta', re: /cripta|descer a cripta|escada|degrau|baixo|entrar|entro/, bloqueio: S.f.criptaAberta ? null : 'A porta da cripta está trancada. Procure a chave, abra a fechadura, force a porta ou tente a janela soterrada.' }
        ];
      }
    },

    /* ---------------------------------------------------------------- 4. antecâmara */
    cripta: {
      nome: 'Antecâmara da Cripta', lugar: 'Debaixo da capela',
      desc: function (S) {
        if (criptaLimpa(S) || resolvido(S)) return 'Sala comprida de teto baixo, com nichos de ossadas nas paredes. Os mortos estão quietos. No fundo, um corredor estreito desce.';
        return 'Sala comprida de teto baixo, com nichos de ossadas nas paredes. Um esqueleto de pé no meio da sala e um corpo pesado que se arrasta no fundo.' + (S.f.passouFurtivo ? ' Eles não notaram você.' : '');
      },
      presentes: function (S) { return (criptaLimpa(S) || resolvido(S)) ? [] : S.inimigos.cripta.filter(function (e) { return e.vivo; }).map(function (e) { return e.nome + (e.tipo === 'zumbi' ? ' (lento, no fundo)' : ' (de sentinela)'); }); },
      seguro: function (S) { return criptaLimpa(S) || resolvido(S); },
      motivoInseguro: 'Os mortos da antecâmara ainda estão de pé.',
      entrar: function (S, o) {
        if (resolvido(S)) {
          S.inimigos.cripta.forEach(function (e) { e.vivo = false; });
          if (!o.calado) out(S, 'narra', 'A antecâmara está parada. Os mortos voltaram a ser só mortos.');
          return;
        }
        if (criptaLimpa(S)) { if (!o.calado) out(S, 'narra', 'A antecâmara está quieta, com os ossos espalhados onde caíram. O corredor do fundo desce para a batida do sino.'); return; }
        if (S.f.passouFurtivo) { out(S, 'narra', 'Você volta à antecâmara colado à parede. O esqueleto e o zumbi continuam no mesmo vaivém, sem notar você.'); return; }
        if (S.f.mortosAlerta || S.f.barulho) {
          out(S, 'narra', S.f.mortosAlerta ? 'Os mortos da antecâmara se viram assim que seu pé toca o último degrau.' : 'O barulho da sua entrada acordou a sala. Um esqueleto já vem na sua direção com uma espada curta, e no fundo algo mais pesado começa a se arrastar.');
          iniciarCombate(S, 'cripta', S.f.mortosAlerta ? {} : { ini: 'desvantagem' });
          return;
        }
        out(S, 'narra', 'Os degraus terminam numa sala comprida de teto baixo. Nichos nas paredes, cheios de ossadas arrumadas com capricho. Alguns nichos estão vazios.\n\nNo meio da sala, de costas para você, um esqueleto de pé, com uma espada curta enferrujada, balançando no ritmo da batida que vem do fundo. Mais longe, um corpo inchado se arrasta de uma parede à outra.\n\n' + (S.inimigos.cripta.length > 2 ? 'E não são só esses: outros vultos se mexem entre os nichos.\n\n' : '') + 'Eles ainda não notaram ninguém. Dá para atacar primeiro ou tentar passar rente à parede até o corredor.');
        fato(S, 'O sino levantou mortos na antecâmara da cripta: esqueletos e zumbis.');
      },
      acoes: [
        {
          id: 'atacar_mortos', rot: 'Atacar os mortos-vivos', re: /atac|ataq|luto|lutar|destru|golpe|flech|atir|mato|matar|invest/,
          se: function (S) { return !criptaLimpa(S) && !resolvido(S); },
          fazer: function (S) {
            out(S, 'narra', 'Você avança antes que o esqueleto termine de se virar.');
            iniciarCombate(S, 'cripta', { ini: 'vantagem' });
          }
        },
        {
          id: 'esgueirar_mortos', rot: 'Passar rente à parede, em silêncio', re: /esgueir|furtiv|silencio|parede|passar|escond|sorrateir|contorn/,
          se: function (S) { return !criptaLimpa(S) && !S.f.passouFurtivo && !resolvido(S); },
          veredito: function () { return { tipo: 'teste', per: 'furtividade', cd: 13, grupo: true }; },
          fazer: function (S, r) {
            if (r.ok) {
              S.f.passouFurtivo = true;
              out(S, 'narra', 'Você cola as costas na parede e anda no intervalo entre uma batida e outra. O esqueleto vira a cabeça uma vez, para o lado errado. Você chega à boca do corredor.');
              fato(S, 'Você atravessou a antecâmara sem acordar a atenção dos mortos.');
              desvio(S, 'combate contra os mortos-vivos da antecâmara', 'você passou por eles em silêncio.', 'escolha do jogador, com sucesso em Furtividade.');
            } else {
              out(S, 'narra', 'Sua bota acha um fêmur solto. O estalo é pequeno e é o bastante: o esqueleto gira inteiro na sua direção.');
              iniciarCombate(S, 'cripta', {});
            }
          }
        },
        {
          id: 'revistar_nichos', rot: 'Revistar os nichos', re: /nicho|revist|vasculh|procur|ossada|examin/,
          se: function (S) { return criptaLimpa(S) && !S.f.revistouNichos; },
          veredito: function () { return { tipo: 'teste', per: 'investigacao', cd: 10 }; },
          fazer: function (S, r) {
            S.f.revistouNichos = true;
            if (r.ok) { S.ouro += 12; out(S, 'narra', 'A maioria dos mortos foi enterrada com as mãos vazias. Mas o terceiro nicho está limpo, forrado com um cobertor de criança, e vazio. No nicho ao lado, esquecida, uma bolsinha com 12 peças de ouro.'); fato(S, 'O terceiro nicho da antecâmara está forrado com um cobertor de criança e vazio.'); }
            else out(S, 'narra', 'Ossos, pano podre e pó. Você não encontra nada de valor, só repara que um dos nichos está vazio e mais limpo que os outros.');
          }
        }
      ],
      topicos: [
        { re: /esqueleto|zumbi|morto/, txt: function (S) { return criptaLimpa(S) ? 'Os mortos desta sala não se levantam mais.' : 'Um esqueleto com espada curta, rápido, e um zumbi lento e resistente. Esqueletos quebram fácil com golpes de concussão.'; } },
        { re: /corredor|fundo|sino|batida/, txt: function () { return 'O corredor do fundo desce. A batida do sino vem de lá.'; } }
      ],
      saidas: function (S) {
        var livre = criptaLimpa(S) || S.f.passouFurtivo || resolvido(S);
        return [
          { para: 'capela', rot: 'Subir de volta à capela', re: /capela|subir|subo|voltar|volto|escada|sair|saio/ },
          { para: 'camara', rot: 'Seguir pelo corredor do fundo', re: /corredor|fundo|seguir|sigo|camara|sino|adiante|frente|descer|desco/, bloqueio: livre ? null : 'O esqueleto e o zumbi estão entre você e o corredor. É preciso derrotá-los ou passar sem ser notado.' }
        ];
      }
    },

    /* ---------------------------------------------------------------- 5. câmara do sino */
    camara: {
      nome: 'Câmara do Sino', lugar: 'Fundo da cripta',
      desc: function (S) {
        if (resolvido(S)) return 'Câmara redonda. O sino de pedra ' + (S.f.sino === 'quebrado' ? 'está em pedaços no chão' : S.f.sino === 'levado' ? 'foi embrulhado para a viagem' : S.f.sino === 'selado' ? 'está travado com vigas e correntes' : 'pende do cavalete, parado') + '. No banco, a figura pequena coberta por um xale.' + (S.f.ivo !== 'morto' ? ' Ivo está sentado no chão, de cabeça baixa.' : '');
        return 'Câmara redonda. No centro, suspenso num cavalete de vigas, o sino de pedra. Ivo segura a corda. Ao lado dele, num banco, uma figura pequena coberta por um xale. Um morto grande monta guarda entre você e eles.';
      },
      presentes: function (S) {
        if (resolvido(S)) return S.f.ivo === 'morto' ? [] : ['Ivo, o sacristão'];
        return ['Ivo, o sacristão, junto ao sino', 'Um morto-vivo de guarda'];
      },
      seguro: function (S) { return resolvido(S); },
      motivoInseguro: 'Ivo e o guardião estão bem ali.',
      entrar: function (S, o) {
        if (resolvido(S)) { if (!o.calado) out(S, 'narra', 'A câmara do sino está em silêncio.'); return; }
        if (!S.f.armadilha) {
          S.f.armadilha = true;
          out(S, 'narra', 'O corredor é estreito, de laje irregular, e desce em curva.');
          out(S, 'veredito', 'O mestre pede um teste de Percepção (Sabedoria), CD 13 · médio.');
          var hp = melhor(S, 'percepcao'), ht = ativos(S)[0];
          var r = teste(S, 'Percepção de ' + hp.nome, bonusPericia(hp, 'percepcao'), null, 13, hp);
          if (r.ok) {
            out(S, 'narra', 'Uma das lajes está um dedo mais alta que as outras, e limpa demais. Você passa por cima dela com um passo largo. Na parede, na altura do peito, três furos escuros esperavam por você.');
            fato(S, hp.nome + ' notou e evitou a armadilha de dardos no corredor da cripta.');
          } else {
            out(S, 'narra', 'Uma laje afunda debaixo da sua bota com um clique.');
            var sv = d20(S, 'Salvaguarda de Destreza de ' + ht.nome, bonusSalv(ht, 'des'), null, 12, 'CD', ht);
            fecharD20(S, sv, sv.total >= 12);
            if (sv.total >= 12) { out(S, 'narra', 'Você se joga para a frente e três dardos enferrujados passam pelas suas costas e se quebram na parede oposta.'); fato(S, ht.nome + ' disparou a armadilha de dardos do corredor, mas escapou ileso.'); }
            else {
              var dn = rolarSoma(S, 'Dardos', [{ n: 1, l: 4 }], 0, { sufixo: 'perfurante' });
              ht.pv = Math.max(1, ht.pv - dn);
              out(S, 'narra', 'Dardos velhos saem da parede e um deles acha o braço de ' + ht.nome + ': ' + dn + ' de dano. PV ' + ht.pv + '/' + ht.pvMax + '.');
              fato(S, 'A armadilha de dardos do corredor feriu ' + ht.nome + '.');
            }
          }
        }
        if (S.f.ivoAlerta) {
          out(S, 'narra', 'Ivo já está com a corda na mão quando você aparece. “Eu avisei”, ele diz, e o sino bate.');
          iniciarCombate(S, 'camara', {});
          return;
        }
        if (S.f.viuCamara) { out(S, 'narra', 'Ivo continua junto ao sino, com a corda enrolada no pulso, olhando para você sem piscar.'); return; }
        S.f.viuCamara = true;
        out(S, 'narra', 'O corredor se abre numa câmara redonda, iluminada por uma lamparina no chão. No centro, suspenso num cavalete de vigas novas, o sino de pedra cinzenta, largo como uma mesa.\n\nUm homem magro, de mãos enfaixadas, segura a corda. Ao lado dele, sentada num banco, uma figura pequena coberta por um xale, imóvel. Entre você e os dois, um morto grande, de mortalha, parado como um móvel.\n\n“Não chegue perto”, diz o homem, baixo, como quem tem medo de acordar alguém. “Ela está quase acordando. Mais umas noites. Desça o morro e diga que não achou nada.”');
        fato(S, 'Você encontrou Ivo vivo na câmara do sino. É ele quem toca o sino de pedra.');
      },
      acoes: [
        {
          id: 'convencer_ivo', rot: 'Convencer Ivo a soltar a corda', re: /convenc|persuad|argument|pedir|peco|apel|razao|solt|parar|pare|consol|ajud/,
          se: function (S) { return !resolvido(S); },
          veredito: function (S) { return { tipo: 'teste', per: 'persuasao', cd: 15, modo: S.f.segredo ? 'vantagem' : null, porque: 'você leu o caderno e sabe de Lívia' }; },
          fazer: function (S, r) {
            if (r.ok) {
              var sabia = !!S.f.segredo;
              S.f.ivo = 'convencido'; S.f.resolvido = true; S.f.segredo = true;
              S.inimigos.camara.forEach(function (e) { if (e.tipo !== 'ivo') e.vivo = false; });
              out(S, 'narra', (sabia ? 'Você diz o nome dela. Lívia. ' : 'Você fala devagar, sem dar um passo. ') + 'Diz o que ele já sabe e não aguenta saber: que os olhos se abrem e não olham, que o que o sino levanta é só o que sobrou. Que ela merece dormir.\n\nIvo escuta com a corda tremendo na mão. Olha para a figura no banco por um tempo comprido. Depois abre os dedos.\n\nA corda cai. O sino dá uma última meia batida e para. O morto de mortalha desaba como roupa largada. Debaixo do xale, nada se mexe.\n\n“Eu só queria ouvir a voz dela mais uma vez”, diz Ivo. É a filha dele, Lívia, morta no inverno.');
              fato(S, 'Você convenceu Ivo a soltar a corda. O sino parou sem que ninguém fosse ferido.');
              if (!sabia) fato(S, 'Segredo descoberto: Ivo tocava o sino para trazer de volta a filha morta, Lívia.');
              desvio(S, 'combate final contra Ivo e o guardião', 'você resolveu a cena pela conversa.', 'escolha do jogador, com sucesso em Persuasão.');
              checkpoint(S);
            } else {
              out(S, 'narra', 'Por um instante parece que ele escuta. Depois o rosto se fecha. “Você não viu os olhos dela se abrirem. Eu vi.” Ele puxa a corda com as duas mãos, e o morto de mortalha dá o primeiro passo.');
              iniciarCombate(S, 'camara', {});
            }
          }
        },
        {
          id: 'intimidar_ivo', rot: 'Ameaçar Ivo', re: /intimid|ameac|assust|amedront|grit|orden/,
          se: function (S) { return !resolvido(S); },
          veredito: function () { return { tipo: 'teste', per: 'intimidacao', cd: 15 }; },
          fazer: function (S, r) {
            if (r.ok) {
              S.f.ivo = 'rendido'; S.f.resolvido = true;
              S.inimigos.camara.forEach(function (e) { if (e.tipo !== 'ivo') e.vivo = false; });
              out(S, 'narra', 'Você diz, sem levantar a voz, o que vai fazer com o sino, com o guardião e com ele, nessa ordem. Ivo é um sacristão, não um soldado. As mãos enfaixadas se abrem sozinhas.\n\nA corda cai, o sino para, e o morto de mortalha desaba. Ivo se encolhe ao lado do banco, entre você e a figura pequena debaixo do xale, como se ainda houvesse algo ali para proteger.');
              fato(S, 'Você intimidou Ivo, que largou a corda e se rendeu. O sino parou.');
              desvio(S, 'combate final contra Ivo e o guardião', 'você fez Ivo se render pelo medo.', 'escolha do jogador, com sucesso em Intimidação.');
              checkpoint(S);
            } else {
              out(S, 'narra', '“Já perdi tudo o que dava para perder”, responde Ivo, quase com pena de você. E puxa a corda.');
              iniciarCombate(S, 'camara', {});
            }
          }
        },
        {
          id: 'falar_ivo', rot: 'Perguntar a Ivo o que ele está fazendo', re: /fal|convers|pergunt|ivo|sacristao|quem|por que|ouvir|escut/,
          se: function (S) { return !resolvido(S); },
          fazer: function (S) {
            if (S.f.falouIvo) { out(S, 'narra', 'Ivo não responde mais. Só aperta a corda e olha para o banco.'); return; }
            S.f.falouIvo = true;
            out(S, 'narra', '“O que qualquer pai faria”, diz Ivo, sem tirar os olhos do banco. “O sino chama. Ela ouviu. Abriu os olhos na primeira noite.” Ele engole em seco. “Os outros também levantam, eu sei. Não fazem mal a quem fica longe. Vá embora.”');
            fato(S, 'Ivo diz que o sino “chama” e que “ela” abriu os olhos. Ele fala como pai.');
          }
        },
        {
          id: 'atacar_ivo', rot: 'Atacar', re: /atac|ataq|luto|lutar|golpe|flech|atir|mato|matar|invest|avanc/,
          se: function (S) { return !resolvido(S); },
          fazer: function (S) {
            out(S, 'narra', 'Você avança. Ivo grita alguma coisa que não é para você e puxa a corda com o peso do corpo.');
            iniciarCombate(S, 'camara', { ini: null });
          }
        },
        {
          id: 'ouvir_ivo', rot: 'Ouvir o que Ivo tem a dizer', re: /fal|convers|pergunt|ivo|sacristao|ouvir|escut|por que/,
          se: function (S) { return resolvido(S) && S.f.ivo !== 'morto' && !S.f.ouviuIvo; },
          fazer: function (S) {
            S.f.ouviuIvo = true; var novo = !S.f.segredo; S.f.segredo = true;
            out(S, 'narra', 'Ivo fala olhando para as próprias mãos. A filha, Lívia, nove anos, levada pela febre do inverno. O livro de registros da capela, que explicava por que o sino foi feito mudo. A primeira noite, quando ela abriu os olhos. As esmolas pagas aos goblins para ninguém subir.\n\n“Ela não me olhou nenhuma vez”, ele diz. “Eu sabia. Toquei assim mesmo.”');
            if (novo) fato(S, 'Segredo descoberto: Ivo tocava o sino de pedra para trazer de volta a filha morta, Lívia.');
          }
        },
        {
          id: 'examinar_figura', rot: 'Olhar a figura no banco', re: /figura|banco|xale|menina|crianca|livia|corpo|olh|examin/,
          se: function (S) { return resolvido(S) && !S.f.viuLivia; },
          fazer: function (S) {
            S.f.viuLivia = true;
            out(S, 'narra', 'Você não levanta o xale. Não precisa. É uma criança, enterrada há meses e vestida de novo com cuidado. Seja o que for que o sino tenha movido nela, não era ela.');
            fato(S, 'A figura no banco é o corpo de uma criança, desenterrado e vestido com cuidado.');
          }
        },
        {
          id: 'quebrar_sino', rot: 'Quebrar o sino de pedra', re: /quebr|destru|despedac|marret|partir o sino|arrebent/,
          se: function (S) { return resolvido(S) && !S.f.sino; },
          fazer: function (S) {
            S.f.sino = 'quebrado';
            out(S, 'narra', 'A marreta que Ivo usou para montar o cavalete está encostada na parede. São sete golpes. No sétimo, o sino racha de alto a baixo e cai em três pedaços, com um som de pedra comum.');
            fato(S, 'Você quebrou o sino de pedra. Ele nunca mais vai soar.');
          }
        },
        {
          id: 'selar_sino', rot: 'Travar o sino e selar a câmara', re: /selar|selo|trav|trancar|acorrent|deixar o sino|fechar a camara|enterr/,
          se: function (S) { return resolvido(S) && !S.f.sino; },
          fazer: function (S) {
            S.f.sino = 'selado';
            out(S, 'narra', 'Você cunha o sino com as vigas do cavalete, passa a corrente da lamparina pelo badalo e corta a corda rente. Inteiro, mas mudo, como os que o fizeram queriam.');
            fato(S, 'Você travou o sino de pedra e o deixou na cripta, mudo e inteiro.');
          }
        },
        {
          id: 'levar_sino', rot: 'Levar o badalo do sino para a vila', re: /levar|levo|carreg|badalo|guardar|ficar com/,
          se: function (S) { return resolvido(S) && !S.f.sino; },
          fazer: function (S) {
            S.f.sino = 'levado';
            out(S, 'narra', 'O sino pesa mais que três homens, mas o badalo de pedra sai do gancho com esforço. Sem ele, o sino é só um vaso virado. Você o embrulha no cobertor e amarra às costas. É frio mesmo através do pano.');
            fato(S, 'Você retirou o badalo do sino de pedra e o levou consigo.');
          }
        }
      ],
      topicos: [
        { re: /sino|abaf/, txt: function (S) { return resolvido(S) ? 'O sino está parado. O destino dele é decisão sua.' : 'O sino está junto de Ivo, no centro da câmara.' + (S.f.sabeSino ? ' Você sabe que abafá-lo quebra o chamado na hora: os mortos cairiam.' : ''); } },
        { re: /ivo|sacristao/, txt: function (S) { return resolvido(S) ? (S.f.ivo === 'morto' ? 'Ivo está morto.' : 'Ivo não oferece mais resistência.') : 'Magro, exausto, de mãos enfaixadas. Não parece um combatente, mas não larga a corda.'; } },
        { re: /figura|banco|xale|menina|livia|filha/, txt: function (S) { return S.f.segredo ? 'É Lívia, a filha de Ivo, morta no inverno.' : 'Pequena, coberta por um xale, imóvel. Daqui não dá para saber mais.'; } }
      ],
      saidas: function (S) {
        var s = [{ para: 'cripta', rot: 'Voltar pelo corredor', re: /corredor|voltar|volto|antecamara|cripta|recuar|recuo|sair|saio/ }];
        if (resolvido(S)) s.unshift({ para: 'estalagem', rot: 'Voltar para Pedra-Funda', re: /vila|pedra funda|estalagem|marga|descer o morro|ir embora|vou embora/ });
        return s;
      }
    }
  };

  function bentoConta(S) {
    S.f.sabeTrilha = true;
    out(S, 'narra', '“Goblins. Um bando pequeno, pelo rastro. Ficam de tocaia no trecho das pedras grandes, logo depois da segunda curva. Quem sobe olhando para o chão não vê.” Ele aponta com o queixo. “Tem um caminho por cima do barranco, pelas raízes. Dá para passar sem que eles saibam.”');
    fato(S, 'Bento contou que goblins emboscam o trecho das pedras e que há um caminho por cima do barranco.');
  }
  function acordoGoblins(S) {
    S.f.goblins = 'acordo'; S.f.pistaMoedas = true;
    out(S, 'narra', 'Antes de sumir no mato, o maior aponta para o alto do morro e mostra um cobre com um sino cunhado. “Homem do sino dá moeda. Nós espanta gente. Homem do sino lá embaixo da casa de pedra.” E os dois desaparecem.');
    fato(S, 'Os goblins foram embora sem luta. Disseram que o “homem do sino” os pagava para espantar quem subisse.');
    desvio(S, 'combate contra os goblins na trilha', 'você resolveu a emboscada na conversa.', 'escolha do jogador, com sucesso no teste.');
  }

  function epilogoMalvisto(S) {
    var f = S.f, p = [];
    p.push('Você desce o morro com o trabalho feito e ninguém para ouvir.');
    if (f.sino === 'levado') p.push('O badalo de pedra pesa na sua bolsa. Não há a quem entregá-lo.');
    p.push('À meia-noite, Pedra-Funda fica acordada de ouvido no morro, atrás de portas trancadas. O sino não toca. A vila entende o que isso quer dizer, e entende também quem foi.');
    p.push('Ninguém conta moedas em cima de balcão nenhum. Você atravessa a rua de janelas fechadas e toma a estrada debaixo de chuva. O que aconteceu na estalagem vai chegar à próxima vila antes de você.');
    out(S, 'narra', p.join('\n\n'));
    fato(S, 'O sino de Pedra-Funda não toca mais. Ninguém pagou pelo serviço, e a vila não quer ver você de novo.');
    S.fim = { tipo: 'vitoria' };
    out(S, 'titulo', 'Fim da aventura');
    out(S, 'sistema', resumo(S));
  }
  function epilogo(S) {
    var f = S.f, p = [];
    p.push('Você conta. A sala escuta sem interromper.');
    if (f.ivo === 'convencido') p.push('Ivo desceu a trilha ao seu lado, carregando Lívia nos braços, embrulhada no xale. Ninguém na sala o acusa de nada. Duas mulheres se levantam e vão buscar pás: a menina vai ser enterrada de novo ao amanhecer, desta vez com a vila inteira presente.');
    else if (f.ivo === 'rendido') p.push('Ivo veio com você, de mãos amarradas e sem dizer palavra. Dona Marga olha para ele por muito tempo. “A vila decide o que fazer contigo amanhã”, diz por fim. “Hoje você come e dorme.” Ninguém discorda.');
    else p.push('Quando você diz que Ivo não vai descer, Dona Marga fecha os olhos. Bento tira o gorro. Alguém no fundo da sala começa a chorar baixo e para.');
    if (f.segredo) p.push('Você conta de Lívia. Marga faz que sim com a cabeça, devagar, como quem soma uma conta que já desconfiava. “A gente devia ter subido para ver como ele estava. No inverno. Não agora.”');
    else p.push('O que ninguém entende, nem você, é por que um homem quieto como Ivo faria aquilo. Marga pergunta. Você não tem o que responder.');
    if (f.sino === 'quebrado') p.push('À meia-noite, a vila inteira está acordada, de ouvido no morro. A hora passa em silêncio. Alguém ri de nervoso. Depois, aos poucos, as pessoas vão para casa.');
    else if (f.sino === 'selado') p.push('À meia-noite, a vila inteira está acordada, de ouvido no morro. Silêncio. O sino continua lá em cima, travado e mudo, e Marga promete mandar murar a porta da cripta antes do próximo inverno.');
    else if (f.sino === 'levado') p.push('Você põe o badalo de pedra em cima do balcão. Ninguém quer tocar nele. Marga o tranca no porão, embrulhado em cobertores. À meia-noite, silêncio no morro. Ela não gosta de ter aquilo em casa. Você também não tem certeza.');
    else p.push('À meia-noite, silêncio no morro. Mas o sino ficou lá em cima, inteiro, com a corda no lugar, e você dorme mal pensando em quem pode achá-lo.');
    S.ouro += 30;
    p.push('Dona Marga conta trinta peças de ouro em cima do balcão, uma por uma, e empurra na sua direção. “Cama e comida enquanto quiser ficar”, diz. “Pedra-Funda não esquece.”');
    out(S, 'narra', p.join('\n\n'));
    fato(S, 'Você recebeu as 30 po prometidas. O sino de Pedra-Funda não toca mais.');
    S.fim = { tipo: 'vitoria' };
    out(S, 'titulo', 'Fim da aventura');
    out(S, 'sistema', resumo(S));
  }
