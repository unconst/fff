import bittensor
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from . import utils as utils
from loguru import logger
logger = logger.opt(colors=True)

def add_args(parser):
    create_parser = parser.add_parser("create", help="""Create miners""")
    create_parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        type=str,
        required=False,
        help="Config file to use",
        default="default",
    )
    create_parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="""Set debug""",
        default=False,
    )
    create_parser.add_argument(
        "-n",
        "--names",
        dest="names",
        type=str,
        nargs="*",
        required=False,
        action="store",
        help="A list of nodes (hostnames) the selected command should operate on",
    )


def create(config):
    droplets = utils.get_machines(config)
    existing_droplets = [droplet.name for droplet in droplets]
    to_create = config.machines
    if config.names != None:
        to_create = config.names

    def _create(name):
        try:
            if name not in existing_droplets:
                if not utils.create_droplet(config, name):
                    logger.error(
                        "<blue>{}</blue>: Failed to create droplet with name.", name
                    )
                    return
                else:
                    logger.success("<blue>{}</blue>: Created droplet.", name)
            else:
                logger.success("<blue>{}</blue>: Droplet already exists.", name)
        except Exception as e:
            logger.exception(e)
        finally:
            logger.success("<blue>{}</blue>: DONE CREATE", name)

    with ThreadPoolExecutor(max_workers=config.max_threads) as executor:
        tqdm(executor.map(_create, to_create), total=len(to_create))

