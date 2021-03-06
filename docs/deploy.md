# All-New, All-Purpose Deployment Guide

This section has been completely re-written with tried-and-tested steps. It
has everything you need to do to deploy onto a fresh CentOS7 install using
Postgresql as the database. Most commands are now copy-and-paste bash friendly!

----

**Note:**
All these commands should be run as root, except where indicated by `sudo -u`

----

* Do a full system update and reboot
    ```bash
    $ yum update
    $ shutdown -r now
    ```
* Install Python 3.6
    ```bash
    $ yum install epel-release
    $ yum install python36
    ```
* Choose a name for your deployment, usually chosen after the project name.
This is used in many of the commands below. If you're copy-pasting into bash,
then bash will do the substitution for you.
    ```bash
    $ export DEPLOYMENT=deployment
    ```
* Create the os user for the application deployment.
    ```bash
    useradd $DEPLOYMENT
    ```
* Install PostgreSQL and setup the application database.
    ```bash
    yum install https://download.postgresql.org/pub/repos/yum/11/redhat/rhel-7-x86_64/pgdg-centos11-11-2.noarch.rpm
    yum install postgresql11 postgresql11-server postgresql11-devel
    /usr/pgsql-11/bin/postgresql-11-setup initdb
    systemctl enable postgresql-11 && systemctl start postgresql-11
    sudo -u postgres createuser $DEPLOYMENT
    sudo -u postgres createdb -O $DEPLOYMENT $DEPLOYMENT
    ```
* Extract the code bundle to `/opt/$DEPLOYMENT`. It should be owned by the root
    user or some user other than the deployment user. The deployment user is
    used to run it and good security practice is to not let your code have write
    permission to itself.

    **Hint:** run a command like this from your local development machine for a
    clean one-liner that copies the code over. Note that you have to create the
    directory first.

    ```bash
    # On your local machine:
    $ export DEPLOYMENT=deployment
    $ ./manage.py bundle master --tar -o - | ssh remote-machine.example.com sudo tar xC /opt/$DEPLOYMENT --no-same-owner
    ```

    *See the "Deploying Changes" section below for a convenient script that
    re-deploys changes to an existing deployment.*
* Back on the server, `cd` into the deployment directory
    ```bash
    $ cd /opt/$DEPLOYMENT
    ```
* Setup the python virtual environment and install the requirements. Our
  new bundle command pre-downloads all dependencies, but we have to turn
  pip's dependency resolver off because it's not smart enough to realize
  a dependency of one command line argument is given in another command
  line argument.
    ```bash
    $ /usr/bin/python3.6 -m venv env
    $ source env/bin/activate
    $ pip install --upgrade pip  # optional
    $ pip install --no-index --no-deps dependencies/*
    ```
    
* Set up environment var file. `cp project/develop/env .env` and then edit `.env`
    * Set `DJANGO_SETTINGS_MODULE=project.deploy.settings`
    * Set `DEBUG=false`
    * Set the SECRET_KEY
    * Set the ALLOWED_HOSTS
    * Set `DATABASE_URL=postgres:///$DEPLOYMENT` (must explicitly set the
        database name, but the username and host are implicit)
    * Any other settings as appropriate for your deployment
    
* If you need postgres extensions loaded, do that manually now before you
migrate
    ```bash
    $ yum install postgresql11-contrib
    $ sudo -u postgres psql $DEPLOYMENT
    ```
    ```sql
    CREATE EXTENSION citext;
    ```
    
* Migrate the database to make sure db access is working
    ```bash
    $ sudo -u $DEPLOYMENT env/bin/python ./manage.py migrate
    ```
* Collect the static files
    ```bash
    $ ./manage.py collectstatic
    ```
* Add a run directory for the gunicorn socket. Make it writable by your
  deployment user. I usually use `./run`
    ```bash
    $ mkdir /opt/$DEPLOYMENT/run && chown $DEPLOYMENT:$DEPLOYMENT /opt/$DEPLOYMENT/run
    ```
* Make and chown any other directories your deployment needs to write to
  (such as a media root)
* Install supervisor and create the config using this template
    ```bash
    $ yum install supervisor
    $ cat > /etc/supervisord.d/$DEPLOYMENT.ini <<- EOF
    [program:$DEPLOYMENT]
    directory = /opt/$DEPLOYMENT
    command = /opt/$DEPLOYMENT/env/bin/gunicorn --pythonpath /opt/$DEPLOYMENT --bind=unix:/opt/$DEPLOYMENT/run/gunicorn.sock -w 4 --timeout 300 project.wsgi
    stdout_logfile = /opt/$DEPLOYMENT/run/gunicorn.log
    redirect_stderr = true
    autostart = true
    autorestart = true
    user = $DEPLOYMENT
    group = $DEPLOYMENT
    EOF
    ```
* Start the supervisor process and add it to the system startup
    ```bash
    $ systemctl enable supervisord
    $ systemctl start supervisord
    ```
