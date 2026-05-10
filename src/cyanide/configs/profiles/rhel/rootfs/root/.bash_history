root@rhel-server-01 ~ # cat /etc/redhat-release
Red Hat Enterprise Linux release 9.3 (Plow)
root@rhel-server-01 ~ # uname -a
Linux rhel-server-01 5.14.0-362.8.1.el9_3.x86_64 #1 SMP PREEMPT_DYNAMIC Tue Nov 7 07:14:44 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux
root@rhel-server-01 ~ # id
uid=0(root) gid=0(root) groups=0(root)
root@rhel-server-01 ~ # ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 52:54:00:ab:cd:ef brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.100/24 brd 192.168.1.255 scope global noprefixroute eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::5054:ff:feab:cdef/64 scope link
       valid_lft forever preferred_lft forever
root@rhel-server-01 ~ # df -h
Filesystem                   Size  Used Avail Use% Mounted on
devtmpfs                     4.0M     0  4.0M   0% /dev
tmpfs                        1.8G     0  1.8G   0% /dev/shm
tmpfs                        720M  9.7M  710M   2% /run
/dev/mapper/rhel-root         70G  4.2G   66G   6% /
/dev/sda1                   1014M  286M  729M  29% /boot
/dev/mapper/rhel-home         10G  172M  9.9G   2% /home
tmpfs                        360M     0  360M   0% /run/user/0
root@rhel-server-01 ~ # ps aux | head
USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root           1  0.0  0.1 171488 12408 ?        Ss   Mar24   0:15 /usr/lib/systemd/systemd --switched-root --system --deserialize 31
root           2  0.0  0.0      0     0 ?        S    Mar24   0:00 [kthreadd]
root           3  0.0  0.0      0     0 ?        I<   Mar24   0:00 [rcu_gp]
root         850  0.0  0.1 590888 13000 ?        Ssl  Mar24   0:07 /usr/sbin/NetworkManager --no-daemon
root        1245  0.0  0.0  16236  5384 ?        Ss   Mar24   0:00 /usr/sbin/sshd -D
root        1901  0.0  0.0 228024  4848 ?        Ss   Mar24   0:00 /usr/sbin/crond -n
root@rhel-server-01 ~ # systemctl status sshd
● sshd.service - OpenSSH server daemon
     Loaded: loaded (/usr/lib/systemd/system/sshd.service; enabled; preset: enabled)
     Active: active (running) since Sun 2024-03-24 14:32:15 UTC; 42 days 14h ago
       Docs: man:sshd(8)
             man:sshd_config(5)
   Main PID: 1245 (sshd)
      Tasks: 1 (limit: 23163)
     Memory: 5.2M
        CPU: 253ms
     CGroup: /system.slice/sshd.service
             └─1245 "sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups"
root@rhel-server-01 ~ # tail -n 5 /var/log/secure
Mar 25 02:13:44 rhel-server-01 sshd[7100]: Accepted password for admin from 192.168.1.50 port 58222 ssh2
Mar 25 02:14:01 rhel-server-01 sudo[7112]:    admin : TTY=pts/1 ; PWD=/home/admin ; USER=root ; COMMAND=/bin/bash
root@rhel-server-01 ~ # exit
logout
