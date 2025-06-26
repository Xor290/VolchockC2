#include "file_utils.h"
#include "base64.h"
#include <fstream>

std::vector<unsigned char> read_file_bin(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) return {};
    std::vector<unsigned char> buffer((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    return buffer;
}

std::string handle_download(const std::string& filepath) {
    auto data = read_file_bin(filepath);
    if (data.empty()) {
        return "[ERROR] File not found or cannot read.";
    }
    std::string encoded_file = base64_encode(base64_encode(std::string(data.begin(), data.end())));
    return encoded_file;
}

std::string save_base64_file(const std::string& filename, const std::string& b64_encoded_filecontent) {
    std::string decoded = base64_decode(b64_encoded_filecontent);
    std::ofstream outfile(filename.c_str(), std::ios::binary);
    if (outfile) {
        outfile.write(decoded.data(), decoded.size());
        outfile.close();
        return "File uploaded.";
    }
    else {
        return "File not uploaded.";
    }
}
