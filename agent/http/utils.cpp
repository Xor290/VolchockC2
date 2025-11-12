#include "utils.hpp"
#include "detectors.hpp"
#include <string>
#include <codecvt>
#include <vector>

string utils::bstr_to_str(BSTR bstr) {
	if (!bstr) return string("");

	wstring ws(bstr, SysStringLen(bstr));
	wstring_convert<std::codecvt_utf8_utf16<wchar_t>> converter;
	string narrow = converter.to_bytes(ws);

	return narrow;
}

string utils::lowercase(string str) {
	string result = "";

	for (auto c : str) {
		result += std::tolower(c);
	}

	return result;
}

bool utils::str_includes(string str, vector<string> includes) {
	for (auto i : includes) {
		if (str.find(i) != string::npos) {
			return true;
		}
	}

	return false;
}