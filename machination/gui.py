#! /usr/bin/python3

import sys
import time
import copy
import functools
import os
import context
import inspect
from lxml import etree
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import PyQt5.uic
from machination.webclient import WebClient
from collections import OrderedDict

class MGUI():

    def __init__(self):

        self.wcs = {}
        self.model = HModel()

        QDir.addSearchPath("icons","")
        print(QDir.searchPaths("icons"))

        self.myfile = inspect.getfile(inspect.currentframe())
        self.mydir = os.path.dirname(self.myfile)
        self.ui = PyQt5.uic.loadUi(os.path.join(self.mydir, "gui.ui"))
        self.ui.show()
        self.ui.treeView.setModel(self.model)
        self.readSettings()

        ### Dialogs ####################
        # service_url
        self.d_service_url = QInputDialog(self.ui)
        self.d_service_url.setLabelText("Service URL:")
        self.d_service_url.setComboBoxItems(
            ["http://localhost/machination/hierarchy",
             "https://mach2-test.see.ed.ac.uk/machination/hierarchy",
             "https://mach2.see.ed.ac.uk/machination/hierarchy",
             "--new--"]
            )

        # Signals, slots and events
        self.ui.actionExit.triggered.connect(self.handlerExit)
        self.ui.closeEvent = self.handlerExit
        self.ui.actionConnect.triggered.connect(self.handlerConnect)

        self.ui.treeView.expanded.connect(self.model.on_expand)

    def handlerExit(self, ev = None):
        print("Bye!")
        self.saveSettings()
        sys.exit()

    def handlerConnect(self, ev = None):
        '''Handler for Service.connect menu item
        '''
        ok = self.d_service_url.exec_()
        if ok:
            self.connect_to_service(self.d_service_url.textValue())

    def saveSettings(self):
        s = QSettings("Machination", "Hierarchy Editor")
        s.beginGroup("mainwin")
        s.setValue("pos", self.ui.pos())
        s.setValue("size", self.ui.size())
        s.endGroup()

        s.setValue("splitter/sizes", self.ui.splitter.sizes())

        s.beginGroup("treeview")
        s.setValue("colwidths",
                   [self.ui.treeView.columnWidth(i)
                    for i in range(self.model.columnCount())]
                   )
        s.endGroup()

    def readSettings(self):
        s = QSettings("Machination", "Hierarchy Editor")
        s.beginGroup("mainwin")
        self.ui.resize(s.value("size", QSize(900,600)))
        self.ui.move(s.value("pos", QPoint(100,100)))
        s.endGroup()

        self.ui.splitter.setSizes(
            [int(x) for x in s.value("splitter/sizes",[300,600])]
            )

        s.beginGroup("treeview")
        for i, sz in enumerate(s.value("colwidths",[200,0,0,0,100])):
            self.ui.treeView.setColumnWidth(i, int(sz))
        self.ui.treeView.hideColumn(1)
        self.ui.treeView.hideColumn(2)
        self.ui.treeView.hideColumn(3)
        s.endGroup()

    def connect_to_service(self, url):
        '''Connect to a machination hierarchy service.
        '''
        d = CredentialsDialog(self.ui, url)
        selt = etree.fromstring(
            "<service><hierarchy id='{}'/></service>".format(url)
            )
        tmpwc = WebClient(url, 'public', 'person')
        istr = tmpwc.call('ServiceConfig')
        info = etree.fromstring(istr)
        auth_type_elts = info.xpath('authentication/type')
        authtypes = [x.get("id") for x in auth_type_elts]
        d.setAuthMethodsList(authtypes)
        default_method = info.xpath('authentication/objType[@id="person"]/@defaultAuth')[0]
        d.default_auth_method = default_method
        d.setAuthMethod(default_method)
        ok = d.exec_()
        if ok:
            cred = d.getCred()
            self.wcs[url] = WebClient(url, d.current_auth_method, 'person', credentials = cred)
            self.model.add_service(self.wcs[url])

