# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, 
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of 
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

import os
import json
import paramiko
import digitalocean
import fabric
from fabric import Connection
from loguru import logger
logger = logger.opt(colors=True)

def get_droplets ( config ):
    manager = digitalocean.Manager( token = config.token )
    droplets = manager.get_all_droplets( tag_name = [ config.cluster ])
    droplets = [drop for drop in droplets if drop.name in config.machines]
    if config.names != None:
        droplets = [drop for drop in droplets if drop.name in config.names]
    return droplets

def connection_for_droplet( config, droplet ) -> Connection:
    try:
        key = paramiko.RSAKey.from_private_key_file( os.path.expanduser( config.sshkey ) )
        con = Connection( droplet.ip_address, user='root', connect_kwargs={ "pkey" : key })
    except:
        con = Connection( droplet.ip_address, user='root', connect_kwargs={ "key_filename" : os.path.expanduser( config.sshkey )})
    return con

def can_connect( config, connection ) -> bool:
    try:
        result = connection.run('')
        return True
    except:
        return False

def create_droplet( config, name ) -> bool:
    client = digitalocean.Manager( token = config.token ) 
    projects = client.get_all_projects()
    keys = client.get_all_sshkeys()
    droplet = digitalocean.Droplet( 
        name = name,
        region = config.machines[name].region,
        size_slug = config.machines[name].slug,
        image = config.machines[name].image,
        ssh_keys = keys,
        token = config.token,
        tags = [ config.cluster ]
    )
    droplet.create()

    # Optionally assign to the cluster project.
    for p in projects:
        if p.name == config.cluster:
            p.assign_resource(["do:droplet:{}".format(droplet.id)])
            break
    
    return True


def droplet_with_name( config, name: str, tags ):
    manager = digitalocean.Manager( token =  config.token)
    droplets = manager.get_all_droplets( tag_name = [ config.cluster if tags == None else list(tags) ])
    for droplet in droplets:
        if droplet.name == name:
            return droplet
    return None

def install_python_deps( config, connection ):
    install_python_deps_command = "sudo apt-get update && sudo apt-get install --no-install-recommends --no-install-suggests -y apt-utils curl git cmake build-essential gnupg lsb-release ca-certificates software-properties-common apt-transport-https"
    logger.debug("Installing python deps: {}", install_python_deps_command)
    install_python_deps_result = connection.run(install_python_deps_command, hide=not config.debug, warn=True)
    logger.debug(install_python_deps_result)
    return install_python_deps_result

def install_python( config, connection ):
    install_python_command = "sudo apt-get install --no-install-recommends --no-install-suggests -y python3"
    logger.debug("Installing python: {}", install_python_command)
    install_python_result = connection.run(install_python_command, hide=not config.debug, warn=True)
    logger.debug(install_python_result)
    return install_python_result

def install_bittensor_deps( config, connection ):
    install_bittensor_deps_command = "sudo apt-get install --no-install-recommends --no-install-suggests -y python3-pip python3-dev python3-venv"
    logger.debug("Installing bittensor deps: {}", install_bittensor_deps_command)
    install_bittensor_deps_result = connection.run(install_bittensor_deps_command, hide=not config.debug, warn=True)
    logger.debug(install_bittensor_deps_result)
    return install_bittensor_deps_result

def install_swapspace( config, connection ):
    install_swap_command = "ulimit -n 50000 && sudo fallocate -l 20G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && sudo cp /etc/fstab /etc/fstab.bak"
    logger.debug("Installing swapspace: {}", install_swap_command)
    install_swap_result = connection.run(install_swap_command, hide=not config.debug, warn=True)
    logger.debug(install_swap_result)
    return install_swap_result

def install_npm( config, connection ):
    install_npm_command = "sudo apt install npm -y"
    logger.debug("Installing npm: {}", install_npm_command)
    install_npm_result = connection.run(install_npm_command, hide=not config.debug, warn=True)
    logger.debug(install_npm_result)
    return install_npm_result

def install_pm2( config, connection ):
    install_pm2_command = "sudo npm install pm2@latest -g"
    logger.debug("Installing pm2: {}", install_pm2_command)
    install_pm2_result = connection.run(install_pm2_command, hide=not config.debug, warn=True)
    logger.debug(install_pm2_result)
    return install_pm2_result

def install_bittensor( config, connection ):
    install_command = "cd ~/.bittensor/bittensor ; pip3 install -e ."
    logger.debug("Installing bittensor: {}", install_command)
    install_result = connection.run(install_command, hide=not config.debug, warn=True)
    return install_result

def is_installed( config, connection ) -> bool:
    check_bittensor_install_command = 'python3 -c "import bittensor"'
    logger.debug("Checking installation: {}", check_bittensor_install_command)
    check_install_result = connection.run(check_bittensor_install_command, hide=not config.debug, warn=True)
    if check_install_result.failed:
        return False
    else:
        return True

