# Convenient software launching

## Using the feature

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

## Developing within this framework

1. Add your top-level launching script to the pylabnet/launchers directory. For an example of this script, see counters.py
    1. The launching script (in the example case, counters.py) should instantiate a `Launcher` object defined in launcher.py
    2. During instantiation, pass the `Launcher` all information required to run the desired application. This includes:
        1. **A list of script modules to execute, sequentially (e.g. `[script_module]`).**
            * This module can implement arbitrary classes, but the module itself must have a method `script_module.launcher(**kwargs)` which can run the desired script/application (see `count_monitor.launcher(**kwargs)` for an example and/or `Launcher._launch_scripts()` for the generic implementation)
            * These will be run in the main process thread, and in general require other servers and/or GUIs to be running (see below)
            * In our counter example, we want to run a single script given in the monitor_counts.py module. 
        2. **A list of required server modules to be running, prior to execution of the script(s) (e.g. `[server_module_1, server_module_2]`).**
            * These server-launching submodules should be located in the `pylabnet.launchers.servers` module
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
            "port": 5678,
            "host": "localhost",
            "redirectOutput" : true,
            "processId": "${command:pickProcess}"
        },
        ```
        * Launch the process (with double-click), then launch the debugger immediately following
        * It will give you a search bar to search for and select the process to debug
    3. Now you can debug your subprocess that was launched via Launch Control!
    4. Each time you encounter an instantiation of Popen(), this will launch a new process that will need to be separately debugged. *Note that you **can** have multiple debuggers running simultaneously, you just need to make multiple configurations in your launch.json file that have different `"name"` subfields. So you can play the same trick over and over again to your heart's desire.*
