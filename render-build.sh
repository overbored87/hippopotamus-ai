#!/bin/bash

# Update package lists
apt-get update

# Install PortAudio (required for PyAudio and sounddevice)
apt-get install -y portaudio19-dev