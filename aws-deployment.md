# AWS EC2 Deployment Notes

## Launch
- Ubuntu 24.04 LTS
- t3.micro
- Open ports 22 and 8000
- Created RSA .pem key pair

## Connect
EC2 Instance Connect

## Update

sudo apt update && sudo apt upgrade -y

## Install dependencies

sudo apt install python3-pip python3-venv git -y

## Clone project

git clone https://github.com/1-gokul/DepthCharge.git
cd DepthCharge

## Create virtual environment

python3 -m venv venv
source venv/bin/activate

## Install dependencies

pip install -r requirements.txt

## Build project

python3 seed_data.py
python3 network.py
python3 ml_model.py

## Install Docker

sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker

## Docker

sudo docker build -t depthcharge .
sudo docker run -d -p 8000:8000 --name depthcharge depthcharge

## Test

http://<EC2_PUBLIC_IP>:8000/docs
