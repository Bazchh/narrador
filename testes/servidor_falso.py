# Servidor de mentira, só para testar o encaixe "servidor próprio". Guarda tudo na memória.
import json, sys, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
D = {'mesas': {}, 'ponto': {}, 'indice': {}, 'elenco': {}, 'trava': {}, 'pedidos': [], 'erro_ia': 0, 'soleitura': set()}
L = threading.Lock()
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def manda(self, cod, obj=None):
        self.send_response(cod)
        self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Cronica-Quem'); self.send_header('Access-Control-Allow-Methods', 'GET, PUT, POST, OPTIONS')
        b = b'' if obj is None else json.dumps(obj).encode()
        if obj is not None: self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def corpo(self):
        n = int(self.headers.get('Content-Length') or 0); return json.loads(self.rfile.read(n) or b'null')
    def do_OPTIONS(self): self.manda(204)
    def rota(self, metodo):
        u = urlparse(self.path); p = [x for x in u.path.split('/') if x]; quem = self.headers.get('X-Cronica-Quem') or ''
        with L:
            if p == ['estado']: return self.manda(200, {'mestre': True, 'mesas': True})
            if p == ['_teste'] and metodo == 'POST':
                c = self.corpo(); D['erro_ia'] = c.get('erro_ia', D['erro_ia'])
                if 'soleitura' in c: D['soleitura'].add(c['soleitura'])
                return self.manda(200, {'pedidos': len(D['pedidos']), 'ultimo': D['pedidos'][-1] if D['pedidos'] else None})
            if p == ['mestre'] and metodo == 'POST':
                c = self.corpo(); D['pedidos'].append(c.get('pedido'))
                if D['erro_ia']: return self.manda(D['erro_ia'], {'erro': 'x'})
                return self.manda(200, {'tipo': 'improviso', 'veredito': 'teste', 'pericia': 'atuacao', 'cd': 10, 'sucesso': 'A sala relaxa um pouco.', 'falha': 'Ninguém repara.', 'fato': 'Alguém assobiou na estalagem.'})
            if metodo == 'PUT' and quem in D['soleitura']: return self.manda(403, {'erro': 'sem permissão'})
            if len(p) == 2 and p[0] in ('mesas', 'elenco', 'indice'):
                if metodo == 'GET': return self.manda(200, D[p[0]][p[1]]) if p[1] in D[p[0]] else self.manda(404)
                if metodo == 'PUT': D[p[0]][p[1]] = self.corpo(); return self.manda(204)
            if p == ['indice'] and metodo == 'GET':
                n = int(parse_qs(u.query).get('n', ['30'])[0]); return self.manda(200, [{'id': k, 'dado': v} for k, v in list(D['indice'].items())[:n]])
            if len(p) == 3 and p[0] == 'mesas' and p[2] == 'ponto':
                if metodo == 'GET': return self.manda(200, D['ponto'][p[1]]) if p[1] in D['ponto'] else self.manda(404)
                if metodo == 'PUT': D['ponto'][p[1]] = self.corpo(); return self.manda(204)
            if len(p) == 3 and p[0] == 'mesas' and p[2] == 'trava' and metodo == 'POST':
                c = self.corpo(); t = D['trava'].get(p[1]); agora = time.time() * 1000
                if t and t['ate'] > agora and t['quem'] != c.get('quem'): return self.manda(200, {'livre': False})
                D['trava'][p[1]] = {'quem': c.get('quem'), 'ate': agora + max(1000, c.get('ms') or 2500)}; return self.manda(200, {'livre': True})
        self.manda(404)
    def do_GET(self): self.rota('GET')
    def do_PUT(self): self.rota('PUT')
    def do_POST(self): self.rota('POST')
if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv) > 1 else 8791), H).serve_forever()
