#pragma once
#include <string>

std::string exec_cmd(const std::string& cmd);
std::string handle_upload(std::string data);
std::string parse_task(std::string b64_encoded_task);
