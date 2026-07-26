# lollo-k3s-ops 🚀

My personal **GitOps-managed Cloud Infrastructure**. This repository manages a **k3s** cluster on **Hetzner Cloud** using **FluxCD**, serving as both a private media hub and a portfolio for my personal projects.

## 🌟 Key Features

### 🎧 Private Spotify Alternative
A fully automated music pipeline that allows me to stream my library anywhere via **Tailscale**:
1. **Download**: Audio is sourced via **MeTube** or **SpotDL**.
2. **Auto-Tag**: A custom **Python Tagger** (CronJob) automatically fixes metadata and adds cover art using the MusicBrainz API.
3. **Stream**: **Navidrome** serves the library to my phone/desktop, providing a Spotify-like experience without the subscription.
4. **Access**: Secure, seamless connection through a **Tailscale** mesh network.

### 🕹️ Personal Projects Portfolio
The cluster hosts my custom-built applications, demonstrating full-stack Kubernetes deployment:
- **Tris Inception**: A full-stack game consisting of a React frontend, a Node.js backend, and a PostgreSQL database, all orchestrated with dedicated Kubernetes manifests.

## 🏗️ Technical Stack
- **Infrastructure**: k3s on Ubuntu (Hetzner Cloud).
- **Automation**: FluxCD for GitOps synchronization.
- **Security**: Tailscale (Private Mesh), Let's Encrypt (TLS), and SOPS (Secret Management).
- **Ingress**: Traefik with Cert-Manager.

## 📂 Project Structure
- `apps/`: 
    - `music-server/`: The automated media stack.
    - `tris-game/`: Full-stack "Tris Inception" project.
- `infrastructure/`: Shared services (Tailscale, Cert-Manager).
- `clusters/`: Environment-specific configurations.

## 🛠️ Operations

### Cluster Access
1. `scp root@<ip>:/etc/rancher/k3s/k3s.yaml ~/.kube/config-lollo`
2. Update `server` to the Tailscale IP.
3. `export KUBECONFIG=~/.kube/config-lollo`

### Manual Tagging
```bash
kubectl -n music-server create job --from=cronjob/music-tagger manual-tagging-$(date +%s)
```

### 💾 Host Storage Setup (Btrfs Quotas & NOCOW)

The persistent storage disk (`/mnt/das-storage`) uses **Btrfs**. To ensure service isolation and prevent database fragmentation, the host storage is configured with Btrfs Subvolumes, Quotas (`qgroup`), and NOCOW (`chattr +C`).

#### 1. Btrfs Subvolumes & Quotas
Subvolumes isolate Immich and Seafile and enforce strict disk space limits to prevent one service from filling the host disk:
```bash
# Enable quota management on the Btrfs mount
sudo btrfs quota enable /mnt/das-storage

# Set hard quota limits (700GB for Immich, 1000GB for Seafile)
sudo btrfs qgroup limit 700G /mnt/das-storage/immich/library
sudo btrfs qgroup limit 1000G /mnt/das-storage/seafile/data

# Check quota usage and limits
sudo btrfs qgroup show -p /mnt/das-storage
```

#### 2. Database NOCOW Configuration (`chattr +C`)
Btrfs Copy-on-Write (CoW) causes severe disk fragmentation and performance degradation for write-heavy databases (PostgreSQL and MariaDB). NOCOW (`+C`) is set on the database directories:
```bash
# Disable CoW on PostgreSQL (Immich) and MariaDB (Seafile) directories
sudo chattr +C /mnt/das-storage/immich/postgres
sudo chattr +C /mnt/das-storage/seafile/db

# Verify that the 'C' attribute is active
lsattr -d /mnt/das-storage/immich/postgres /mnt/das-storage/seafile/db
```
> **Note**: `chattr +C` must be applied to empty directories before files are written into them.

