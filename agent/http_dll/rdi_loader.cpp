// compile with : x86_64-w64-mingw32-g++ -o rdi_loader.exe rdi_loader.cpp -fpermissive
#include <windows.h>
#include <winnt.h>

typedef void (*pReflectFunc)(void*);

void* MyMemmem(const void* haystack, size_t haystacklen, const void* needle, size_t needlelen) {
    if (needlelen == 0) return (void*)haystack;
    const char *h = (const char*)haystack;
    for (size_t i = 0; i <= haystacklen - needlelen; ++i) {
        if (!memcmp(h+i, needle, needlelen)) return (void*)(h+i);
    }
    return NULL;
}


FARPROC GetExportByName(BYTE* base, const char* name) {
    IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)base;
    IMAGE_NT_HEADERS64* nt = (IMAGE_NT_HEADERS64*)(base + dos->e_lfanew);
    IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
    if (!dir.VirtualAddress) return NULL;
    IMAGE_EXPORT_DIRECTORY* exp = (IMAGE_EXPORT_DIRECTORY*)(base + dir.VirtualAddress);
    DWORD* func = (DWORD*)(base + exp->AddressOfFunctions);
    DWORD* nameptr = (DWORD*)(base + exp->AddressOfNames);
    WORD* ord = (WORD*)(base + exp->AddressOfNameOrdinals);
    for (DWORD i=0;i<exp->NumberOfNames;i++) {
        char* curr = (char*)(base + nameptr[i]);
        if (lstrcmpiA(curr, name) == 0) {
            WORD fOrdinal = ord[i];
            return (FARPROC)(base + func[fOrdinal]);
        }
    }
    return NULL;
}



void RunReflectiveDLL(void* buffer, size_t len) {
    BYTE* pImage = (BYTE*)buffer;
    auto dos = (IMAGE_DOS_HEADER*)pImage;
    auto nt = (IMAGE_NT_HEADERS64*)(pImage + dos->e_lfanew);
    SIZE_T ImageSize = nt->OptionalHeader.SizeOfImage;
    BYTE* mem = (BYTE*)VirtualAlloc(0, ImageSize, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    memcpy(mem, pImage, nt->OptionalHeader.SizeOfHeaders);
    WORD nSections = nt->FileHeader.NumberOfSections;
    IMAGE_SECTION_HEADER* sec = (IMAGE_SECTION_HEADER*)((BYTE*)&nt->OptionalHeader + nt->FileHeader.SizeOfOptionalHeader);
    for (int i = 0; i < nSections; i++) {
        memcpy(mem + sec[i].VirtualAddress, pImage + sec[i].PointerToRawData, sec[i].SizeOfRawData);
    }
    // relocations
    ULONG_PTR delta = mem - nt->OptionalHeader.ImageBase;
    if (delta) {
        auto dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC];
        if (dir.Size) {
            auto reloc = (IMAGE_BASE_RELOCATION*)(mem + dir.VirtualAddress);
            while (reloc->VirtualAddress && reloc->SizeOfBlock) {
                int num = (reloc->SizeOfBlock - sizeof(IMAGE_BASE_RELOCATION))/2;
                WORD* rdata = (WORD*)((BYTE*)reloc + sizeof(IMAGE_BASE_RELOCATION));
                for (int i = 0; i < num; i++) {
                    if ((rdata[i] >> 12) == IMAGE_REL_BASED_DIR64) {
                        ULONG_PTR* patch = (ULONG_PTR*)(mem + reloc->VirtualAddress + (rdata[i] & 0xFFF));
                        *patch += delta;
                    }
                }
                reloc = (IMAGE_BASE_RELOCATION*)((BYTE*)reloc + reloc->SizeOfBlock);
            }
        }
    }
    auto idir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (idir.Size) {
        IMAGE_IMPORT_DESCRIPTOR* imp = (IMAGE_IMPORT_DESCRIPTOR*)(mem + idir.VirtualAddress);
        while (imp->Name) {
            char* lib = (char*)(mem + imp->Name);
            HMODULE dll = LoadLibraryA(lib);
            ULONG_PTR* ft = (ULONG_PTR*)(mem + imp->FirstThunk);
            ULONG_PTR* orig = (ULONG_PTR*)(mem + imp->OriginalFirstThunk);
            if (!orig) orig = ft;
            while (*orig) {
                if (*orig & IMAGE_ORDINAL_FLAG64) {
                    *ft = (ULONG_PTR)GetProcAddress(dll, (LPCSTR)(*orig & 0xFFFF));
                } else {
                    auto impByName = (IMAGE_IMPORT_BY_NAME*)(mem + (*orig));
                    *ft = (ULONG_PTR)GetProcAddress(dll, impByName->Name);
                }
                ++ft; ++orig;
            }
            ++imp;
        }
    }
    auto go = (pReflectFunc)GetExportByName(mem, "go");
    if (go) go(nullptr);
    VirtualFree(mem, 0, MEM_RELEASE);
}


int main(int argc, char** argv) {
    if (argc != 2) return 1;
    HANDLE f = CreateFileA(argv[1], GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, 0, 0);
    DWORD sz = GetFileSize(f, 0);
    BYTE* buf = (BYTE*)HeapAlloc(GetProcessHeap(), 0, sz);
    DWORD r;
    ReadFile(f, buf, sz, &r, 0);
    CloseHandle(f);

    RunReflectiveDLL(buf, sz);
    HeapFree(GetProcessHeap(), 0, buf);
    return 0;
}
