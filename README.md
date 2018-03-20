# Django Skeleton

[![Build Status](https://travis-ci.org/ITNG/django-skeleton.svg?branch=master)](https://travis-ci.org/ITNG/django-skeleton)

Designed to work with Django 1.11 on Python 3.6.

## Starting a New Project
Starting a new project and want to use this Skeleton? Follow these steps.

1. Copy the contents of the skeleton to your new project directry.
2. Change the app name from the placeholder "appname" to a name of your 
choosing in the following places:

   * The app directory name itself
   * In `common_settings.py` the INSTALLED_APPS setting
   * In `common_settings.py` the LOGGING setting
   * The import statement in the project-wide `urls.py`
   
3. Run `git init` and make your initial commit
4. Set up git remotes and push the initial commit to a remote repository
5. Continue to the next step for Setting up your Development Enviroment
6. Delete this section from the readme, as it's only relevant to the skeleton!
   
## Setting up your Development Environment

1. Clone the project to a local directory (or if coming from the previous 
section, skip this step)
2. CD into your project directory
3. Create a virtual environment and install the requirements listed in
   `requirements.txt`

   * In this directory, run `python3.4 -m venv env` to create the virtual 
   environment.
   * activate your virtualenv for this terminal with `source 
   ./env/bin/activate`.
   * Now run `pip install -r requirements.txt`

3. From the base directory, copy `project/develop/env` to `.env`. No
   changes are needed for development. See the README in the `project`
   directory for more information on how environment files work and how our 
   settings are organized.

4. Create your database and initial schemas with
   `./manage.py migrate`. The default database is a
   sqlite-based file in the base directory of your project.

5. You now have a working development environment. Run the django test server
   with `./manage.py runserver`
   
# All-New, All-Purpose Deployment Guide
This section has been completely re-written with tried-and-tested steps. It 
has everything you need to do to deploy onto a fresh CentOS7 install using 
Postgresql as the database. Most commands are now copy-and-paste bash friendly!

All these commands should be run as root, except where indicated by `sudo -u`

* Do a full system update and reboot
    ```bash
    yum update
    shutdown -r now
    ```
* `yum install https://centos7.iuscommunity.org/ius-release.rpm`
* `yum install python34u`
* Choose a name for your deployment, usually chosen after the project name. 
This is used in many of the commands below. If you're copy-pasting into bash,
then bash will do the substitution for you.
    ```bash
    export DEPLOYMENT=deployment
    ```
* `useradd $DEPLOYMENT`
* `yum install https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-7-x86_64/pgdg-centos96-9.6-3.noarch.rpm`
* `yum install postgresql96 postgresql96-server postgresql96-devel`
* `/usr/pgsql-9.6/bin/postgresql96-setup initdb`
* `systemctl enable postgresql-9.6 && systemctl start postgresql-9.6`
* `sudo -u postgres createuser $DEPLOYMENT`
* `sudo -u postgres createdb -O $DEPLOYMENT $DEPLOYMENT`
* Extract the code bundle to `/opt/$DEPLOYMENT`. It should be owned by the 
root user or some user other than the deployment user. The deployment user is 
used to run it and good security practice is to not let your code have write 
permission to itself.

    Hint: run a command like this from your local development machine for a 
    clean one-liner that copies the code over. Note you have to create the 
    directory first.
    
    ```bash
    # On your local machine:
    export DEPLOYMENT=deployment
    ./manage.py bundle --tar -o - | ssh remote-machine.example.com sudo tar xC /opt/$DEPLOYMENT
    
    ```
    
    See below in the section on Delpoying Changes for a convenient script 
    that re-deploys changes to an existing deployment.
  
* back on the server, CD into the deployment directory

    `cd /opt/$DEPLOYMENT`
* `/usr/bin/python3.4 -m venv env`
* `source env/bin/activate`
* `pip install -r requirements.txt gunicorn psycopg2`
* `yum install supervisor`
* Set up environment var file. `cp project/develop/env .env` and then edit `.env`
  * Set DJANGO_SETTINGS_MODULE to `project.deploy.settings`
  * Set DEBUG to false
  * Set a SECRET_KEY
  * Set the allowed hosts
  * Set DATABASE_URL to `postgres:///$DEPLOYMENT` (must explicitly set the 
  database name, but the username and host are implicit)
  * Any other settings as appropriate for your deployment
* If you need postgres extensions loaded, do that manually now before you 
migrate
    ```bash
    yum install postgresql96-contrib
    sudo -u postgres psql $DEPLOYMENT
    ```
    ```postgresql
    CREATE EXTENSION citext;
    ```
* Migrate the database to make sure db access is working

    ```bash
    sudo -u $DEPLOYMENT env/bin/python ./manage.py migrate
    ```
* Add a run directory for the gunicorn socket. Make it writable by your 
  deployment user. I usually use `./run`
  ```bash
  mkdir /opt/$DEPLOYMENT/run && chown $DEPLOYMENT:$DEPLOYMENT /opt/$DEPLOYMENT/run
  ```
* Make and chown any other directories your deployment needs to write to 
  (such as a media root)
* Create supervisor config using this template
    ```bash
    cat > /etc/supervisord.d/$DEPLOYMENT.ini <<- EOF
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
* `systemctl enable supervisord && systemctl start supervisord`
* Check `supervisorctl status` to see if things worked okay
* `yum install nginx`
* Create nginx config
    ```bash
    cat > /etc/nginx/conf.d/$DEPLOYMENT.conf <<- EOF
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
    enviornment config. The backslashes escape the dollar signs for bash; 
    remove them if you're copy-pasting the config into the file instead of 
    pasting bash commands.
    
    Also, if this host is itself behind another Nginx reverse proxy that
    does SSL termination, remove the X-Forwarded-Proto header line and
    make sure the upstream proxy adds it.
    
    Also make sure to add any additional static directories such as your 
    media files, if that applies to your project.
* `nginx -t` to make sure the config passes syntax validation
* `./manage.py collectstatic`
* `systemctl enable nginx && systemctl start nginx`

## Deployment Troubleshooting

If you run into weird permission problems, check your system logs for SELinux
errors. If SELinux denies nginx permission to read the gunicorn socket file, 
you can give nginx read-write permissions to all files in a directory with 
these commands:

```bash
yum install policycoreutils-python
semanage fcontext -a -t httpd_sys_rw_content_t "/opt/$DEPLOYMENT/run(/.*)?"
restorecon -vR /opt/$DEPLOYMENT/run
```
[Read more about the different context types that RedHat/CentOS uses with web servers](https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/6/html-single/Managing_Confined_Services/#sect-Managing_Confined_Services-The_Apache_HTTP_Server-Types)

# SSL Setup

To get LetsEncrypt running on the Nginx instance you just set up, follow
these steps

(adapted from <https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-16-04>
and <https://certbot.eff.org/#centosrhel7-nginx>)

1. `yum install certbot` (assumes CentOS7 and epel repos installed)
2. Create a directory somewhere on the filesystem such as /opt/webroot
3. Add a new location block to your nginx config that looks like this:

   ```
   location ~ /.well-known {
       root /opt/webroot;
   }
   ```
   and reload nginx with `nginx -s reload`
   
3. Run `certbot certonly`

   This will ask you for your domain name and web root. If successful, it
   will go ahead and issue you your cert.
   
   If your deployment is not yet serving users, and nginx isn't yet running, 
   then choose certbot's "spin up a temporary web server" option for this step.

4. Generate strong dh parameters with

   ```openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048```

5. Modify your nginx config. Add this block for port 80

    ```
    server {
         listen 80;
         server_name deployment.example.com;
         return 301 https://$server_name$request_uri;
    }
    ```
    
    And change your existing block's listen line to `listen 443 ssl;` and add
    these new lines to it:
    
    ```
    ssl_certificate /etc/letsencrypt/live/deployment.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/deployment.example.com/privkey.pem;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_prefer_server_ciphers on;
    ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
    ssl_ecdh_curve secp384r1;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;
    add_header Strict-Transport-Security "max-age=6307200; includeSubdomains";
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nostiff;
    ssl_dhparam /etc/ssl/certs/dhparam.pem;
    ```
    
    Make sure to change the hostname in the `server_name` directives and in 
    the certificate paths.

   Now test and reload your nginx config

   ```
   nginx -t && nginx -s reload
   ```

6. Configure certbot to renew certificates automatically:

   run `certbot renew --dry-run` to make sure everything looks okay. If you 
   initially had certbot spin up a temporary web server, you may need to 
   reconfigure it to use a webroot.
   
   1. Open the file at `/etc/letsencrypt/renewal/my-hostname.example.com.conf`
   2. Change the line `authenticator = standalone` to `authenticator = webroot`
   3. Add these lines at the bottom of the file:
   
      ```
      [[webroot_map]]
      my-hostname.example.com = /opt/webroot
      ```
      
   4. Run `certbot renew --dry-run` to make sure it works

   Add the following to a file at `/etc/cron.d/letsencrypt`

   ```
    MAILTO=admin-email@example.com
    PATH=/sbin:/bin:/usr/sbin:/usr/bin
    
    15 10,22 * * * root certbot renew --quiet --post-hook "nginx -s reload"
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
./manage.py bundle --tar -o - | ssh $REMOTE sudo tar xC /opt/$DEPLOYMENT
# Install any new requirements
ssh $REMOTE sudo /opt/$DEPLOYMENT/env/bin/pip install -r /opt/$DEPLOYMENT/requirements.txt
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
