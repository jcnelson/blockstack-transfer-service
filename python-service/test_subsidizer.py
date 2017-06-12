# fire up blockstack: 
# $ BLOCKSTACK_TEST_CLIENT_RPC_PORT=6270 blockstack-test-scenario --interactive 2 blockstack_integration_tests.scenarios.rpc_register_multisig
# this file should be called after loading the *blockstack venv*
# and *with* your regtest client config + testnet settings
# $ export BLOCKSTACK_CLIENT_CONFIG=/tmp/blockstack-run-scenario.blockstack_integration_tests.scenarios.rpc_register_multisig/client/client.ini && export BLOCKSTACK_TESTNET=1

from flask import Flask

from blockstack_client.config import get_utxo_provider_client, APPROX_TX_IN_P2SH_LEN, get_tx_broadcaster
from blockstack_client.operations import fees_transfer
from blockstack_client.scripts import tx_make_subsidizable
from blockstack_client.backend.nameops import estimate_payment_bytes
from blockstack_client.backend.blockchain import get_tx_fee, broadcast_tx
from blockstack_client.tx import deserialize_tx
from blockstack_client.proxy import get_default_proxy
from blockstack_client.rpc import local_api_status
from blockstack_client.actions import get_wallet_keys

import sys, os, json

config_path = os.environ.get("BLOCKSTACK_CLIENT_CONFIG")

def get_wallet_multisig():
    w = {
	"payment_address": "2NCL5euNJV9wNcKWQkTtEv7BxUdSTbaf7W1", 
	"payment_privkey": {
	    "address": "2NCL5euNJV9wNcKWQkTtEv7BxUdSTbaf7W1", 
	    "private_keys": [
		"6f432642c087c2d12749284d841b02421259c4e8178f25b91542c026ae6ced6d01", 
		"65268e6267b14eb52dc1ccc500dc2624a6e37d0a98280f3275413eacb1d2915d01", 
		"cdabc10f1ff3410082448b708c0f860a948197d55fb612cb328d7a5cc07a6c8a01"
	    ], 
            "redeem_script": ("522102d341f728783eb93e6fb5921a1ebe9d149e941de31e403cd" + 
                              "69afa2f0f1e698e812102f21b29694df4c2188bee97103d10d017" + 
                              "d1865fb40528f25589af9db6e0786b6521028791dc45c049107fb" + 
                              "99e673265a38a096536aacdf78aa90710a32fff7750f9f953ae")
        }
    }
    return w

def get_wallet_singlesig():
    w = {
        "payment_address": "mvF2KY1UbdopoomiB371epM99GTnzjSUfj", 
        "payment_privkey": "f4c3907cb5769c28ff603c145db7fc39d7d26f69f726f8a7f995a40d3897bb5201"
    }
    return w

def make_subsidized_tx(serialized_tx):
    wallet = get_wallet_keys(config_path=config_path, password=False)

    payment_address = str(wallet["payment_address"])
    payment_privkey_info = wallet["payment_privkey"]

    print "subsidizing tx: " + serialized_tx
    
    utxo_client = get_utxo_provider_client(config_path=config_path)
    
    # estimating tx_fee...
    ## will need to pad to estimated length of payment input and output

    num_extra_bytes = estimate_payment_bytes( payment_address, utxo_client, config_path=config_path )
    approxed_tx = serialized_tx + '00' * num_extra_bytes

    tx_fee = get_tx_fee(approxed_tx, config_path = config_path)

    # make the subsidized tx
    subsidized_tx = tx_make_subsidizable(serialized_tx,
                                         fees_transfer,
                                         500000,
                                         payment_privkey_info,
                                         utxo_client,
                                         tx_fee=tx_fee)

    return subsidized_tx

def do_broadcast(serialized_tx):
    # broadcast it.
    try:
        resp = broadcast_tx(serialized_tx, config_path = config_path,
                            tx_broadcaster = get_tx_broadcaster(config_path = config_path))
    except Exception as e:
        print e
        print('Failed to broadcast transaction: {}'.format(
            json.dumps(deserialize_tx(serialized_tx), indent=4)))

        print('raw: \n{}'.format(serialized_tx))
        
        return {'error': 'Failed to broadcast transaction (caught exception)'}

    if 'error' in resp:
        print('Failed to broadcast transaction: {}'.format(resp['error']))

    return resp

app = Flask(__name__)

@app.route("/subsidized_tx/<rawtx>")
def get_subsidize_tx(rawtx):
    subsidized = make_subsidized_tx(str(rawtx))

    return '["' + subsidized + '"]'

@app.route("/broadcast/<rawtx>")
def broadcast(rawtx):
    resp = do_broadcast(str(rawtx))
    return json.dumps(resp)


if __name__ == "__main__":
    app.run()