# dump2h.py
import sys

dll_path = sys.argv[1]
h_path = sys.argv[2]

raw = open(dll_path, "rb").read()
out = "unsigned char dll_payload[] = {\n"
out += ','.join(f'0x{x:02x}' for x in raw)
out += '};\n'
out += f'unsigned int dll_payload_len = {len(raw)};\n'

with open(h_path, "w") as f:
    f.write(out)
