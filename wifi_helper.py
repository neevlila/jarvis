import subprocess
import re

def get_current_wifi():
    """Get currently connected WiFi name"""
    try:
        output = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces']).decode('utf-8', errors="backslashreplace")
        for line in output.split('\n'):
            if "SSID" in line and "BSSID" not in line:
                return line.split(":")[1].strip()
        return None
    except Exception as e:
        print(f"Error getting current WiFi: {e}")
        return None

def get_wifi_password(profile_name):
    """Get password for a specific WiFi profile"""
    try:
        # Sanitize profile name to prevent argument injection
        profile_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', profile_name)
        if not profile_name:
            return None
        # Get password for specific profile
        output = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', profile_name, 'key=clear']).decode('utf-8', errors="backslashreplace")
        password = [line.split(":")[1].strip() for line in output.split('\n') if "Key Content" in line]
        return password[0] if password else None
    except Exception as e:
        print(f"Error getting password for {profile_name}: {e}")
        return None