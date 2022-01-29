<div align="center">

# **Bittensor-Cluster**
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/3rUr6EcvbB)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
---

[Discord](https://discord.gg/3rUr6EcvbB) • [Docs](https://app.gitbook.com/@opentensor/s/bittensor/) • [Network](https://www.bittensor.com/metagraph) • [Research](https://uploads-ssl.webflow.com/5cfe9427d35b15fd0afc4687/5fa940aea6a95b870067cf09_bittensor.pdf) • [Code](https://github.com/opentensor/BitTensor)

A command-line tool for running a cluster of bittensor miners over multiple digital ocean droplets.

</div>
 
## Installation
Installs the marius tool.
```bash
$ python3 -m pip install -e .
```

## Setup
Marius requires various enviroment variables to run.
```bash
$ cp config_template.yaml config.yaml # to create your config.
$ export MARIUS_DOTOKEN=<a digital ocean api token>
$ export MARIUS_SSH_KEY=<an ssh key used to communicate with your droplets>
$ export MARIUS_WANDB_KEY=<a wandb api key used to create telemety>
```

## Config Setup
First, copy the template into your own config.yaml.
```bash
$ cp configs/config_template.yaml configs/default.yaml # to create your config.
```

Next, Edit this config file to define the cluster.
```bash
# You must set this env var with your digital ocean api key i.e. export MARIUS_DOTOKEN=0830jj2190j290j138183j12j092e
token: ENV_MARIUS_DOTOKEN 

# You must create an ssh key and pass the path i.e. export MARIUS_SSH_KEY=~/.ssh/marius
sshkey: ENV_MARIUS_SSH_KEY 

# You must create a wandb account and create this env var i.e. export MARIUS_WANDB_KEY=2082308183802182302
wandb_key: ENV_MARIUS_WANDB_KEY

# The name of the cluster to switch between different clusters clone this config, change this file and use the -c command line arg
cluster: marius 

# The name of the coldkey used to control this cluster. You should create this key using btcli before running
# i.e. btcli new_coldkey --wallet.name marius
coldkey: marius

# Number of processing threads used to run this tool.
max_threads: 10


# Below list all you machines.
machines:

  # The name of your machine
  M0:
    # Machine region.
    region: nyc1

    # Size of droplet, see https://slugs.do-api.dev/ for a full list
    slug: s-4vcpu-8gb

    # Probably dont change this.
    image: ubuntu-20-04-x64

    # Bittensor branch.
    branch: master

    # The command to run on the machine when you run marius start.
    command: /root/.bittensor/bittensor/bittensor/_neuron/text/advanced_server/main.py

    # Custom string arguments to pass into the command.
    extra_args: '--logging.debug'

    # Arguments as a nested yaml. These are unfolded and passed to the command.
    args: 
    
      subtensor: 
        network: nakamoto

      neuron:
        model_name: distilgpt2

      wandb:
        api_key: $WANDBKEY # This is filled using the wandb key from above.
        project: $CLUSTER # Special arg is filled with the cluster name
        run_group: $NAME # Special arg is filled using the machine name.
        name: $NAME

    # Optionally add more machines below this point
    # M2
    # ...
```

# Commands
- [Deploy](#deploy)
- [Status](#status)
- [Create](#create)
- [Install](#install)
- [Register](#register)
- [Start](#start)
- [Logs](#logs)

## Deploy
Create, Install, Register and Deploy your Cluster.
```bash
$ marius -d # Deploy entire cluster with debug 
or
$ marius --config <config name> --debug --names ...
or
$ marius deploy --config <config name> --debug --names ...
```

#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use from configs/

    -n --names: optional, default: All instances.
        Get status for DO droplets with these names only.

    -d --debug: optional, default False
        Sets debug to True
```
---
---


## Status
Shows marius status and exits.
```bash
$ marius status --config <config name> --debug --names ...
```

#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use configs/

    -n --names: optional, default: All instances.
        Get status for DO droplets with these names only.

    -d --debug: optional, default False
        Sets debug to True
```
---
---

## Create
Creates marius from yaml file.
```bash
$ marius create --config <config name> --debug --names ...
```
#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use configs/

    -n --names: optional, default: All instances.
        Create all machines with these names.

    -d --debug: optional, default False
        Sets debug to True
```
---
---

## Install
Installs Bittensor and starts a subtensor instance running on your droplets.
```bash
$ marius install --config <config name> --debug --names ...
```
#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use configs/

    -n --names: optional, default: All instances.
        Install requirements on these droplets.

    -d --debug: optional, default False
        Sets debug to True
```
---
---

## Register
Register the keys on your droplet.
```bash
$ marius register --config <config name> --debug --names ...
```
#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use configs/

    -n --names: optional, default: All instances.
        Install requirements on these droplets.

    -d --debug: optional, default False
        Sets debug to True
```
---
---

## Start
Starts the run command on droplets
```bash
$ marius start --config <config name> --debug --names ...
```
#### Args:
```bash

    -c --config: optional, default config.yaml
        Which config file to use configs/

    -n --names: optional, default: All instances.
        Start command on these droplets.

    -d --debug: optional, default False
        Sets debug to True
```
---
---

## Logs
Gets logs from droplsts
```bash
$ marius logs --config <config name> --debug --names ...
```
#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use configs/

    -n --names: optional, default: All instances.
        Get logs from these droplets.

    -d --debug: optional, default False
        Sets debug to True
```
---