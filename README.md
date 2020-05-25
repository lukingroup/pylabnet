# pylabnet
Client-server, python-based laboratory software

This is the repository for pylabnet, a software package for client-server, python-based experiment control, designed for use in solid-state quantum optics + quantum network experiments in the Lukin group. 

## Installation

TODO

## Using and developing the package

If you are an external user and you would like to use the package, please fork the package to your own personal or group repository. 

If you are an internal user (SiV Lukin lab team), and you would like to setup the package on a new machine, you can follow the steps below:

1. First, clone the repository onto the local machine. Make sure git is installed on the local machine! This can be done from the command line, (preferrably in your home user directory) and use the command "git clone https://github.com/lukingroup/pylabnet.git". Follow instructions in setup/readme.txt as well.

If you plan on developing the package (e.g. writing new drivers or scripts that do not exist yet), then please follow steps 2-6. If you plan on immediately using the package for expeirmental control without development, skip to step 7.

2. Create a new working branch "new-branch" (insert a relevant name) for your changes. Within the local github repository, use the command "git checkout -b XXX" (insert relevant branch name). This simultaneously creates a new branch and switches over to it. **Please do not make the changes directly in the master branch!**

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
