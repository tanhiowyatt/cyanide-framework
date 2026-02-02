import asyncio
import time
from .base import Command

import argparse

class CurlCommand(Command):
    async def execute(self, args, input_data=""):
        parser = argparse.ArgumentParser(prog="curl", add_help=False)
        parser.add_argument("-I", "--head", action="store_true")
        parser.add_argument("url", nargs="?")
        
        try:
            parsed, unknown = parser.parse_known_args(args)
        except SystemExit:
            return "", "", 1
            
        url = parsed.url
        if not url:
            # Check if url was in unknown or just missing
            if unknown: url = unknown[-1]
            else: return "", "curl: try 'curl --help' for more information\n", 1
            
        if parsed.head:
            output = f"HTTP/1.1 200 OK\nDate: {time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())}\nServer: Apache\nContent-Type: text/html; charset=UTF-8\nConnection: close\n\n"
        else:
            output = f"<html><body><h1>Fake Response from {url}</h1></body></html>\n"
        return output, "", 0

class PingCommand(Command):
    async def execute(self, args, input_data=""):
        parser = argparse.ArgumentParser(prog="ping", add_help=False)
        parser.add_argument("-c", "--count", type=int, default=4)
        parser.add_argument("host", nargs="?")
        
        try:
            parsed, unknown = parser.parse_known_args(args)
        except SystemExit:
            return "", "", 1
            
        host = parsed.host
        if not host:
             if unknown: host = unknown[-1]
             else: return "", "ping: usage error: Destination address required\n", 2
        
        count = parsed.count
        
        # Simulate pings
        out = f"PING {host} ({host}) 56(84) bytes of data.\n"
        for i in range(1, count + 1):
            out += f"64 bytes from {host}: icmp_seq={i} ttl=64 time=0.04{i} ms\n"
            
        out += f"\n--- {host} ping statistics ---\n"
        out += f"{count} packets transmitted, {count} received, 0% packet loss, time {count*1000}ms\n"
        return out, "", 0

class EditorCommand(Command):
    async def execute(self, args, input_data=""):
        # vi/nano mock
        # Simply clear screen and tell user it's a fake editor or just exit
        # Real honeypots might allow editing a temp buffer.
        # For now, just print error or clear screen simulation.
        # But this command is synchronous... 
        # We can't interact. 
        # So we just say "Error: terminal not fully interactive" or similar, 
        # or fake it by printing a "saved" message if a filename is given.
        
        if args:
            filename = args[0]
            # fake save
            return f"Saved {filename}.\n", "", 0
        return "No filename specified.\n", "", 1
