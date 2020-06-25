# pylabnet: structure

1. pylabnet/gui: modules for graphical output, e.g. plotting and PyQT based GUIs

2. pylabnet/hardware: modules for hardware drivers, organized by task. For simple devices, an interface structure is followed, so that the user can use simple, hardware-independent interface commands in scripts. Individual drivers connect those commands with hardware specific operations. For more complicated or specialized devices, the interface layer may be skipped. These can be used directly without involving any client server interface for direct and transparent access to devices if necessary

3. pylabnet/launchers: scripts for launching experiments or components of experiments, such as hardware servers

4. pylabnet/network: all functionality relating to the client-server interface for pylabnet, including core implementation of `ServiceBase`, `ClientBase`, and `GenericServer`, as well as implementation of specific `Service` and `Client` classes for relevant GUI and hardware modules

5. pylabnet/scripts: experimental scripts. These may combine several different devices and GUI objects into a single experiment, and are the main interface for the user. These potentially leverage (multiple) client-server interface(s). For a given experiment, once all device connections are properly initialized via notebooks, for a given experiment, the user should be able to isntantiate a script object which can be used to easily run the desired experiment and output the result conveniently.

6. pylabnet/utils: low-level utilities, such as logging
