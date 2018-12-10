# Django Skeleton

Extended startproject template for new Django projects.

**Django 2.1** and **Python 3.6**

## Using this Template

Starting a new project and want to use this skeleton? Follow these steps.

1. Copy the contents of the skeleton to your new project directory.
2. Change the app name from the placeholder "appname" to a name of your
choosing in the following places:
    - The `appname` directory itself
    - In `common_settings.py`, the `INSTALLED_APPS` setting
    - In `common_settings.py`, the `LOGGING` setting
    - The import statement in the project-wide `urls.py`
    - The references in `tox.ini`
3. Change the skeleton project name references to your project name.
    - The [developer docs](docs)
4. Run `git init` and make your initial commit
5. Set up git remotes and push the initial commit to a remote repository
6. Delete this readme, as it's only relevant to the skeleton!
7. Proceed to the development doc page for setting up your dev environment
