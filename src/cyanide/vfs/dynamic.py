import datetime
import secrets
import time
from typing import Any, Dict, Optional


def uptime_provider(context: Any, args: Optional[Dict[str, Any]] = None) -> str:
    """Returns a realistic uptime string."""
    start_time = time.time() - secrets.SystemRandom().randint(3600, 86400 * 30)
    uptime_sec = time.time() - start_time
    idle_sec = uptime_sec * 0.9
    return f"{uptime_sec:.2f} {idle_sec:.2f}\n"


def cpuinfo_provider(context: Any, args: Optional[Dict[str, Any]] = None) -> str:
    """Returns a fake cpuinfo string, using profile template if available."""
    if hasattr(context, "system_templates") and context.system_templates:
        tpl = context.system_templates.get("cpuinfo")
        if tpl:
            return str(tpl)
    return """processor\t: 0
vendor_id\t: GenuineIntel
cpu family\t: 6
model\t\t: 158
model name\t: Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz
stepping\t: 10
microcode\t: 0xca
cpu MHz\t\t: 3696.000
cache size\t: 12288 KB
flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb invpcid_single pti ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 hle avx2 smep bmi2 erms invpcid rtm mpx rdseed adx smap clflushopt intel_pt xsaveopt xsavec xgetbv1 xsaves dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp md_clear flush_l1d
bugs\t\t: cpu_meltdown spectre_v1 spectre_v2 spec_store_bypass l1tf mds swapgs taa itlb_multihit srbds
bogomips\t: 7392.00
clflush size\t: 64
cache_alignment\t: 64
address sizes\t: 39 bits physical, 48 bits virtual
power management:
"""


LAST_LOGINS: Dict[str, str] = {}


def motd_provider(context: Any, args: Optional[Dict[str, Any]] = None) -> str:
    """Returns a realistic OS-specific MOTD banner."""
    args = args or {}
    src_ip = str(args.get("src_ip", ""))

    os_name = getattr(context, "os_name", "Ubuntu 22.04.1 LTS")
    kernel = getattr(context, "kernel_version", "5.15.0-41-generic")
    arch = getattr(context, "arch", "x86_64")

    banner_parts = ["\r\n"]

    if "Ubuntu" in os_name:
        banner_parts.append(f"Welcome to {os_name} (GNU/Linux {kernel} {arch})\r\n\r\n")
        banner_parts.append(" * Documentation:  https://help.debian.com\r\n")
        banner_parts.append(" * Management:     https://landscape.canonical.com\r\n")
        banner_parts.append(" * Support:        https://debian.com/advantage\r\n")
    elif "CentOS" in os_name:
        banner_parts.append(f"Welcome to {os_name} (GNU/Linux {kernel} {arch})\r\n\r\n")
        banner_parts.append(" * Documentation:  https://docs.centos.org\r\n")
        banner_parts.append(" * Community:      https://www.centos.org/community/\r\n")
    elif "Debian" in os_name:
        banner_parts.append(f"Welcome to {os_name} (GNU/Linux {kernel} {arch})\r\n\r\n")
        banner_parts.append(" * Documentation:  https://www.debian.org/doc/\r\n")
        banner_parts.append(" * Support:        https://www.debian.org/support\r\n")
    else:
        banner_parts.append(f"Welcome to {os_name} ({kernel} {arch})\r\n")

    now = datetime.datetime.now()
    last_login_date = now - datetime.timedelta(days=secrets.SystemRandom().randint(1, 10))
    date_str = last_login_date.strftime("%a %b %d %H:%M:%S %Y")

    last_ip = LAST_LOGINS.get(src_ip)
    if not last_ip:
        mgmt_ips = ["192.168.1.10", "192.168.1.25", "10.0.0.5", "172.168.5.20"]
        last_ip = secrets.SystemRandom().choice(mgmt_ips)

    if src_ip:
        LAST_LOGINS[src_ip] = src_ip

    banner_parts.append(f"\r\nLast login: {date_str} from {last_ip}\r\n")

    return "".join(banner_parts)


