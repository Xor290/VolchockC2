#include "system_utils.h"
#include <windows.h>
#include <psapi.h>
#include <cstdlib>
#include <ctime>
#include <string>
#include <sstream>
#include <iomanip>
#define UNLEN 127

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
    static std::string agent_id;
    if (agent_id.empty()) {
        static bool seeded = false;
        if (!seeded) {
            std::srand(static_cast<unsigned int>(std::time(nullptr)));
            seeded = true;
        }
        int num = 10000000 + std::rand() % 90000000; // nombre entre 10000000 et 99999999
        std::ostringstream oss;
        oss << std::setw(8) << std::setfill('0') << num; // formatte sur 8 chiffres
        agent_id = oss.str();
    }
    return agent_id;
}