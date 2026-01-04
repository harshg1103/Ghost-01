#include <winsock2.h>
#include <windows.h>
#include <gdiplus.h>
#include <iostream>
#include <string>
#include <sstream>

#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "gdiplus.lib")

using namespace Gdiplus;
using namespace std;

// Get JPEG encoder CLSID
int GetEncoderClsid(const WCHAR* format, CLSID* pClsid) {
    UINT num = 0, size = 0;
    GetImageEncodersSize(&num, &size);
    if (size == 0) return -1;
    
    ImageCodecInfo* pImageCodecInfo = (ImageCodecInfo*)malloc(size);
    if (!pImageCodecInfo) return -1;
    
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

// Capture full screen to JPEG
string CaptureScreen(const string& filename) {
    cout << "[CAPTURE] Taking screenshot..." << endl;
    
    HDC hdcScreen = GetDC(NULL);
    HDC hdcMem = CreateCompatibleDC(hdcScreen);
    
    int width = GetSystemMetrics(SM_CXSCREEN);
    int height = GetSystemMetrics(SM_CYSCREEN);
    
    cout << "[CAPTURE] Screen resolution: " << width << "x" << height << endl;
    
    HBITMAP hbmScreen = CreateCompatibleBitmap(hdcScreen, width, height);
    SelectObject(hdcMem, hbmScreen);
    BitBlt(hdcMem, 0, 0, width, height, hdcScreen, 0, 0, SRCCOPY);

    Bitmap bitmap(hbmScreen, NULL);
    CLSID clsid;
    
    if (GetEncoderClsid(L"image/jpeg", &clsid) > -1) {
        wstring wFilename(filename.begin(), filename.end());
        Status status = bitmap.Save(wFilename.c_str(), &clsid, NULL);
        
        if (status == Ok) {
            cout << "[CAPTURE] Saved to " << filename << endl;
        } else {
            cout << "[CAPTURE] Save failed with status: " << status << endl;
        }
    }
    
    DeleteObject(hbmScreen);
    DeleteDC(hdcMem);
    ReleaseDC(NULL, hdcScreen);
    
    return "captured";
}

// Perform mouse click at coordinates
void PerformClick(int x, int y, bool doubleClick) {
    string action = doubleClick ? "DOUBLE-CLICK" : "CLICK";
    cout << "[" << action << "] Moving to (" << x << ", " << y << ")" << endl;
    
    // Move cursor
    if (!SetCursorPos(x, y)) {
        cout << "[ERROR] SetCursorPos failed" << endl;
        return;
    }
    
    // Small delay to ensure cursor moves
    Sleep(50);
    
    // Perform clicks
    int clicks = doubleClick ? 2 : 1;
    for (int i = 0; i < clicks; i++) {
        INPUT inputs[2] = {};
        
        // Mouse down
        inputs[0].type = INPUT_MOUSE;
        inputs[0].mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
        
        // Mouse up
        inputs[1].type = INPUT_MOUSE;
        inputs[1].mi.dwFlags = MOUSEEVENTF_LEFTUP;
        
        UINT sent = SendInput(2, inputs, sizeof(INPUT));
        
        if (sent != 2) {
            cout << "[ERROR] SendInput failed on click " << (i+1) << endl;
        }
        
        if (doubleClick && i == 0) {
            Sleep(50); // Delay between double-click
        }
    }
    
    cout << "[" << action << "] Completed" << endl;
}

void StartServer() {
    // Initialize Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        cout << "[ERROR] WSAStartup failed" << endl;
        return;
    }
    
    // Create socket
    SOCKET serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (serverSocket == INVALID_SOCKET) {
        cout << "[ERROR] Socket creation failed" << endl;
        WSACleanup();
        return;
    }
    
    // Allow port reuse
    int opt = 1;
    setsockopt(serverSocket, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
    
    // Bind socket
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(8080);
    
    if (bind(serverSocket, (sockaddr*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        cout << "[ERROR] Bind failed. Port 8080 may be in use." << endl;
        closesocket(serverSocket);
        WSACleanup();
        return;
    }
    
    // Listen
    if (listen(serverSocket, 5) == SOCKET_ERROR) {
        cout << "[ERROR] Listen failed" << endl;
        closesocket(serverSocket);
        WSACleanup();
        return;
    }
    
    cout << "========================================" << endl;
    cout << "Ghost-01 Driver v6 (Fixed)" << endl;
    cout << "Listening on 127.0.0.1:8080" << endl;
    cout << "========================================" << endl;

    // Initialize GDI+
    GdiplusStartupInput gdiplusStartupInput;
    ULONG_PTR gdiplusToken;
    GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, NULL);

    // Main server loop
    while (true) {
        SOCKET clientSocket = accept(serverSocket, NULL, NULL);
        
        if (clientSocket == INVALID_SOCKET) {
            cout << "[ERROR] Accept failed" << endl;
            continue;
        }
        
        char buffer[1024] = {0};
        int bytesReceived = recv(clientSocket, buffer, sizeof(buffer) - 1, 0);
        
        if (bytesReceived <= 0) {
            closesocket(clientSocket);
            continue;
        }
        
        string command(buffer);
        cout << "\n[RECEIVED] " << command << endl;

        // Parse and execute command
        if (command.find("DBLCLICK") == 0) {
            stringstream ss(command);
            string cmd;
            int x, y;
            ss >> cmd >> x >> y;
            PerformClick(x, y, true);
            send(clientSocket, "OK", 2, 0);
        }
        else if (command.find("CLICK") == 0) {
            stringstream ss(command);
            string cmd;
            int x, y;
            ss >> cmd >> x >> y;
            PerformClick(x, y, false);
            send(clientSocket, "OK", 2, 0);
        } 
        else if (command.find("CAPTURE") == 0) {
            CaptureScreen("screen.jpg");
            send(clientSocket, "OK", 2, 0);
        }
        else {
            cout << "[ERROR] Unknown command: " << command << endl;
            send(clientSocket, "ERROR", 5, 0);
        }
        
        closesocket(clientSocket);
    }
    
    // Cleanup
    GdiplusShutdown(gdiplusToken);
    closesocket(serverSocket);
    WSACleanup();
}

int main() {
    // Set DPI awareness for proper screen capture
    SetProcessDPIAware();
    
    StartServer();
    return 0;
}
