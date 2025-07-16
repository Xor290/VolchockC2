# teamserver/encryption/xor_util.py
# Contains utility functions for XOR-based encryption and decryption 
# used in Teamserver communications.

import base64
from teamserver.logger.CustomLogger import CustomLogger
log = CustomLogger("volchock")

class XORCipher:
    def __init__(self, key: str):
        if not key:
            log.critical("[+] Key must not be empty")
            raise ValueError("Key must not be empty")
        self.key = key.encode()  

    def xor_bytes(self, data: bytes) -> bytes:
        key_len = len(self.key)
        return bytes([b ^ self.key[i % key_len] for i, b in enumerate(data)])

    # Encryption : string → xor → base64 
    # Decryption : base64 → xor → string

    def encrypt(self, data: str) -> str:
        xored = self.xor_bytes(data)
        b64_encoded = base64.b64encode(xored)
        return b64_encoded.decode("utf-8", errors="replace")

    def decrypt(self, b64_encoded: str) -> str:
        xored = base64.b64decode(b64_encoded)
        clear_result = self.xor_bytes(xored)
        clear_result = clear_result.decode("utf-8", errors="replace")
        return clear_result