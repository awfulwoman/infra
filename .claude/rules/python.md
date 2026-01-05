# Python

This project uses Python in many places, including pre-commit hooks. Therefore you must ensure that Python is operating within a virtual environment.

```bash
python3 -m venv ./venv
source ./venv/bin/activate
```

At the project level a `requirements.txt` file exists. Ensure all packages within it are installed via:

```bash
pip3 install -r ./requirements.txt
```

Python scripts defined within Ansible rules are an exception to this. They will have their own virtual environments defined in the Ansible tasks.
