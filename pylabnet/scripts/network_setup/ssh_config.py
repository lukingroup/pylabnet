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
        hostname = host['hostname']
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

            servername = server['servername']

            try:
                disable = bool(server['disable'])
            except KeyError:
                disable = False

            # Don't execute any ssh commands if flag is set.
            if disable:
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

            ssh.exec_command(cmd)


        ssh.close()


