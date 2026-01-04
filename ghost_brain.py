import socket
import time
import os
import json
from typing import Optional, Tuple
import ctypes
import google.generativeai as genai
from PIL import Image

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyAkBAGtdkE3o8mh0kWinIAAN0f_6YurJ3E")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Server configuration
HOST = '127.0.0.1'
PORT = 8080
SOCKET_TIMEOUT = 5

def get_windows_scaling_factor():
    """Detect Windows display scaling (100%, 125%, 150%, etc.)"""
    try:
        # Get DPI awareness
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        
        # Get actual screen size (physical pixels)
        actual_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        actual_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        
        # Get DPI
        hdc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, hdc)
        
        # Calculate scaling factor
        scaling = dpi / 96.0  # 96 DPI = 100% scaling
        
        print(f"🖥️ Display Info:")
        print(f"   Resolution: {actual_width}x{actual_height}")
        print(f"   DPI: {dpi}")
        print(f"   Scaling: {scaling*100:.0f}%")
        
        return scaling, actual_width, actual_height
    except Exception as e:
        print(f"⚠️ Could not detect scaling: {e}")
        return 1.0, 1920, 1080

SCALING_FACTOR, SCREEN_WIDTH, SCREEN_HEIGHT = get_windows_scaling_factor()

def send_cpp_command(command: str, retries: int = 3) -> Optional[str]:
    """Send command to C++ driver with retry logic"""
    for attempt in range(retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((HOST, PORT))
            sock.send(command.encode())
            response = sock.recv(1024).decode()
            sock.close()
            return response
        except (socket.timeout, ConnectionRefusedError) as e:
            if attempt == 0:
                print(f"⚠️ Connection failed: {e}")
            if attempt < retries - 1:
                time.sleep(0.5)
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    return None

def validate_coordinates(x: int, y: int, img_width: int, img_height: int, target: str) -> bool:
    """Validate if coordinates make sense for the target"""
    # Recycle Bin should be in top-left area (first 20% of screen)
    if "recycle" in target.lower() or "bin" in target.lower():
        if x > img_width * 0.2 or y > img_height * 0.3:
            print(f"⚠️ Suspicious: Recycle Bin usually in top-left, got ({x}, {y})")
            return False
    return True

def get_coordinates_from_gemini(user_instruction: str, image_path: str, max_retries: int = 3) -> Tuple[Optional[int], Optional[int]]:
    """Get UI element coordinates from Gemini with retry logic"""
    if not os.path.exists(image_path):
        return None, None
    
    img = Image.open(image_path)
    print(f"📸 Screenshot dimensions: {img.width}x{img.height}")
    
    all_attempts = []
    
    for attempt in range(max_retries):
        prompt = f"""You are a precise UI element locator analyzing a Windows desktop screenshot.

Screenshot size: {img.width} x {img.height} pixels

Task: Find the exact CENTER POINT of: "{user_instruction}"

CRITICAL INSTRUCTIONS:
- Look at the ENTIRE screenshot carefully
- Desktop icons are usually in the TOP-LEFT corner
- Recycle Bin is typically at coordinates around (50-100, 200-400) in the image
- Return the CENTER of the icon including its label text
- X=0 is LEFT edge, Y=0 is TOP edge
- Be VERY precise - a real mouse will click this exact spot

Return ONLY this JSON (no explanation, no markdown, no backticks):
{{"x": <number>, "y": <number>}}"""
        
        try:
            response = model.generate_content([prompt, img])
            text = response.text.replace("```json", "").replace("```", "").strip()
            
            coords = json.loads(text)
            img_x, img_y = int(coords['x']), int(coords['y'])
            
            all_attempts.append((img_x, img_y))
            
            print(f"🤖 Attempt {attempt + 1}: ({img_x}, {img_y})")
            
            # Validate
            if validate_coordinates(img_x, img_y, img.width, img.height, user_instruction):
                print(f"✓ Coordinates validated")
                return img_x, img_y
            else:
                if attempt < max_retries - 1:
                    print(f"   Retrying...")
                    time.sleep(0.5)
                    
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} error: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5)
    
    # If all attempts failed validation, use the first one anyway
    if all_attempts:
        print(f"⚠️ Using best guess from attempts: {all_attempts}")
        # Pick the attempt closest to top-left for recycle bin
        if "recycle" in user_instruction.lower():
            best = min(all_attempts, key=lambda p: p[0] + p[1])  # Closest to (0,0)
            print(f"📍 Selected: {best}")
            return best[0], best[1]
        return all_attempts[0]
    
    return None, None

def convert_screenshot_to_screen_coords(img_x: int, img_y: int, img_width: int, img_height: int) -> Tuple[int, int]:
    """Convert screenshot coordinates to actual screen coordinates"""
    
    # If screenshot is larger than screen resolution, we need to scale down
    if img_width > SCREEN_WIDTH or img_height > SCREEN_HEIGHT:
        # Screenshot is high-DPI, scale down to match screen coordinates
        scale_x = SCREEN_WIDTH / img_width
        scale_y = SCREEN_HEIGHT / img_height
        
        screen_x = int(img_x * scale_x)
        screen_y = int(img_y * scale_y)
        
        print(f"📐 Scaling: Image({img_x},{img_y}) at {img_width}x{img_height}")
        print(f"   → Screen({screen_x},{screen_y}) at {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        print(f"   → Scale factors: X={scale_x:.3f}, Y={scale_y:.3f}")
        
        return screen_x, screen_y
    else:
        # Screenshot matches screen resolution
        print(f"📐 No scaling needed: ({img_x},{img_y})")
        return img_x, img_y

def main():
    print("="*60)
    print("👻 Ghost-01 AI Mouse (Scaling-Aware)")
    print("="*60)
    print("\nCommands:")
    print("  • Type what to click (e.g., 'recycle bin', 'chrome icon')")
    print("  • Use 'open <target>' for double-click")
    print("  • Type 'test' to see where mouse moves without clicking")
    print("  • Type 'exit' to quit")
    print("\n" + "="*60 + "\n")
    
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
            
            time.sleep(1.0)
            
            # Get coordinates from Gemini
            print("🧠 Analyzing with Gemini...")
            img_x, img_y = get_coordinates_from_gemini(task, "screen.jpg")
            
            if img_x is None or img_y is None:
                print("❌ Could not locate target")
                continue
            
            # Get image dimensions
            img = Image.open("screen.jpg")
            
            # Convert to screen coordinates
            screen_x, screen_y = convert_screenshot_to_screen_coords(
                img_x, img_y, img.width, img.height
            )
            
            print(f"✓ Target found at screen position: ({screen_x}, {screen_y})")
            
            # Perform action
            if "test" in task.lower():
                # Just move, don't click
                send_cpp_command(f"MOVE {screen_x} {screen_y}")
                print("🖱️ Mouse moved (test mode - no click)")
            else:
                is_open = "open" in task.lower()
                action = "DBLCLICK" if is_open else "CLICK"
                
                print(f"🖱️ Performing {action}...")
                result = send_cpp_command(f"{action} {screen_x} {screen_y}")
                
                if result:
                    print("✓ Action completed")
                else:
                    print("❌ Action failed")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()