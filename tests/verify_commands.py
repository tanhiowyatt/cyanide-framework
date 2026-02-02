import asyncio
import sys
import os
import json
from pathlib import Path

# Add project root to python path
sys.path.append(os.getcwd())

from src.core.fake_filesystem import FakeFilesystem
from src.core.shell_emulator import ShellEmulator

class Verifier:
    def __init__(self):
        self.results = []
        self.fs = FakeFilesystem()
        self.shell = ShellEmulator(self.fs, "root")

    async def run_test(self, category, test_case):
        command = test_case["command"]
        expect = test_case["expect"]
        
        stdout, stderr, rc = await self.shell.execute(command)
        
        # Validation
        passed = True
        reason = []
        
        if isinstance(expect, str):
            if expect and expect not in stdout and expect not in stderr:
                passed = False
                reason.append(f"Expected string '{expect}' not found in output")
        elif isinstance(expect, list):
            for e in expect:
                if e.startswith("!"):
                    val = e[1:]
                    if val in stdout or val in stderr:
                        passed = False
                        reason.append(f"Excluded string '{val}' found in output")
                else:
                    if e not in stdout and e not in stderr:
                        passed = False
                        reason.append(f"Expected string '{e}' not found in output")
        
        # If expect is empty string, we just care that it didn't fail with 'command not found' 
        # unless it was intended? Typically empty expect means we don't care about stdout
        # but rc should be 0 usually.
        if rc != 0 and not expect:
             # Basic sanity: if no expectation provided, assume it should succeed (rc=0)
             # unless the command itself is designed to fail? 
             # For this dataset, we'll assume rc=0 for success.
             passed = False
             reason.append(f"Command failed with non-zero exit code {rc}")

        res = {
            "category": category,
            "command": command,
            "passed": passed,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "rc": rc,
            "reasons": reason
        }
        self.results.append(res)
        return passed

    async def run_all(self, dataset_path):
        with open(dataset_path, "r") as f:
            dataset = json.load(f)
            
        print(f"{'CATEGORY':<20} | {'COMMAND':<40} | {'STATUS'}")
        print("-" * 80)
        
        for category, tests in dataset.items():
            for test in tests:
                status = await self.run_test(category, test)
                status_str = "PASS" if status else "FAIL"
                print(f"{category:<20} | {test['command']:<40} | {status_str}")
                
        self.generate_report()

    def generate_report(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        
        print("\n" + "="*80)
        print(f"VERIFICATION SUMMARY: {passed}/{total} Passed")
        print("="*80)
        
        if passed < total:
            print("\nFailures:")
            for r in self.results:
                if not r["passed"]:
                    print(f"[{r['category']}] {r['command']}")
                    for reason in r["reasons"]:
                        print(f"  - {reason}")
                    if r['stderr']:
                        print(f"  STDERR: {r['stderr']}")
        
        # Also save to JSON for walkthrough artifact
        with open("tests/verification_results.json", "w") as f:
            json.dump({
                "summary": {"total": total, "passed": passed},
                "results": self.results
            }, f, indent=2)

if __name__ == "__main__":
    dataset_file = "tests/command_dataset.json"
    if not os.path.exists(dataset_file):
        print(f"Dataset not found: {dataset_file}")
        sys.exit(1)
        
    asyncio.run(Verifier().run_all(dataset_file))
