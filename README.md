# pylabnet

Client-server, python-based laboratory software


[![DOI](https://zenodo.org/badge/219227835.svg)](https://zenodo.org/badge/latestdoi/219227835)

 ![Devices](https://raw.githubusercontent.com/lukingroup/pylabnet/master/devices.ico)

This is the repository for pylabnet, a software package for client-server, python-based experiment control, designed for use in solid-state quantum optics + quantum network experiments in the Lukin group.

## Prerequisites

* Supported Python versions: 3.7 - 3.8
* Microsoft Visual C++ 14.0 or greater, installed from [Build Tools for Visual Studio](https://visualstudio.microsoft.com/downloads/)

## For users

### Installation

The package can be installed from the commandline using
```bash
pip install pylabnet
```
You can now `import pylabnet` and its submodules in your own scripts and notebooks. The source code is installed to  `{PYTHONPATH}\Lib\site-packages\pylabnet` and configuration files should be placed in `{PYTHONPATH}\Lib\site-packages\pylabnet\configs`.

The package can be updated to the latest version using the command
```bash
pip install --upgrade pylabnet
```

### <a name="executable"></a>Usage

After `pip` installation of pylabnet, three executables will be created in the system `PATH`: `pylabnet_master.exe`, `pylabnet_proxy.exe` and `pylabnet_staticproxy.exe`. These can be used to launch master and proxy versions of the Launch Control GUI, from which relevant experimental software can be accessed over `pylabnet`. If desired, you can create shortcuts for these executables and pin the `devices.ico` icon (shown above and located in the root directory) for bonus style.

The master Launch Control `pylabnet_master.exe` runs a `LogServer` to keep track of all clients and servers on the network, and proxy Launch Control units simply connect to the master `LogServer` and mirror its information for convenience on remote machines. The difference between `pylabnet_proxy.exe` and `pylabnet_staticproxy.exe` is that the former will ask for the master `LogServer`'s location interactively while the latter reads directly from `configs/static_proxy.json` via the fields `master_ip`, `master_log_port`, and `master_gui_port`.

The general workflow is the following:

1. Launch a master `LogServer`. Can be done from a custom script, but easiest to just use the `pylabnet_master` executable.
2. (This step is skipped if connecting hardware on the same computer as the one running the master `LogServer`) Launch a proxy `LogServer` on the local computer to be connected to the desired hardware device. This enables the local computer to communicate any device updates to the master `LogServer` where it will be logged.
3. Connect to hardware device locally, and instantiate a `GenericServer` for each device (or logical module) to allow remote access from anywhere in the network. The `GenericServer` will itself interface with the the device through drivers located in the `pylabnet/hardware` submodule and expose desired functions to be called remotely. These drivers can also be used for standalone control of hardware, if desired.
4. On any other computers present across the network, create the hardware client for the corresponding hardware server to be connected to. This will enable access to the exposed device functions which can be freely called to remotely communicate with and control the device.

Steps 2-4 can also be done manually from an interactive python notebook or custom script, but common functionality is incorporated into the Launch Control GUI for automatic "double-click" running of these steps. In particular, step 4 will require knowledge of the hardware server's IP address and port if the client is created manually, but execution from the Launch Control GUI will enable automatic server connection via IP and port values stored in the master `LogServer`.


#### Initial Setup Notes

* You will likely need to allow python through Windows firewall the first time you run Launch Control on a new machine.

* The package uses SSL authentication via a self-signed private key. You can generate this key using OpenSSL from the commandline
```bash
openssl req -new -x509 -days 365 -nodes -out pylabnet.pem -keyout pylabnet.pem
```
You may adjust the value of the `days` flag in order to change the period over which the key is valid. This private key file `pylabnet.pem` is automatically placed in the `C:/Windows/System32` directory of the machine it is generated on. It can then be copied into the equivalent directory of any other machines using the same *pylabnetwork*.

* At time of starting up the master `LogServer`, you will require a configuration file named `static_proxy.json` in the `configs` subfolder to specify the ports to be opened and the logging path in the following format:
```javascript
{
    "master_log_port": 12345,
    "master_gui_port": 12346,
    "logger_path": "C:\\User\\pylabnet_logs"
}
```
The logger and GUI port can be freely chosen. For subsequent devices that wish to connect to the already-created master `LogServer`, they will require an additional field `master_ip: xxx.xxx.xxx.xxx` where the IP address of the msater `LogServer` will be added. The logger and GUI ports will also need to be the same as those that were originally set on the master server. 

## For developers

### Installation

First, clone the repository onto the local machine. Make sure `git` is installed. Cloning can be done from the command line, (preferrably in your home user directory) with the command
```bash
git clone https://github.com/lukingroup/pylabnet.git
```
---
**NOTE ON DEVELOPMENT IN DEDICATED ENVIRONMENT**

For installation in a dedicated pip virtual environment to prevent conflicts with the base python package, create a virtual environment using the following command:
```bash
python -m venv /path/to/new/virtual/testenv
```

Activate the development environment using the command:
```bash
/path/to/new/virtual/testenv/Scripts/activate
```
Be sure to set the interpreter in your IDE to `/path/to/new/virtual/testenv/Scripts/python.exe` if you will be launching pylabnet scripts directly from the IDE.

---
Next, navigate to the root directory of the cloned repository in the commandline and run the command to install all package requirements:
```bash
pip install -r requirements.txt
```

> **_NOTE:_** If it fails, try upgrading pip with `python -m pip install --upgrade pip`.

Finally, run the command to install `pylabnet`:
```bash
python setup.py develop
```

> **_NOTE:_** There may be some errors during dependency installation, but as long as the command terminates with output `Finished processing dependencies for pylabnet==x.y.z` the installation has worked. This command can also be re-used at a later time to maintain the environment (either virtual or base) if new package requirements are added to `setup.py`.

This will now allow you to `import pylabnet` from your scripts, and ensures you have the dependencies installed. It also creates a `pylabnet.egg-info` file which can be safely deleted if desired (it should not be tracked by github).

This also creates the standard `pylabnet` executables located in `{PYTHONPATH}\Lib\site-packages\pylabnet` (see [above](#executable)). Just be careful that you are using the correct executable if you have installed `pylabnet` in several environments.

### Development

1. **Create a new working branch before making any changes to the repository. Please do not make the changes directly in the master branch!** This can be done either from your IDE of choice, or from the commandline within the local github repository, using `git checkout -b new-branch-name`

2. Implement and test your changes.

3. For GUI-based applications, it is recommended to create a launcher module (see pylabnet/launchers/README.md for more details.

4. For non-GUI applications, please make a Jupyter notebook in the pylabnet/demo folder in order to demonstrate and test the added functionality.

5. Note that pushing changes to the `lukingroup/pylabnet` repository requires administrative access. Please contact one of the previous contributors for details.

6. Try to keep the your local repository up to date with the online repository to avoid unnecessary merge conflicts down the line.

7. Once stable + working, submit a pull request.

### Publishing a new version to pip

Generally, not every commit or even merge into master needs to be published to pip as a new version. However, if substantial functionality is added that could be useful to other users (especially ones that are not actively developing the platform), it is a good idea to release a new version on pip. In this case, you can do this with the following steps:

1. Make sure the `install_requires` kwarg in `setup.py` is up to date with all mandatory packages. If you have added new depedendencies, add them here.
 > **_NOTE:_** The preferred format is to use `>=` to constrain package versions, rather than `==`. Try not to write code that requires a `<` constraint, since this could cause user-dependent conflicts. As an example of this poor practice, the latest version of spyder has a conflict with the latest versions of pyqt5.

2. Update the version number in `__init__.py` in the root module. We have adoped a 3 digit versioning scheme `x.y.z` where `x` is the major version, each new `y` digit corresponds to a substantially new release (with new software components), and the `z` digit can increment with any improvements, changes, and bug fixes.

3. Update `CHANGELOG.md`

3. Run the following from the commandline
```bash
python setup.py sdist bdist_wheel
```
This will create a pylabnet/dist directory (which should not be tracked by github) containing the build files for this version. Note that this requires one to `pip install wheel`.

4. To upload to pip, run the command
```bash
twine upload dist/*
```
> **_NOTE:_** This requires credentials on https://pypi.org, as well as the twine package which can be installed with `pip install twine`. You may also run into issues if your `dist/` folder has older distributions, these should be deleted prior to upload.
---
**NOTE**

If you are done using a particular machine for development and would like to use and update the package the standard way via pip, you can remove the pylabnet installation by running the command `pip uninstall pylabnet` from a directory that does not have `pylabnet` inside it.

Your local repository can now be deleted and pylabnet can be installed, used, and maintained via pip.

---