def make_bittensor_dir( config, connection ):
    make_bittensor_dir = 'mkdir -p ~/.bittensor/bittensor/'
    logger.debug("Making bittensor director: {}", make_bittensor_dir)
    make_bittensor_dir_result = connection.run(make_bittensor_dir, hide=not config.debug)
    logger.debug(make_bittensor_dir_result)
    return make_bittensor_dir_result

def remove_bittensor_installation( config, connection ):
    remove_bittensor_command = 'rm -rf ~/.bittensor/bittensor'
    logger.debug("Removing bittensor installation: {}", remove_bittensor_command)
    remove_result = connection.run(remove_bittensor_command, hide=not config.debug)
    logger.debug(remove_result)
    return remove_result

def git_clone_bittensor( config, connection ):
    clone_bittensor = "git clone --recurse-submodules https://github.com/opentensor/bittensor.git ~/.bittensor/bittensor"
    logger.debug("Pulling bittensor from github: {}", clone_bittensor)
    clone_result = connection.run(clone_bittensor, hide=not config.debug)
    logger.debug(clone_result)
    return clone_result

def git_pull_submodules( config, connection ):
    bittensor_submodules = "cd ~/.bittensor/bittensor; git submodule update --init --recursive"
    logger.debug("Cloning submodules: {}", bittensor_submodules)
    submodules_result = connection.run(bittensor_submodules, hide=not config.debug)
    logger.debug(submodules_result)
    return submodules_result

def git_checkout_bittensor( config, connection, branch ):
    if "tags/" in branch:
        branch_str = "%s -b tag-%s" % (branch, branch.split("/")[1])
    else:
        branch_str = branch
    checkout_command = 'cd ~/.bittensor/bittensor ; git checkout %s' % branch_str
    logger.debug("Checking out branch: {}", checkout_command)
    checkout_result = connection.run(checkout_command, hide=not config.debug, warn=True)
    logger.debug(checkout_result)
    return checkout_result

def git_branch_bittensor( config, connection ) -> str:
    get_branch_command = 'cd ~/.bittensor/bittensor ; git branch --show-current'
    logger.debug("Determining installed branch: {}", get_branch_command)
    get_branch_result = connection.run(get_branch_command, hide=not config.debug, warn=True)
    logger.debug(get_branch_result)
    return get_branch_result

def get_branch( config, connection ) -> str:
    branch_result = git_branch_bittensor( config, connection )
    if branch_result.failed:
        return None
    branch_name = branch_result.stdout.strip()
    return branch_name

def make_wallet_dirs( config, connection ):
    mkdirs_command = 'mkdir -p /root/.bittensor/wallets/default/hotkeys'
    logger.debug("Making wallet dirs: {}", mkdirs_command)
    mkdir_result = connection.run( mkdirs_command, warn=True, hide=not config.debug )
    logger.debug(mkdir_result)
    return mkdir_result

def copy_hotkey( config, connection, wallet ):
    hotkey_str = open(wallet.hotkey_file.path, 'r').read()
    copy_hotkey_command = "echo '%s' > /root/.bittensor/wallets/default/hotkeys/default" % hotkey_str
    logger.debug("Copying hotkey: {}", copy_hotkey_command)
    copy_hotkey_result = connection.run( copy_hotkey_command, warn=True, hide=not config.debug )
    logger.debug(copy_hotkey_result)
    return copy_hotkey_result

def copy_coldkeypub( config, connection, wallet ):
    coldkeypub_str = open(wallet.coldkeypub_file.path, 'r').read()
    copy_coldkeypub_command = "echo '%s' > /root/.bittensor/wallets/default/coldkeypub.txt" % coldkeypub_str
    logger.debug("Copying coldkeypub: {}", copy_coldkeypub_command)
    copy_coldkey_result = connection.run( copy_coldkeypub_command, warn=True, hide=not config.debug )
    logger.debug(copy_coldkey_result)
    return copy_coldkey_result

def copy_script( config, connection, script_path ):
    rm_script_command = "rm /root/main.py"
    logger.debug("rm script: {}", rm_script_command)
    rm_script_result = connection.run(rm_script_command, warn=True, hide=not config.debug)
    logger.debug(rm_script_result)
    transfer_object = fabric.transfer.Transfer( config, connection )
    copy_script_result = transfer_object.put( script_path, "/root/main.py", preserve_mode = True )
    logger.debug(copy_script_result)
    return copy_script_result

def get_script( config, connection, script) -> str:
    cat_script_command = "cat /root/main.py".format(script)
    logger.debug("Getting script: {}", cat_script_command)
    cat_script_result = connection.run(cat_script_command, warn=True, hide = not config.debug)
    if cat_script_result.failed:
        return None
    return cat_script_result.stdout

def get_hotkey( config, connection ) -> str:
    cat_hotkey_command = "cat /root/.bittensor/wallets/default/hotkeys/default"
    logger.debug("Getting hotkey: {}", cat_hotkey_command)
    cat_hotkey_result = connection.run(cat_hotkey_command, warn=True, hide=not config.debug)
    if cat_hotkey_result.failed:
        return None
    hotkey_info = json.loads(cat_hotkey_result.stdout)
    return hotkey_info['ss58Address']

