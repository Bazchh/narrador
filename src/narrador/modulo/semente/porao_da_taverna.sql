-- Semente da pasta de aventuras: a aventura original mínima do projeto, "O Porão da Taverna",
-- já no formato canônico, para testes automáticos e para o esqueleto ambulante (DC-09).
insert into aventura (id, titulo, origem_arquivo, impressao_digital, formato, edicao_informada)
values ('av-porao', 'O Porão da Taverna', 'semente/porao-da-taverna.md', 'sha256:semente-porao-v1', 'markdown', '2024');

-- Nasce como rascunho; é publicada no fim, depois de conferida (A03). Publicada, não muda mais.
insert into modulo_versao (aventura_id, versao, origem, publicada_em, impressao_texto)
values ('av-porao', 1, 'importado', null, 'sha256:semente-porao-v1');

insert into item_canonico (id, aventura_id, versao, tipo, nome, dados, pagina_origem) values
 ('cena-taverna',  'av-porao', 1, 'cena',   'A taverna ao anoitecer',
   '{"descricao":"Mesas vazias, um taverneiro nervoso e um alçapão trancado atrás do balcão.","objetivo":"descobrir o que faz barulho no porão"}', 1),
 ('cena-porao',    'av-porao', 1, 'cena',   'O porão',
   '{"descricao":"Escuro, úmido, barris roídos. Dois pares de olhos vermelhos.","encontro":["cri-rato-1","cri-rato-2"]}', 2),
 ('cena-tunel',    'av-porao', 1, 'cena',   'O túnel atrás dos barris',
   '{"descricao":"Um túnel recém-cavado leva ao esgoto. No chão, um anel de prata.","objetivo":"recuperar o anel do taverneiro"}', 2),
 ('loc-taverna',   'av-porao', 1, 'local',  'Taverna do Cavalo Manco', '{"zonas":["salão","balcão","alçapão"]}', 1),
 ('np-taverneiro', 'av-porao', 1, 'personagem', 'Taverneiro',
   '{"objetivo":"recuperar o anel sem admitir que o perdeu no jogo","sabe":["o barulho começou há três noites"],"atitude":"nervoso"}', 1),
 ('cri-rato-1',    'av-porao', 1, 'criatura', 'Rato gigante', '{"quantidade":1}', 2),
 ('cri-rato-2',    'av-porao', 1, 'criatura', 'Rato gigante', '{"quantidade":1}', 2),
 ('it-anel',       'av-porao', 1, 'item',   'Anel de prata do taverneiro', '{"valor_po":25}', 2),
 ('gancho-barulho','av-porao', 1, 'gancho', 'O barulho no porão', '{"texto":"O taverneiro oferece uma noite grátis a quem olhar o porão."}', 1);

insert into item_canonico (id, aventura_id, versao, tipo, nome, dados, pagina_origem, segredo, condicao_descoberta) values
 ('seg-anel', 'av-porao', 1, 'segredo', 'O taverneiro perdeu o anel apostando com o cavador do túnel',
   '{"texto":"O túnel foi cavado por um contrabandista que ganhou o anel no jogo e o deixou cair."}', 2, 1,
   'Persuadir ou intimidar o taverneiro, ou examinar as marcas de ferramenta no túnel');

insert into ligacao (aventura_id, versao, de_item, para_item, tipo, caminho_critico) values
 ('av-porao', 1, 'cena-taverna', 'cena-porao', 'leva_a', 1),
 ('av-porao', 1, 'cena-porao',   'cena-tunel', 'leva_a', 1),
 ('av-porao', 1, 'loc-taverna',  'cena-taverna', 'contem', 0),
 ('av-porao', 1, 'cena-taverna', 'np-taverneiro', 'contem', 0),
 ('av-porao', 1, 'cena-taverna', 'gancho-barulho', 'contem', 0),
 ('av-porao', 1, 'np-taverneiro','seg-anel', 'sabe_de', 0),
 ('av-porao', 1, 'cena-tunel',   'it-anel', 'contem', 0);

insert into mapeamento_srd (aventura_id, versao, item_id, srd_id, srd_versao) values
 ('av-porao', 1, 'cri-rato-1', 'srd:criatura:giant-rat', '5.2.1'),
 ('av-porao', 1, 'cri-rato-2', 'srd:criatura:giant-rat', '5.2.1');

-- Conferida: publica a versão 1.
update modulo_versao set publicada_em = strftime('%Y-%m-%dT%H:%M:%fZ','now') where aventura_id = 'av-porao' and versao = 1;