def meminfo_provider(context: Any, args: Optional[Dict[str, Any]] = None) -> str:
    """Returns a fake meminfo string, using profile template if available."""
    if hasattr(context, "system_templates") and context.system_templates:
        tpl = context.system_templates.get("meminfo")
        if tpl:
            return str(tpl)
    return """MemTotal:        8165972 kB
MemFree:         1245620 kB
MemAvailable:    5642312 kB
Buffers:          210452 kB
Cached:          4123564 kB
SwapCached:            0 kB
Active:          3120452 kB
Inactive:        2845612 kB
Active(anon):    1564212 kB
Inactive(anon):   845612 kB
Active(file):    1556240 kB
Inactive(file):  2000000 kB
Unevictable:           0 kB
Mlocked:               0 kB
SwapTotal:       2097148 kB
SwapFree:        2097148 kB
Dirty:                44 kB
Writeback:             0 kB
AnonPages:       2410000 kB
Mapped:           542124 kB
Shmem:             42124 kB
KReclaimable:     210452 kB
Slab:             412356 kB
SReclaimable:     210452 kB
SUnreclaim:       201904 kB
KernelStack:       10452 kB
PageTables:        41235 kB
NFS_Unstable:          0 kB
Bounce:                0 kB
WritebackTmp:          0 kB
CommitLimit:     6180132 kB
Committed_AS:    4123564 kB
VmallocTotal:   34359738367 kB
VmallocUsed:       41235 kB
VmallocChunk:          0 kB
Percpu:             4564 kB
HardwareCorrupted:     0 kB
AnonHugePages:         0 kB
ShmemHugePages:        0 kB
ShmemPmdMapped:        0 kB
FileHugePages:         0 kB
FilePmdMapped:         0 kB
HugePages_Total:       0
HugePages_Free:        0
HugePages_Rsvd:        0
HugePages_Surp:        0
Hugepagesize:       2048 kB
Hugetlb:               0 kB
DirectMap4k:      210452 kB
DirectMap2M:     6123564 kB
DirectMap1G:     2123564 kB
"""


def shadow_provider(context: Any, args: Optional[Dict[str, Any]] = None) -> str:
    """Returns a fake shadow file with realistic password hashes."""
    # Standard Linux users with realistic (but fake/randomized) password hashes
    lines = [
        "root:$6$8w3z.1xO$E6E1pYkG/r1XWvXzX6P...:19000:0:99999:7:::",
        "daemon:*:18500:0:99999:7:::",
        "bin:*:18500:0:99999:7:::",
        "sys:*:18500:0:99999:7:::",
        "sync:*:18500:0:99999:7:::",
        "games:*:18500:0:99999:7:::",
        "man:*:18500:0:99999:7:::",
        "lp:*:18500:0:99999:7:::",
        "mail:*:18500:0:99999:7:::",
        "news:*:18500:0:99999:7:::",
        "uucp:*:18500:0:99999:7:::",
        "proxy:*:18500:0:99999:7:::",
        "www-data:*:18500:0:99999:7:::",
        "backup:*:18500:0:99999:7:::",
        "list:*:18500:0:99999:7:::",
        "irc:*:18500:0:99999:7:::",
        "gnats:*:18500:0:99999:7:::",
        "nobody:*:18500:0:99999:7:::",
        "admin:$6$V4x0...:19000:0:99999:7:::",
    ]
    return "\n".join(lines) + "\n"


def processes_provider(context: Any, args: Optional[Dict[str, Any]] = None) -> str:
    """Returns a realistic process list as JSON, using profile template if available."""
    import json

    if hasattr(context, "system_templates") and context.system_templates:
        tpl = context.system_templates.get("processes")
        if tpl:
            return json.dumps(tpl)

    processes = [
        {
            "pid": 1,
            "tty": "?",
            "time": "00:00:15",
            "cmd": "/sbin/init",
            "user": "root",
        },
        {
            "pid": 2,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[kthreadd]",
            "user": "root",
        },
        {
            "pid": 3,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[rcu_gp]",
            "user": "root",
        },
        {
            "pid": 4,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[rcu_par_gp]",
            "user": "root",
        },
        {
            "pid": 5,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[kworker/0:0-events]",
            "user": "root",
        },
        {
            "pid": 6,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[kworker/0:0H-kblockd]",
            "user": "root",
        },
        {
            "pid": 7,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[mm_percpu_wq]",
            "user": "root",
        },
        {
            "pid": 8,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[ksoftirqd/0]",
            "user": "root",
        },
        {
            "pid": 9,
            "tty": "?",
            "time": "00:00:02",
            "cmd": "[rcu_sched]",
            "user": "root",
        },
        {
            "pid": 10,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[migration/0]",
            "user": "root",
        },
        {
            "pid": 11,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[cpuhp/0]",
            "user": "root",
        },
        {
            "pid": 12,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[kdevtmpfs]",
            "user": "root",
        },
        {
            "pid": 13,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[netns]",
            "user": "root",
        },
        {
            "pid": 14,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[kauditd]",
            "user": "root",
        },
        {
            "pid": 15,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[khungtaskd]",
            "user": "root",
        },
        {
            "pid": 16,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[oom_reaper]",
            "user": "root",
        },
        {
            "pid": 17,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[writeback]",
            "user": "root",
        },
        {
            "pid": 18,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[kcompactd0]",
            "user": "root",
        },
        {
            "pid": 19,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[ksmd]",
            "user": "root",
        },
        {
            "pid": 20,
            "tty": "?",
            "time": "00:00:00",
            "cmd": "[khugepaged]",
            "user": "root",
        },
    ]
    return json.dumps(processes)


PROVIDERS = {
    "uptime_provider": uptime_provider,
    "cpuinfo_provider": cpuinfo_provider,
    "motd_provider": motd_provider,
    "meminfo_provider": meminfo_provider,
    "shadow_provider": shadow_provider,
    "processes_provider": processes_provider,
}
