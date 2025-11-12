#pragma once
#include <string>
#include <vector>
#include <wtypes.h>

namespace utils {
	string bstr_to_str(BSTR bstr);
	string lowercase(string str);
	bool str_includes(string str, vector<string> includes);
};