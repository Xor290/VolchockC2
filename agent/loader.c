#include <windows.h>
#include <stdio.h>

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("usage: %s <shellcode.bin>\n", argv[0]);
        return 1;
    }

    // Charge le shellcode
    FILE* f = fopen(argv[1],"rb");
    if (!f) { puts("fopen fail"); return 1; }
    fseek(f,0,SEEK_END); size_t sz = ftell(f); rewind(f);
    unsigned char* sc = (unsigned char*)VirtualAlloc(0, sz, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    fread(sc, 1, sz, f); fclose(f);

    // Exécute le shellcode
    HANDLE th = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)sc, NULL, 0, NULL);
    WaitForSingleObject(th, INFINITE);

    VirtualFree(sc, 0, MEM_RELEASE);
    return 0;
}
