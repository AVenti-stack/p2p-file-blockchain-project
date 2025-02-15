from flexx import flx, ui

class Uploadwidget(flx.Widget):

    CSS = """
            
                background-color: #6201E7;
                color: #fff;
            }
            .flx-Uploadwidget > .flx-Button:hover{
                background-color: #fff;
                color: #6201E7;;
            }
          """

    def init(self):
        with flx.HBox():
            with flx.VBox(flex=1):
                self.namelabel = flx.Label(text="Name: ", flex=1)
                self.taglabel = flx.Label(text="Tags: ", flex=1)
                self.typelabel = flx.Label(text="Type: ", flex=1)
            with flx.VBox(flex=3):
                self.nameline = flx.LineEdit(flex=1)
                self.tagline = flx.LineEdit(flex=1)
                self.typedrop = flx.ComboBox(options=("Image", "Video", "Document", "Audio", "App"), flex=1)
            self.submitbut = flx.Button(text="Submit", css_class="btn-continue", flex=2)

    @flx.reaction('submitbut.pointer_click')
    def updatefilestrs(self):
        # print("This is working :)")
        self.root.upload(self.nameline.text, self.tagline.text, self.typedrop.text)

    @flx.action
    def emptystrs(self):
        print("This is emptying the strs :)")
        self.nameline.set_text("")
        self.tagline.set_text("")
        self.typedrop.set_text("")




