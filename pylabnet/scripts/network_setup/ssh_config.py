from pylabnet.utils.helper_methods import unpack_launcher
from pylabnet.utils.helper_methods import show_console, hide_console, load_config
import paramiko
from decouple import config

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
        ssh.connect(host_ip, username=hostname, password=LOCALHOST_PW)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("ipconfig -all")

        logger.info(f"{ssh_stdout}")








