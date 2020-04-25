# Setup Instructions

1. Clone pylabnet from GitHub (C:/Users/Username is the recommended location)

2. Clone pulseblock from GitHub (C:/Users/Username is the recommended location)

3. add pylabnet and pulseblock locations to PYTHONPATH environment variable.

4. Create pylabnet environment according to `pylabnet/setup/env_file.yml` (navigate to pylabnet/setup
	in conda shell and run command :
		`conda env create -f env_file.yml`

5. Make sure to activate pylabnet virtual environment to run Jupyter Notebook
    and configure PyCharm to use Python interpreter from pylabnet environment.

- For Jupyter: run Jupyter Notebook in Pylabnet environment by using command:
`activate pylabnet` followed by `jupyter notebook`.

- This will open the notebook in pylabnet environment. In future, can just pin the pylabnet environment
 (rather than Anaconda base) to the start menu.

# Maintaining Conda Environments

After having added or removed a python package, update the `env_file.yml` entry accordingly. If someone else has modified the file `env_file.yml` and your local conda environement misses the newly added packages,   move to the `pylabenet/setup` folder and execute:

`conda env update --file env_file.yml  `


