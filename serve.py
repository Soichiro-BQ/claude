#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合宿レク 同期サーバー — 別PCから投影するためのLANサーバー

操作PCでこのスクリプトを起動すると、同じWi-Fi上の別PC（投影PC）と
リアルタイムで得点・シーンが同期されます。Python標準ライブラリのみ使用。

使い方:
  Mac    : start-server.command をダブルクリック（または `python3 serve.py`）
  Windows: start-server.bat をダブルクリック（または `python serve.py`）

起動後に表示されるURLを各PCのブラウザで開いてください。停止は Ctrl+C。
"""
import json
import os
import socket
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 8765
BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE, '.event-state.json')

cond = threading.Condition()
data = {'version': 0, 'state': None}

# 前回のイベント状態があれば復元（サーバー再起動しても得点が消えない）
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, encoding='utf-8') as f:
            loaded = json.load(f)
        if isinstance(loaded, dict) and 'version' in loaded:
            data = loaded
    except Exception:
        pass


def lan_ip():
    """LAN上でのこのPCのIPアドレスを取得（パケットは送信しない）"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


LAN = 'http://{}:{}'.format(lan_ip(), PORT)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def log_message(self, *args):  # アクセスログは出さない
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/api/state':
            q = parse_qs(u.query)
            try:
                since = int(q.get('since', ['-1'])[0])
            except ValueError:
                since = -1
            try:
                wait = float(q.get('wait', ['0'])[0])
            except ValueError:
                wait = 0
            deadline = time.time() + min(max(wait, 0), 30)
            with cond:
                # ロングポーリング：バージョンが進むかタイムアウトまで待つ
                while data['version'] <= since and time.time() < deadline:
                    cond.wait(max(0.05, deadline - time.time()))
                payload = {'version': data['version'], 'state': data['state'], 'lan': LAN}
            try:
                self._json(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path == '/api/state':
            try:
                n = int(self.headers.get('Content-Length', '0'))
                body = json.loads(self.rfile.read(n) or b'{}')
            except Exception:
                self._json({'error': 'bad json'}, 400)
                return
            with cond:
                data['version'] += 1
                data['state'] = body.get('state')
                cond.notify_all()
                snapshot = dict(data)
            try:
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(snapshot, f, ensure_ascii=False)
            except Exception:
                pass
            self._json({'version': snapshot['version']})
            return
        self._json({'error': 'not found'}, 404)


if __name__ == '__main__':
    print('=' * 58)
    print('  🏆 合宿レク 同期サーバー 起動しました')
    print('=' * 58)
    print('  🎮 操作用（このPCのブラウザで開く）:')
    print('       {}'.format(LAN))
    print('  📺 投影PC用（同じWi-Fiの別PCで開く → 自動で投影モード）:')
    print('       {}/#present'.format(LAN))
    print('-' * 58)
    print('  ※ 両方のPCを同じWi-Fi（またはスマホのテザリング）に接続')
    print('  ※ 停止するには Ctrl+C（このウィンドウは閉じずに置いておく）')
    print('=' * 58)
    try:
        ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print('\n停止しました')
