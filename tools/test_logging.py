import asyncio
import asyncssh
import sys

async def run_client():
    try:
        async with asyncssh.connect('localhost', port=2222, username='root', password='admin', known_hosts=None) as conn:
            print("Connected!")
            # Trigger some activity
            await conn.run('ls -la')
            await conn.run('whoami')
            # Trigger anomaly
            await conn.run('A'*200)
            print("Activity completed.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_client())
