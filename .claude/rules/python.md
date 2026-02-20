# Python

This project uses Python tooling on the command line. Therefore you must ensure that Python is running within a virtual environment whenever Claude starts.

```bash
python3 -m venv ./.venv
source ./.venv/bin/activate
```

Utilise the `requirements.txt` file at the project root and ensure all packages within it are installed when Claude starts via:

```bash
pip3 install -r ./requirements.txt
```

Python scripts defined within Ansible rules are an exception to this. They will have their own virtual environments defined in the Ansible tasks.
