# 👻 Ghost-01: The Universal Large Action Model (LAM)

> **"Giving AI Eyes and Hands to automate the un-automatable."**

![Hackathon](https://img.shields.io/badge/Status-Hackathon_Submission-orange?style=flat-square)
![AI](https://img.shields.io/badge/AI-Google_Gemini_1.5-blue?style=flat-square)
![Core](https://img.shields.io/badge/Core-Native_C++_%2F_WinAPI-red?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-lightgrey?style=flat-square)

---

## 📖 Project Overview
**Ghost-01** is an "Agentic AI" that controls a computer exactly like a human does: **Visually.**

While traditional automation (like Selenium) relies on hidden code, Ghost-01 uses **Google Gemini 1.5** to see the screen pixels and a custom **C++ Driver** to physically move the mouse. This allows it to automate *any* software—legacy enterprise apps, games, and desktop tools—without needing an API.

---

## 🏗️ How It Works
The system follows a "See-Think-Act" loop:

1.  **See:** The **C++ Driver** captures the screen in real-time.
2.  **Think:** The **Python Brain** sends the image to **Gemini 1.5 Flash**, which analyzes the UI to find the coordinates of buttons (e.g., "The Recycle Bin").
3.  **Act:** The **C++ Driver** receives the coordinates and performs a hardware-level mouse click.

```mermaid
graph LR
    User[User Command] --> Python[Python Brain]
    Python -->|Capture| CPP[C++ Driver]
    CPP -->|Image| Python
    Python -->|Image + Prompt| Gemini[Google Gemini API]
    Gemini -->|Coordinates x,y| Python
    Python -->|Click x,y| CPP
    CPP -->|Mouse Event| OS[Windows OS]
