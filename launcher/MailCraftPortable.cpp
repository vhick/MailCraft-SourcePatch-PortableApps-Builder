// MailCraft PortableApps launcher, b1r1. MIT OR Apache-2.0.
// Owns only the MailCraft process it starts. It neither harvests host profiles
// nor edits registry, shortcuts, credentials, or shared application folders.
#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <filesystem>
#include <string>
#include <vector>

namespace fs = std::filesystem;

static int Fail(const std::wstring& message, int code = 2) {
    MessageBoxW(nullptr, message.c_str(), L"MailCraft Portable", MB_OK | MB_ICONERROR);
    return code;
}

static bool DirectorySafe(const fs::path& path) {
    DWORD attr = GetFileAttributesW(path.c_str());
    return attr != INVALID_FILE_ATTRIBUTES &&
        (attr & FILE_ATTRIBUTE_DIRECTORY) && !(attr & FILE_ATTRIBUTE_REPARSE_POINT);
}

static bool EnsureDirectory(const fs::path& path) {
    if (CreateDirectoryW(path.c_str(), nullptr)) return DirectorySafe(path);
    return GetLastError() == ERROR_ALREADY_EXISTS && DirectorySafe(path);
}

static bool FileRegular(const fs::path& path) {
    DWORD attr = GetFileAttributesW(path.c_str());
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY) &&
           !(attr & FILE_ATTRIBUTE_REPARSE_POINT);
}

static std::wstring Quote(const std::wstring& argument) {
    std::wstring result = L"\"";
    size_t slashes = 0;
    for (wchar_t ch : argument) {
        if (ch == L'\\') { ++slashes; continue; }
        if (ch == L'"') {
            result.append(slashes * 2 + 1, L'\\');
            result += L'"';
            slashes = 0;
            continue;
        }
        result.append(slashes, L'\\');
        slashes = 0;
        result += ch;
    }
    result.append(slashes * 2, L'\\');
    return result + L'"';
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    wchar_t module[32768] = {};
    DWORD count = GetModuleFileNameW(nullptr, module, 32768);
    if (count == 0 || count >= 32768) return Fail(L"Cannot determine the portable folder.");
    const fs::path root = fs::path(module).parent_path();
    const fs::path app = root / L"App" / L"MailCraft";
    const fs::path data = root / L"Data";
    const fs::path own = data / L"MailCraft";
    const fs::path binary = app / L"mailcraft.exe";
    if (!DirectorySafe(root) || !DirectorySafe(root / L"App") || !DirectorySafe(app))
        return Fail(L"Invalid application folder or reparse point. The package may be incomplete.");
    if (!FileRegular(binary) || !FileRegular(app / L"portable.txt"))
        return Fail(L"Missing MailCraft application or portable marker. Re-extract the package.");
    // Refuse redirection through a junction/symlink: user mail must stay here.
    if (!EnsureDirectory(data) || !EnsureDirectory(own))
        return Fail(L"Cannot create a safe local Data folder. Check disk permissions and links.");
    const fs::path probe = own / (L".__mailcraft-probe-" + std::to_wstring(GetCurrentProcessId()));
    HANDLE test = CreateFileW(probe.c_str(), GENERIC_WRITE, 0, nullptr,
                              CREATE_NEW, FILE_ATTRIBUTE_TEMPORARY, nullptr);
    if (test == INVALID_HANDLE_VALUE)
        return Fail(L"The Data folder is not writable. MailCraft was not started.");
    CloseHandle(test);
    DeleteFileW(probe.c_str());

    int argc = 0;
    wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv) return Fail(L"Cannot read command-line arguments.");
    std::wstring command = Quote(binary.wstring());
    for (int i = 1; i < argc; ++i) command += L" " + Quote(argv[i]);
    LocalFree(argv);
    std::vector<wchar_t> mutableCommand(command.begin(), command.end());
    mutableCommand.push_back(L'\0');
    STARTUPINFOW start{};
    start.cb = sizeof(start);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(binary.c_str(), mutableCommand.data(), nullptr, nullptr, FALSE,
                        0, nullptr, app.c_str(), &start, &process))
        return Fail(L"MailCraft could not start. Verify the application executable and Windows version.");
    CloseHandle(process.hThread);
    // When MailCraft closes to tray, its process remains alive. Do not end early.
    DWORD waited = WaitForSingleObject(process.hProcess, INFINITE);
    DWORD exitCode = 1;
    if (waited == WAIT_OBJECT_0) GetExitCodeProcess(process.hProcess, &exitCode);
    CloseHandle(process.hProcess);
    return static_cast<int>(exitCode);
}
