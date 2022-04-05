import bittensor
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from . import utils as utils
import random
import time
from loguru import logger
logger = logger.opt(colors=True)

def add_args(parser):
    fast_register_parser = parser.add_parser(
        "fast_register", help="""register"""
    )
    fast_register_parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        type=str,
        required=False,
        help="Config file to use",
        default="default",
    )
    fast_register_parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="""Set debug""",
        default=False,
    )
    fast_register_parser.add_argument(
        "-n",
        "--names",
        dest="names",
        type=str,
        nargs="*",
        required=False,
        action="store",
        help="A list of nodes (hostnames) the selected command should operate on",
    )
    fast_register_parser.add_argument(
        "-p",
        "--procs",
        dest="procs",
        type=int,
        required=False,
        help="A list of nodes (hostnames) the selected command should operate on",
        default=5,
    )
    fast_register_parser.add_argument(
        "-t",
        "--timeout",
        dest="timeout",
        type=int,
        required=False,
        help="Default registration timeout.",
        default=60 * 60 * 2,
    )
    fast_register_parser.add_argument(
        "-w",
        "--workers",
        dest="workers",
        type=int,
        required=False,
        help="Number of workers to use for registering, -1 for all.",
        default=-1,
    )

    bittensor.wallet.add_args(fast_register_parser)



def fast_register(config):
    def _do_register(droplet):
        try:
            # Make connection.
            name = droplet.name
            wallet = bittensor.wallet(config)
            logger.debug("<blue>{}</blue>: Registering ", name)
            connection = utils.connection_for_machine(config, droplet)
            if not utils.can_connect(config, connection):
                logger.error(
                    "<blue>{}</blue>: Failed to make connection to droplet", name
                )
                return
            else:
                logger.debug("<blue>{}</blue>: Made connection to droplet", name)

            # Copy wallet.
            if not wallet.hotkey_file.exists_on_device():
                logger.error(
                    "<blue>{}</blue>: Wallet does not have hotkey: {}",
                    name,
                    wallet.hotkey_file.path,
                )
                return
            else:
                logger.debug("<blue>{}</blue>: Found hotkey: {}", name, name)

            if not wallet.coldkeypub_file.exists_on_device():
                logger.error(
                    "<blue>{}</blue>: Wallet does not have coldkeypub: {}",
                    name,
                    wallet.coldkeypub_file.path,
                )
                return
            else:
                logger.debug(
                    "<blue>{}</blue>: Found coldkeypub: {}",
                    name,
                    wallet.coldkeypub_file.path,
                )

            if utils.make_fast_wallet_dirs(config, connection).failed:
                logger.error("<blue>{}</blue>: Error creating wallet dirs", name)
                return
            else:
                logger.debug("<blue>{}</blue>: Created wallet directories", name)

            if utils.copy_fast_hotkey(config, connection, wallet).failed:
                logger.error("<blue>{}</blue>: Error coping hotkey.", name)
                return
            else:
                logger.debug(
                    "<blue>{}</blue>: Copied hotkey to dir: {}",
                    name,
                    "/root/.bittensor/wallets/fast/hotkeys/fast",
                )

            if utils.copy_fast_coldkeypub(config, connection, wallet).failed:
                logger.error("<blue>{}</blue>: Error copy coldkey", name)
                return
            else:
                logger.debug(
                    "<blue>{}</blue>: Copied coldkey to dir: {}",
                    name,
                    "/root/.bittensor/wallets/fast/coldkeypub.txt",
                )

            if utils.get_fast_hotkey(config, connection) == None:
                logger.error(
                    "<blue>{}</blue>: Failed to retrieve hotkey from {}",
                    name,
                    connection.host,
                )
                return
            else:
                logger.debug(
                    "<blue>{}</blue>: Could retrieve hotkey: {}",
                    name,
                    utils.get_fast_hotkey(config, connection),
                )

            if utils.get_fast_coldkeypub(config, connection) == None:
                logger.error(
                    "<blue>{}</blue>: Failed to retrieve coldkeypub from {}",
                    name,
                    connection.host,
                )
                return
            else:
                logger.debug(
                    "<blue>{}</blue>: Could retrieve coldkeypub: {}",
                    name,
                    utils.get_fast_coldkeypub(config, connection),
                )

            # Copy speed registration tools.
            utils.copy_registration_tools(config, connection)

            # Kill previous.
            utils.kill_fast_register(config, connection)
            logger.debug("<blue>{}</blue>: Killed previous registration.", name)

            # Run registration tool.
            utils.run_registration_tools(config, connection)
            logger.debug("<blue>{}</blue>: Started fast registration...", name)

            start = time.time()
            while time.time() - start < config.timeout:
                sub = bittensor.subtensor()
                wallet_neuron = sub.neuron_for_pubkey(wallet.hotkey.ss58_address)
                if not wallet_neuron.is_null:
                    utils.kill_fast_register(config, connection)
                    logger.success(
                        "<blue>{}</blue>: Killed fast register with success.", name
                    )
                    break
                else:
                    # logger.success('<blue>{}</blue>: Waiting on registration: remaining: {}/{}', name, time.time() - start, config.timeout)
                    time.sleep(2)
                    continue

        except Exception as e:
            logger.debug(e)

        finally:
            # Kill fast registration.
            utils.kill_fast_register(config, connection)
            logger.debug("<blue>{}</blue>: Killed fast register on final.", name)

            logger.debug("<blue>{}</blue>: DONE Registering ", name)
            connection.close()

    droplets = utils.get_machines(config)
    if config.workers != -1:
        random.shuffle(droplets)
        droplets = droplets[: min(config.workers, len(droplets))]
    with ThreadPoolExecutor(max_workers=len(droplets) * 2) as executor:
        tqdm(executor.map(_do_register, droplets), total=len(droplets))