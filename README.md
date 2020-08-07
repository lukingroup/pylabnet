# pylabnet

Client-server, python-based laboratory software

 ![Devices](https://raw.githubusercontent.com/lukingroup/pylabnet/master/devices.ico)

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

### <a name="executable"></a>Usage

 After `pip` installation of pylabnet, two executables will be created in the system `PATH`: `pylabnet.exe` and `pylabnet_proxy.exe`. These can be used to launch master and proxy versions of the Launch Control GUI, from which relevant experimental software can be accessed over pylabnet. If desired, you can create shortcuts for these executables and pin the `devices.ico` icon (shown above and located in the root directory) for bonus style.

 > **_NOTE 1:_** You will likely need to allow python through Windows firewall the first time you run Launch Control on a new machine.

> **_NOTE 2:_** The package uses SSL authentication via a self-signed private key. You can generate this key using OpenSSL from the commandline
> ```bash
> openssl req -new -x509 -days 365 -nodes -out pylabnet.pem -keyout pylabnet.pem
> ```
> You may adjust the value of the `days` flag in order to change the period over which the key is valid. This private key file `pylabnet.pem` is automatically placed in the `C:/Windows/System32` directory of the machine it is generated on. It can then be copied into the equivalent directory of any other machines using the same *pylabnetwork*.

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
---
**NOTE ON DEVELOPMENT IN DEDICATED ENVIRONMENT**

For installation in a dedicated pip virtual environment to prevent conflicts with the base python package, create a virtual environment - can be done from the command line using
```bash
python -m venv /path/to/new/virtual/testenv
```

Activate the development environment using the command
```bash
/path/to/new/virtual/testenv/Scripts/activate
```
Be sure to set the interpreter in your IDE to `/path/to/new/virtual/testenv/Scripts/python.exe` if you will be launching pylabnet scripts directly from the IDE.

---
Next, navigate to the root directory in the commandline and run the command
```bash
python setup.py develop
```
> **_NOTE 1:_** there may be some errors during dependency installation, but as long as the command terminates with output `Finished processing dependencies for pylabnet==x.y.z` the installation has worked.

> **_NOTE 2:_** this command can also be re-used at a later time to maintain the environment (either virtual or base) if new package requirements are added to `setup.py`.

This will now allow you to `import pylabnet` from your scripts, and ensures you have the dependencies installed. It also creates a `pylabnet.egg-info` file which can be safely deleted if desired (it should not be tracked by github).

This also creates the standard pylabnet executables which can be used for launching (see [above](#executable)). Just be careful that you are using the correct execuatable if you have installed pylabnet in environments.

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
