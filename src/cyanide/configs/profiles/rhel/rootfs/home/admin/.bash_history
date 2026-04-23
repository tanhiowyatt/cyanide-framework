cat /etc/redhat-release
sudo yum install -y vim
vi /etc/ssh/sshd_config
sudo systemctl restart sshd
sudo systemctl status sshd
ls -la ~/.ssh/
cat ~/.ssh/authorized_keys
ssh-keygen -t rsa -b 4096 -C "admin@rhel-server-01"
cat ~/.ssh/id_rsa.pub
wget https://example.com/script.sh
chmod +x script.sh
./script.sh
git clone https://github.com/example/repo.git
cd repo
ls
cat README.md
sudo dnf update -y
sudo dnf install -y python3 python3-pip
pip3 install requests
python3 -c "import socket; print(socket.gethostname())"
df -h
free -m
top -bn1 | head -20
ps aux
sudo tail -f /var/log/secure
id
whoami
exit
