import socket
import time
import google.generativeai as genai
from PIL import Image
import os

# --- CONFIGURATION ---
GOOGLE_API_KEY = "AIzaSyCUo89teBIa3i7RQyKfgOwjSGma66hnWJg" 
genai.configure(api_key=GOOGLE_API_KEY)
# Use Flash for speed
model = genai.GenerativeModel('gemini-2.5-flash')

# === 🛠️ TUNING FOR 125% SCALING 🛠️ ===
# We multiply by 0.8 to counteract the 1.25x Windows Zoom
X_MULTIPLIER = 0.8
Y_MULTIPLIER = 0.8
# ======================================

def send_cpp_command(command):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', 8080))
        client.send(command.encode())
        response = client.recv(1024).decode()
        client.close()
        return response
    except:
        return None

def get_coordinates_from_gemini(user_instruction, image_path):
    print(f"🧠 Thinking: Looking for '{user_instruction}'...")
    if not os.path.exists(image_path): return None, None
    
    img = Image.open(image_path)
    
    prompt = f"""
    You are a mouse automation agent. The image size is {img.width}x{img.height}.
    Find the exact center coordinates of: "{user_instruction}".
    Return JSON: {{"x": number, "y": number}}
    """
    
    try:
        response = model.generate_content([prompt, img])
        text = response.text.replace("```json", "").replace("```", "").replace("\n", "")
        import json
        coords = json.loads(text)
        
        # APPLY THE 125% FIX
        final_x = int(coords['x'] * X_MULTIPLIER)
        final_y = int(coords['y'] * Y_MULTIPLIER)
        
        print(f"Original: {coords['x']},{coords['y']} -> Tuned (0.8x): {final_x},{final_y}")
        return final_x, final_y
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None, None

def main():
    print("👻 Ghost-01 (125% Scale Mode)")
    print(f"Correction Factor: 0.8x")
    
    while True:
        task = input("\nCommand > ")
        if task == "exit": break
        
        send_cpp_command("CAPTURE")
        time.sleep(1.5)
        
        x, y = get_coordinates_from_gemini(task, "screen.jpg")
        
        if x and y:
            if "open" in task.lower():
                send_cpp_command(f"DBLCLICK {x} {y}")
            else:
                send_cpp_command(f"CLICK {x} {y}")

if __name__ == "__main__":
    main()