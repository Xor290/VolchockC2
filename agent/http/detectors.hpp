#pragma once
#include <string>
#include <vector>

using namespace std;

namespace detect {
	extern vector<string> vm_names;
	extern vector<string> legit_cpu_ids;

	bool cpu_hypervisor_bit();
	bool cpu_id();
	bool cpu_brand();
	bool bios_manufacturer();
	bool bios_version();
	bool screen_resolution();
	bool memory_amount();
	bool cpu_cores();
	bool disk_space();
    bool device_drivers();
};