# VM_SETUP.md — AgentLens Cyber Scenario

There are **two setup paths**:

- **Path A — Calix SeedLabs PoC (start here).** A single Ubuntu VM over NAT with
  SSH port-forwarded to `127.0.0.1:2222`. This replicates Dr. Calix's YouTube
  walkthrough exactly and clears his minimum bar: *"SSH into the VM and ping
  8.8.8.8."* Proven by `agents/vm_proof_of_concept.py`.
- **Path B — full attacker/defender lab.** Two VMs on an isolated host-only
  network (`192.168.56.101/102`). This is what the `tools/cyber/` suite
  (`config.py`, `cyber_agent.py`) is wired for. Build it once Path A works.

> ⚠️ **Credentials/addresses differ between the two paths.** Path A uses
> `seed` / `dees` at `127.0.0.1:2222` (NAT). Path B uses `agentlens` /
> `agentlens123` at `192.168.56.101/102` (host-only). The PoC script hard-codes
> Path A; the tool suite reads Path B from `tools/cyber/config.py`. Reconcile
> these before pointing the full suite at a real VM.

> ⚠️ **Isolation / authorization.** These VMs are a personal lab you own. Keep
> offensive tooling (`nmap`, `iptables`, failed-login probing) pointed only at
> your own VMs. `ping 8.8.8.8` over NAT is the one deliberate outbound test.

---

# Path A — Calix SeedLabs PoC (single VM, NAT, port 2222)

## A.1 Download the VM
- Download the **SeedLabs Ubuntu 20.04 VM** (~4 GB zip) from
  <https://seedsecuritylabs.org/labsetup.html>.
- Prefer the **Digital Ocean mirror** (faster than the primary).
- Default credentials: **username `seed`, password `dees`**.
- *Alternative:* a standard Ubuntu 20.04 ISO works too (then create your own
  user; the PoC script's credentials would need to match).

## A.2 VirtualBox configuration
Create/import the VM with exactly these settings:

| Setting | Value |
|---|---|
| Name | `agentlens-vm` (or `attacker-vm` / `defender-vm`) |
| RAM | 2048 MB |
| CPUs | 2 |
| Video memory | 58 MB minimum |
| Network — Adapter 1 | **NAT** (NOT bridged, NOT host-only) |
| Storage | **Map the existing VDI file** from the downloaded zip |

## A.3 Port forwarding (Calix's exact config — critical)
VM **Settings → Network → Adapter 1 → NAT → Advanced → Port Forwarding**, add:

| Field | Value |
|---|---|
| Name | `SSH` |
| Protocol | `TCP` |
| Host IP | `127.0.0.1` |
| Host Port | `2222` |
| Guest IP | *(leave blank)* |
| Guest Port | `22` |

This maps `127.0.0.1:2222` on the Windows host to port 22 inside the VM.

## A.4 Enable SSH inside the VM
Boot the VM, open a terminal, and run:
```bash
sudo ufw disable
sudo service ssh start
netstat -na | grep tcp
```
Confirm a line shows port **22** in state **LISTEN** (e.g.
`tcp  0  0  0.0.0.0:22  0.0.0.0:*  LISTEN`).

> If `ssh` is not installed on a plain Ubuntu image:
> `sudo apt update && sudo apt install -y openssh-server`, then re-run
> `sudo service ssh start`.

## A.5 Test SSH from Windows (PuTTY)
Open **PuTTY** with:

| Field | Value |
|---|---|
| Host Name | `127.0.0.1` |
| Port | `2222` |
| Login | `seed` |
| Password | `dees` |

You should land on a shell inside the VM. This is the manual version of the
next step.

## A.6 Prove it programmatically
Run the proof-of-concept, which SSHes in with paramiko, runs Calix's tests
(`ping -c 3 8.8.8.8`, `ifconfig`, `ls -l`, `uname -a`), logs each to
`data/trajectories/real_vm_logs.csv`, and prints **`VM CONNECTION SUCCESSFUL`**:
```bash
python agents/vm_proof_of_concept.py
```
If the VM is not running or port forwarding is misconfigured, the script prints:
```
VM not reachable at 127.0.0.1:2222
Follow docs/VM_SETUP.md to configure VirtualBox first
```

---

# Path B — Full attacker/defender lab (two VMs, host-only)

The `tools/cyber/` suite drives two VMs on an isolated host-only network.
Build this after Path A works.

## B.0 Prerequisites
- Virtualization enabled in BIOS/UEFI (VT-x / AMD-V).
- ~20 GB free disk, 4 GB+ RAM to spare (2 GB per VM).

## B.1 Install VirtualBox
1. Install VirtualBox from <https://www.virtualbox.org> (default options install
   the host-only network driver).
