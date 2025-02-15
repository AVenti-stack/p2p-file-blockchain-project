from flexx import flx

class MainBootstrap(flx.Widget):

    CSS = """
          .flx-MainBootstrap, .flx-RadioButton, .flx-Label { 
           color: #fff !important;
           margin-bottom: 10px;
          }
          .flx-Label {
           padding: 0
          }
          """

    def init(self):
        with flx.VBox():
            self.b1 = flx.RadioButton(text="bchain-network.xyz")
            self.bootlabel = flx.Label(text='No bootstrap selected')

    @flx.reaction('b1.checked')
    def strapselected(self, *events):
        ev = events[-1]
        if ev.source.checked:
            self.bootlabel.set_text(ev.source.text + ' bootstrap selected')
