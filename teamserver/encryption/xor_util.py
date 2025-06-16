import base64

class XORCipher:
    def __init__(self, key: str):
        if not key:
            raise ValueError("Key must not be empty")
        self.key = key.encode()  # Travailler en bytes pour universalité

    def xor_bytes(self, data: bytes) -> bytes:
        key_len = len(self.key)
        return bytes([b ^ self.key[i % key_len] for i, b in enumerate(data)])

    def xor_str(self, data: str) -> bytes:
        # Entrée string, sortie bytes xorés
        return self.xor_bytes(data.encode())

    def decode_to_str(self, data: bytes) -> str:
        # Pour obtenir string à partir de bytes xorés
        return self.xor_bytes(data).decode(errors="replace")

    def encrypt_b64(self, data: str) -> str:
        # XOR puis encodage base64 pour JSON/HTTP
        xored = self.xor_str(data)
        return base64.b64encode(xored).decode()

    def decrypt_b64(self, data_b64: str) -> str:
        # base64 → xor → string
        xored = base64.b64decode(data_b64.encode())
        return self.decode_to_str(xored)
