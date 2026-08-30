"""Realistic fake command outputs for MOCK_MODE.

Lets the full attacker/defender pipeline be built and tested before the VMs
in docs/VM_SETUP.md exist. Each entry is keyed by a short tag; execute_command
in mock mode matches the command it is handed to one of these.
"""

from .config import ATTACKER_HOST, DEFENDER_HOST

# Keyed fake stdout blocks. Keep them shaped like the real tool output so the
# parsing/consumers do not have to special-case mock vs live.
MOCK_OUTPUTS = {
    "nmap_sv": (
        "Starting Nmap 7.80 ( https://nmap.org )\n"
        f"Nmap scan report for {DEFENDER_HOST}\n"
        "Host is up (0.00042s latency).\n"
        "PORT     STATE SERVICE VERSION\n"
        "22/tcp   open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.5\n"
        "80/tcp   open  http    Apache httpd 2.4.41 ((Ubuntu))\n"
        "3306/tcp open  mysql   MySQL 8.0.32\n"
        "Service detection performed. Nmap done: 1 IP address (1 host up)\n"
    ),
    "nmap_ports": (
        "Starting Nmap 7.80 ( https://nmap.org )\n"
        f"Nmap scan report for {DEFENDER_HOST}\n"
        "PORT     STATE SERVICE\n"
        "22/tcp   open  ssh\n"
        "80/tcp   open  http\n"
        "443/tcp  open  https\n"
        "3306/tcp open  mysql\n"
        "Nmap done: 1 IP address (1 host up) scanned\n"
    ),
    "auth_log": (
        f"Aug 29 13:42:01 defender-vm sshd[2011]: Failed password for root from {ATTACKER_HOST} port 51234 ssh2\n"
        f"Aug 29 13:42:03 defender-vm sshd[2011]: Failed password for root from {ATTACKER_HOST} port 51234 ssh2\n"
        f"Aug 29 13:42:07 defender-vm sshd[2013]: Failed password for admin from {ATTACKER_HOST} port 51240 ssh2\n"
        "Aug 29 13:45:22 defender-vm sshd[2050]: Accepted password for agentlens from 192.168.56.1 port 51888 ssh2\n"
    ),
    "listening_ports": (
        "State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
        "LISTEN 0      128          0.0.0.0:22        0.0.0.0:*     users:((\"sshd\",pid=812,fd=3))\n"
        "LISTEN 0      511          0.0.0.0:80        0.0.0.0:*     users:((\"apache2\",pid=901,fd=4))\n"
        "LISTEN 0      70         127.0.0.1:3306      0.0.0.0:*     users:((\"mysqld\",pid=1002,fd=21))\n"
    ),
    "failed_logins": (
        f"Aug 29 13:42:01 defender-vm sshd[2011]: Failed password for root from {ATTACKER_HOST} port 51234 ssh2\n"
        f"Aug 29 13:42:03 defender-vm sshd[2011]: Failed password for root from {ATTACKER_HOST} port 51234 ssh2\n"
        f"Aug 29 13:42:07 defender-vm sshd[2013]: Failed password for admin from {ATTACKER_HOST} port 51240 ssh2\n"
    ),
    "iptables_block": "",  # iptables -A prints nothing on success
    "processes": (
        "USER       PID %CPU %MEM    VSZ   RSS TTY STAT START   TIME COMMAND\n"
        "mysql     1002  4.1  6.2 1804200 51200 ?  Sl   13:30   0:14 /usr/sbin/mysqld\n"
        "www-data   901  1.3  1.1 214884  9020 ?    S    13:30   0:02 /usr/sbin/apache2 -k start\n"
        "root       812  0.0  0.4  72300  4100 ?    Ss   13:29   0:00 /usr/sbin/sshd -D\n"
        "root         1  0.0  0.2 168240 11200 ?    Ss   13:29   0:01 /sbin/init\n"
    ),
    "system_info": (
        "Linux defender-vm 5.4.0-152-generic #169-Ubuntu SMP x86_64 GNU/Linux\n"
        " 13:50:11 up  0:21,  1 user,  load average: 0.08, 0.03, 0.01\n"
    ),
    "syslog": (
        "Aug 29 13:49:01 defender-vm CRON[2140]: (root) CMD (command -v debian-sa1)\n"
        "Aug 29 13:49:33 defender-vm systemd[1]: Started Session 5 of user agentlens.\n"
        "Aug 29 13:50:02 defender-vm kernel: [ 1260.3] UFW BLOCK IN=enp0s3 SRC=192.168.56.101\n"
    ),
}


def mock_for(command: str) -> str:
    """Best-effort map a real shell command string to a mock output block."""
    c = command.lower()
    if "nmap" in c and "-sv" in c:
        return MOCK_OUTPUTS["nmap_sv"]
    if "nmap" in c and "-p" in c:
        return MOCK_OUTPUTS["nmap_ports"]
    if "failed password" in c:
        return MOCK_OUTPUTS["failed_logins"]
    if "auth.log" in c:
        return MOCK_OUTPUTS["auth_log"]
    if c.startswith("ss ") or "ss -tlnp" in c or "netstat" in c:
        return MOCK_OUTPUTS["listening_ports"]
    if "iptables" in c:
        return MOCK_OUTPUTS["iptables_block"]
    if c.startswith("ps ") or "ps aux" in c:
        return MOCK_OUTPUTS["processes"]
    if "uname" in c or "uptime" in c:
        return MOCK_OUTPUTS["system_info"]
    if "syslog" in c:
        return MOCK_OUTPUTS["syslog"]
    return f"[mock] no canned output for command: {command}"
