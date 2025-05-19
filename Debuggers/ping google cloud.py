# Last updated: 2025-05-19 18:26:37
import subprocess

def ping(host):
    """
    Pings the given host and returns True if successful, False otherwise.
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]  # Send one packet

    try:
        subprocess.check_call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ping failed with error: {e}")
        return False
    except FileNotFoundError:
        print("Error: 'ping' command not found. Make sure it's in your system's PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    import platform
    cloud_sql_ip = "35.205.81.251"
    print(f"Pinging {cloud_sql_ip} from Charleroi...")
    if ping(cloud_sql_ip):
        print(f"Successfully pinged {cloud_sql_ip}")
    else:
        print(f"Failed to ping {cloud_sql_ip}")