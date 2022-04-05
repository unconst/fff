
import bittensor
from rich.console import Console
from rich.table import Table
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from . import utils as utils
from loguru import logger
logger = logger.opt(colors=True)

class status:

    def add_args(parser):
        status_parser = parser.add_parser(
            "status", help="""Show mining overview"""
        )
        status_parser.add_argument(
            "-c",
            "--config",
            dest="config_file",
            type=str,
            required=False,
            help="Config file to use",
            default="default",
        )
        status_parser.add_argument(
            "-d",
            "--debug",
            dest="debug",
            action="store_true",
            help="""Set debug""",
            default=False,
        )
        status_parser.add_argument(
            "-n",
            "--names",
            dest="names",
            type=str,
            nargs="*",
            required=False,
            action="store",
            help="A list of nodes (hostnames) the selected command should operate on",
        )

    def run(config):
        total_stake = 0.0
        total_rank = 0.0
        total_trust = 0.0
        total_consensus = 0.0
        total_incentive = 0.0
        total_dividends = 0.0
        total_emission = 0.0

        def get_row(droplet):
            try:
                connection = utils.connection_for_machine(config, droplet)
                can_connect_bool = utils.can_connect(config, connection)
                subtensor = bittensor.subtensor()
                connect_str = "[bold green] YES" if can_connect_bool else "[bold red] NO"
                hotkey_str = "[yellow] None"
                coldkeypub_str = "[yellow] None"
                branch_str = "[yellow] None"
                is_installed_str = "[bold red] No"
                is_running_str = "[bold red] No"
                is_registered_str = "[bold red] No"
                is_running = False
                installed = False
                nonlocal total_stake
                nonlocal total_rank
                nonlocal total_trust
                nonlocal total_consensus
                nonlocal total_incentive
                nonlocal total_dividends
                nonlocal total_emission
                is_registered = False
                if can_connect_bool:
                    try:
                        hotkey = utils.get_hotkey(config, connection)
                        hotkey_str = hotkey if hotkey != None else "[yellow] None"
                    except Exception as e:
                        hotkey_str = "[yellow] None"
                        logger.error(
                            "{}: Failed to pull hotkey error = {}", droplet.name, e
                        )
                if can_connect_bool:
                    try:
                        coldkeypub = utils.get_coldkeypub(config, connection)
                        coldkeypub_str = (
                            coldkeypub[0:10] if coldkeypub != None else "[yellow] None"
                        )
                    except Exception as e:
                        logger.error(
                            "{}: Failed to pull coldkey error = {}", droplet.name, e
                        )
                if can_connect_bool:
                    try:
                        branch = utils.get_branch(config, connection)
                        branch_str = branch if branch != None else "[yellow] None"
                    except Exception as e:
                        logger.error(
                            "{}: Failed to pull branch error = {}", droplet.name, e
                        )
                if can_connect_bool and branch != None:
                    try:
                        installed = utils.is_installed(config, connection)
                        is_installed_str = (
                            "[bold green] Yes" if installed else "[bold red] No"
                        )
                    except Exception as e:
                        logger.error(
                            "{}: Failed to pull install status error = {}", droplet.name, e
                        )
                if can_connect_bool and installed:
                    try:
                        is_running = utils.is_script_running(config, connection)
                        is_running_str = (
                            "[bold green] Yes" if is_running else "[bold red] No"
                        )
                    except Exception as e:
                        logger.error(
                            "{}: Failed to pull running status: error = {}", droplet.name, e
                        )
                try:
                    neuron = subtensor.neuron_for_pubkey(hotkey_str)
                    if not neuron.is_null:
                        is_registered = True
                        is_registered_str = (
                            "[bold green] Yes" if is_registered else "[bold red] No"
                        )
                except:
                    pass

                if is_registered:
                    metrics = [
                        str(neuron.uid),
                        "{:.5f}".format(neuron.stake),
                        "{:.5f}".format(neuron.rank),
                        "{:.5f}".format(neuron.trust),
                        "{:.5f}".format(neuron.consensus),
                        "{:.5f}".format(neuron.incentive),
                        "{:.5f}".format(neuron.dividends),
                        "{:.5f}".format(neuron.emission),
                        str(neuron.last_update),
                        str(neuron.active),
                    ]
                    total_stake += neuron.stake
                    total_rank += neuron.rank
                    total_trust += neuron.trust
                    total_consensus += neuron.consensus
                    total_incentive += neuron.incentive
                    total_dividends += neuron.dividends
                    total_emission += neuron.emission
                else:
                    metrics = ["-", "-", "-", "-", "-", "-", "-", "-", "-", "-"]

                row = (
                    [
                        str(droplet.name),
                        str(droplet.tags[0]),
                        str(droplet.ip_address),
                        str(droplet.region["name"]),
                        str(droplet.size_slug),
                        str(connect_str),
                        branch_str,
                        is_installed_str,
                        is_registered_str,
                        is_running_str,
                    ]
                    + metrics
                    + [coldkeypub_str, hotkey_str]
                )
                connection.close()
            except:
                row = [
                    str(droplet.name),
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                ]
            return row

        droplets = utils.get_machines(config)
        TABLE_DATA = []
        with ThreadPoolExecutor(max_workers=config.max_threads) as executor:
            TABLE_DATA = list(tqdm(executor.map(get_row, droplets), total=len(droplets)))

        TABLE_DATA = [row for row in TABLE_DATA if row != None]
        TABLE_DATA.sort(key=lambda TABLE_DATA: TABLE_DATA[0])

        table = Table(show_footer=False)
        table.title = "[bold white]Marius"
        table.add_column(
            "[overline white]Name",
            str(len(config.machines)),
            footer_style="overline white",
            style="white",
        )
        table.add_column("[overline white]TAG", style="white")
        table.add_column("[overline white]IP", style="blue")
        table.add_column("[overline white]Location", style="yellow")
        table.add_column("[overline white]Size", style="green")
        table.add_column("[overline white]Connected", style="green")
        table.add_column("[overline white]Branch", style="bold purple")
        table.add_column("[overline white]Installed")
        table.add_column("[overline white]Registered")
        table.add_column("[overline white]Running")

        table.add_column(
            "[overline white]Uid", footer_style="overline white", style="yellow"
        )
        table.add_column(
            "[overline white]Stake",
            "{:.5f}".format(total_stake),
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]Rank",
            "{:.5f}".format(total_rank),
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]Trust",
            "{:.5f}".format(total_trust),
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]Consensus",
            "{:.5f}".format(total_consensus),
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]Incentive",
            "{:.5f}".format(total_incentive),
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]Dividends",
            "{:.5f}".format(total_dividends),
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]Emission",
            "{:.5f}".format(total_emission),
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]Lastupdate (blocks)", justify="right", no_wrap=True
        )
        table.add_column(
            "[overline white]Active", justify="right", style="green", no_wrap=True
        )

        table.add_column("[overline white]Coldkey", style="bold blue", no_wrap=False)
        table.add_column("[overline white]Hotkey", style="blue", no_wrap=False)
        table.show_footer = True

        for row in TABLE_DATA:
            table.add_row(*row)
        table.box = None
        table.pad_edge = False
        table.width = None
        console = Console()
        console.print(table)