2. Get the **Ubuntu 20.04 LTS Server** ISO from
   <https://releases.ubuntu.com/20.04/> (server is enough).

## B.2 Create the host-only network (192.168.56.0/24)
VirtualBox → **Tools → Network → Host-only Networks → Create**:
- Adapter IPv4 address: `192.168.56.1`, mask `255.255.255.0`
- **Disable** the DHCP server (we assign static IPs). `vboxnet0` is often
  pre-created with this range; reuse it if present.

## B.3 Create the two VMs
For each of **attacker-vm** then **defender-vm**:
1. **Machine → New**: Type Linux, Version Ubuntu (64-bit), 2048 MB RAM, 20 GB
   dynamically-allocated disk.
2. **Settings → Network → Adapter 1**: **Host-only Adapter** → the
   `192.168.56.0/24` network. *(Add a temporary NAT adapter 2 only while
   installing packages, then disable it.)*
3. **Settings → Storage**: attach the Ubuntu 20.04 ISO.
4. Install Ubuntu Server (create the `agentlens` user during install — see B.5).

## B.4 Assign static IPs (netplan)
Find the host-only interface with `ip a` (often `enp0s3`), then edit netplan.

**attacker-vm** → `/etc/netplan/00-installer-config.yaml`:
```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: no
      addresses: [192.168.56.101/24]
```
**defender-vm** → same file with `192.168.56.102/24`. Apply on both:
`sudo netplan apply`

| VM | Host-only IP |
|---|---|
| attacker-vm | 192.168.56.101 |
| defender-vm | 192.168.56.102 |

## B.5 Create the dedicated user (BOTH VMs)
```bash
sudo adduser agentlens          # password: agentlens123
sudo usermod -aG sudo agentlens # defender needs sudo for iptables
```
> For unattended `block_ip`, allow passwordless sudo for just that command
> (defender-vm only):
> ```bash
> echo 'agentlens ALL=(ALL) NOPASSWD: /usr/sbin/iptables' | sudo tee /etc/sudoers.d/agentlens
> ```

## B.6 Enable SSH (BOTH VMs)
```bash
sudo apt update && sudo apt install -y openssh-server
sudo systemctl enable ssh && sudo systemctl start ssh
sudo systemctl status ssh      # "active (running)"
```

## B.7 Install per-role tools
```bash
# attacker-vm
sudo apt install -y nmap
# defender-vm
sudo apt install -y iproute2 procps iptables
```
Then disable the temporary NAT adapter so the lab is isolated.

## B.8 Verify connectivity & SSH
```bash
# from attacker-vm
ping -c 3 192.168.56.102
ssh agentlens@192.168.56.102    # password: agentlens123
```

## B.9 Point AgentLens at the VMs
1. In `tools/cyber/__init__.py` set `MOCK_MODE = False` (or export
   `AGENTLENS_MOCK=0` — the env var wins).
2. Confirm coordinates in `tools/cyber/config.py`
   (`ATTACKER_HOST=192.168.56.101`, `DEFENDER_HOST=192.168.56.102`, user
   `agentlens`; override via `AGENTLENS_SSH_USER` / `AGENTLENS_SSH_PASS`).
3. Smoke test: `python agents/cyber_agent.py`

If a tool raises `SSH error`, re-check B.6 (sshd running) and B.8 (ping works).
