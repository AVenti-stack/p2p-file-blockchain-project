import discovery
from flexx import flx
from flexx.ui import FileBrowserWidget
from tinydb import Query
from pathlib import Path

import framework
from exchange import download_file, upload_file
from framework.gateway import Gateway

import blockchain

class Core(flx.PyWidget):

    CSS = '''
        .flx-TreeWidget {
            background: #000;
            color: #afa;
        }
        '''

    Filepath = ""

    def init(self):

        self.label = flx.Label(flex=1, style='overflow-y:scroll;')

        self.g = Gateway()
        self.fs = FileBrowserWidget()
        self.g.set_jfs(self.fs._jswidget)


    @flx.action
    def download_file(self, file_id, size, path):
        download_file(framework.my_peer, file_id, size, path)

    def download_progress(self, file_id, progress, download=True):
        progress *= 100
        progress = int(progress)
        File = Query()
        db = framework.downloads_db if download else framework.uploads_db
        db.upsert({"id": file_id, "progress": progress}, File.id == file_id)
        self.g.download_progress(file_id, progress, download)

    @flx.action
    def get_chain(self, filter=None):
        transactions = []
        blocks = None
        db = None
        if filter:
            if filter == "download":
                db = framework.downloads_db
            elif filter == "upload":
                db = framework.uploads_db
            if db is not None:
                files = db.all()
                print(files)
                hashes = []
                for file in files:
                    hashes.append(file["id"])
                print(hashes)
                if hashes:
                    File = Query()
                    blocks = blockchain.db.search(
                        File.previous_hash.one_of(hashes))
                else:
                    blocks = []
                print(blocks)

        if blocks is None:
            blocks = blockchain.db.all()

        for block in blocks:
            for transaction in block["transactions"]:
                transaction["id"] = block["previous_hash"]
                if db is None:
                    db = framework.downloads_db
                File = Query()
                query = db.search(File.id == transaction["id"])
                if len(query) > 0:
                    transaction["progress"] = query[0]["progress"]
                else:
                    transaction["progress"] = -1
                transactions.append(transaction)
                print(transaction)
        self.g.send_chain(transactions)

    def bootstrap_progress(self, progress):
        self.g.bootstrap_progress(progress * 100)


    # this is the reaction for when a file is selected for upload
    @flx.reaction('fs.selected')
    def fileselect(self, *events):
        SFile = events[-1]  # shows the path
        # print("(SFile the file selected is: ", SFile)
        Namefile = SFile.filename
        self.Filepath = Namefile
        # SFile.set_path('C:/Users/Trevor_G/Storingfile')

    # def getFileName(self, *events):
    #     ev = events[-1]
    #     name = str(ev.filename)
    #     return name




    @flx.action
    def upload(self, name, tags, type):
        upload_file(framework.my_peer, Path(self.Filepath), name, tags, type, str(Path(self.Filepath).stat().st_size))
        self.g.emptystrs()

    @flx.action
    def bootstrap(self, domain: str):
        framework.my_peer.bootstrap(framework.ddns)

