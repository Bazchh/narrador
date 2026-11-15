  /* ---------------- ligações e partida ---------------- */
  $('entrada').addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (!M || ocupado) return;
    var t = $('texto').value;
    if (!t.trim()) return;
    $('texto').value = '';
    enviar(t);
  });
  $('modo').addEventListener('change', mostrarModo);
  var abasEl = document.querySelectorAll('.aba[data-aba]');
  for (var ia = 0; ia < abasEl.length; ia++) abasEl[ia].addEventListener('click', function () { abrirAba(this.getAttribute('data-aba')); });
  $('btn-painel').addEventListener('click', function () { abrirAba(aba); });
  $('btn-fechar-painel').addEventListener('click', function () { document.body.classList.remove('painel-aberto'); });
  $('btn-sair').addEventListener('click', function () { irPara('jogar'); });
  $('btn-ficha').addEventListener('click', function () { if (M) abrirFicha(heroiDaFicha(), M.S); });
  $('btn-fechar-modal').addEventListener('click', fecharFicha);
  $('modal').addEventListener('click', function (ev) { if (ev.target === $('modal')) fecharFicha(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && !$('modal').hidden) fecharFicha(); });
  $('btn-mapa').addEventListener('click', function () { prefs.mapa = prefs.mapa === false; gravar(K_PREFS, prefs); desenharMapa(); });
  $('dados').addEventListener('click', fecharDados);
  window.addEventListener('resize', function () { if (M && rotaDesenhada === 'mesa') desenharMapa(); });
  window.addEventListener('hashchange', function () { fecharFicha(); });
  window.addEventListener('hashchange', desenharRota);

  desenharRota();
  carregarCapacidades();
