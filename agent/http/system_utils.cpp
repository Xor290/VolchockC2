#include "system_utils.h"
#include <windows.h>
#include <psapi.h>
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
    return get_hostname() + "_" + get_username() + "_" + get_process_name();
}
