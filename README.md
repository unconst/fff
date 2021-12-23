<div align="center">

# **Bittensor-Cluster**
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/3rUr6EcvbB)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
---

[Discord](https://discord.gg/3rUr6EcvbB) • [Docs](https://app.gitbook.com/@opentensor/s/bittensor/) • [Network](https://www.bittensor.com/metagraph) • [Research](https://uploads-ssl.webflow.com/5cfe9427d35b15fd0afc4687/5fa940aea6a95b870067cf09_bittensor.pdf) • [Code](https://github.com/opentensor/BitTensor)

A command-line tool for running a cluster of bittensor miners over multiple digital ocean droplets.

</div>

## Installation
'''
$ python3 -m pip install -e .
'''

# How to use
'''
cluster -c config.yaml
'''

# Commands
- [Status](#status)
- [Create](#create)
- [Start](#start)
- [Destroy](#destroy)


### Status
Shows cluster status and exits.
```
$ clsuter status --debug
```
Args:
```
    --debug: optional, default False
        Sets debug to True
```
---

### Create
Creates cluster from yaml file.
```
$ cluster create --debug
```
Args:
```
    -- names: optional, default: All instances with tag.
        Get status for DO droplets with these names only.

    -- debug: optional, default False
        Sets debug to True
```
---
