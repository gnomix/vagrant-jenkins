from time import sleep

from fabric.api import env, local, run, sudo, cd
from fabric.contrib.files import append, exists

def jenkins():
    run("wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -")
    sudo("sh -c 'echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list'")
    sudo("apt-get -qq update")
    sudo("apt-get -qq install jenkins")
    # Jenkins takes a while to start in the background, so we need to check
    # that the proper directories were created before proceeding:
    while not exists("/var/lib/jenkins/plugins"):
        print "Waiting for Jenkins to start..."
        sleep(1)

    jenkins_install_plugins()

def jenkins_install_plugins():
    # Install new plugins
    with cd("/var/lib/jenkins/plugins"):
        # git
        sudo("wget -nv --no-check-certificate http://updates.jenkins-ci.org/latest/git.hpi")

        # github (depends on github-api)
        sudo("wget -nv --no-check-certificate http://updates.jenkins-ci.org/latest/github-api.hpi")
        sudo("wget -nv --no-check-certificate http://updates.jenkins-ci.org/latest/github.hpi")

    # Configure the "git" plugin:
    sudo("apt-get -qq install git-core")
    sudo('su -c "git config --global user.email \"jenkins@xxx.x\"" -s /bin/bash jenkins')
    sudo('su -c "git config --global user.name \"jenkins\"" -s /bin/bash jenkins')

    # Restart Jenkins to register the new plugins
    # Important: one has to use pty=False, otherwise the init script doesn't
    # work (http://docs.fabfile.org/en/1.4.1/faq.html#init-scripts-don-t-work)
    sudo("/etc/init.d/jenkins restart", pty=False)


def forward_port():
    sudo("apt-get -qq install nginx")
    sudo("rm /etc/nginx/sites-available/default")
    conf = """\
upstream app_server {
    server 127.0.0.1:8080 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80 default ipv6only=on;
    server_name ci.yourcompany.com;

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;

        if (!-f $request_filename) {
            proxy_pass http://app_server;
            break;
        }
    }
}
"""

    append("/etc/nginx/sites-available/jenkins", conf, use_sudo=True)
    sudo("ln -s /etc/nginx/sites-available/jenkins /etc/nginx/sites-enabled")
    sudo("service nginx restart")


def vagrant():
    vc = _get_vagrant_config()
    # change from the default user to 'vagrant'
    env.user = vc['User']
    # connect to the port-forwarded ssh
    env.hosts = ['%s:%s' % (vc['HostName'], vc['Port'])]
    # use vagrant ssh key
    env.key_filename = vc['IdentityFile']

def _get_vagrant_config():
    """
    Parses vagrant configuration and returns it as dict of ssh parameters
    and their values
    """
    result = local('vagrant ssh-config', capture=True)
    conf = {}
    for line in iter(result.splitlines()):
        parts = line.split()
        conf[parts[0]] = ' '.join(parts[1:])

    return conf

def uname():
    run('uname -a')
