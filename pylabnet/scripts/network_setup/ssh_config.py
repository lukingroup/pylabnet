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
            logger.warn(f"Failed to setup SSH connection to {hostname}@{host_ip}")

        logger.warn(f"Connected via SSH to {hostname}@{host_ip}")

        python_path = host['python_path']
        script_path = host['script_path']
        venv_path =  host['venv_path']
        servers = host['servers']

        for server in servers:

            servername = server['servername']
            server_port = np.random.randint(1, 9999)

            # Activate virtual env
            ssh.exec_command(venv_path)


            cmd = '"{}" "{}" --logip {} --logport {} --serverport {} --server {} --debug {}'.format(
                        python_path,
                        script_path,
                        loghost,
                        logport,
                        server_port,
                        servername,
                        False
                    )

            ssh.exec_command(cmd)


        ssh.close()



