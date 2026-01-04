#include <winsock2.h>
#include <windows.h>
#include <gdiplus.h>
#include <iostream>
#include <vector>
#include <string>
#include <sstream>

#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "gdiplus.lib")

using namespace Gdiplus;
using namespace std;

// --- Helper: Get Encoder ---
int GetEncoderClsid(const WCHAR* format, CLSID* pClsid) {
    UINT num = 0, size = 0;
    GetImageEncodersSize(&num, &size);
    if (size == 0) return -1;
    ImageCodecInfo* pImageCodecInfo = (ImageCodecInfo*)(malloc(size));
    GetImageEncoders(num, size, pImageCodecInfo);
    for (UINT j = 0; j < num; ++j) {
        if (wcscmp(pImageCodecInfo[j].MimeType, format) == 0) {
            *pClsid = pImageCodecInfo[j].Clsid;
            free(pImageCodecInfo);
            return j;
        }
    }
    free(pImageCodecInfo);
    return -1;
}

// --- Screen Capture ---
string CaptureScreen(const string& filename) {
    // Force System DPI Awareness just for the screenshot to be high-res
    SetProcessDPIAware(); 
    
    HDC hdcScreen = GetDC(NULL);
    HDC hdcMem = CreateCompatibleDC(hdcScreen);
    int width = GetSystemMetrics(SM_CXSCREEN);
    int height = GetSystemMetrics(SM_CYSCREEN);
    HBITMAP hbmScreen = CreateCompatibleBitmap(hdcScreen, width, height);
    SelectObject(hdcMem, hbmScreen);
    BitBlt(hdcMem, 0, 0, width, height, hdcScreen, 0, 0, SRCCOPY);

    Bitmap bitmap(hbmScreen, NULL);
    CLSID clsid;
    if (GetEncoderClsid(L"image/jpeg", &clsid) > -1) {
        wstring wFilename(filename.begin(), filename.end());
        bitmap.Save(wFilename.c_str(), &clsid, NULL);
    }
    DeleteObject(hbmScreen);
    DeleteDC(hdcMem);
    ReleaseDC(NULL, hdcScreen);
    return "captured";
}

// --- Action: Move & Click (Raw Input) ---
void PerformClick(int x, int y, bool doubleClick) {
    // Debug info
    cout << "Move Request: " << x << ", " << y << endl;
    
    // Simple SetCursorPos - No Math here. Python handles it.
    SetCursorPos(x, y);

    int clicks = doubleClick ? 2 : 1;
    for(int i=0; i<clicks; i++) {
        INPUT inputs[2] = {};
        inputs[0].type = INPUT_MOUSE;
        inputs[0].mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
        inputs[1].type = INPUT_MOUSE;
        inputs[1].mi.dwFlags = MOUSEEVENTF_LEFTUP;
        SendInput(2, inputs, sizeof(INPUT));
        if (doubleClick) Sleep(100); 
    }
}

void StartServer() {
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
    SOCKET serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(8080);
    bind(serverSocket, (sockaddr*)&serverAddr, sizeof(serverAddr));
    listen(serverSocket, 1);
    
    cout << "Ghost-01 Driver v5 (Raw Mode) Listening on Port 8080..." << endl;

    GdiplusStartupInput gdiplusStartupInput;
    ULONG_PTR gdiplusToken;
    GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, NULL);

    while (true) {
        SOCKET clientSocket = accept(serverSocket, NULL, NULL);
        char buffer[1024] = {0};
        recv(clientSocket, buffer, 1024, 0);
        string command(buffer);

        if (command.find("DBLCLICK") == 0) {
            stringstream ss(command);
            string cmd; int x, y;
            ss >> cmd >> x >> y;
            PerformClick(x, y, true);
            send(clientSocket, "OK", 2, 0);
        }
        else if (command.find("CLICK") == 0) {
            stringstream ss(command);
            string cmd; int x, y;
            ss >> cmd >> x >> y;
            PerformClick(x, y, false);
            send(clientSocket, "OK", 2, 0);
        } 
        else if (command.find("CAPTURE") == 0) {
            CaptureScreen("screen.jpg");
            send(clientSocket, "OK", 2, 0);
        }
        closesocket(clientSocket);
    }
    GdiplusShutdown(gdiplusToken);
    WSACleanup();
}

int main() {
    StartServer();
    return 0;
}