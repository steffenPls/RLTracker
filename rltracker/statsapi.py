"""Verbindung zur offiziellen Rocket League Stats API (lokaler TCP-Socket).

Rocket League sendet JSON-Nachrichten der Form {"Event": ..., "Data": {...}}.
Dieser Client laeuft in einem eigenen Thread, verbindet sich automatisch neu
und legt jede Nachricht in eine Queue, die die Oberflaeche abholt.
"""
from __future__ import annotations

import base64
import codecs
import json
import os
import queue
import socket
import struct
import threading
import time

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 49123


class StreamDecoder:
    """Zerlegt einen TCP-Bytestrom in einzelne JSON-Objekte.

    Die API garantiert keine Zeilenumbrueche zwischen den Nachrichten, daher
    wird mit raw_decode Objekt fuer Objekt aus dem Puffer gelesen.
    """

    def __init__(self) -> None:
        self._buf = ""
        self._dec = json.JSONDecoder()

    def feed(self, chunk: str) -> list[dict]:
        buf = self._buf + chunk
        out: list[dict] = []
        pos, n = 0, len(buf)
        while True:
            # Fuellzeichen zwischen Nachrichten (Leerzeichen, Newlines, \0) ueberspringen
            while pos < n and buf[pos] not in "{[":
                pos += 1
            if pos >= n:
                break
            try:
                obj, pos2 = self._dec.raw_decode(buf, pos)
            except json.JSONDecodeError:
                # Nachricht noch unvollstaendig – auf mehr Daten warten.
                if n - pos > 5_000_000:  # Schutz gegen kaputten Datenstrom
                    pos = n
                break
            pos = pos2
            for msg in obj if isinstance(obj, list) else [obj]:
                norm = normalize_message(msg)
                if norm:
                    out.append(norm)
        self._buf = buf[pos:]
        return out


def normalize_message(msg) -> dict | None:
    if not isinstance(msg, dict):
        return None
    event = msg.get("Event") or msg.get("event")
    data = msg.get("Data", msg.get("data", {}))
    if isinstance(data, str):  # manche Relays senden Data als JSON-String
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            data = {"raw": data}
    if not event:
        return None
    return {"Event": event, "Data": data or {}}


