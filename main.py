import paramiko
import sys
from scp import SCPClient

def ssh_connect(ip, username, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password)
    return ssh

def list_apps_by_container(ssh):
    print("[*] Listing apps from /var/containers/Bundle/Application...")
    cmd = r"find /var/containers/Bundle/Application -name '*.app' 2>/dev/null"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    apps = stdout.read().decode().strip().split('\n')
    if not apps or apps == ['']:
        print("[-] No apps found.")
        return []
    for i, app in enumerate(apps):
        print(f"{i + 1}. {app}")
    return apps

def extract_ipa(ssh, app_path):
    import os
    app_name = os.path.basename(app_path)
    bundle_id = app_name.replace(".app", "")
    temp_dir = f"/var/tmp/ipa_extract_{bundle_id}"
    ipa_name = f"{bundle_id}.ipa"

    print(f"[+] Using app path: {app_path}")
    commands = [
        f'rm -rf "{temp_dir}"',
        f'mkdir -p "{temp_dir}/Payload"',
        f'cp -r "{app_path}" "{temp_dir}/Payload/"',
        f'cd "{temp_dir}" && zip -qr "{ipa_name}" Payload'
    ]

    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        if stdout.channel.recv_exit_status() != 0:
            print(f"[-] Command failed: {cmd}")
            print(stderr.read().decode())
            return False

    with SCPClient(ssh.get_transport()) as scp:
        print(f"[+] Downloading {ipa_name}...")
        scp.get(f"{temp_dir}/{ipa_name}", ipa_name)

    ssh.exec_command(f'rm -rf "{temp_dir}"')
    print(f"[+] IPA saved: {ipa_name}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python extract_ipa.py <device_ip> <username> <password>")
        sys.exit(1)

    ip, username, password = sys.argv[1:4]
    try:
        ssh = ssh_connect(ip, username, password)
        apps = list_apps_by_container(ssh)
        if not apps:
            ssh.close()
            sys.exit(1)

        choice = int(input("Enter the number of the app to extract: "))
        if choice < 1 or choice > len(apps):
            print("[-] Invalid choice.")
            ssh.close()
            sys.exit(1)

        selected_app_path = apps[choice - 1]
        print(f"[+] Selected: {selected_app_path}")

        if not extract_ipa(ssh, selected_app_path):
            ssh.close()
            sys.exit(1)

        ssh.close()
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)
