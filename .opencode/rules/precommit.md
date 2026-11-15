# Pre-commit hooks

When starting the project you must ensure that the Python package `pre-commit` is installed. You can check for it by running `pre-commit --version`. If not, use the `requirements.txt` file to install it. Then initialise it with `pre-commit install`.

When committing any files you must expect that this package will be run via a git pre-commit hook. The configuration for this is in `.pre-commit-config.yaml`.

If any errors are shown you should inform the user and fix them before attempting to commit again.
