from pathlib import Path

from flexx import flx
from pscript import RawJS

from framework import load_static, load_template, widgets

DEFAULT_PAGE = "splash"
pages = {}


def load_templated_page(file, name, kwargs):
    print(f"Loaded template {file}.html ({name})")
    pages[name] = load_template(f"{file}.html", kwargs)


page_props = {
    "d": {},
    "index": {
        "name": "Explore",
        "type": "explore"
    },
    "download": {
        "name": "Library",
        "type": "download"
    },
    "upload": {
        "name": "Uploads",
        "type": "upload"
    }
}

virtual_pages = {
    "index": ["download", "upload"]
}

for page in Path("gui/templates").iterdir():
    vpages = [page.stem]
    if page.stem in virtual_pages:
        vpages.extend(virtual_pages[page.stem])
    for vpage in vpages:
        if page.is_file() and page.suffix == ".html":
            props = page_props["d"]
            if vpage in page_props:
                props = {**props, **page_props[vpage]}
            props["PAGE"] = vpage
            load_templated_page(page.stem, vpage, props)

flx.assets.associate_asset("framework.gateway", f"js/app.js", lambda: load_static(f"gui/js/app.js"))


class Gateway(flx.Label):
    CSS = load_static("gui/css/responsive.css") + load_static("gui/css/font-awesome.css") + load_static(
        "gui/css/style.css")

    actions = {}

    elements = {}

    page_elements = []

    widgets = {}

    jfs = None

    def init(self):
        self.actions = {
            "change_page": self.change_page,
            "download_file": self.download_file,
            "app_update": self.app_update,
            "get_chain": self.get_chain
        }
        self.elements = {
            "Button": flx.Button,
            "MainTable": widgets.MainTable,
            "Bootstrap": widgets.MainBootstrap,
            "Searchbar": widgets.Searchbar,
            "Menuwidget": widgets.MenuWidget,
            "Filewidget": None,
            "Uploadwidget": widgets.Uploadwidget,
            "Sortwidget": widgets.SortOptions
        }
        self.set_html(pages[DEFAULT_PAGE])

    def _create_dom(self):
        return flx.create_element("div", {"id": "app", "onreact": self.react})

    def _render_dom(self):
        return None

    def react(self, action, *data):
        if action in self.actions:
            return self.actions[action](*data)
        else:
            print(f"{action} not found!")

    def change_page(self, page):
        for element in self.page_elements:
            element.outernode.remove()
            element.dispose()
        self.page_elements.clear()
        self.widgets.clear()
        self.set_html(pages[page])

    def get_widget(self, element_id):
        return self.widgets[element_id]

    @flx.action
    def emptystrs(self):
        self.get_widget("uploadwidget").emptystrs()

    def app_update(self):
        global window
        flexx_elements = window.document.querySelectorAll("x-flx")
        construct = RawJS("Reflect.construct")
        self.__enter__()
        for i in flexx_elements:
            element = flexx_elements[i]
            el_name = element.getAttribute("el")
            if el_name in self.elements:
                kwargs = {}
                for data in element.dataset:
                    kwargs[data] = element.dataset[data]
                flx_node = None
                if el_name == "Filewidget":
                    flx_node = self.jfs
                else:
                    constructor = self.elements[el_name]
                    flx_node = construct(constructor, [{"flx_args": [], "flx_kwargs": kwargs}])
                    element_id = element.getAttribute("id")
                    if element_id is not None:
                        self.widgets[element_id] = flx_node
                    self.page_elements.append(flx_node)
                element.after(flx_node.outernode)
                element.remove()
        self.__exit__()

    def download_file(self, file_id, size, path):
        self.root.download_file(file_id, size, path)

    @flx.action
    def download_progress(self, file_id, progress, download=True):
        global window
        if self.get_widget("table-chain"):
            for card in self.get_widget("table-chain").cards:
                if str(card.card_id) == file_id:
                    card.change_progress(progress)
                    break

    @flx.action
    def set_jfs(self, filebrowser):
        self.jfs = filebrowser

    @flx.action
    def bootstrap_progress(self, progress):
        global window
        progress_str = str(int(progress)) + "%"
        if window.document.getElementById("bootstrap-progress-text") is None:
            return
        window.document.getElementById("bootstrap-progress-text").innerText = progress_str
        window.document.getElementById("bootstrap-progress-bar").style.width = progress_str
        if progress >= 100:
            window.document.getElementById("continue-btn").removeAttribute("disabled")
            window.document.getElementById("continue-btn").onclick = RawJS("() => changePage('index')")
            window.document.getElementById("bootstrap-text").innerText = ""
        elif progress >= 90:
            window.document.getElementById("bootstrap-text").innerText = "Establishing connection..."

    @flx.action
    def send_chain(self, chain):
        self.get_widget("table-chain").send_chain(chain)

