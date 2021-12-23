import argparse
from time import time
import bittensor
import torch
import torch.nn.functional as F

from transformers import AutoModel,AutoTokenizer,AutoConfig
from torch.nn.utils.rnn import pad_sequence
from loguru import logger; logger = logger.opt(colors=True)

import wandb
import pandas
import datetime
import traceback
import time
import sys
import os

from loguru import logger; logger = logger.opt(colors=True)
from torch.nn.utils import clip_grad_norm_
from datetime import datetime,timedelta
from threading import Lock
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

class server(torch.nn.Module):
    def __init__(self, 
                config: 'bittensor.config' = None,
                pretrained: bool = None,
                model_name: str = None,
                padding: bool =None, 
                interpolate: bool =None,
                inter_degree: str = None,
                model = None,
                tokenizer = None,
                mapping_function = None,
                token_remap = None,
                checking= None):
        r"""" Creates a server that serves up a pretrained miner on the bittensor network
        Args:
                config (:obj:`bittensor.Config`, `required`): 
                    bittensor.server.config()
                pretrained (:obj:bool , `optional`):
                    if the model should pretrained or not
                model_name (:obj:string , `optional`):
                    name of the pretrained model from huggingface to use
                padding (:obj:bool, `optional`):
                    If the server should pad out to match the hidden units that the bittensor network is using
                    If set to False, it will instead create a mapping layer to do the same thing.
                interpolate (:obj:bool, `optional`):
                    If the server should interpolate between sequence length differences.
                    If set to false, there should be a mapping function that takes care of the differnces
                inter_degree (:obj:str, `optional`):
                    The Interpolate algorithm (nearest | linear | bilinear | bicubic | trilinear | area)
                model (:obj:torch.module, `optional`):
                    Overrides the huggingface pretrained model with your own pretrained model
                tokenizer (:obj:huggingface.tokenizer, `optional`):
                    Overrides the huggingface tokenizer with your tokenizer
                mapping_function (:obj:Callable, `optional`):
                    Custom mapping function that maps between sequence length differences between tokenizers
                token_remap (:obj:Callable, `optional`):
                    Custom function that maps between tokenizers (defaults to self.remapping_token)
        """
        super(server, self).__init__()
        if config == None: config = server.config()
        self.config = config;print(config)
        
        #setting up pretrained model
        self.model_name = model_name if model_name != None else config.neuron.model_name
        self.pretrained = pretrained if pretrained != None else config.neuron.pretrained
        if self.pretrained == True:
            self.pre_model = model if model != None else AutoModel.from_pretrained(self.model_name)
            self.tokenizer = tokenizer if tokenizer != None else AutoTokenizer.from_pretrained(self.model_name)
        elif self.pretrained == False:
            model_config = AutoConfig.from_pretrained(self.model_name)
            model_config.vocab_size= bittensor.__vocab_size__
            self.pre_model = model if model != None else AutoModel.from_config(model_config)
            self.tokenizer = bittensor.tokenizer()

        #parameters of the models
        self.final_dim =  bittensor.__network_dim__
        self.pre_dimension = self.pre_model.config.hidden_size
        self.device = config.neuron.device
        self.padding = padding if padding != None else config.neuron.padding
        self.interpolate = interpolate if interpolate != None else config.neuron.interpolate
        self.inter_degree = inter_degree if inter_degree != None else config.neuron.inter_degree
        self.checking = checking if checking != None else config.neuron.checking
        self.mapping_function= mapping_function
        self.token_remap = token_remap if token_remap != None else self.remapping_token

        if self.padding == False:
            self.mapping = torch.nn.Linear( self.pre_dimension, self.final_dim)

        self.decoder = torch.nn.Linear( self.final_dim, bittensor.__vocab_size__ , bias=False)
        self.loss_fct = torch.nn.CrossEntropyLoss()
        
        self.outputs_cache = None
        self.gradients_cache = None

        #checking if the parameters of the server makes sense
        if self.checking and pretrained == True:
            self.check()
        
        # -- keeps track of gradients applied
        self.backward_gradients = 0 
        
    def forward(self, inputs,tokenizer=None):
        """
            Forward pass through the whole server model. Returns the loss and decoded predictions.

            Args:
                inputs ( :obj:`torch.Tensor`, `required`):
                    torch inputs to be forward processed.
                tokenizer (:obj:'huggingface.tokenizer', optional):
                    The tokenizer which was used to tokenize the inputs
             Returns:
                loss (:obj:`torch.FloatTensor`):
                    MLM loss from the inputs
                decoded_targets (:obj:`torch.FloatTensor`):
                    Decoded predictions of the next token in the sentence.

        """
        decoded_targets = self.decoder(self.encode_forward(inputs,tokenizer))
        
        shift_logits = decoded_targets[..., :-1, :].contiguous()
        shift_labels = inputs[..., 1:].contiguous()     
        loss = self.loss_fct( shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1) ) 

        return loss, decoded_targets
    
    def encode_forward(self,inputs,tokenizer=None):
        r""" Forward pass through the pretrained model and possible mappings between hidden units. 
             The response tensor should be the hidden units computed using the local context and with shape: [batch_size, sequence_len, __network_dim__].

            Args:
                inputs ( :obj:`torch.Tensor`, `required`):
                    torch inputs to be forward processed.
                tokenizer ( huggingface.tokenizer, `optional`):
                    The tokenizer which was used to tokenize the inputs

            Returns:
                outputs (:obj:`torch.FloatTensor`):
                    The nucleus's outputs as a torch tensor of shape [batch_size, sequence_len, __network_dim__]
        """
        sen_len = inputs.size()
        inputs = self.token_remap(inputs,tokenizer).to(self.device)
        pre_hidden = self.pre_model(inputs).last_hidden_state

        if self.interpolate:
            down= F.interpolate(pre_hidden.unsqueeze(1),size=[sen_len[1],pre_hidden.size()[2]],mode=self.inter_degree).squeeze(1)
        elif self.mapping_function:
            down = self.mapping_function(pre_hidden)
        else:
            raise Exception('interpolation off but no mapping function found. Please attach a mapping function')

        if self.padding:
            padding_l = (self.final_dim-self.pre_dimension)//2
            padding_r = (self.final_dim-self.pre_dimension) - padding_l
            encoded_hidden = F.pad(down, (padding_l, padding_r),  "constant", 0)
        else:
            encoded_hidden = self.mapping(down)
        return encoded_hidden

    def remapping_token(self,input, old_tokenizer=None):
        r""" Default remapping of tokenizers; decodes the message and then remaps the message using a new tokenizer
            Args:
                inputs_x ( :obj:`torch.Tensor`, `required`):
                    torch inputs to be forward processed.
                old_tokenizer ( huggingface.tokenizer, `required`):
                    The tokenizer which was used to tokenize the input  (defaults to bittensor tokenizer if none is given)
        """
        if old_tokenizer == None:
            old_tokenizer = bittensor.tokenizer()
        new_data = []
        for i in range(input.shape[0]):
            decoded = old_tokenizer.decode(input[i]) 
            hugging = self.tokenizer(decoded)
            new_data += [torch.LongTensor(hugging.input_ids)]
        new_data = pad_sequence(new_data,batch_first=True)
        return new_data
    
    def check(self):
        r"""Checks the server settings
        """
        assert self.tokenizer.name_or_path == self.pre_model.name_or_path, 'incorrect model ({}) and tokenizer ({})'.format(self.pre_model.name_or_path,self.tokenizer.name_or_path)
        if self.interpolate == False:
            assert self.mapping_function != None, 'Incorrect Settings; needs atleast one mapping function for sequence length changes'

    def save(self, path):
        try:
            state_dict = {
                'model': self.pretrained,
                'pretrained_model': self.pre_model.state_dict(), 
                'decoder': self.decoder.state_dict()
            }
            if self.padding == False:
                state_dict['mapping'] = self.mapping.state_dict()
            torch.save( state_dict, "{}/model.torch".format( path) )
            bittensor.logging.success(prefix='Saved model', sufix='<blue>{}/model.torch</blue>'.format( path ) )
        except Exception as e:
            logger.exception('Failed to save model with error:{}', e)

    def load(self, path):
        try:
            state_dict=  torch.load("{}/model.torch".format( path ))
            if self.pretrained == state_dict['model']:
                self.pre_model.load_state_dict(state_dict['pretrained_model'], strict=False)
                self.decoder.load_state_dict(state_dict['decoder'])
                if self.padding == False:
                    self.mapping.load_state_dict(state_dict['mapping'])

                bittensor.logging.success( prefix = 'Reloaded model', sufix = '<blue>{}/model.torch</blue>'.format( path ))


        except Exception as e:
            logger.warning('No saved model found with error: {}', e)

    @staticmethod
    def config ():
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', type=str, help='If set, defaults are overridden by passed file.')
        parser.add_argument('--neuron.learning_rate', type=float, help='Training initial learning rate.', default=0.01)
        parser.add_argument('--neuron.momentum', type=float, help='optimizer momentum.', default=0.8)
        parser.add_argument('--neuron.clip_gradients', type=float, help='Implement gradient clipping to avoid exploding loss on smaller architectures.', default=1.0)
        parser.add_argument('--neuron.device', type=str, help='miner default training device cpu/cuda', default=("cuda" if torch.cuda.is_available() else "cpu"))
        parser.add_argument('--neuron.model_name', type=str, help='pretrained model from hugging face',default='gpt2')
        parser.add_argument('--neuron.pretrained', action='store_false', help='if the model should be pretrained',default=True)
        parser.add_argument('--neuron.padding', action='store_false', help='To pad out final dimensions',default=True)
        parser.add_argument('--neuron.interpolate', action='store_false', help='To interpolate between sentence length',default=True)
        parser.add_argument('--neuron.inter_degree', type=str, help='Interpolate algorithm (nearest | linear | bilinear | bicubic | trilinear | area)', default='nearest')
        parser.add_argument('--neuron.name', type=str, help='Trials for this miner go in miner.root / (wallet_cold - wallet_hot) / miner.name ', default='advanced_server')

        parser.add_argument('--neuron.no_training', action='store_false', help='Sets off training loop, the miner does not run training over the dataset', default=True)
        parser.add_argument('--neuron.no_backward', action='store_false', help='Filters all backward requests, does not do backward training', default=True)
        parser.add_argument('--neuron.checking', action='store_false', help='To check if server settings are correct',default=True)

        parser.add_argument('--neuron.no_restart', action='store_true', help='if the model should restart', default=False)
        parser.add_argument('--neuron.blacklist.stake.forward', type=float, help='Amount of stake (tao) in order not to get blacklisted for forward requests', default=10)
        parser.add_argument('--neuron.blacklist.stake.backward', type=float, help='Amount of stake (tao) in order not to get blacklisted for backward requests', default=100)

        parser.add_argument('--neuron.blocks_per_epoch', type=int, help='Blocks per epoch', default=2)
        parser.add_argument('--neuron.blacklist.time', type=int, help='how often a peer can query you (seconds) ', default=2)

        bittensor.wallet.add_args( parser )
        bittensor.axon.add_args( parser )
        bittensor.subtensor.add_args( parser )
        bittensor.logging.add_args( parser )
        bittensor.wandb.add_args(parser)
        bittensor.prioritythreadpool.add_args( parser )
        bittensor.dataset.add_args( parser )
        return bittensor.config( parser )
    


