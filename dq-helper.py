# -*- coding: utf-8 -*-
"""
DQ魔法エフェクトカメラ 会議終了ヘルパー（Windows専用・標準ライブラリのみ）

エフェクトページ(index.html)の会議モードから
  http://localhost:8124/cast?spell=madante
を受け取り、Zoomミーティングを「全員に対して会議を終了」する。

使い方: start-helper.bat をダブルクリック（または python dq-helper.py）
"""
import ctypes
import json
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---------------- 設定 ----------------
PORT = 8124
TARGET = 'zoom'            # 'zoom'=全員に対して終了(ホスト時) / 'teams'=退出 / 'kill'=プロセス強制終了
KILL_SPELLS = {'madante'}  # このじゅもんのときだけ会議を終了する（他の呪文は演出のみ）
KILL_DELAY_S = 0.2         # 爆発ピークから終了までの間(秒)
# --------------------------------------

user32 = ctypes.windll.user32
VK_MENU, VK_CONTROL, VK_SHIFT, VK_RETURN = 0x12, 0x11, 0x10, 0x0D
KEYUP = 0x0002


def log(msg):
    print(time.strftime('[%H:%M:%S] ') + msg, flush=True)


def key_down(vk):
    user32.keybd_event(vk, 0, 0, 0)


def key_up(vk):
    user32.keybd_event(vk, 0, KEYUP, 0)


def tap(vk):
    key_down(vk)
    time.sleep(0.04)
    key_up(vk)


def combo(mods, vk):
    for m in mods:
        key_down(m)
        time.sleep(0.05)
    tap(vk)
    time.sleep(0.05)
    for m in reversed(mods):
        key_up(m)


def list_windows():
    wins = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(h, _):
        if user32.IsWindowVisible(h):
            n = user32.GetWindowTextLengthW(h)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(h, buf, n + 1)
                wins.append((h, buf.value))
        return True

    user32.EnumWindows(proc(cb), 0)
    return wins


def find_window(keyword_sets):
    """優先度順のキーワード集合でウィンドウを探す"""
    wins = list_windows()
    for kw_set in keyword_sets:
        for h, t in wins:
            if all(k.lower() in t.lower() for k in kw_set):
                return h, t
    return 0, ''


ZOOM_KEYWORDS = [('zoom', 'ミーティング'), ('zoom', 'meeting'), ('zoom',)]
TEAMS_KEYWORDS = [('microsoft teams',), ('teams',)]


def focus(hwnd):
    # フォアグラウンド奪取制限の回避にALTを一瞬押してからアクティブ化する
    key_down(VK_MENU)
    key_up(VK_MENU)
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.35)


def end_zoom():
    hwnd, title = find_window(ZOOM_KEYWORDS)
    if not hwnd:
        log('Zoomウィンドウが見つかりません → taskkillにフォールバック')
        subprocess.run(['taskkill', '/IM', 'Zoom.exe', '/F'], capture_output=True)
        return
    log(f'Zoomウィンドウ「{title}」→ Alt+Q → Enter（全員に対して会議を終了）')
    focus(hwnd)
    combo([VK_MENU], 0x51)   # Alt+Q: 終了ダイアログを開く
    time.sleep(0.7)
    tap(VK_RETURN)           # 既定ボタン = ホスト時「全員に対して会議を終了」


def end_teams():
    hwnd, title = find_window(TEAMS_KEYWORDS)
    if not hwnd:
        log('Teamsウィンドウが見つかりません')
        return
    log(f'Teams「{title}」→ Ctrl+Shift+H（退出）')
    focus(hwnd)
    combo([VK_CONTROL, VK_SHIFT], 0x48)


def end_kill():
    for exe in ('Zoom.exe', 'Teams.exe', 'ms-teams.exe'):
        subprocess.run(['taskkill', '/IM', exe, '/F'], capture_output=True)
    log('会議アプリをtaskkillしました')


ACTIONS = {'zoom': end_zoom, 'teams': end_teams, 'kill': end_kill}


def do_cast(spell):
    if spell not in KILL_SPELLS:
        log(f'{spell} 発動（会議終了の対象外なので何もしません）')
        return
    log(f'{spell} 発動!! {KILL_DELAY_S}秒後に会議を終了します')
    time.sleep(KILL_DELAY_S)
    ACTIONS.get(TARGET, end_zoom)()


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/health':
            kw = ZOOM_KEYWORDS if TARGET == 'zoom' else TEAMS_KEYWORDS
            hwnd, title = find_window(kw)
            self._send({'ok': True, 'target': TARGET,
                        'window': title if hwnd else '(会議ウィンドウ未検出)'})
        elif u.path == '/cast':
            spell = (parse_qs(u.query).get('spell') or ['?'])[0]
            threading.Thread(target=do_cast, args=(spell,), daemon=True).start()
            self._send({'ok': True, 'spell': spell})
        else:
            self._send({'ok': False}, 404)

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    log(f'会議終了ヘルパー起動: http://localhost:{PORT} (target={TARGET}, 対象呪文={sorted(KILL_SPELLS)})')
    log('エフェクトページの「会議モード」をONにすると接続されます。Ctrl+Cで終了')
    HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
