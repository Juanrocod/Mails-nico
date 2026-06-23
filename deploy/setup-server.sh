#!/bin/bash
# =============================================================================
# Setup script for Oracle Cloud VM — Gestión de Minutas
# Run as: ssh -i key.pem ubuntu@<IP> 'bash -s' < setup-server.sh
# =============================================================================
set -euo pipefail

echo "=== Actualizando sistema ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== Instalando Docker ==="
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== Configurando Docker para usuario ubuntu ==="
sudo usermod -aG docker ubuntu

echo "=== Abriendo puertos en iptables ==="
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save

echo "=== Instalando Git ==="
sudo apt-get install -y git

echo ""
echo "=========================================="
echo "  Setup completo!"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "  1. Desconectate y reconectate (para que el grupo docker tome efecto):"
echo "     ssh -i key.pem ubuntu@<IP>"
echo ""
echo "  2. Cloná el repo:"
echo "     git clone https://github.com/TU_USUARIO/Gestion-Mails.git"
echo "     cd Gestion-Mails"
echo ""
echo "  3. Creá el .env:"
echo "     cp deploy/.env.production .env"
echo "     nano .env  # editá las claves"
echo ""
echo "  4. Levantá todo:"
echo "     docker compose up --build -d"
echo ""
echo "  5. Corré las migraciones:"
echo "     docker compose exec backend alembic upgrade head"
echo ""
echo "  6. Creá el primer usuario:"
echo "     docker compose exec backend python create_invite.py invite"
echo ""
