# pylabnet
Client-server, python-based laboratory software

This is the repository for pylabnet, a software package for client-server, python-based experiment control, designed initially for use in solid-state quantum optics + quantum network experiments in the Lukin group. 


## Using and developing the package properly with github

If you are an external user and you would like to use the package, please fork the package to your own personal or group repository. See below for a description of the package.

If you are an internal user (SiV Lukin lab team), and you would like to setup the package on a new machine, you can follow the steps below:

1. First, clone the repository onto the local machine. Make sure github is installed on the local machine! Go to the command line, in your home user directory and use the command "git clone XXX" (insert the link above). Follow instructions in setup/readme.txt as well.

If you plan on developing the package (e.g. writing new drivers or scripts that do not exist yet), then please follow steps 2-6. If you plan on immediately using the package for expeirmental control without development, skip to step 7.

2. Create a new working branch "new-branch" (insert a relevant name) for your changes. Within the local github repository, use the command "git checkout -b XXX" (insert relevant branch name). This simultaneously creates a new branch and switches over to it. **Please do not make the changes directly in the master branch!**

3. Make changes to (or add new) relevant modules: pylabnet/hardware, pylabnet/gui, and pylabnet/script.

4. Write a Jupyter notebook in the pylabnet/demo folder in order to demonstrate and test the added functionality.

5. Once stable + working, commit your changes locally and push them to the remote repository. Note, this requires administrative access to lukingroup on github. Please contact one of the previous contributors if you need access.

6. If you would like your changes to be incorporated into the master branch, so other lab computers + users can use them, submit a pull request for "master" <- "new-branch". If successful, "new-branch" can be deleted from the online repository.

7. When you are ready to start the experiment, switch back to the master branch and "git pull" to make sure you are using the latest version. Then copy the relevant notebooks from the "demo" folder into a new folder outside the repository to begin working on experiments.

## Package structure

The package is contained in the pylabnet module. Within pylabnet, there are a number of sub-modules:

1. pylabnet/core: core module for setting up generic servers (for communicating with "instruments") and clients (who communicate with servers).

2. pylabnet/gui: modules for graphical output, e.g. plotting

3. pylabnet/hardware: modules for hardware drivers, organized by task. For simple devices, an interface structure is followed, so that the user can use simple, hardware-independent interface commands in scripts. Individual drivers connect those commands with hardware specific operations. For more complicated or specialized devices, the interface layer may be skipped.

4. pylabnet/logic: module for logical utilities that can be useful in scripts across many devices, for example nested/multi-dimensional sweeping or PID locking

5. pylabnet/scripts: experimental scripts. These may combine several different devices and GUI objects into a single experiment, and are the main interface for the user. For a given experiment, once all device connections are properly initialized via notebooks, for a given experiment, the user should be able to isntantiate a script object which can be used to easily run the desired experiment and output the result conveniently.

6. pylabnet/utils: low-level utilities, such as logging

## Using pylabnet for experiments

The general experimental flow is the following. It generally consists of running several auxiliary notebooks, and one master notebook. **These notebooks should be created and run outside of the pylabnet package**, but can (and should) be based off of notebooks in the demo directory within the package. Each will need to import its relevant components of the pylabnet package. Note that this could take place across multiple physically separate machines. The user will however be running scripts on one "master computer" while there may be many individual hardware specific computers.

1. On the master computer, run the notebook to set up the log-server.

2. For each individual device, on its respectice local machine, setup an individual hardware server notebook. This should contain a logger client which communicates with the log-server.

3. Create the master experiment notebook. 
(1) On the master computer, instantiate clients that connect to individual hardware servers. Note: depending on the experiment, it may be beneficial to set up a "pause" server in this notebook. This way, from a separate notebook (separate thread) you can connect to the pause server and pause the experiment while it is running inside a loop.
(2) Set up a GUI instance for the experimental result output. 
(3) Program in script parameters for the desired experimental script.
(4) Run the experiment!

## New feature: Convenient software launching

1. Make sure your Windows default `python` executable runs from the pylabnet environment. You can do this by modifying the `PATH` variable so that the path to the pylabnet python.exe is *before* any other paths that contain another python.exe file
2. (Optional) make a shortcut for pylabnet.cmd and attach to Desktop
3. Double-click your shortcut (or pylabnet.cmd). This should launch a minimzied shell and the pylabnet `Launch Control` GUI.
4. From here, you can 
- run any scripts in the pylabnet/launcher directory by double clicking on the desired script
- view all active clients to the running `Logger`
- view all client information, including port number (if the client is running its own server) and .ui file (if the client is a GUI)
5. In addition to experimental scripts, you can launch:
- an arbitrary GUI using the `pylabnet_GUI` script, which will prompt you to choose a ui template from the command line
- an arbitrary module which contains an appropriate `launch(**kwargs)` method using the `pylabnet_server` script
6. In order to debug scripts that you are launching via `Launch Control`, you can place a `time.sleep(x)` statement at the top of your script, and attach a debugger to the active process before it executes beyond the `sleep(x)` statement

