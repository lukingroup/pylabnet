from pylabnet.utils.helper_methods import unpack_launcher
from pylabnet.utils.helper_methods import show_console, hide_console, load_config
import paramiko
from decouple import config
import time
import numpy as np

LOCALHOST_PW = config('LOCALHOST_PW')


def launch(**kwargs):
    """ Launches the WLM monitor + lock script """

    logger, loghost, logport, clients, guis, params = unpack_launcher(**kwargs)

    hosts = load_config(kwargs['config'], logger=kwargs['logger'])['hosts']

    for host in hosts:

        # Initiate SSH connection
        hostname = f"\'{host['hostname']}\'"
        host_ip = host['ip']

        logger.info(f"Starting SSH connection to {hostname}@{host_ip}")

        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()

        try:
            ssh.connect(host_ip, username=hostname, password=LOCALHOST_PW)
        except TimeoutError:
            logger.error(f"Failed to setup SSH connection to {hostname}@{host_ip}.")

        logger.info(f"Succesfully connected via SSH to {hostname}@{host_ip}.")

        python_path = host['python_path']
        script_path = host['script_path']
        venv_path =  host['venv_path']
        servers = host['servers']

        # I fappropriate flag is set, kill all python processes on host machine.
        # WARNING: Make sure host machine is not running any non-pylabnet processes.
        if host['kill_all'] == "True":
            logger.warn(f"Killing all python processes on {hostname}@{host_ip}.")
            kill_command = "taskkill /F /IM python.exe /T"
            ssh.exec_command(kill_command)

        for server in servers:

            try:
                disable_raw = server['disable']

                if disable_raw == 'False':
                    disable = False
                else:
                    disable = True
            except KeyError:
                disable = False

            servername = server['servername']
            logger.info(f"Trying to connect to {servername} on {hostname}.")

            # Don't execute any ssh commands if flag is set.
            if disable:
                logger.info(f'Connection to {servername} is disabled')
                continue

            # Look for optional debug flag
            try:
                if server['debug'] == "True":
                    debug = 1
                else:
                    debug = 0
            except KeyError:
                debug = 0

            # Look for optional config flag
            try:
                config = server['config']
            except KeyError:
                config = None

            server_port = np.random.randint(1, 9999)

            # Activate virtual env
            ssh.exec_command(venv_path)

            cmd = '"{}" "{}" --logip {} --logport {} --serverport {} --server {} --debug {} --config {}'.format(
                        python_path,
                        script_path,
                        loghost,
                        logport,
                        server_port,
                        servername,
                        debug,
                        config
                    )
            # Look for device name and ID
            try:
                cmd += f" --device_name {server['device_name']} --device_id {server['device_id']}"
            except KeyError:
                logger.warn(f'Device name and ID not specified for {servername}')
            logger.info(f'Executing command on {hostname}:\n{cmd}')

            ssh.exec_command(cmd)

        ssh.close()



