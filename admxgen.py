from yast import import_module
import_module('Wizard')
import_module('UI')
from yast import *
from ui import *
import os.path

class MainDialog:
    def __init__(self):
        self.__setup_menus()

    def __setup_menus(self):
        menus = [{'title': '&File', 'id': 'file', 'type': 'Menu'},
                 {'title': '&Open', 'id': 'open', 'type': 'MenuEntry', 'parent': 'file'},
                 {'title': '&Save', 'id': 'save', 'type': 'MenuEntry', 'parent': 'file'},
                 {'title': 'S&ave As...', 'id': 'saveas', 'type': 'MenuEntry', 'parent': 'file'},
                 {'title': 'E&xit', 'id': 'abort', 'type': 'MenuEntry', 'parent': 'file'}]
        CreateMenu(menus)

    def __reset(self):
        UI.SetApplicationTitle('ADMX Generator')
        UI.ReplaceWidget('main', self.__main_page())
        self.__setup_menus()

    def Show(self):
        open_file = None
        self.__reset()
        while True:
            event = UI.WaitForEvent()
            if 'WidgetID' in event:
                ret = event['WidgetID']
            elif 'ID' in event:
                ret = event['ID']

            if ret in ['back', 'abort', 'cancel']:
                break
            elif ret == 'open':
                open_file = UI.AskForExistingFile(os.path.expanduser('~/'), '*.admx *.adml', 'Select an ADMX/ADML file for editing')
                data = open(open_file, 'r').read()
                UI.ChangeWidget('text', 'Value', data)
            elif ret == 'saveas' or (ret == 'save' and open_file is None):
                open_file = UI.AskForSaveFileName(os.path.expanduser('~/'), '*.admx *.adml', 'Choose an ADMX/ADML filename for saving')
                with open(open_file, 'w') as w:
                    data = UI.QueryWidget('text', 'Value')
                    w.write(data)
            elif ret == 'save' and open_file is not None:
                with open(open_file, 'w') as w:
                    data = UI.QueryWidget('text', 'Value')
                    w.write(data)

    def __main_page(self, filename=None):
        if filename:
            pass
        else:
            textbox = MultiLineEdit(Id('text'), '', '')
        return VBox(ReplacePoint(Id('topmenu'), Empty()), HBox(
            HWeight(1, textbox),
            HWeight(1, ReplacePoint(Id('wysiwyg'), Empty()))
        ))

if __name__ == "__main__":
    UI.OpenDialog(Opt('mainDialog'), ReplacePoint(Id('main'), ReplacePoint(Id('topmenu'), Empty())))
    MainDialog().Show()
    UI.CloseDialog()

