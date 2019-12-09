# pylabnet: structure

1. pylabnet/core: core module for setting up generic servers (for communicating with "instruments") and clients (who communicate with servers).

2. pylabnet/gui: modules for graphical output, e.g. plotting

3. pylabnet/hardware: modules for hardware drivers, organized by task. For simple devices, an interface structure is followed, so that the user can use simple, hardware-independent interface commands in scripts. Individual drivers connect those commands with hardware specific operations. For more complicated or specialized devices, the interface layer may be skipped.

4. pylabnet/logic: module for logical utilities that can be useful in scripts across many devices, for example nested/multi-dimensional sweeping or PID locking

5. pylabnet/scripts: experimental scripts. These may combine several different devices and GUI objects into a single experiment, and are the main interface for the user. For a given experiment, once all device connections are properly initialized via notebooks, for a given experiment, the user should be able to isntantiate a script object which can be used to easily run the desired experiment and output the result conveniently.

6. pylabnet/utils: low-level utilities, such as logging
