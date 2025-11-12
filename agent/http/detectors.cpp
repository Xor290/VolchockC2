#include <string>
#include "detectors.hpp"
#include <windows.h>
#include <intrin.h>
#include <array>
#include "vmi.hpp"
#include "<Wbemidl.h>"
#include <iostream>
#include "utils.hpp"
#include <vector>

using namespace std;

vector<string> detect::vm_names = { "virtual", "qemu", "vmware", "oracle", "innotek" };
vector<string> detect::legit_cpu_ids = { "AuthenticAMC", "GenuineIntel" };

bool detect::cpu_hypervisor_bit() {
    array<int, 4> cpuInfo = { 0, 0, 0, 0 };
    __cpuid(cpuInfo.data(), 0x1);

    return (cpuInfo[2] >> 31) & 0x1;
}

bool detect::cpu_id() {
    array<int, 4> cpuInfo = { 0, 0, 0, 0 };
    string cpu = "";
    __cpuid(cpuInfo.data(), 0x0);

    for (int i = 1; i <= 3; i++) {
        cpu += cpuInfo[i] & 0xff;
        cpu += (cpuInfo >> 8) & 0xff;
        cpu += (cpuInfo >> 16) & 0xff;
        cpu += (cpuInfo >> 24) & 0xff;     
    }

    return !utils::str_includes(cpu, detect::legit_cpu_ids);
}

bool detect::cpu_brand() {
    array<int, 4> cpuInfo = { 0, 0, 0, 0 };
    string cpu = "";
    for (int id = 2; id <= 4; id++) {
        __cpuid(cpuInfo.data(), 0x80000000 + id);

        for (auto i: cpuInfo) {
            cpu += tolower(i & 0xff);
            cpu += tolower((i >> 8) & 0xff);
            cpu += tolower((i >> 16) & 0xff);
            cpu += tolower((i >> 24) & 0xff);
        }
    }
    return utils::str_includes(cpu, detect::vm_names);
}

bool detect::bios_manufacturer() {
	string manufacturer = "";
	wmi::get_wmi("select * from Win32_BIOS", [&](IWbemClassObject* pclsObj, VARIANT* vtProp) {
		HRESULT hr = pclsObj->Get(L"Manufacturer", 0, vtProp, 0, 0);
		manufacturer = utils::lowercase(utils::bstr_to_str(vtProp->bstrVal));
		});

	std::cout << manufacturer << std::endl;

	return utils::str_includes(manufacturer, detect::vm_names);
}

bool detect::bios_version() {
	string version = "";
	wmi::get_wmi("select * from Win32_BIOS", [&](IWbemClassObject* pclsObj, VARIANT* vtProp) {
		HRESULT hr = pclsObj->Get(L"SMBIOSBIOSVersion", 0, vtProp, 0, 0);
		version = utils::lowercase(utils::bstr_to_str(vtProp->bstrVal));
		});

	return utils::str_includes(version, detect::vm_names);
}

bool detect::screen_resolution() {
	auto w = GetSystemMetrics(SM_CXSCREEN);
	auto h = GetSystemMetrics(SM_CYSCREEN);

	if (w == 1600 && h == 900) return false;
	if (w == 1920 && h == 1080) return false;
	if (w == 1920 && h == 1200) return false;
	if (w == 2560 && h == 1440) return false;
	if (w == 3840 && h == 2160) return false;

	return true;
}

bool detect::memory_amount() {
	MEMORYSTATUSEX statex;
	statex.dwLength = sizeof(statex);

	if (GlobalMemoryStatusEx(&statex) == FALSE) {
		return true;
	}

	return statex.ullTotalPhys / 1024 / 1024 < 4096;
}

bool detect::cpu_cores() {
	SYSTEM_INFO info;
	GetSystemInfo(&info);

	return info.dwNumberOfProcessors < 4;
}

bool detect::disk_space() {
	ULARGE_INTEGER bytes;
	BOOL result = GetDiskFreeSpaceExA(
		"\\\\?\\c:\\",
		NULL,
		&bytes,
		NULL
	);

	if (result == FALSE) return true;

	return bytes.QuadPart / 1024 / 1024 / 1024 < 100;
}

bool detect::device_drivers() {
    vector<string> suspicious = { "VBoxGuest", "vmhgfs", "vmxnet", "VMMouse", "QEMU" };
    HDEVINFO deviceInfo = SetupDiGetClassDevs(NULL, "ROOT", NULL, DIGCF_ALLCLASSES | DIGCF_PRESENT);
    if (deviceInfo == INVALID_HANDLE_VALUE) return false;

    SP_DEVINFO_DATA devInfoData;
    devInfoData.cbSize = sizeof(SP_DEVINFO_DATA);

    for (DWORD i = 0; SetupDiEnumDeviceInfo(deviceInfo, i, &devInfoData); i++) {
        TCHAR buffer[256];
        if (SetupDiGetDeviceRegistryProperty(deviceInfo, &devInfoData, SPDRP_DEVICEDESC, NULL, (PBYTE)buffer, sizeof(buffer), NULL)) {
            string desc = utils::lowercase(buffer);
            if (utils::str_includes(desc, suspicious))
                return true;
        }
    }
    SetupDiDestroyDeviceInfoList(deviceInfo);
    return false;
}
