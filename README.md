# pylabnet

Client-server, Python-based laboratory software

[![DOI](https://zenodo.org/badge/219227835.svg)](https://zenodo.org/badge/latestdoi/219227835)

 ![Devices](https://raw.githubusercontent.com/lukingroup/pylabnet/master/devices.ico)

This is the repository for pylabnet, a software package for client-server, Python-based experiment control, designed for use in solid-state quantum optics and quantum network experiments in the Lukin group.

## Prerequisites

* Supported Python versions: 3.7 - 3.8

## Installation

1.  Clone the repository onto the local machine. For Windows, this will require [git for Windows](https://gitforwindows.org/) to be installed.
```bash
git clone https://github.com/lukingroup/pylabnet.git
```

2. Navigate into the root directory of the cloned repository:
```bash
cd pylabnet
```

3. (Optional but highly recommended to avoid conflicts with dependencies) Create a virtual environment using the following command:
```bash
python -m venv <env_path>
```
where `<env_path>` is the desired location of the virtual environment. For example, if you want to place the environment in the root level of the `pylabnet` folder and name it `env`, the command would simply be `python -m venv env`.

Activate the development environment using the command:
```bash
<env_path>\Scripts\activate # Windows
. <env_path>/bin/activate   # Linux
```
Be sure to set the interpreter in your IDE to `<env_path>\Scripts\python.exe` (Windows) or `<env_path>/bin/python` (Linux) if you will be launching pylabnet scripts directly from the IDE.

4.  Install all package requirements:
```bash
pip install -r requirements.txt
```

If it fails, try upgrading pip with `python -m pip install --upgrade pip`. Also make sure that your [Python version is supported](#prerequisites).

5. Finally, run the command to install pylabnet:
```bash
python setup.py develop
```

There may be some errors during dependency installation, but as long as the command terminates with output `Finished processing dependencies for pylabnet==x.y.z` the installation has worked.

6. To confirm that the installation has completed, you should be able to run  `import pylabnet` in your scripts, and you should also find the executables `pylabnet_master`, and `pylabnet_proxy`, and `pylabnet_staticproxy` in the folder `<env_path>\Scripts` (Windows) or `<env_path>/bin` (Linux). Continue reading on to the [initial setup notes](initial-setup-notes) for the initial configuration that needs to be done when setting up a new computer.


### Initial Setup Notes for Launch Control

* The package uses SSL authentication via a self-signed private key. You can generate this key using OpenSSL from the command line:
```bash
openssl req -new -x509 -days 365 -nodes -out pylabnet.pem -keyout pylabnet.pem
```
You may adjust the value of the `days` flag in order to change the period over which the key is valid. This private key file `pylabnet.pem` should be placed into the `C:/Windows/System32` (Windows) or the `/etc/ssl/certs` (Linux) directory of the machine it is generated on. On Windows, one of the easiest way to run OpenSSL is using the Git Bash shell that is installed together with Git for Windows.

* You will need to create a configuration file named `static_proxy.json` in the `pylabnet/configs` subfolder with the following fields:
```
{
    "logger_path": "C:\\pylabnet_logs" # Only required for master logger (i.e. running pylabnet_master)
    "master_ip": "192.168.50.101",     # Only required for logger client   (i.e. running pylabnet_staticproxy)
    "master_log_port": 12345,                  
    "master_gui_port": 12346
}
```
The `master_log_port` and `master_gui_port` are freely chosen by the master logger in its configuration file, and all LogClients will need to specify these same ports in order to conenct to the master logger. LogClients will additionally also need to specify the master logger's IP address in `master_ip`.

* You will likely need to allow Python through Windows Firewall the first time you run Launch Control on a new machine.

---

## Key pylabnet Structure

pylabnet consists of several interacting components that work together to create a network of computers that can access and control hardware connected to any another computer. We review the main building blocks here:

- pylabnet can be used whenever we have a collection of computers that are all connected over a single local area network
- Whenever we have a hardware device that is physically connected to a computer (**host computer**), this host computer will connect to and control the device using a device-specific **Driver** which implements desired functionality using device-native commands. The host computer will also host a device **Server** that provides exposed **Services**, which are Python functions that other computers can use in order to interact with the device.
- In order to communicate with the device from another computer (**client computer**),  the client computer will need to run a device **Client** locally, and we will connect to the Server by specifying its IP address and port. These parameters can also be automatically specified when the client is created from Launch Control instead (see below). Once the Client is initialized, it will be able to call client-side functions, which are communicated to the host computer via RPyC, translated to the equivalent server-side functions, and finally sent to the device via the device Driver.
- To provide logging of error, debug, or informational messages generated by the devices or functions, there is an analogous server-client structure for message logging. There will be a **master computer / master logger** that will start up a **LogServer**. All other pylabnet servers will then create their own **LogClient** to communicate with the LogServer in order to send messages and receive messages sent by other computers.

In principle, this is all that we need to run pylabnet! We can start Servers and Clients in Jupyter notebooks and use the associated device functionality from any connected computer on the local network. However, it is tedious to keep track of all the Servers and their associated IP addresses and ports, and it would also be annoying to have to remote into different computers to start up different device Servers. This brings us to the **Launch Control** GUI.

![image](https://github.com/lukingroup/pylabnet/assets/36173574/4d32b799-ce0e-437d-9549-fa6617c8db1f)

This brings several new functionalities:
- We can start a Server on a remote computer by specfiying its IP address and ssh parameters.
- We can create Clients that connect to the appropriate existing Server automatically (without specifying the Server IP/port) via name matching of the Server.
- We can launch scripts and GUIs for commonly performed tasks, and specify which Servers are required for these scripts to load. If these Servers do not exist, they will be created automatically together with the corresponding Client.
- We can specify device-specific and script-specific configurations using a JSON config file, which are then listed in the Launch Control GUI and can be double-clicked to launch their respective device Server or script.

---

## Usage

The main executables used for launching the Launch Control GUI are `pylabnet_master`, `pylabnet_proxy` and `pylabnet_staticproxy` located in the folder `<env_path>\Scripts` (Windows) or `<env_path>/bin` (Linux). If desired, you can create shortcuts for these executables together with the `devices.ico` icon (shown above) for bonus style. 

The master Launch Control `pylabnet_master` starts a `LogServer` and also keeps track of all servers on the network, while proxy Launch Control instances simply connect to the master logger and mirror its information for convenience on remote machines. The difference between `pylabnet_proxy` and `pylabnet_staticproxy` is that the former will ask for the master Launch Control's location interactively while the latter reads directly from `pylabnet/configs/static_proxy.json`.

The general workflow for working with Launch Control is the following:

1. Choose a computer to be the master logger. We recommend that this computer be stable with low downtime as all pylabnet communication will require the master logger to be online. Here, launch a master Launch Control using the `pylabnet_master` executable.
2. For all other computers on the network, launch a proxy Launch Control to mirror the information that is being recorded on the master logger. This enables the local computer to receive logging messages from all other computers on the network.
3. For each device that you want to connect, a separate configuration JSON file will be required to specify parameters such as the device ID and ssh settings (if the device is located on a remote computer). These config files must be located in `pylabnet/configs/devices/<device_type>/<config_filename>.json`. To start this device server, double click on the config filename in the Devices column of Launch Control.
4. For each script that you want to run, a separate configuration JSON file will be required, which minimally specifies the prerequisite device servers and the script location. These config files must be located in `pylabnet/configs/script/<script_type>/<config_filename>.json`. To start this script, double click on the config filename in the Scripts column of Launch Control.
