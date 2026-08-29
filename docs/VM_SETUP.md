# VM_SETUP.md — AgentLens Cyber Scenario

Two Ubuntu VMs on an isolated host-only network. The **attacker-vm** runs
reconnaissance tools against the **defender-vm**; the defender inspects its
own logs and firewall. Both are driven over SSH by `agents/cyber_agent.py`.

> ⚠️ **Isolation is mandatory.** Use a **host-only** network so the lab cannot
> reach the internet or your LAN. `nmap`, `iptables` and failed-login probing
> against anything you do not own is out of scope for this project. Snapshot
> both VMs after setup so you can roll back.

---

## 0. Prerequisites
- A host machine with virtualization enabled in BIOS/UEFI (VT-x / AMD-V).
- ~20 GB free disk, 4 GB+ RAM to spare (2 GB per VM).

---

## 1. Install VirtualBox
1. Download VirtualBox for your host OS from <https://www.virtualbox.org>.
2. Install it with default options (this also installs the host-only network driver).
3. Download the **Ubuntu 20.04 LTS Server** ISO from
   <https://releases.ubuntu.com/20.04/> (server is enough — no desktop needed).

---

## 2. Create the host-only network (192.168.56.0/24)
VirtualBox → **Tools → Network → Host-only Networks → Create**:
- Adapter IPv4 address: `192.168.56.1`, mask `255.255.255.0`
- **Disable** the DHCP server for this network (we assign static IPs).

VirtualBox usually pre-creates `vboxnet0` with exactly this range; reuse it if present.

---

## 3. Create the two VMs
Repeat for each VM. Names: **attacker-vm**, then **defender-vm**.

1. **Machine → New**: Name `attacker-vm`, Type Linux, Version Ubuntu (64-bit),
   2048 MB RAM, 20 GB dynamically-allocated disk.
2. **Settings → Network**:
   - Adapter 1: **Host-only Adapter** → the `192.168.56.0/24` network above.
     *(This is the only adapter the lab needs. Add a temporary NAT adapter 2
     only while installing packages, then disable it.)*
3. **Settings → Storage**: attach the Ubuntu 20.04 ISO to the optical drive.
4. Start the VM and install Ubuntu Server (defaults are fine; you can create
   the `agentlens` user during install — see §5).

---

## 4. Assign static IPs (netplan)
On each VM, find the host-only interface name with `ip a` (often `enp0s3`),
then edit netplan.

**attacker-vm** → `/etc/netplan/00-installer-config.yaml`:
```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: no
      addresses: [192.168.56.101/24]
```

**defender-vm** → same file:
```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: no
      addresses: [192.168.56.102/24]
```

Apply on both: `sudo netplan apply`

| VM | Host-only IP |
|---|---|
| attacker-vm | 192.168.56.101 |
| defender-vm | 192.168.56.102 |

---

## 5. Create the dedicated user (on BOTH VMs)
```bash
sudo adduser agentlens          # set password: agentlens123
sudo usermod -aG sudo agentlens # defender needs sudo for iptables
```

> ⚠️ `agentlens123` is a throwaway lab credential. Never reuse it, and never
> expose these VMs to a routable network. For unattended `block_ip`, allow
> passwordless sudo for just that command (defender-vm only):
> ```bash
> echo 'agentlens ALL=(ALL) NOPASSWD: /usr/sbin/iptables' | sudo tee /etc/sudoers.d/agentlens
> ```

---

## 6. Enable SSH (on BOTH VMs)
```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh
sudo systemctl status ssh      # should read "active (running)"
```

---

## 7. Install the tools each role needs
**attacker-vm** (recon):
```bash
sudo apt install -y nmap
```
**defender-vm** (inspection — mostly preinstalled on Ubuntu):
```bash
sudo apt install -y iproute2 procps iptables
```
Once packages are installed, disable the temporary NAT adapter (§3.2) so the
lab is fully isolated.

---

## 8. Verify connectivity
From **attacker-vm**:
```bash
ping -c 3 192.168.56.102        # reach the defender
```
From **defender-vm**:
```bash
ping -c 3 192.168.56.101        # reach the attacker
```

## 9. Verify SSH
From **attacker-vm**:
```bash
ssh agentlens@192.168.56.102    # password: agentlens123
```
You should land on the defender's shell. `exit` to return.

---

## 10. Point AgentLens at the VMs
The tool suite ships with `MOCK_MODE = True` so the whole pipeline runs with
no VMs. Once the lab above is verified, flip it to live:

1. In `tools/cyber/__init__.py` set `MOCK_MODE = False`
   (or export `AGENTLENS_MOCK=0` — the env var wins over the file default).
2. Confirm the host coordinates match `tools/cyber/config.py`:
   - `ATTACKER_HOST = 192.168.56.101`
   - `DEFENDER_HOST = 192.168.56.102`
   - user `agentlens`, password `agentlens123` (override via the
     `AGENTLENS_SSH_USER` / `AGENTLENS_SSH_PASS` env vars).
3. Smoke test: `python agents/cyber_agent.py`

If a tool raises `SSH error`, re-check §6 (sshd running) and §8 (ping works).