class HModel(QStandardItemModel):
    '''Model Machination hierarchy for QTreeView
    '''

    columns = ['name', 'type_id', 'obj_id', 'channel_id', '__branch__']

    def __init__(self, wc = None):
        super().__init__(0,4)
        self.wcs = {}
        if wc is not None:
            self.add_service(wc)

        self.setHorizontalHeaderLabels(HModel.columns)

    def add_service(self, wc):
        '''Add a new service at the root of the tree.'''
        self.wcs[wc.url] = wc
        name_index = self.add_object(
            self.invisibleRootItem(),
            {'name': wc.url,
             'type_id': 'machination:hc',
             'obj_id': '0',
             },
            wc = wc
            )
        self.itemFromIndex(name_index).setEditable(False)

    @functools.lru_cache(maxsize=None)
    def get_icon(self, name):
        '''Return the correct icon for name
        '''
        return QIcon(os.path.join(context.resources_dir(),'{}.svg'.format(name)))

    def add_object(self, parent, obj, wc=None,
                   peek_children=True):
        '''Add an object to parent in tree'''
        if not isinstance(parent, QStandardItem):
            # Assume parent is an index
            parent = self.itemFromIndex(parent)
        if wc is None:
            wc = self.get_wc(parent)

        name_item = QStandardItem(obj.get('name'))
        type_id = obj.get('type_id')
        type_name = wc.memo('TypeInfo', type_id).get('name')

        if not obj.get('__branch__'):
            obj['__branch__'] = 'contents'

        if  type_id == 'machination:hc':
            name_item.setIcon(self.get_icon('folder'))
        elif obj.get('channel_id'):
            name_item.setIcon(self.get_icon('__attached__{}'.format(type_name)))
        else:
            name_item.setIcon(self.get_icon(type_name))
        row = [
            name_item,
            QStandardItem(type_id),
            QStandardItem(obj.get('obj_id')),
            QStandardItem(obj.get('channel_id')),
            QStandardItem(obj.get('__branch__')),
            ]
        parent.appendRow(row)

        if peek_children:
            obj = self.peek_children(self.indexFromItem(name_item))
            if obj:
                self.add_object(name_item, obj, peek_children=False)


        return self.indexFromItem(name_item)

    def get_wc(self, thing):
        '''Find the webclient for an item or index'''
        obj_path = self.get_obj_path(thing)
        return self.wcs.get(obj_path[0].text())

    def get_obj_path(self, thing):
        '''Return list of StandardItem objects from index or item to root.'''
        if isinstance(thing, QStandardItem):
            index = thing.index()
        else:
            index = thing

        if not index.isValid():
            return []

        path = self.get_obj_path(index.parent())
        path.append(self.itemFromIndex(index))

        return path

    def get_path(self, thing):
        '''Return a string path to an index or StandardItem'''
        obj_path = self.get_obj_path(thing)

        last_index = self.indexFromItem(obj_path[-1])
        if self.get_value(last_index, '__branch__') != 'contents':
            wc = self.get_wc(last_index)
            return '{}:{}'.format(
                wc.memo('TypeInfo', self.get_value(last_index, 'type_id')).get('name'),
                self.get_value(last_index, 'obj_id')
                )

        path = ['']
        for obj in obj_path[1:]:
            path.append(obj.text())
        if len(path) == 1:
            return '/'
        return '/'.join(path)

    def get_item(self, index, col_name):
        '''Return QStandardItem given column name and any index in row'''
        return self.itemFromIndex(
            self.index(
                index.row(),
                HModel.columns.index(col_name),
                index.parent()
                )
            )

    def get_value(self, index, col_name):
        '''Return the text stored in column col_name given a row or index'''
        return self.get_item(index, col_name).text()

    def on_expand(self, index):
        '''Slot for 'expanded' signal.'''
        self.refresh(index)

    def refresh(self, index):
        '''Refresh a node from the hierarchy'''
        print('refreshing {}'.format(self.get_path(index)))
        wc = self.get_wc(index)
        type_id = self.get_value(index, 'type_id')
        if type_id == 'machination:hc':
            self.removeRows(0,self.rowCount(index),index)
            for child in self.get_children(index):
                self.add_object(index, child)
        elif wc.memo('TypeInfo', type_id).get('is_attachable') == '1':
            pass
        else:
            raise Exception("Don't know how to refresh {}".format(type_id))

    def peek_children(self, index):
        '''Look to see if an item which could have children actually has any.'''
        wc = self.get_wc(index)
        type_id = self.get_value(index, 'type_id')
        if type_id == 'machination:hc':
            attachments = wc.call(
                'ListAttachments',
                self.get_path(index),
                {'max_objects': 1}
                )
            if attachments:
                attachments[0]['__branch__'] = 'attachments'
                return attachments[0]
            contents = wc.call(
                'ListContents', self.get_path(index), {'max_objects': 1}
                )
            if contents:
                return contents[0]
            else:
                return False
        if wc.memo('TypeInfo', type_id).get('is_agroup') == '1':
            members = wc.call('AgroupMembers', self.get_path(index))
            if members:
                members[0]['__branch__'] = 'members'
                return members[0]
            else:
                return False

    def get_children(self, index):
        '''Fetch children from hierarchy if object has any.'''
        wc = self.get_wc(index)
        type_id = self.get_value(index, 'type_id')
        if type_id == 'machination:hc':
            return_list = []
            attachments = wc.call(
                'ListAttachments', self.get_path(index),
                {'get_members':0}
                )
            for newatt in attachments:
                newatt['__branch__'] = 'attachments'
            return_list.extend(attachments)
            contents = wc.call(
                'ListContents', self.get_path(index)
                )
            for newobj in contents:
                newobj['__branch__'] = 'contents'
            return_list.extend(contents)
            return return_list
        if wc.memo('TypeInfo', type_id).get('is_agroup') == '1':
            members = wc.call('AgroupMembers', self.get_path(index))
            for member in members:
                member['__branch__'] = 'members'
            return members

