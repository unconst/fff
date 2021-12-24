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
$ export MARIUS_DO_TOKEN=<a digital ocean api token>
$ export MARIUS_SSH_KEY=<an ssh key used to communicate with your droplets>
$ export MARIUS_WANDB_KEY=<a wandb api key used to create telemety>
```

## Config Yaml
Edit this config file to create your cluster
```bash
cluster: marius # Name of the cluster
coldkey: marius # Coldkey on this device to run the cluster

token: MARIUS_DO_TOKEN # ENV var where your digital ocean token is stored
sshkey: MARIUS_SSH_KEY # ENV var with path to your ssh key.
wandb_key: MARIUS_WANDB_KEY # ENV var where your wandb key is stored.

max_threads: 10 # Threads this tool uses 

machines: # Your machines are defined below.

  M0: # Name of the droplet.
    region: nyc1 # Datacenter Location 
    slug: s-4vcpu-8gb # Save of droplet, see https://slugs.do-api.dev/ for a full list
    image: ubuntu-20-04-x64 # Image name
    branch: master # Bittensor branch to install on this device.
    command: /root/.bittensor/bittensor/bittensor/_neuron/text/advanced_server/main.py # Command to run.
    args: "--subtensor.network local --wandb.api_key $WANDBKEY --logging.debug --neuron.name $NAME --wandb.name $NAME --wandb.project $CLUSTER --wandb.run_group $NAME --neuron.model_name distilgpt2" # passed args.

```



# Commands
- [Deploy](#deploy)
- [Status](#status)
- [Create](#create)
- [Install](#install)
- [Start](#start)
- [Logs](#logs)

## Deploy
Create, Install and Deploy Cluster
```bash
$ cluster  # Deploy entire cluster 
or
$ clsuter --config <config name> --debug --names ...
or
$ clsuter deploy --config <config name> --debug --names ...
```

#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use.

    -n --names: optional, default: All instances.
        Get status for DO droplets with these names only.

    -d --debug: optional, default False
        Sets debug to True
```
---
---


## Status
Shows cluster status and exits.
```bash
$ clsuter status --config <config name> --debug --names ...
```

#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use.

    -n --names: optional, default: All instances.
        Get status for DO droplets with these names only.

    -d --debug: optional, default False
        Sets debug to True
```
---
---

## Create
Creates cluster from yaml file.
```bash
$ cluster create --config <config name> --debug --names ...
```
#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use.

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
$ cluster install --config <config name> --debug --names ...
```
#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use.

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
$ cluster start --config <config name> --debug --names ...
```
#### Args:
```bash

    -c --config: optional, default config.yaml
        Which config file to use.

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
$ cluster logs --config <config name> --debug --names ...
```
#### Args:
```bash
    -c --config: optional, default config.yaml
        Which config file to use.

    -n --names: optional, default: All instances.
        Get logs from these droplets.

    -d --debug: optional, default False
        Sets debug to True
```
---