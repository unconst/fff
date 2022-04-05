
import bittensor
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from . import utils as utils
from loguru import logger
logger = logger.opt(colors=True)

def add_args(parser):
    checkout_parser = parser.add_parser("checkout", help="""checkout""")
    checkout_parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        type=str,
        required=False,
        help="Config file to use",
        default="default",
    )
    checkout_parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="""Set debug""",
        default=False,
    )
    checkout_parser.add_argument(
        "-n",
        "--names",
        dest="names",
        type=str,
        nargs="*",
        required=False,
        action="store",
        help="A list of nodes (hostnames) the selected command should operate on",
    )

def checkout(config):
    def _checkout(droplet):
        try:
            name = droplet.name
            branch = config.machines[name].branch
            connection = utils.connection_for_machine(config, droplet)

            if not utils.can_connect(config, connection):
                logger.error(
                    "<blue>{}</blue>: Failed to make connection to droplet", name
                )
                return
            else:
                logger.success("<blue>{}</blue>: Made connection to droplet", name)

            if utils.make_bittensor_dir(config, connection).failed:
                logger.error("<blue>{}</blue>: Failed to make bittensor dirs.", name)
                return
            else:
                logger.success("<blue>{}</blue>: Made bittensor dirs.", name)

            if utils.remove_bittensor_installation(config, connection).failed:
                logger.error(
                    "<blue>{}</blue>: Failed to remove previous bittensor installation",
                    name,
                )
                return
            else:
                logger.success(
                    "<blue>{}</blue>: Remove previous bittensor installation", name
                )

            if utils.git_clone_bittensor(config, connection).failed:
                logger.error("<blue>{}</blue>: Failed to clone bittensor", name)
                return
            else:
                logger.success("<blue>{}</blue>: Cloned bittensor", name)

            if utils.git_checkout_bittensor(config, connection, branch).failed:
                logger.error(
                    "<blue>{}</blue>: Failed to checkout bittensor branch: {}",
                    name,
                    branch,
                )
                return
            else:
                logger.success("<blue>{}</blue>: Checked out bittensor branch", name)

            branch_result = utils.git_branch_bittensor(config, connection)
            if branch_result.failed:
                logger.error("{}: Failed to get branch", name)
                return
            else:
                logger.success(
                    "<blue>{}</blue>: Branch set to: {}",
                    name,
                    branch_result.stdout.strip(),
                )

        except Exception as e:
            logger.exception(e)
        finally:
            logger.success("<blue>{}</blue>: DONE CHECKOUT ", name)
            connection.close()

    droplets = utils.get_machines(config)
    with ThreadPoolExecutor(max_workers=config.max_threads) as executor:
        tqdm(executor.map(_checkout, droplets), total=len(droplets))