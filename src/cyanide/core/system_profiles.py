"""
OS Profiles for Cyanide Honeypot.
Defines consistent sets of system information to mimic specific OS versions.
"""

PROFILES = {
    "ubuntu_22_04": {
        "name": "Ubuntu 22.04 LTS",
        "ssh_banner": "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6",
        "uname_r": "5.15.0-91-generic",
        "uname_a": "Linux server 5.15.0-91-generic #101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux",
        "etc_issue": "Ubuntu 22.04.3 LTS \\n \\l\n\n",
        "proc_version": "Linux version 5.15.0-91-generic (buildd@lcy02-amd64-015) (gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0, GNU ld (GNU Binutils for Ubuntu) 2.38) #101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023\n"
    },
    "debian_11": {
        "name": "Debian 11 (Bullseye)",
        "ssh_banner": "SSH-2.0-OpenSSH_8.4p1 Debian-5+deb11u3",
        "uname_r": "5.10.0-28-amd64",
        "uname_a": "Linux server 5.10.0-28-amd64 #1 SMP Debian 5.10.209-2 (2024-01-31) x86_64 GNU/Linux",
        "etc_issue": "Debian GNU/Linux 11 \\n \\l\n\n",
        "proc_version": "Linux version 5.10.0-28-amd64 (debian-kernel@lists.debian.org) (gcc-10 (Debian 10.2.1-6) 10.2.1 20210110, GNU ld (GNU Binutils for Debian) 2.35.2) #1 SMP Debian 5.10.209-2 (2024-01-31)\n"
    },
    "centos_7": {
        "name": "CentOS 7",
        "ssh_banner": "SSH-2.0-OpenSSH_7.4",
        "uname_r": "3.10.0-1160.108.1.el7.x86_64",
        "uname_a": "Linux server 3.10.0-1160.108.1.el7.x86_64 #1 SMP Thu Jan 25 16:17:31 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux",
        "etc_issue": "\\S\nKernel \\r on an \\m\n\n",
        "proc_version": "Linux version 3.10.0-1160.108.1.el7.x86_64 (mockbuild@kbuilder.bsys.centos.org) (gcc version 4.8.5 20150623 (Red Hat 4.8.5-44) (GCC) ) #1 SMP Thu Jan 25 16:17:31 UTC 2024\n"
    }
}
