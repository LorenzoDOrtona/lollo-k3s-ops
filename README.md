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
