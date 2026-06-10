#!/bin/bash

touch /home/azureuser/setup_started

# Update apt cache and install required packages
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q python3-pip htop unzip wget

# Download repo and unpack
wget -q https://github.com/va1entin/iu-unsupervised-learning-and-feature-engineering/archive/refs/heads/main.zip
unzip -o -q main.zip
mv iu-unsupervised-learning-and-feature-engineering-main /home/azureuser/iu-unsupervised-learning-and-feature-engineering
chown -R azureuser:azureuser /home/azureuser/iu-unsupervised-learning-and-feature-engineering

# Install Python dependencies and apply patch for BERTopic
python3 -m pip config set global.break-system-packages true
python3 -m pip install --no-input -r /home/azureuser/iu-unsupervised-learning-and-feature-engineering/requirements.txt
patch /usr/local/lib/python3.13/dist-packages/bertopic/_bertopic.py /home/azureuser/iu-unsupervised-learning-and-feature-engineering/_bertopic.patch
echo -e '\nalias python=python3' >> /home/azureuser/.bashrc

touch /home/azureuser/setup_finished