class StatsApiClient(threading.Thread):
    """Hintergrund-Thread: haelt die Verbindung und fuellt self.events.

    Probiert nacheinander mehrere Wege, weil Rocket League je nach Einstellung
    nur auf IPv4, nur auf IPv6 oder nur per WebSocket (WebPort) lauscht.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, web_port: int = 49124) -> None:
        super().__init__(daemon=True, name="RLStatsApiClient")
        self.host = host
        self.port = port
        self.web_port = web_port
        self.events: "queue.Queue[dict]" = queue.Queue()
        self.status: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self._stop_evt = threading.Event()
        self.connected = False
        self.endpoint = ""
        self.last_errors: dict[str, str] = {}

    def endpoints(self) -> list[tuple[str, str, int]]:
        eps = [("tcp", self.host, self.port)]
        if self.host in ("127.0.0.1", "localhost"):
            eps.append(("tcp", "::1", self.port))
        if self.web_port:
            eps.append(("ws", self.host, self.web_port))
        return eps

    def stop(self) -> None:
        self._stop_evt.set()

    def _set_status(self, state: str, text: str) -> None:
        self.status.put((state, text))

    def run(self) -> None:
        attempt = 0
        while not self._stop_evt.is_set():
            for kind, host, port in self.endpoints():
                if self._stop_evt.is_set():
                    return
                name = f"{kind}://{host}:{port}"
                try:
                    self._session(kind, host, port, name)
                    self.last_errors.pop(name, None)
                except OSError as e:
                    self.last_errors[name] = _describe(e)
                except Exception as e:  # nie den Thread sterben lassen
                    self.last_errors[name] = f"{type(e).__name__}: {e}"
                if self.connected:
                    self.connected = False
                    self._set_status("disconnected", "Verbindung getrennt – warte auf Rocket League …")
            attempt += 1
            if attempt == 1 or attempt % 3 == 0:
                self._set_status("waiting", "Warte auf Rocket League … Läuft ein Match? (Zum Testen: Freeplay "
                                            "starten.) Sonst Tab Einrichtung → „Verbindung prüfen“")
            self._stop_evt.wait(2.0)

    def _session(self, kind: str, host: str, port: int, name: str) -> None:
        sock = socket.create_connection((host, port), timeout=1.5)
        try:
            sock.settimeout(1.0)
            rest = _ws_handshake(sock, host, port) if kind == "ws" else b""
            self.connected = True
            self.endpoint = name
            self._set_status("connected", f"Verbunden mit Rocket League ({name})")
            decoder = StreamDecoder()
            utf8 = codecs.getincrementaldecoder("utf-8")(errors="replace")
            reader = _WsReader(sock, rest) if kind == "ws" else None
            while not self._stop_evt.is_set():
                try:
                    chunk = reader.read() if reader else sock.recv(65536)
                except socket.timeout:
                    continue
                if chunk is None or chunk == b"":
                    if reader and chunk is None:
                        continue  # Steuer-Frame (Ping o.ae.)
                    break
                for msg in decoder.feed(utf8.decode(chunk)):
                    self.events.put(msg)
        finally:
            sock.close()


def _describe(e: OSError) -> str:
    if isinstance(e, ConnectionRefusedError):
        return "abgelehnt – an diesem Port lauscht nichts (Stats API aus oder Spiel nicht im Match)"
    if isinstance(e, socket.timeout):
        return "Zeitüberschreitung"
    return f"{type(e).__name__}: {e}"


# ------------------------------------------------------------- Mini-WebSocket
def _ws_handshake(sock: socket.socket, host: str, port: int) -> bytes:
    key = base64.b64encode(os.urandom(16)).decode()
    h = host if ":" not in host else f"[{host}]"
    req = (f"GET / HTTP/1.1\r\nHost: {h}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
    sock.sendall(req.encode())
    buf = b""
    deadline = time.monotonic() + 3
    while b"\r\n\r\n" not in buf:
        if time.monotonic() > deadline:
            raise OSError("WebSocket-Handshake: keine Antwort")
        try:
            part = sock.recv(4096)
        except socket.timeout:
            continue
        if not part:
            raise OSError("WebSocket-Handshake: Verbindung geschlossen")
        buf += part
    head, _, rest = buf.partition(b"\r\n\r\n")
    if b" 101" not in head.split(b"\r\n", 1)[0]:
        raise OSError("WebSocket-Handshake abgelehnt: " + head.split(b"\r\n", 1)[0].decode(errors="replace"))
    return rest


class _WsReader:
    """Liest WebSocket-Frames und liefert den Text-Inhalt als Bytes."""

    def __init__(self, sock: socket.socket, rest: bytes = b"") -> None:
        self.sock = sock
        self.buf = rest

    def _need(self, n: int) -> bytes:
        while len(self.buf) < n:
            part = self.sock.recv(65536)  # socket.timeout wird nach oben gereicht
            if not part:
                raise ConnectionResetError("WebSocket geschlossen")
            self.buf += part
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def read(self) -> bytes | None:
        b1, b2 = self._need(2)
        op, masked, ln = b1 & 0x0F, b2 & 0x80, b2 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", self._need(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", self._need(8))[0]
        mask = self._need(4) if masked else None
        data = self._need(ln)
        if mask:
            data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
        if op == 0x8:
            return b""  # Close
        if op == 0x9:  # Ping -> Pong (Client-Frames muessen maskiert sein)
            m = os.urandom(4)
            self.sock.sendall(bytes([0x8A, 0x80 | len(data)]) + m + bytes(c ^ m[i % 4] for i, c in enumerate(data)))
            return None
        if op in (0x1, 0x2, 0x0):
            return data
        return None


def send_command(sock: socket.socket, command: str, data: dict) -> None:
    """Optionale Kommandos an das Spiel (z.B. SetHUDVisibility)."""
    sock.sendall(json.dumps({"Command": command, "Data": data}).encode("utf-8"))


if __name__ == "__main__":  # kleiner Konsolen-Test: python -m rltracker.statsapi
    c = StatsApiClient()
    c.start()
    try:
        while True:
            try:
                print(c.status.get_nowait()[1])
            except queue.Empty:
                pass
            try:
                m = c.events.get(timeout=0.5)
                print(m["Event"], json.dumps(m["Data"])[:200])
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        c.stop()
        time.sleep(0.2)
