from pylabnet.utils.helper_methods import unpack_launcher
from pylabnet.utils.helper_methods import show_console, hide_console, load_config
import paramiko
from decouple import config
import time

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


        python_path = host['python_path']
        script_path = host['script_path']
        servers = host['servers']

        for server in servers:

            servername = server['servername']
            server_port = np.random.randint(1, 9999)

            cmd = 'start "{}, {}" "{}" "{}" --logip {} --logport {} --serverport {} --server {} --debug {} --config {}'.format(
                        servername+"_server",
                        time.strftime("%Y-%m-%d, %H:%M:%S", time.gmtime()),
                        python_path,
                        script_path,
                        loghost,
                        logport,
                        server_port,
                        servername,
                        False,
                        None
                    )

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)



