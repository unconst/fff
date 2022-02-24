import sys
import time
import bittensor
import os
import signal

sub = bittensor.subtensor()
wallet = bittensor.wallet( name = sys.argv[1], hotkey = sys.argv[2])
start = time.time()
try:
    with bittensor.__console__.status("Registering\n\n\twallet:\t[bold white]{}[/bold white]\n\telapsed:\t[bold white]{}[/bold white] ".format(wallet, time.time() - start)) as status:
        while True:
            if not sub.neuron_for_pubkey( wallet.hotkey.ss58_address ).is_null:
                print ('DONE')
                os.kill(os.getppid(), signal.SIGKILL) # Kill parent
                break
            else:
                status.update("Registering\n\twallet:\t[bold white]{}[/bold white]\n\telapsed:\t[bold white]{}[/bold white] ".format(wallet, time.time() - start))
                continue
except KeyboardInterrupt:
    print ('STOPPED')

