# pylabnet

Client-server, python-based laboratory software

 ![Devices](devices.ico)

This is the repository for pylabnet, a software package for client-server, python-based experiment control, designed for use in solid-state quantum optics + quantum network experiments in the Lukin group. 

## For users

### Installation

The package can be installed from the commandline using
```bash
pip install pylabnet
```
You can now `import pylabnet` and its submodules in your own scripts and notebooks. The package can be updated to the latest version using the command
```bash
pip install --upgrade pylabnet
```

### Usage

 After `pip` installation of pylabnet, two executables will be created in the system `PATH`: `pylabnet.exe` and `pylabnet_proxy.exe`. These can be used to launch master and proxy versions of the Launch Control GUI, from which relevant experimental software can be accessed over pylabnet. If desired, you can create shortcuts for these executables and pin the `devices.ico` icon (shown above and located in the root directory) for bonus style.

The master Launch Control runs a `LogServer` to keep track of all clients and servers on the network, and proxy Launch Control units simply connect to the master and mirror its information for convenience on remote machines.

The general workflow is the following

1. Launch a master `LogServer`. Can be done from a cusftom script, but easiest to just use the `pylabnet` executable.
2. Connect to hardware locally. This is done through use of drivers located in the `pylabnet/hardware` submodule. These drivers can also be used for standalone control of hardware, if desired.
3. Instantiate a `GenericServer` for each device (or logical module) to allow remote programming from anywhere in the network
4. Create clients for the hardware servers, which can be used to perform arbitrary functions on devices present across the network

Steps 2-4 can also be done manually from an interactive python notebook or custom script, but common functionality is incorporated into the Launch Control GUI for automatic "double-click" running of these steps.

## For developers

### Installation

First, clone the repository onto the local machine. Make sure git is installed. Cloning can be done from the command line, (preferrably in your home user directory) with the command 
```bash
git clone https://github.com/lukingroup/pylabnet.git
```

**Environment-independent installation (recommended)**. For installation in a dedicated conda environment, see `pylabnet/setup/README.md`

Once cloned, navigate to the root directory in the commandline, and run the command
```bash
python setup.py develop
```
This will create the same packaged executables in the system `PATH` as if the standard `pip install pylabnet` were carried out, but these executables will link to the current directory, which can then be developed and tested

### Development

1. **Create a new working branch before making any changes to the repository. Please do not make the changes directly in the master branch!** This can be done either from your IDE of choice, or from the commandline within the local github repository, using `git checkout -b new-branch-name`  

2. Implement and test your changes.

3. For GUI-based applications, it is recommended to create a launcher module (see pylabnet/launchers/README.md for more details. 

4. For non-GUI applications, please make a Jupyter notebook in the pylabnet/demo folder in order to demonstrate and test the added functionality.

5. Note that pushing changes to the `lukingroup/pylabnet` repository requires administrative access. Please contact one of the previous contributors for details.

6. Try to keep the your local repository up to date with the online repository to avoid unnecessary merge conflicts down the line.

7. Once stable + working, submit a pull request. 

### Publishing a new version to pip

1. Make sure the `install_requires` kwarg in `setup.py` is up to date with all mandatory packages.

2. Update the version number in `__init__.py` in the root module.