def serve( config, server):
    config.to_defaults()

    # Create Subtensor connection
    subtensor = bittensor.subtensor(config = config)

    # Load/Create our bittensor wallet.
    wallet = bittensor.wallet( config = config ).create().register()

    # Load/Sync/Save our metagraph.
    metagraph = bittensor.metagraph ( 
        subtensor = subtensor
    ).load().sync().save()

    # Instantiate the model we are going to serve on the network.
    # Creating a threading lock for updates to the model
    mutex = Lock()
    gp_server = server.to(server.device)
    
    # Create our optimizer.
    optimizer = torch.optim.SGD(
        [ {"params": gp_server.parameters()} ],
        lr = config.neuron.learning_rate,
        momentum = config.neuron.momentum,
    )
    
    timecheck = {}
    # Define our forward function.
    def forward_text ( inputs_x ):
        r""" Forward function that is called when the axon recieves a forward request from other peers
            Args:
                inputs_x ( :obj:`torch.Tensor`, `required`):
                    torch inputs to be forward processed.

            Returns:
                outputs (:obj:`torch.FloatTensor`):
                    The nucleus's outputs as a torch tensor of shape [batch_size, sequence_len, __network_dim__]
        """ 
        return gp_server.encode_forward( inputs_x.to(server.device) )

    # Define our backward function.
    def backward_text (inputs_x, grads_dy ):
        r"""Backwards function that is called when the axon recieves a backwards request from other peers.
            Updates the server parameters with gradients through the chain.

            Args:
                inputs_x ( :obj:`torch.Tensor`, `required`):
                    torch inputs from previous forward call.
                grads_dy ( :obj:`torch.Tensor`, `required`):
                    torch grads of forward output.
                    
        """
        # -- normalized grads -- 
        grads_dy = grads_dy/(grads_dy.sum() + 0.00001)
        
        with mutex:
            outputs_y = gp_server.encode_forward( inputs_x.to(server.device) )
            with torch.autograd.set_detect_anomaly(True):
                torch.autograd.backward (
                    tensors = [ outputs_y ],
                    grad_tensors = [ grads_dy.to(server.device) ],
                    retain_graph=True
                )
            logger.info('Backwards axon gradient applied')

        gp_server.backward_gradients += inputs_x.size(0)
       
    def priority(pubkey:str, request_type:bittensor.proto.RequestType, inputs_x) -> float:
        r"""Calculates the priority on requests based on stake and size of input

            Args:
                pubkey ( str, `required`):
                    The public key of the caller.
                inputs_x ( :obj:`torch.Tensor`, `required`):
                    torch inputs to be forward processed.
                request_type ( bittensor.proto.RequestType, `required`):
                    the request type ('FORWARD' or 'BACKWARD').
        """        
        uid = metagraph.hotkeys.index(pubkey)
        priority = metagraph.S[uid].item()/ sys.getsizeof(inputs_x)

        return priority

    def blacklist(pubkey:str, request_type:bittensor.proto.RequestType) -> bool:
        r"""Axon security blacklisting, used to blacklist message from low stake members
            Args:
                pubkey ( str, `required`):
                    The public key of the caller.
                request_type ( bittensor.proto.RequestType, `required`):
                    the request type ('FORWARD' or 'BACKWARD').
        """

        # Filtering all backward requests.
        if request_type == bittensor.proto.RequestType.BACKWARD and config.neuron.no_backward:
            True

        # Check for stake
        def stake_check():
            uid =metagraph.hotkeys.index(pubkey)
            if request_type == bittensor.proto.RequestType.FORWARD:
                if metagraph.S[uid].item() < config.neuron.blacklist.stake.forward:
                    return True
                else:
                    return False

            elif request_type == bittensor.proto.RequestType.BACKWARD:
                if metagraph.S[uid].item() < config.neuron.blacklist.stake.backward:
                    return True
                else:
                    return False

        # Check for time
        def time_check():
            current_time = datetime.now()
            if pubkey in timecheck.keys():
                prev_time = timecheck[pubkey]
                if current_time - prev_time >= timedelta(seconds=config.neuron.blacklist.time):
                    timecheck[pubkey] = current_time
                    return False
                else:
                    timecheck[pubkey] = current_time
                    return True
            else:
                timecheck[pubkey] = current_time
                return False

        # Black list or not
        if stake_check() or time_check():
            return True
        else: 
            return False
            

    # Create our axon server
    axon = bittensor.axon (
        wallet = wallet,
        forward_text = forward_text,
        backward_text = backward_text,
        blacklist = blacklist,
        priority = priority
    ) 

    # Training Data
    if not config.neuron.no_training:
        dataset = bittensor.dataset(config=config)

    # load our old model
    if config.neuron.no_restart != True:
        gp_server.load(config.neuron.full_path)

    if config.wandb.api_key != 'default':
        # --- Init Wandb.
        bittensor.wandb(
            config = config,
            cold_pubkey = wallet.coldkeypub.ss58_address,
            hot_pubkey = wallet.hotkey.ss58_address,
            root_dir = config.neuron.full_path
        )

    nn = subtensor.neuron_for_pubkey(wallet.hotkey.ss58_address)

    # -- Main Training loop --
    try:
        # -- download files from the mountain
        if not config.neuron.no_training:
            data = next(dataset)

        # --- creating our chain weights
        chain_weights = torch.zeros(metagraph.n)
        uid = nn.uid
        chain_weights[uid] = 1 

        # --  serve axon to the network.
        axon.start().serve(subtensor = subtensor)
        
        while True:
            # --- Run 
            current_block = subtensor.get_current_block()
            start_block = current_block
            end_block = current_block + config.neuron.blocks_per_epoch
            interation = 0
            losses = None

            # --- Training step.
            while end_block >= current_block:
                if current_block != subtensor.get_current_block():
                    if not config.neuron.no_training:
                        loss, _ = gp_server( next( dataset ).to(gp_server.device) )
                        if losses == None:
                            losses = loss 
                        else:
                            losses += loss
                    else:
                        time.sleep(bittensor.__blocktime__)
                    interation += 1
                    current_block = subtensor.get_current_block()
            
            #Custom learning rate
            if gp_server.backward_gradients > 0:
                optimizer.param_groups[0]['lr'] =  1/(gp_server.backward_gradients)
            else:
                optimizer.param_groups[0]['lr'] =  0.1
            
            # --- Update parameters
            if interation != 0 or gp_server.backward_gradients != 0 and not config.neuron.no_backward:
                with mutex:
                    logger.info('Backpropagation Started')
                    if interation != 0:
                        if losses != None:
                            losses.backward()
                    clip_grad_norm_(gp_server.parameters(), 1.0)
                    
                    optimizer.step()
                    optimizer.zero_grad()
                    logger.info('Backpropagation Successful: Model updated')

            nn = subtensor.neuron_for_pubkey(wallet.hotkey.ss58_address)

            gp_server.backward_gradients = 0
            # --- logging data
            wandb_data = {
                'block': end_block,
                'loss': losses.cpu().item()/interation if losses != None else 0,
                'stake': nn.stake,
                'rank': nn.rank,
                'incentive': nn.incentive,
                'trust': nn.trust,
                'consensus': nn.consensus,
                'incentive': nn.incentive,
                'dividends': nn.dividends,
                'emission':  nn.emission,
            } 
            bittensor.__console__.print('[green]Current Status:[/green]', wandb_data)

            # Add additional wandb data for axon, metagraph etc.
            if config.wandb.api_key != 'default':

                df = pandas.concat( [
                    bittensor.utils.indexed_values_to_dataframe( prefix = 'w_i_{}'.format(nn.uid), index = metagraph.uids, values = metagraph.W[:, uid] ),
                    axon.to_dataframe( metagraph = metagraph ),
                ], axis = 1)
                df['uid'] = df.index
                wandb_info_axon = axon.to_wandb()                
                wandb.log( { **wandb_data, **wandb_info_axon }, step = current_block )
                wandb.log( { 'stats': wandb.Table( dataframe = df ) }, step = current_block )

            # Save the model
            gp_server.save(config.neuron.full_path)
            
            if current_block % 10 == 0:
                
                # --- Setting weights
                try: 
                    # Set self weights to maintain activity.
                    chain_weights = torch.zeros(metagraph.n)
                    chain_weights [ uid ] = 1 
                    did_set = subtensor.set_weights(
                        uids=metagraph.uids,
                        weights = chain_weights,
                        wait_for_inclusion = False,
                        wallet = wallet,
                    )
                    
                    if did_set:
                        logger.success('Successfully set weights on the chain')
                    else:
                        logger.error('Failed to set weights on chain. (Timeout)')
                except Exception as e:
                    logger.error('Failure setting weights on chain with error: {}', e)


            if current_block - start_block > 2000:
                metagraph.sync()
                start_block = current_block


    except KeyboardInterrupt:
        # --- User ended session ----
        axon.stop()
    except Exception as e:
        # --- Unknown error ----
        logger.exception('Unknown exception: {} with traceback {}', e, traceback.format_exc())

class neuron:

    def __init__(
        self, 
        config: 'bittensor.config' = None
    ):
        if config == None: config = server.config()
        config = config; 
        self.check_config( config )
        bittensor.logging (
            config = config,
            logging_dir = config.neuron.full_path,
        )

        self.model = server(config=config)
        self.config = config

    def run(self):
        serve( self.config, self.model )

    @staticmethod
    def check_config( config: 'bittensor.Config' ):
        r""" Checks/validates the config namespace object.
        """
        bittensor.logging.check_config( config )
        bittensor.wallet.check_config( config )
        bittensor.subtensor.check_config( config )
        bittensor.metagraph.check_config( config )
        bittensor.dataset.check_config( config )
        bittensor.axon.check_config( config )
        bittensor.wandb.check_config( config )
        full_path = os.path.expanduser('{}/{}/{}/{}'.format( config.logging.logging_dir, config.wallet.name, config.wallet.hotkey, config.neuron.name ))
        config.neuron.full_path = os.path.expanduser(full_path)
        if not os.path.exists(config.neuron.full_path):
            os.makedirs(config.neuron.full_path)


if __name__ == "__main__":
    template = neuron().run()