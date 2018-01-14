# CHC Server
**Raspberry Pi Infra Red Universal Remote Control  Python Server** 

I created a server application to turn my raspberry pi into a universal remote with internet connectivity. My intention is to connect this to an Amazon Alexa app, but that I'm running into difficulties with a lack of documentation on the smart home skill API. 

The setup for the IR configuration on the GPIO pins is from [here](https://www.hackster.io/austin-stanton/creating-a-raspberry-pi-universal-remote-with-lirc-2fd581)

This is a python3 server that is intended to be run on a raspberry pi 3. I have no idea if it'll work on anything other than a 3, because I've only tested it on a 3. That said, it should work on a 2.

# Getting Started
## Requirements
1. Raspberry pi running Raspbian
###### (I've only used a 3, but 2 might work.)
2. [Parts]( http://a.co/6wFIXxT)
3. A bit of technical savvy
## Configuring
Using the link [here](https://www.hackster.io/austin-stanton/creating-a-raspberry-pi-universal-remote-with-lirc-2fd581), connect the components as indicated in the first step. 

###### If you bought the same breadboard I did, you may notice that the positive and negative marks on the sides of the board are opposite what is in that link. This is fine. As long as you connect the same pattern, it doesn't matter. The marks are just there for convenience, and have no bearing on the physical structure of the board. 

Once you have it connected, install pigpiod:
```
sudo apt-get update
sudo apt-get install pigpio python-pigpio python3-pigpio
```
CD into the directory with the files from here,  and simply run:

```
python3 __main__.py
```
Alternatively, you might find it more useful to use the command:
```
nohup python3 __main__.py &
```
This is will run the server in the background, redirect all output to a file called "nohup.out", and keep the script from being tied to your session.

(if you've ssh'd into your pi in order to run this, without nohup, your pi will stop running the script when you log out of the ssh session)
## Setup
In order to actually use the server, you have to record the signals from your current remotes. I recommend having a terminal with the server running visible during the setup process.
1. Using the code_names.txt file, input all of the names of your codes
2. Send a "setup" command to the server to begin the process.
3. Point your remote at the sensor, and begin recording the IR codes

# Files

## `irrp.py`
* This is a class that I created from a script I found at 		
		
		http://abyz.me.uk/rpi/pigpio/examples.html
* Controls the LED recording and playback


## `skill_server.py`

* Creates a server using python's socket library. 
* Constants before class declaration are used for which GPIO pins are used. Default values are for if you followed the link I posted above.

## `test.py`
* Easy script for testing if the server is working and receiving commands.
* Simply put whatever code name you want the receiver to emit, or 'setup', into the data variable, fill in the host, and run `python3 test.py`

## `code_names.txt`

* The names that will be read in and used to refer to the IR codes

## `remote_codes.txt`
* Codes stored in JSON format

## `__main__.py`

* Pops up the server, and listens indefinitely on port 9999



# Troubleshooting


## Can't connect to pigpiod

1. Make sure you have pigpiod installed:

	`apt list --installed | grep "pigpio"`

	Output:
	```
	pigpio/now 1.60-1 armhf [installed,upgradable to: 1.64-1]
	python-pigpio/now 1.60-1 all [installed,upgradable to: 1.64-1]
	python3-pigpio/now 1.60-1 all [installed,upgradable to: 1.64-1]
	```
2. Try restarting pigpiod:
	```
	sudo killall pigpiod
	sudo pigpiod
	```

## Can't Connect To Server
1. Check that the port is open while the script is running
	`nmap -p9999 [Raspberry Pi IP Address]`
2. Check that your firewall isn't blocking the port
3. Check that you have permissions to open ports
4. Check that your pi is connected to the internet