class CredentialsDialog(QDialog):
    '''Capture the correct credentials to authenticate to a service'''

    def __init__(self, parent, url):
        super().__init__(parent)
        self.url = url

        self.setWindowTitle('Connecting to {}'.format(url))

        # Precreated text entry widgets for credentials
        self.cred_inputs = OrderedDict(
            [
                ('public', OrderedDict()),
                ('cosign', OrderedDict(
                        [
                            ('login', {
                                    'label': QLabel('Login Name'),
                                    'widget': QLineEdit()
                                    }
                             ),
                            ('password', {
                                    'label': QLabel('Password'),
                                    'widget': self.makePasswordBox()
                                    }
                             ),
                            ]
                        )
                 ),
                ('cert', OrderedDict(
                        [
                            ('key', {
                                    'label': QLabel('Key File'),
                                    'widget': QLineEdit()
                                    }
                             ),
                            ('cert', {
                                    'label': QLabel('Certificate File'),
                                    'widget': QLineEdit()
                                    }
                             )
                            ]
                        )
                 ),
                ('basic', OrderedDict(
                        [
                            ('username', {
                                    'label': QLabel('User Name'),
                                    'widget': QLineEdit()
                                    }
                             ),
                            ('password', {
                                    'label': QLabel('Password'),
                                    'widget': self.makePasswordBox()
                                    }
                             )
                            ]
                        )
                 ),
                ('debug', OrderedDict(
                        [
                            ('name', {
                                    'label': QLabel('Name'),
                                    'widget': QLineEdit()
                                    }
                             )
                            ]
                        )
                 ),
                ]
            )

        # A combobox for the different authentication methods
        self.auth_method_label = QLabel('Authentication Method:')
        self.auth_methods = QComboBox()

        # The button box along the bottom
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok |
            QDialogButtonBox.Cancel
            )

        # Lay out the main widgets
        self.main_layout = QVBoxLayout()
        self.cred_layout = QVBoxLayout()
        self.main_layout.addLayout(self.cred_layout)
        self.main_layout.addWidget(QLabel(url))
        self.main_layout.addWidget(self.auth_method_label)
        self.main_layout.addWidget(self.auth_methods)
        self.main_layout.addWidget(self.button_box)
        self.setLayout(self.main_layout)

        # Populate the authentication combobox
        self.setAuthMethodsList([x for x in self.cred_inputs.keys()])

        # Connect signals and slots
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.auth_methods.currentIndexChanged.connect(self.method_chosen)

    def makePasswordBox(self):
        '''Make a QLineEdit widget with the 'Password' echo mode.'''
        box = QLineEdit()
        box.setEchoMode(QLineEdit.Password)
        return box

    def setAuthMethodsList(self, methods):
        '''Set the list of authentication methods to choose from.'''
        self.auth_methods.clear()
        self.auth_methods.addItems(methods)
        self.default_auth_method = methods[0]

    def setAuthMethod(self, method):
        '''Set the current choice of authentication method.'''
        self.auth_methods.setCurrentIndex(
            self.auth_methods.findText(method, Qt.MatchExactly)
            )

    def method_chosen(self, idx):
        '''Slot called when an authentication method is chosen.'''
        if idx < 0: return
        print('choosing index {}'.format(idx))
        method = self.auth_methods.itemText(idx)
        print('choosing method {}'.format(method))
        self.current_auth_method = method
        self.auth_method_label.setText("(default = {}, current = {}):".format(self.default_auth_method, self.current_auth_method))
        # Clear cred_layout
        for i in range(self.cred_layout.count()):
            self.cred_layout.itemAt(0).itemAt(0).widget().hide()
            self.cred_layout.itemAt(0).itemAt(1).widget().hide()
            self.cred_layout.removeItem(self.cred_layout.itemAt(0))
        # Add entry fields
        for key, data in (self.cred_inputs.get(method).items()):
            layout = QHBoxLayout()
            data.get('label').show()
            data.get('widget').show()
            layout.addWidget(data.get('label'))
            layout.addWidget(data.get('widget'))
            self.cred_layout.addLayout(layout)

    def getCred(self):
        '''Get the captured credentials for the current authentication method.'''
        cred_tmp = self.cred_inputs.get(self.current_auth_method)
        return {x:y.get('widget').text() for x,y in cred_tmp.items()}

def main():
    ex = MGUI()
    return app.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    sys.exit(main())



