from flexx import flx, ui, event
from tinydb import Query

from framework import core
import framework
import exchange, blockchain, discovery

# Sort Button for explorer


class SortOptions(flx.Widget):

    CSS = """
        .flx-SortOptions > .flx-Button{
        padding = 100px;
        }
        """

    def init(self):
        with flx.HBox():
            self.label = flx.Label(text='Latest First')
            self.options = flx.ComboBox(text='Latest First', options=('Latest First', 'Oldest First'))

    @flx.reaction
    def update_label(self):
        self.label.set_text(self.options.text)
        if self.options.text == 'Latest First':
            self.parent.get_widget("table-chain").update_firlas(False)
        else:
            self.parent.get_widget("table-chain").update_firlas(True)


# Main table

class MainTable(flx.Widget):

    CSS = """
            .flx-MainTable {
              overflow-y: auto;
              max-height: 75vh !important;
            }    
           .flx-MenuWidget > .flx-Button{
            padding = 100px;
            }
          """

    cards = flx.TupleProp(())
    chain = flx.ListProp()
    search = flx.StringProp()
    type = flx.StringProp()
    sort = flx.StringProp()
    firlas = flx.BoolProp()

    def _create_dom(self):
        # TODO: notify when chain changed, instead of requesting a chain update
        self.root.get_chain(str(self.type))
        return flx.create_element('div', {'class': 'grid-view'})

    @flx.reaction('chain', 'search', 'sort','firlas')
    def update_cards(self):
        for card in self.cards:
            card.dispose()

        new_cards = tuple()

        transactions = []
        for block in self.chain:
            if self.firlas==False:
                transactions.insert(0, block)
            else:
                transactions.append(block)

        if self.search:
            i = len(transactions) - 1
            while i >= 0:
                transaction = transactions[i]
                if self.search.lower() not in transaction.title.lower():
                    transactions.pop(i)
                i -= 1

        if self.sort and self.sort != "All":
            i = len(transactions) - 1
            while i >= 0:
                transaction = transactions[i]
                progress = transaction.progress
                done = progress == 100
                print(done)
                if done and self.sort == "Active" or not done and self.sort == "Completed":
                    transactions.pop(i)
                i -= 1


        self.__enter__()
        for transaction in transactions:
            card = Gridcard(transaction.title, transaction.type, transaction.size, str(self.type), transaction.id, transaction.filename, transaction.tags, progress=transaction.progress, css_class="grid-card")
            new_cards.append(card)
        self.__exit__()

        self.change_cards(new_cards)

    @flx.action
    def send_chain(self, chain):
        self._mutate_chain(chain)

    @flx.action
    def change_cards(self, cards):
        self._mutate_cards(cards)

    @flx.action
    def update_search(self, search):
        self._mutate_search(search)

    @flx.action
    def update_sort(self, sort):
        self._mutate_sort(sort)

    @flx.action
    def update_firlas(self, firlas):
        self._mutate_firlas(firlas)


class Searchbar(flx.Widget):
    def init(self):
        with flx.HBox(flex=1):
            self.searchbar = flx.LineEdit()

    @flx.reaction
    def update_search(self):
        self.parent.get_widget("table-chain").update_search(self.searchbar.text)

class Gridcard(flx.Widget):

    card_id = flx.StringProp()
    progress = flx.IntProp(-1)

    def __init__(self, name, category, file_size, grid_type, file_id, filename, tags, **kwargs):
        self.name = name
        self.file_id = file_id
        self.category = category
        self.file_size = file_size
        self.type = grid_type
        self.filename = filename
        self.tags = tags.replace(",", ", ")
        kwargs["card_id"] = file_id
        super().__init__(**kwargs)

# explorer gridcard stuff
    def init(self):
        with flx.HFix():
            # each box holds the individual files with all fo its information and download button and stuff
            with flx.VBox(flex=3):
                with flx.HBox():
                    self.namelabel = flx.Label(html="<h6>" + self.name + "</h6>")
                with flx.HBox():
                    self.genrelabel = flx.Label(text="" + self.category)
                    self.taglabel = flx.Label(text="" + self.tags)
                with flx.HFix():
                    self.sizelabel = flx.Label(text=blockchain.prettyBytes(self.file_size), flex=3)
                    self.downloadlabel = flx.Label(html='<div></div>', flex=4)
            button_css = "btn-continue btn-download"
            button_flex = 1

            if self.type != "explore" or self.progress == 100:
                button_css += " invisible"
                button_flex = 0
            self.button = flx.Button(text="Download", flex=button_flex, css_class=button_css)
            if self.progress == 100:
                self.on_change_progress()


    @flx.action
    def change_progress(self, progress):
        self._mutate_progress(progress)

    @flx.reaction('button.pointer_click')
    def on_button_clicked(self):
        if self.type == "explore":
            print(self.file_size)
            progress = "0"
            self.root.download_file(self.file_id, int(self.file_size), self.filename)
            self.sizelabel.set_text(blockchain.prettyBytes(self.file_size) + " / " + progress + "%")
            self.downloadlabel.set_html('<div class="grid-container"><div class="grid-border"><div class="grid-grey" style="width:' + progress + '%;"></div></div></div>')

    @flx.reaction('progress')
    def on_change_progress(self):
        if self.progress >= 0:
            self.sizelabel.set_text(blockchain.prettyBytes(self.file_size) + " / " + self.progress + "%")
            self.downloadlabel.set_html('<div class="grid-container"><div class="grid-border"><div class="grid-grey" style="width:' + self.progress + '%;"></div></div></div>')


class MenuWidget(flx.Widget):

    def init(self):
        with flx.VBox():
            self.allb = flx.Button(text='All')
            self.completedb = flx.Button(text='Completed')
            self.activeb = flx.Button(text='Active')

    @flx.reaction('allb.pointer_click', 'completedb.pointer_click', 'activeb.pointer_click')
    def Sort(self, *events):
        ev = events[-1]
        self.Buttonpress(ev.source.text)

    @flx.action
    def Buttonpress(self, sorttype):
        self.parent.get_widget("table-chain").update_sort(sorttype)



