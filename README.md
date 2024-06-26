# WFR Data Acquisition System
This repository stores the code and other software resources defining the WFR Data Acquisition System (DAQ). 

## Key Assumption
A key assumption with the system is that it exists connected to a secure network. If not, disabling the WiFi adapter on the Pi and reverting to Ethernet only as a means of connecting to the DAQ is advised.

## Simple Guide to Setting Up an External SSD
[Go here.](./documentation/INITIALIZATION_GUIDE.md)

## Hardware Setup
For hardware setup, please refer to the following excerpt from [THEORY_README.md](./documentation/old_but_useful_for_problem_solving/THEORY_README.md): 

### Physical Layer
#### CAN Interface
This project has been tested to work with a MCP2515-based CAN Bus board, which connects to `SPI0` on the Raspberry Pi Model 4B:  

<img src="https://user-images.githubusercontent.com/25854486/209448905-cbbaac77-50bf-4a75-8132-85bc5a5c5922.png" width="200"> 

The pin connection is as follows:
| MCP2515 Module| Raspberry Pi Pin #| Pin Description  |
| ------------- |:---------------------:| :-----:|
| VCC           | pin 2                 |5V (it's better to use external 5V power)|
| GND           | pin 6                 |   GND |
| SI            | pin 19                |    GPIO 10 (SPI0_MOSI)|
| SO            | pin 21                |    GPIO 9 (SPI0_MISO)|
| SCK           | pin 23                |    GPIO 11 (SPI0_SCLK)|
| INT           | pin 22                |    GPIO 25 |
| CS            | pin 24                |    GPIO 8 (SPI0_CE0_N)|

#### Raspberry Pi System Storage
Due to the relatively rapid read/write speed requirements of the data acquisition use case, a Samsung T7 external SSD is used as the main storage volume. 500 GB storage capacity is recommended, but more is always welcome. The SSD connects to the Raspberry Pi using a USB-C-to-USB-A 3.1 cable. For connection integrity, it is important that the SSD and Raspberry Pi are packaged as a unit, such that the accelerations experienced by the SSD and the Pi are similar. Otherwise, high-variation cable strain may cause physical damage to the SSD, the cable, the Raspberry Pi, or some combination thereof. Even transient disconnection of the SSD could cause catastrophic data loss. Hence, data should be backed up and extracted from the unit as frequently as possible. 

### Driver Layer
#### SocketCAN 
This project heavily relies on [SocketCAN](https://docs.kernel.org/networking/can.html) which is the Linux kernel's default CAN Bus interface implementation. It treats CAN Bus interface devices similar to regular network devices and mimics the TCP/IP protocol to make it easier to use. It also natively supports MCP2515 based controllers. Since this is built-in, nothing needs to be installed, however the `/boot/config.text` needs to have the following line appended to it:
```
dtoverlay=mcp2515-can0,oscillator=8000000,interrupt=25 
```  
This gets the Linux kernel to automatically discover the CAN Controller on the SPI interface. If your interface pin has a different oscillator frequency, you can change that here.  

Now reboot the Pi and check the kernel messsages (you can bring this up in the terminal by using the command: `dmesg | grep spi)` or `dmesg` to view all kernel messages), and you should see the following:
```
[    8.050044] mcp251x spi0.0 can0: MCP2515 successfully initialized.
```  

Finally, to enable the CAN Interface run the following in the terminal:
```
 sudo /sbin/ip link set can0 up type can bitrate 500000 
```  

If you are using a different bitrate on your CAN Bus, you can change the value. You'll need to edit the declarations of `bus_one` and `bus_two` in `data_logger/canInterface.py` to match the new bitrate. 

You will need to run this command after every reboot, however you can set it to run automatically on startup by appending the following to the `/etc/network/interfaces` file:
```
auto can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 type can bitrate 500000 triple-sampling on restart-ms 100
    up /sbin/ifconfig can0 up
    down /sbin/ifconfig can0 down
```  

And that's everything to get the CAN Bus interface working! Since SocketCAN acts like a regular network device, we can get some statistic information by using the `ifconfig` terminal command, which can be obtained with the `net-tools` package using `sudo apt-get install net-tools`.  

#### CAN-utils
[CAN-utils](https://github.com/linux-can/can-utils#basic-tools-to-display-record-generate-and-replay-can-traffic) is a set of super useful CAN debugging tools for the SocketCAN interface. You can install it using the following command:
```
 sudo apt-get install can-utils 
``` 
This allows us to dump CAN Bus traffic to logs, send test messages and simulate random traffic. Please see the readme on their GitHub page for more details.

## Software Environment

### Operating System
Connect the SSD/storage volume to a host computer. Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install Raspberry Pi OS on the volume. Make sure to configure SSH, network, and administrator settings before the Raspberry Pi Imager installation process. Ensure the hostname *(default: "raspberrypi")* of the device is noted.

### Network
The Raspberry Pi does not need to be connected to a Layer-3 (IP) communications network to function. However, it is highly recommended that it is. Without connection to a network, data egress, data visualization, and system monitoring are deeply impeded, if not impossible. 

Raspberry Pi can connect to IP networks using WiFi or wired Ethernet. WiFi is vastly more convenient, but note that on networks with high network segregation (e.g., secured enterprise networks, like Western's), interdevice connectivity may not be possible. Hence, it is recommended that an external network is established using a router. The network does not need to be connected to the internet for DAQ use, but the DAQ **does** need an internet connection for initial software setup and updates. 

## Software Setup

**It is expected that the reader is relatively familiar with SSH and SFTP for remote access to the Raspberry Pi.** If not, please refer to the internet for a guide on connecting to a Raspberry Pi via SSH. The recommended application for development is [MobaXTerm](https://mobaxterm.mobatek.net/) on Windows, and [Royal TSX](https://www.royalapps.com/ts/mac/download) on MacOS. These applications are capable of multi-tabbed operation, so many SSH terminals and SFTP file transfer sessions may be open at a time. **The following assumes SSH and SFTP are established and accessible by the user.**

### Cloning the Project
On your own computer (Host), use Git CLI to clone the repository, or download as a zip. Duplicate `.env.example`, rename it `.env`, and add a value for the `INFLUX_PASSWORD` environment variable. Save after editing. Don't worry about the `INFLUX_TOKEN` environment variable for now.

On the Raspberry Pi (RPi), create a folder in the home (`~/`) directory called `daq` with the command `mkdir ~/daq`.

On Host, establish an SFTP session with RPi, and transfer the cloned repository to `~/daq/` on RPi.

### Install Docker
Follow the steps [here](https://docs.docker.com/engine/install/debian/#install-using-the-repository) to install Docker on the RPi.

### Starting the Project
On RPi, navigate to the `daq` folder with the command, `cd ~/daq`. Run the command `docker compose up -d` to build the containers required for the application, and link the containers together. 

You can shut down the application by navigating to the `~/daq` folder and executing the command, `docker compose down -v`. 

### Initializing InfluxDB
First, a database bucket and an authentication token must be generated from InfluxDB. To do this:
1. Run command, `docker exec -it wfrdaq-influxdb-1 /bin/bash`, to get command-line access to the container
2. Set up InfluxDB by running the command: 
```
influx setup \
    --username $INFLUX_USERNAME \
    --password $INFLUX_PASSWORD \
    --org $INFLUX_ORGANIZATION \
    --bucket $INFLUX_BUCKET \
    --force
```  

3. Make a configuration and set it as active to authenticate:  
```
influx config create --config-name grafana_cfg \
  --host-url http://localhost:8086 \
  --org $INFLUX_ORGANIZATION \
  --username-password $INFLUX_USERNAME:$INFLUX_PASSWORD \
  --active
```

3. Get the authorization token by running the command:
```
influx auth list \
    --user $INFLUX_USERNAME \
    --hide-headers | cut -f 3
```  

4. Copy the string output from step 3, paste this into `.env` as the value for `$INFLUX_TOKEN`, and save the `.env` file 
5. From the InfluxDB command line, go back to the Pi's CLI by entering the command, `exit`
6. Shutdown the docker project with the command `docker compose down -v`
7. Recompose the Docker project with `docker compose up -d`

InfluxDB is now set up.

### Initializing Grafana

1. On Host, open a web browser, and navigate to the URL, `http://raspberrypi.local:3000/`, replacing "raspberrypi" with the hostname you selected during Raspberry Pi OS installation if you changed it from the default
2. Enter "admin" for both prompts
3. Change the password to whatever password you chose for the `$INFLUX_PASSWORD` environment variable
4. Click the stacked vertical bars in the top left, expand the "connections" item in the dropdown, and click "add new connection"
5. Search "influxdb", click it, and then click the "add new data source" button 
6. Set the following:
    - Query Language: `InfluxQL`
    - URL: `http://influxdb:8086`
    - Database: `RaceData`
    - User: `grafana`
    - Password: whatever password you set for the `$INFLUX_PASSWORD` environment variable in .env file
    - HTTP Method: GET  
8. Click "+ Add header", and set "Header" to "Authorization", and "Value" to "Token [InfluxDB token from [Initializing InfluxDB](#initializing-influxdb)]" **(the capital "T" in "Token" is very important)**  
9. Click "save & test" in the bottom. You should see a box appear at the bottom of the screen that says "datasource is working. 0 measurements found" with a green checkmark on the left. This means the connection from Grafana to InfluxDB is working
10. Click "add new connection" on the left-hand side of the page, then search for "MQTT" and click it
11. On the MQTT data source page, click the "install" button. After installed, click the "add new datasource" button
12. On the configuration page, for the "URL" field, enter `tcp://mqtt_broker:1883`, and click "save & test". You should get the same confirmation box in as in step 8

#### Grafana Dashboards
Now you can make visualizations in Grafana with MQTT and influxdb data sources. Note that MQTT topic subscription is case-sensitive. Also, MQTT topics are defined as [CAN Device Name as per DBC]/[Measurement Name], e.g. "Sensor_board_2_1/Sensor1". **Make sure to save dashboards frequently.**

### DAQ User Interface
The DAQ user interface is provided by a web application, which can be accessed from a computer attached to the same network as the Raspberry Pi. On a web browser, enter the URL: `http://[hostname].local`. If the Raspberry Pi's hostname as selected in the Raspberry Pi Imager is `raspberrypi`, the link is [http://raspberrypi.local](http://raspberrypi.local). As long as the Docker project is composed, you'll be able to access the site. It will look like this:  

<img src="https://github.com/Western-Formula-Racing/daq-2023/assets/70295347/a7f3740e-2d41-49f7-a55e-c6861e5aff2f" width="500">  

The UI is self-explanatory. The webpage refreshes once every minute to update the session hash to make sure it's reflective of the current state.  

Currently, CSVs are the only download method. Motec LD downloads will be added in the near future.  

### Testing Software Configuration with Virtual CAN Datastreams
Refer to the document, [VIRTUAL_DATASTREAM_GENERATION.md](./documentation/VIRTUAL_DATASTREAM_GENERATION.md), for information about how to do this.

### Motec Conversion
Motec log generator was originally written by stevendaniluk and is available here: https://github.com/stevendaniluk/MotecLogGenerator.  

### Swapping DBCs  
DBCs are easily swappable using the following steps:
1. SSH into pi as "pi" user  
2. `cd` to `~/daq-2023/daq-2023`, and downcompose the project with `docker compose down -v`  
3. Edit (with `nano`), or replace (with SFTP; does not work over direct ethernet connection) DBC files in `~/daq-2023/daq-2023/containerization/volumes/dbc`  
4. `cd` back to `~/daq-2023/daq-2023`, then recompose the project with `docker compose up -d`