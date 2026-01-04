import socket
import time
import google.generativeai as genai
from PIL import Image
import os
import json
from typing import Optional, Tuple

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "YOUR_API_KEY_HERE")
if GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
    print("⚠️ Warning: Set GOOGLE_API_KEY environment variable")
    
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Server configuration
HOST = '127.0.0.1'
PORT = 8080
SOCKET_TIMEOUT = 5

def send_cpp_command(command: str, retries: int = 3) -> Optional[str]:
    """Send command to C++ driver with retry logic"""
    for attempt in range(retries):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(SOCKET_TIMEOUT)
            client.connect((HOST, PORT))
            client.send(command.encode())
            response = client.recv(1024).decode()
            client.close()
            return response
        except (socket.timeout, ConnectionRefusedError) as e:
            print(f"⚠️ Connection attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(0.5)
        except Exception as e:
            print(f"❌ Error sending command: {e}")
            break
    return None

def get_coordinates_from_gemini(user_instruction: str, image_path: str) -> Tuple[Optional[int], Optional[int]]:
    """Get UI element coordinates from Gemini vision model"""
    print(f"🧠 Analyzing: '{user_instruction}'...")
    
    if not os.path.exists(image_path):
        print(f"❌ Screenshot not found: {image_path}")
        return None, None
    
    try:
        img = Image.open(image_path)
        print(f"📸 Image size: {img.width}x{img.height}")
        
        prompt = f"""You are a precise UI element locator. 

Task: Find "{user_instruction}" in this screenshot.
Image dimensions: {img.width}x{img.height} pixels

Instructions:
1. Locate the CENTER of the target element
2. Return ONLY valid JSON with exact pixel coordinates
3. Coordinates must be within image bounds

Required format:
{{"x": <number>, "y": <number>}}

Return coordinates for the actual screenshot resolution provided."""
        
        response = model.generate_content([prompt, img])
        text = response.text.strip()
        
        # Clean response
        text = text.replace("```json", "").replace("```", "").strip()
        
        coords = json.loads(text)
        x, y = int(coords['x']), int(coords['y'])
        
        # Validate coordinates
        if not (0 <= x <= img.width and 0 <= y <= img.height):
            print(f"⚠️ Coordinates out of bounds: ({x}, {y})")
            return None, None
        
        print(f"✓ Found at: ({x}, {y})")
        return x, y
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON from Gemini: {e}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None, None

def main():
    print("="*50)
    print("👻 Ghost-01 AI Mouse Automation")
    print("="*50)
    print("\nCommands:")
    print("  • Type what to click (e.g., 'Chrome icon')")
    print("  • Use 'open <target>' for double-click")
    print("  • Type 'exit' to quit")
    print("\n" + "="*50 + "\n")
    
    # Test connection
    if not send_cpp_command("CAPTURE"):
        print("❌ Cannot connect to driver. Is ghost_driver.exe running?")
        return
    
    while True:
        try:
            task = input("\n🎯 Command > ").strip()
            
            if not task:
                continue
            if task.lower() == "exit":
                print("👋 Goodbye!")
                break
            
            # Capture screen
            print("📸 Capturing screen...")
            if not send_cpp_command("CAPTURE"):
                print("❌ Screen capture failed")
                continue
            
            time.sleep(1.0)  # Wait for file to be written
            
            # Get coordinates
            x, y = get_coordinates_from_gemini(task, "screen.jpg")
            
            if x is None or y is None:
                print("❌ Could not locate target")
                continue
            
            # Perform action
            is_open = "open" in task.lower()
            action = "DBLCLICK" if is_open else "CLICK"
            
            print(f"🖱️ Performing {action} at ({x}, {y})...")
            result = send_cpp_command(f"{action} {x} {y}")
            
            if result:
                print("✓ Action completed")
            else:
                print("❌ Action failed")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
