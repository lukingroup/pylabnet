# Conda Setup Instructions

**Note: the package can now be installed, run, and developed without use of a specific conda environment.** These instructions only apply if you plan on developing and using the package in a dedicated conda environment, specified by `env_file.yml`. *This method is no longer recommended as of version 0.2.1*

1. Clone pylabnet from GitHub (`C:/Users/Username` is the recommended location). See README.md in `pylabnet` root directory for more detials.

2. Add pylabnet location to PYTHONPATH environment variable. Note, you may have to create a new environment variable named PYTHONPATH, if it does not already exist on your system.

3. Create pylabnet environment according to `pylabnet/setup/env_file.yml` (navigate to `pylabnet/setup` in conda shell and run the command: 
```python
conda env create -f env_file.yml
```

4. Configure your editor (PyCharm, VisualStudio, etc) to use the `python.exe` executable within the pylabnet environment. This is usually found in `Users/Username/anaconda3/envs/pylabnet`

5. Make sure to activate the pylabnet virtual environment before running any pylabnet scripts or using a Jupyter Notebook with pylabnet.

- For example, to use Jupyter: run Jupyter Notebook in Pylabnet environment by using commands:
```powershell
conda activate pylabnet
jupyter notebook
```
- This will open the notebook in pylabnet environment. In future, can just pin the pylabnet environment (rather than Anaconda base) to the start menu.
- To run a script directly from the command prompt, it's very similar:
```powershell
conda activate pylabnet
python my_script.py arg1 arg2
```

## Maintaining Conda Environments

After having added or removed a python package, update the `env_file.yml` entry accordingly. If someone else has modified the file `env_file.yml` and your local conda environement misses the newly added packages,   move to the `pylabnet/setup` folder and execute:
```bash
conda env update --file env_file.yml
```
