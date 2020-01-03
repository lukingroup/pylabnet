(1) Checkout pylabnet from GitHub (C:/Users/Username is the recommended location)

(2) Checkout pulseblock from GitHub (C:/Users/Username is the recommended location)

(3) add pylabnet and pulseblock locations to PYTHONPATH environment variable.

(4) Create pylabnet environment according to pylabnet/setup/env_file.yml (navigate to pylabnet/setup
	in conda shell and run command :
		conda env create -f env_file.yml
	
(5) Make sure to activate pylabnet virtual environment to run Jypeter Notebook 
    and configure PyCharm to use Python interpreter from pylabnet environment.

--> For Jupyter: run Jupyter Notebook in Pylabnet environment by using command:
		activate pylabnet

		jupyter notebook

--> This will open the notebook in pylabnet environment. In future, can just pin the pylabnet environment
 (rather than Anaconda base) to the start menu

