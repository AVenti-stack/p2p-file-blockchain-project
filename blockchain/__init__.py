import hashlib
from hashlib import sha256
import json
from tinydb import TinyDB

db = TinyDB('bc.json')  # creates a db to store the blocks using tinydb


class Blockchain(object):

    proof = -1

    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        local_chain = db.all()
        print(local_chain)
        if len(local_chain) == 0:
            self.new_block(
                previous_hash="B-Chain 2021 Caleb Carlos Jeffrey Jonathan Giang")
        else:
            _ = self.new_block(
                previous_hash="B-Chain 2021 Caleb Carlos Jeffrey Jonathan Giang", skip_insert=True)
            for block in local_chain[1:]:
                tx = block["transactions"][0]
                _ = self.new_transaction(title=tx['title'],
                                         filename=tx['filename'],
                                         type=tx['type'],
                                         tags=tx['tags'],
                                         size=tx['size'])
                self.new_block(
                    previous_hash=block['previous_hash'], skip_insert=True)

    def nextProof(self):
        self.proof += 1
        return self.proof

    # Create a new block listing key/value pairs of block information in a JSON object. Reset the list of pending transactions
    # & append the newest block to the chain.

    def new_block(self, previous_hash=None, skip_insert=False):
        block = {
            'index': len(self.chain) + 1,
            'transactions': self.pending_transactions,
            'proof': self.nextProof(),
            'previous_hash': previous_hash or self.hash(self.chain[-1]),

        }
        self.pending_transactions = []
        if not skip_insert:
            db.insert(block)
        self.chain.append(block)

        return block

    # Search the blockchain for the most recent block.

    @property
    def last_block(self):
        return self.chain[-1]

    # Add a transaction with relevant info to the 'blockpool' - list of pending tx's.

    def new_transaction(self, title: str, filename: str, type: str, tags: str, size: str):
        transaction = {
            'title': title,
            'filename': filename,
            'type': type,
            'size': size,
            'tags': tags
        }
        self.pending_transactions.append(transaction)
        # db.insert(transaction)
        return self.last_block['index'] + 1

    # receive one block. Turn it into a string, turn that into Unicode (for hashing). Hash with SHA256 encryption,
    # then translate the Unicode into a hexadecimal string.
    def hash(self, block):
        string_object = json.dumps(block, sort_keys=True)
        block_string = string_object.encode()

        raw_hash = hashlib.sha256(block_string)
        hex_hash = raw_hash.hexdigest()

        return hex_hash

    # display the hash in string form
    def compute_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


def prettyBytes(B):
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)
    GB = float(KB ** 3)
    TB = float(KB ** 4)

    if B < KB:
        return '{0} {1}'.format(B, 'Bytes' if 0 == B > 1 else 'Byte')
    elif KB <= B < MB:
        return '{0:.2f} KB'.format(B/KB)
    elif MB <= B < GB:
        return '{0:.2f} MB'.format(B/MB)
    elif GB <= B < TB:
        return '{0:.2f} GB'.format(B/GB)
    else:
        return '{0:.2f} TB'.format(B/TB)
