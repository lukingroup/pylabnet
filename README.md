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

### Using the feature

1. Make sure your Windows default your PATH environment variable contains the directory to conda.exe (e.g. make sure you can rund "conda activate pylabnet" from the command line)
2. Modify the shortcuts with the device icon in the main pylabnet directory
    1. Copy the shortcuts to your desktop.
    2. Right-click on the shortcut, and select properties
    3. In the "Start in" field, replace whatever is entered with the local machine's path to the pylabnet/launchers/ directory. This should be already listed in the "Target" field. *Still trying to come up with a more elegant way to do this, but this is simplest for now*
3. Double-click your new desktop shortcut. This should launch a minimzied shell and the pylabnet `Launch Control` GUI. Note that you can use pylabnet to launch the main Log Server, and pylabnet_proxy to launch a proxy launcher that will connect to an already running Log Server and Launch Control GUI
4. From here, you can 
    1. Run any scripts in the pylabnet/launcher directory by double clicking on the desired script
    2. View all active clients to the running `Logger`
    3. View all client information, including port number (if the client is running its own server) and .ui file (if the client is a GUI)
5. In addition to experimental scripts, you can launch:
    1. An arbitrary GUI using the `pylabnet_GUI` script, which will prompt you to choose a ui template from the command line
    2. An arbitrary module which contains an appropriate `launch(**kwargs)` method using the `pylabnet_server` script

### Developing within the new framework

1. Add your top-level launching script to the pylabnet/launchers directory. For an example of this script, see counters.py
    1. The launching script (in the example case, counters.py) should instantiate a `Launcher` object defined in launcher.py
    2. During instantiation, pass the `Launcher` all information required to run the desired application. This includes:
        1. **A list of script modules to execute, sequentially (e.g. `[script_module]`).**
            * This module can implement arbitrary classes, but the module itself must have a method `script_module.launcher(**kwargs)` which can run the desired script/application (see `count_monitor.launcher(**kwargs)` for an example and/or `Launcher._launch_scripts()` for the generic implementation)
            * These will be run in the main process thread, and in general require other servers and/or GUIs to be running (see below)
            * In our counter example, we want to run a single script given in the monitor_counts.py module. 
        2. **A list of required server modules to be running, prior to execution of the script(s) (e.g. `[server_module_1, server_module_2]`).**
            * These modules should be imported at the top of the launcher script file (in the example case, counter.py)
            * Each server module should have a `server_module.launch(**kwargs)` method that performs connection to hardware (if necessary) and instantiates the desired server
            * Parameters are *not* passed to individual server modules, so any specific configurations should be specified directly in the definition of `server_module.launch(**kwargs)`. *We can consider passing parameters when programming the launcher script, but in reality once configured initially, the hardware + server instantiation should be relatively static, with all variable input happening via the client.*
            * These servers are instantiated in a separate process using `subprocess.Popen` to run the pylabnet_server.py script
            * Once a server is instantiated, a `test_module.Client` will be instantiated in the main launcher thread
            * This client will be passed as part of `**kwargs` to each of the scripts, so that the script has access to all necessary clients
        3. **A list of required GUI modules to be running.** The logic is very similar to item (2) above, but in this case one just needs to provide a list of .ui files, and the necessary GUI servers will be launched in separate processes, with corresponding clients instantiated in the main thread to be passed to the experimental scripts
        4. **A list of parameter dictionaries for each script**, to enable passing arbitrary parameters to each script via `kwargs['params']` in the scripts `launcher(**kwargs)` function (see `count_monitor.launcher(**kwargs)` for an example)
    3. Call Launcher.launch(). That's it.
2. Make sure pylabnet_server.py imports all of the server modules your script(s) require, since this will be the script used to launch them. *We can potentially come up with a better way of doing this, perhaps by consolidating dedicated server launching scripts in a unique location.*
3. Now you should be able to launch your script and requisite servers with a simple double-click from the Launch Control!
4. In practice, everything may fail, and it may seem to be difficult to trace what is happening. In order to debug scripts that you are launching via `Launch Control`:
    1. Place a `time.sleep(x)` statement at the top of your script.
    2. Attach a debugger to the active process launched by the double-click before it executes beyond the `sleep(x)` statement 
    (make sure there is a suitable breakpoint in place)
        *In Visual Studio, this requires configuring a debugger with a launch.json file that looks like this:
        ```
        {
            "name": "Python: attach to launcher",
            "type": "python",
            "request": "attach",
            "processId": "${command:pickProcess}"
        }
        ```
        * Launch the process (with double-click), then launch the debugger immediately following
        * It will give you a search bar to search for and select the process to debug
    3. Now you can debug your subprocess that was launched via Launch Control!
    4. Each time you encounter an instantiation of Popen(), this will launch a new process that will need to be separately debugged. *Note that you **can** have multiple debuggers running simultaneously, you just need to make multiple configurations in your launch.json file that have different `"name"` subfields. So you can play the same trick over and over again to your heart's desire.*