def get_coldkeypub( config, connection ) -> str:
    cat_coldkey_command = "cat /root/.bittensor/wallets/default/coldkeypub.txt"
    logger.debug("Getting coldkey: {}", cat_coldkey_command)
    cat_coldkey_result = connection.run(cat_coldkey_command, warn=True, hide=not config.debug)
    if cat_coldkey_result.failed:
        return None
    coldkeypub_info = json.loads(cat_coldkey_result.stdout)
    return coldkeypub_info['ss58Address']

def register( config, connection ) -> str:
    register_command = "btcli register --no_prompt --subtensor.network nakamoto "
    logger.debug("Registering miner: {}", register_command)
    register_result = connection.run(register_command, warn=True, hide=not config.debug)
    logger.debug(register_result)
    return register_result

def is_script_running( config, connection ) -> bool:
    script_running_command = 'pm2 pid script'
    logger.debug("Getting script status: {}", script_running_command)
    script_running_result = connection.run(script_running_command, hide=not config.debug, warn=True)
    command_output = script_running_result.stdout
    if len(command_output) > 1:
        return True
    else:
        return False

def copy_script( config, connection, script_path ):
    rm_script_command = "rm /root/main.py"
    logger.debug("rm script: {}", rm_script_command)
    rm_script_result = connection.run(rm_script_command, warn=True, hide=not config.debug)
    logger.debug(rm_script_result)
    transfer_object = fabric.transfer.Transfer( config, connection )
    copy_script_result = transfer_object.put( script_path, "/root/main.py", preserve_mode = True )
    logger.debug(copy_script_result)
    return copy_script_result

def get_script( config, connection, script ) -> str:
    cat_script_command = "cat /root/main.py".format(script)
    logger.debug("Getting script: {}", cat_script_command)
    cat_script_result = connection.run(cat_script_command, warn=True, hide=not config.debug)
    if cat_script_result.failed:
        return None
    return cat_script_result.stdout

def start_subtensor( config, connection, ):
    subtensor_command = "sudo apt-get update && sudo apt install docker.io -y && rm /usr/bin/docker-compose || true && curl -L https://github.com/docker/compose/releases/download/1.29.2/docker-compose-Linux-x86_64 -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose && sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose  && rm -rf subtensor || true && git clone https://github.com/opentensor/subtensor.git && cd subtensor && docker-compose up -d"
    logger.debug("Starting subtensor: {}", subtensor_command)
    subtensor_result = connection.run(subtensor_command, warn=True, hide=not config.debug, pty=False)
    logger.debug( subtensor_result )
    return subtensor_result

def start_script( config, connection, name, args ):
    args = args.replace("$NAME", name)
    start_script_command = "pm2 start /root/main.py --name script --time --interpreter python3 -- {}".format( args )
    logger.debug("Starting script: {}", start_script_command)
    start_script_result = connection.run(start_script_command, warn=True, hide=not config.debug, pty=False)
    logger.debug( start_script_result )
    return start_script_result

def args_to_string( args ):
    args_as_string = ""
    for key_1 in args:
        for key_2 in args[key_1]:
            if args[key_1][key_2] != None:
                args_as_string += ' --{}.{} {} '.format( key_1, key_2, args[key_1][key_2] )
            else:
                args_as_string += ' --{}.{}'.format( key_1, key_2 )
    return args_as_string

def start_command( config, connection, name, command ):
    args = config.machines[name].args
    extra_args = config.machines[name].extra_args if 'extra_args' in config.machines[name] else ""
    args_string = args_to_string( args ) + extra_args

    # Replace config items.
    args_string = args_string.replace( "$NAME", name )
    args_string = args_string.replace( "$WANDBKEY", config.wandb_key )
    args_string = args_string.replace( "$CLUSTER", config.cluster )

    start_script_command = "pm2 start {} --name script --time --interpreter python3 -- {}".format( command, args_string )
    logger.debug("Starting script: {}", start_script_command)
    start_script_result = connection.run(start_script_command, warn=True, hide=not config.debug, pty=False)
    logger.debug( start_script_result )
    return start_script_result

def stop_script( config, connection ):
    stop_script_command = "pm2 delete script"
    logger.debug("Stopping script: {}", stop_script_command)
    stop_script_result = connection.run(stop_script_command, warn=True, hide=not config.debug)
    logger.debug( stop_script_result )
    return stop_script_result

def get_logs( config, connection ): 
    logs_command = "pm2 logs script --lines {} --nostream --raw".format( config.lines )
    logger.debug("Running logs: {}", logs_command)
    logs_command = connection.run(logs_command, warn=True, hide = not config.debug)
    if logs_command.failed:
        return "No logs, command failed"
    return logs_command.stdout
