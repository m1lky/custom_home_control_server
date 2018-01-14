import socket
host = ''
port = 9999
data = 'setup\n'
# Test script
# Data = what command to run
# Host = IP address of raspberry pi
# Port = whatever port you're running the server on
def send_data(host, port, data):
    client = socket.socket()
    client.connect((host, port))
    client.send(data.encode())
    print("sent")
send_data(host, port, data)
