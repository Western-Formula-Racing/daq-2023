# Initializing a New DAQ With an External SSD
Prerequisites: 
    - SD card has operating system loaded on it, described in [Operating System](../README.md#operating-system)
    - Raspberry Pi has an internet connection
    - Your computer can ping the Raspberry Pi
    - You have a dual CANbus hat 
    - You have an external SSD connectable with USB
    - RPi has powered on 

1. Physically connect SSD to pi with USB cable  

2. SSH into Pi (read the first paragraph of [Software Setup](../README.md#software-setup) if you don't know how to do this)  

3. Do command `lsblk` and find the appropriate device and part that correspond to your external SSD. Mine had the disk name "UNTITLED" here:  

<img src="https://github.com/Western-Formula-Racing/daq-2023/assets/70295347/565edff4-68ae-472f-9c12-585c70d25e4c" width="453">  

4. Reformat the disk: `sudo mkfs -t ext4 /dev/sda1`. If it's mounted, unmount it with `umount /dev/sda1` (or whatever the device name is), then try the `mkfs` command again  

5. Do `lsblk -f`, find and note the UUID

<img src="https://github.com/Western-Formula-Racing/daq-2023/assets/70295347/0fdf0884-22c3-4aa8-ad7e-653d8f1a6039" width="800">  

6. Edit fstab to automatically mount the disk if it's available at boot with `sudo nano /etc/fstab`. Add the below line and save with ctrl+s: 
```
UUID=[uuid from step 4] /home/pi/daq-2023 ext4 defaults,nofail 0 0  
```  

7. Make the daq-2023 folder with `mkdir /home/pi/daq-2023`

8. Reload fstab config with `sudo systemctl daemon-reload`  

9. Mount the drive with `sudo mount /dev/sda1 /home/pi/daq-2023`. Note that `/dev/sda1` might need to be replaced with whatever your device name is  

10. Change the ownership of the mountpoint with `sudo chown pi /home/pi/daq-2023`  

11. Go into daq-2023 directory with `cd /home/pi/daq-2023`, and then create a test document with `touch test.txt`. You should be able to do this without the `sudo` command prefix

12. Add content to the test document with `nano test.txt`, type something, and then save with ctrl+s. 

13. Reboot the pi to test that A. the SSD is automounted, and B. that the test.txt file has the same contents as before. Reboot with `sudo shutdown -r now`  

14. When the pi boots up again, `cd` back into `/home/pi/daq-2023`, and do `nano test.txt` to make sure the file exists and that it has the same content as before. This verifies the addition of an externally mounted SSD and a correct fstab config  

15. Make sure the required setup is complete for the CAN hat: https://www.waveshare.com/wiki/2-CH_CAN_HAT#Enable_SPI_interface (complete this section and the "Install Libraries" section. Note that sometimes the wiki commands say `. /build` but it actually should be `./build`. I contacted them to fix this but who knows if they will. Also the pip3 installs will fail because the environment is externally managed -- don't worry about these, they just use them for testing later on, which we don't care about)  

16. After finishing the above setup, set the CAN interfaces automatically by first creating a file: `sudo touch /etc/systemd/network/80-can.network`. Then edit the file with `sudo nano /etc/systemd/network/80-can.network`, and add the below lines:  
```
[Match]
Name=can*

[CAN]
BitRate=500K
```  

17. Then, add another file: `sudo touch /etc/systemd/network/80-can.link`. Edit the file with `sudo nano /etc/systemd/network/80-can.link`, and add the below lines:
```
[Match]
OriginalName=can*

[Link]
TransmitQueueLength=65536
```  

18. Then:  
    i. reload systemd-networkd with `sudo systemctl restart systemd-networkd`  
    ii. reload systemd-udevd with `sudo systemctl restart systemd-udevd`  
    iii. enable systemd-networkd with `sudo systemctl enable systemd-networkd`  
    iv. restart the machine with `sudo shutdown -r now`  
    v. when you get the command line back, make sure the CAN interfaces are up with a queue length of 65536 by entering `ip addr` and making sure the following is present for the CAN interfaces:  
    <img src="https://github.com/Western-Formula-Racing/daq-2023/assets/70295347/86c51b1e-6aad-4d6a-8fe1-c72a1471a31c" width="800">  

19. Install docker engine by following the steps here: https://docs.docker.com/engine/install/debian/ (Raspberry Pi OS 64-bit is Debian-based). I recommend using the [Install using the apt repository](https://docs.docker.com/engine/install/debian/#install-using-the-repository) method. **MAKE SURE TO DO THE [LINUX POSTINSTALL STEP](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) WHEN FINISHED!!!**  

20. Go back to the daq-2023 repo folder in the SSD with `cd /home/pi/daq-2023/daq-2023`. Compose the project with `docker compose up -d`.  

21. Navigate back to the SSD daq-2023 folder with `cd /home/pi/daq-2023`. Clone the daq-2023 GitHub repository with git clone https://github.com/Western-Formula-Racing/daq-2023.git 

22. A new folder is created inside `/home/pi/daq-2023`, also called `daq-2023`. Navigate to it with `cd ./daq-2023`. If using the DAQ in the car, switch to the `main-in-car` branch with `git checkout main-in-car`  

23. Make an environment variable folder by copying and renaming the example: `cp .env.example .env`  

24. Edit the `.env` file with `nano .env`. Set a password for InfluxDB by setting the `INFLUX_PASSWORD` environment variable, but leave `INFLUX_TOKEN` blank. Save with ctrl+s, and exit with ctrl+x  

25. Compose the docker project: `docker compose up -d`  

26. On another computer connected to the same network as the Pi (or connected directly with Ethernet), open a web browser, and continue the normal software setup process starting in [Initializing InfluxDB](../README.md#initializing-influxdb)

If booting with an SSD that does not have its filesystem UUID entered in the fstab configuration, or if no SSD is connected, the Raspberry Pi will still boot properly because of the nofail option we had in the fstab config. The DAQ software will not run, assuming the DAQ software is stored on the SSD. Follow the above steps with your new SSD to get it working properly.