* Check `supervisorctl status` to see if things worked okay
* Install nginx and create the config
    ```bash
    $ yum install nginx
    $ cat > /etc/nginx/conf.d/$DEPLOYMENT.conf <<- EOF
    upstream gunicorn {
        server unix:/opt/$DEPLOYMENT/run/gunicorn.sock fail_timeout=0;
    }

    server {
        listen 80;
        server_name $DEPLOYMENT.example.com;

        location /static/ {
            alias /opt/$DEPLOYMENT/static-root/;
        }

        location / {
            client_max_body_size 100m;
            proxy_read_timeout 300;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_set_header Host \$http_host;
            proxy_redirect off;
        proxy_pass http://gunicorn;
      }
    }
    EOF
    ```
    Change the server_name as appropriate to match your ALLOWED_HOSTS in the
    environment config. The backslashes escape the dollar signs for bash;
    remove them if you're copy-pasting the config into the file instead of
    pasting bash commands.

    Also, if this host is itself behind another Nginx reverse proxy that
    does SSL termination, remove the X-Forwarded-Proto header line and
    make sure the upstream proxy adds it.

    Also make sure to add any additional static directories such as your
    media files, if that applies to your project.
* Validate the nginx config by running `nginx -t`
* Start the nginx process and add it to the system startup
    ```bash
    $ systemctl enable nginx
    $ systemctl start nginx
    ```

## Deployment Troubleshooting

If you run into weird permission problems, check your system logs for SELinux
errors. If SELinux denies nginx permission to read the gunicorn socket file,
you can give nginx read-write permissions to all files in a directory with
these commands:

```bash
$ yum install policycoreutils-python
$ semanage fcontext -a -t httpd_sys_rw_content_t "/opt/$DEPLOYMENT/run(/.*)?"
$ restorecon -vR /opt/$DEPLOYMENT/run
```
[Read more about the different context types that RedHat/CentOS uses with web servers](https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/6/html-single/Managing_Confined_Services/#sect-Managing_Confined_Services-The_Apache_HTTP_Server-Types)

# SSL Setup

Adapted from:
- https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-16-04
- https://certbot.eff.org/#centosrhel7-nginx


To get LetsEncrypt running on the Nginx instance you just set up, follow
these steps:

1. `yum install certbot python2-certbot-nginx` (assumes CentOS7 and epel repos installed)
2. Run `certbot --nginx` and follow the prompts. The nginx plugin makes the
   necessary changes to your nginx config to do the validation and to enable SSL.

3. Configure certbot to renew certificates automatically:

   run `certbot renew --dry-run` to make sure everything looks okay. If you
used a different method for installing the initial cert, you may need to edit
the file in `/etc/letsencrypt/renewal/my-hostname.example.com.conf` so that the
`certbot renew` command knows what to do.

   Then add the following to a file at `/etc/cron.d/letsencrypt`

   ```
    #MAILTO=admin-email@example.com
    PATH=/sbin:/bin:/usr/sbin:/usr/bin

    15 10,22 * * * root certbot renew --quiet
   ```
   This checks twice a day if the cert needs renewal. You should adjust the exact
   minute and hours attempted to random values, but it's not a huge deal.

## Deployment notes and tips:

* By default, Supervisor rotates the stdout log file after 50 megabytes and
  keeps 10 past backups. You may consider tweaking these parameters in the
  supervisor config.

  For some situations, it's more appropriate to change Python's logging
  configuration to have Python log to a file instead of stderr so that Python
  can handle the log rotation instead of supervisor (using the
  RotatingFileHandler or TimedRotatingFileHandler). You will need to decide
  for yourself which makes the most sense for your situation.

  It usually makes sense to have supervisor perform the logging, so any
  erroneous writes to stdout or stderr by python outside of the logging
  system go to the same file. On the other hand, you may want to
  separate them if you want your log files in a consistent format, and you're
  using some library that's being rude and doing its own writing to stderr
  instead of using python logging.

* For production deployments, using Sentry is highly recommended. Make sure you
include the sentry DSN in the env file.

## Deploying Changes

A simple script like this one can deploy changes in one shot:

```bash
DEPLOYMENT=deployment
REMOTE=remote-machine.example.com

set -e -x

# Copy the code
./manage.py bundle master --tar -o - | ssh $REMOTE sudo tar xC /opt/$DEPLOYMENT
# Install any new requirements
ssh $REMOTE sudo /opt/$DEPLOYMENT/env/bin/pip install --no-index --no-deps -f /opt/$DEPLOYMENT/dependencies/ -r /opt/$DEPLOYMENT/requirements.txt
# Collect any new static files
ssh $REMOTE sudo /opt/$DEPLOYMENT/env/bin/python /opt/$DEPLOYMENT/manage.py collectstatic --noinput
# Apply any new database migrations
ssh $REMOTE sudo -u $DEPLOYMENT /opt/$DEPLOYMENT/env/bin/python /opt/$DEPLOYMENT/manage.py migrate
# Clear out any old sessions (good to do this once in a while, but not
# necessary)
ssh $REMOTE sudo -u $DEPLOYMENT /opt/$DEPLOYMENT/env/bin/python /opt/$DEPLOYMENT/manage.py clearsessions
# Restart the gunicorn server
ssh $REMOTE sudo supervisorctl restart $DEPLOYMENT
```
