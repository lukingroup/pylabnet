# pylabnet
Client-server, python-based laboratory software

This is the repository for pylabnet, a software package for client-server, python-based experiment control, designed for use in solid-state quantum optics + quantum network experiments in the Lukin group. 

## For users

### Installation

The package can be installed from the commandline using
```bash
pip install pylabnet
```

You can now `import pylabnet` and its submodules in your own scripts and notebooks.

### Standard usage

The general workflow is the following

1. Launch a `LogServer`. This is sort of the brain of the entire software; everything subsequent will be a client to the `LogServer`
2. Connect to hardware locally.
3. Instantiate a `GenericServer` for each device (or logical module) to allow remote programming from anywhere in the network
4. Create clients for the hardware servers, which can be used to perform arbitrary functions on devices present across the network

For maximal convenience, this can be coordinated via the Launch Control GUI. After `pip` installation of pylabnet, two executables will be created in the system PATH: `pylabnet.exe` and `pylabnet_proxy.exe`. These can be used to launch master and proxy versions of the Launch Control GUI, from which relevant experimental software can be accessed over pylabnet. 

The master Launch Control runs the `LogServer` to keep track of all clients and servers on the network, and proxy Launch Control units simply connect to the master and mirror its information for convenience on remote machines.

using the pylabnet shortcut provided in the main directory. This launches the master `LogServer`, and from this GUI, additional hardware servers and scripts can be launched. To program devices and run scripts on remote machines with access to all of the same servers, the pylabnet_proxy shortcut can be used as a proxy for the master `LogServer`.

## For developers

### Installation

1. Clone the repository onto the local machine. Make sure git is installed. Cloning can be done from the command line, (preferrably in your home user directory) with the command 
```bash
git clone https://github.com/lukingroup/pylabnet.git
```

**Environment-independent installation (recommended)**

2. Navigate to the 

Create a new working branch "new-branch" (insert a relevant name) for your changes. Within the local github repository, use the command "git checkout -b XXX" (insert relevant branch name). This simultaneously creates a new branch and switches over to it. **Please do not make the changes directly in the master branch!**

3. Make changes to (or add new) relevant modules: pylabnet/hardware, pylabnet/gui, and pylabnet/script.

4. Write a Jupyter notebook in the pylabnet/demo folder in order to demonstrate and test the added functionality.

5. Once stable + working, commit your changes locally and push them to the remote repository. Note, this requires administrative access to lukingroup on github. Please contact one of the previous contributors if you need access.

6. If you would like your changes to be incorporated into the master branch, so other lab computers + users can use them, submit a pull request for "master" <- "new-branch". If successful, "new-branch" can be deleted from the online repository.

7. When you are ready to start the experiment, switch back to the master branch and "git pull" to make sure you are using the latest version. Then copy the relevant notebooks from the "demo" folder into a new folder outside the repository to begin working on experiments.

## Using pylabnet for experiments

A general workflow is the following

1. Launch a `LogServer`. Everything subsequent will be a client to the `LogServer`
2. Connect to hardware.
3. Instantiate a `GenericServer` for each device to allow remote programming of the hardware
4. Create clients for all servers, which can be used in an arbitrary script

For maximal convenience, this can be coordinated via the Launch Control GUI using the pylabnet shortcut provided in the main directory. This launches the master `LogServer`, and from this GUI, additional hardware servers and scripts can be launched. To program devices and run scripts on remote machines with access to all of the same servers, the pylabnet_proxy shortcut can be used as a proxy for the master `LogServer`.
