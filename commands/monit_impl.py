
import bittensor
import random
from . import utils as utils
from loguru import logger
from . import fast_register_impl
from . import status_impl

logger = logger.opt(colors=True)

def add_args(parser):
    monit_parser = parser.add_parser("monit", help="""Monitor cluster""")
    monit_parser.add_argument(
        "-c",
        "--sconfig",
        dest="config_file",
        type=str,
        required=False,
        help="Config file to use",
        default="default",
    )
    monit_parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="""Set debug""",
        default=False,
    )
    monit_parser.add_argument(
        "-n",
        "--names",
        dest="names",
        type=str,
        nargs="*",
        required=False,
        action="store",
        help="A list of nodes (hostnames) the selected command should operate on",
    )
    monit_parser.add_argument(
        "-p",
        "--procs",
        dest="procs",
        type=int,
        required=False,
        help="A list of nodes (hostnames) the selected command should operate on",
        default=5,
    )
    monit_parser.add_argument(
        "-t",
        "--timeout",
        dest="timeout",
        type=int,
        required=False,
        help="Default registration timeout.",
        default=60 * 60 * 2,
    )
    monit_parser.add_argument(
        "-w",
        "--workers",
        dest="workers",
        type=int,
        required=False,
        help="Number of workers to use for registering, -1 for all.",
        default=-1,
    )
    bittensor.wallet.add_args(monit_parser)


def monit(config):
    droplets = utils.get_machines(config)
    while True:
        status_impl.commands.status(config)
        try:
            random.shuffle(droplets)
            with bittensor.__console__.status(
                ":satellite: Monitoring."
            ) as console_status:
                for i, droplet in enumerate(droplets):
                    console_status.update(
                        ":satellite: Monitoring. current: {} ({}/{})".format(
                            droplet.name, i, len(droplets)
                        )
                    )
                    name = droplet.name
                    logger.debug("<white>{}</white>: Begin Monit", name)
                    subtensor = bittensor.subtensor()
                    connection = utils.connection_for_machine(config, droplet)
                    logger.debug("<white>{}</white>: Made connection", name)
                    hotkey = utils.get_hotkey(config, connection)
                    logger.debug("<white>{}</white>: Got hotkey: {}", name, hotkey)
                    coldkeypub = utils.get_coldkeypub(config, connection)
                    logger.debug("<white>{}</white>: Got coldkey: {}", name, coldkeypub)
                    neuron = subtensor.neuron_for_pubkey(hotkey)
                    logger.debug("<white>{}</white>: Got neuron: {}", name, neuron)

                    if neuron.is_null:
                        console_status.update(
                            ":satellite: Monitoring. current: {} ({}/{}). Registering ... ".format(
                                droplet.name, i, len(droplets)
                            )
                        )
                        utils.stop_script(config, connection)
                        config.wallet.name = config.machines[droplet.name].coldkey
                        config.wallet.hotkey = name
                        fast_register_impl.fast_register(config)

                    if neuron.active == 0 or not utils.is_script_running(
                        config, connection
                    ):
                        console_status.update(
                            ":satellite: Monitoring. current: {} ({}/{}). Restarting ... ".format(
                                droplet.name, i, len(droplets)
                            )
                        )
                        utils.stop_script(config, connection)
                        command = config.machines[name].command
                        utils.start_command(config, connection, name, command)
                        logger.debug("<white>{}</white>: Started", name)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.exception("Monit error: {}", e)