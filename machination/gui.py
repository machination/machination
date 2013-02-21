#! /usr/bin/python3

#Force sip to use API version 2. Should just work on Python3, but let's not
#take any chances
import sip
sip.setapi("QString",2)
sip.setapi("QVariant",2)

import sys
import time
import copy
from lxml import etree
from PyQt4 import QtGui
from PyQt4 import QtCore
from machination.webclient import WebClient
from collections import OrderedDict

class CredentialsDialog(QtGui.QDialog):

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
                                    'label': QtGui.QLabel('Login Name'),
                                    'widget': QtGui.QLineEdit()
                                    }
                             ),
                            ('password', {
                                    'label': QtGui.QLabel('Password'),
                                    'widget': self.makePasswordBox()
                                    }
                             ),
                            ]
                        )
                 ),
                ('cert', OrderedDict(
                        [
                            ('key', {
                                    'label': QtGui.QLabel('Key File'),
                                    'widget': QtGui.QLineEdit()
                                    }
                             ),
                            ('cert', {
                                    'label': QtGui.QLabel('Certificate File'),
                                    'widget': QtGui.QLineEdit()
                                    }
                             )
                            ]
                        )
                 ),
                ('basic', OrderedDict(
                        [
                            ('username', {
                                    'label': QtGui.QLabel('User Name'),
                                    'widget': QtGui.QLineEdit()
                                    }
                             ),
                            ('password', {
                                    'label': QtGui.QLabel('Password'),
                                    'widget': self.makePasswordBox()
                                    }
                             )
                            ]
                        )
                 ),
                ('debug', OrderedDict(
                        [
                            ('name', {
                                    'label': QtGui.QLabel('Name'),
                                    'widget': QtGui.QLineEdit()
                                    }
                             )
                            ]
                        )
                 ),
                ]
            )

        # A combobox for the different authentication methods
        self.auth_method_label = QtGui.QLabel('Authentication Method:')
        self.auth_methods = QtGui.QComboBox()

        # The button box along the bottom
        self.button_box = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok |
            QtGui.QDialogButtonBox.Cancel
            )

        # Lay out the main widgets
        self.main_layout = QtGui.QVBoxLayout()
        self.cred_layout = QtGui.QVBoxLayout()
        self.main_layout.addLayout(self.cred_layout)
        self.main_layout.addWidget(QtGui.QLabel(url))
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
        box = QtGui.QLineEdit()
        box.setEchoMode(QtGui.QLineEdit.Password)
        return box

    def setAuthMethodsList(self, methods):
        self.auth_methods.clear()
        self.auth_methods.addItems(methods)
        self.default_auth_method = methods[0]

    def setAuthMethod(self, method):
        self.auth_methods.setCurrentIndex(
            self.auth_methods.findText(method, QtCore.Qt.MatchExactly)
            )

    def method_chosen(self, idx):
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
            layout = QtGui.QHBoxLayout()
            data.get('label').show()
            data.get('widget').show()
            layout.addWidget(data.get('label'))
            layout.addWidget(data.get('widget'))
            self.cred_layout.addLayout(layout)

    def getCred(self):
        cred_tmp = self.cred_inputs.get(self.current_auth_method)
        return {x:y.get('widget').text() for x,y in cred_tmp.items()}

class MGUI(QtGui.QWidget):

    def __init__(self):
        super().__init__()
        self.init_ui()

        self.wcs = {}

        ### Dialogs ####################
        # service_url
        self.d_service_url = QtGui.QInputDialog(self)
        self.d_service_url.setLabelText("Service URL:")
        self.d_service_url.setComboBoxItems(
            ["https://mach2.see.ed.ac.uk/machination/hierarchy",
             "--new--"]
            )
        # credentials

    def menu_service_connect(self):
        '''Handler for Service.connect menu item
        '''
        ok = self.d_service_url.exec_()
        if ok:
            self.connect_to_service(self.d_service_url.textValue())

    def connect_to_service(self, url):
        '''Connect to a machination hierarchy service.
        '''
        d = CredentialsDialog(self, url)
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

    def init_ui(self):
#        self.model = QtGui.QFileSystemModel()
#        self.model.setRootPath('/')

        self.model = HModel()

        # The main layout
        self.vbox = QtGui.QVBoxLayout(self)
        self.setLayout(self.vbox)

        # Menus
        self.menubar = QtGui.QMenuBar()
        self.layout().setMenuBar(self.menubar)

        # Service menu
        self.service_menu = QtGui.QMenu("&Service", self)
        self.menubar.addMenu(self.service_menu)
        # Connect to a new service
        action = self.service_menu.addAction(
            "connect...",
            self.menu_service_connect
            )


        self.wtitle = QtGui.QLabel()
        self.wtitle.setText("Workers")
        # Generate worker buttons
        # FIXME: Automate getting a worker list
        self.wbbox = QtGui.QVBoxLayout()
        #self.wbbox.addWidget(self.wtitle)
        self.wkb = QtGui.QButtonGroup()
        wkrs = {1: "New",
                2: "Environment",
                3: "Fetcher",
                4: "Firewall",
                5: "Packageman",
                6: "Shortcut",
                7: "Time",
                8: "Usergroup"}
        for wkr in wkrs:
            b = QtGui.QPushButton(wkrs[wkr])
            b.setCheckable(True)
            self.wkb.addButton(b, wkr)
            self.wbbox.addWidget(b)

        self.wkb.buttonClicked.connect(self.worker_button_clicked)

        self.librarylist = QtGui.QListWidget()
        sPol = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                                 QtGui.QSizePolicy.Expanding)
        self.librarylist.setSizePolicy(sPol)
        self.librarylist.itemSelectionChanged.connect(self.worker_list_changed)
        self.hbox = QtGui.QHBoxLayout(self)
        self.vbox.addLayout(self.hbox)
        self.view = QtGui.QTreeView()
        self.hbox.addWidget(self.view)
        self.view.setModel(self.model)
        self.view.expanded.connect(self.model.on_expand)
        # TODO: hide these after coding/debugging is finished
#        self.view.hideColumn(1)
#        self.view.hideColumn(2)
        self.view.sizePolicy().setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        self.view.sizePolicy().setHorizontalStretch(1)
        self.view.resize(self.view.sizeHint())
        self.hbox.addLayout(self.wbbox)
        self.hbox.addWidget(self.librarylist)
#        self.setLayout(self.hbox)
        self.contents = QtGui.QVBoxLayout(self)
        self.hbox.addLayout(self.contents)
        self.cframe = QtGui.QFrame(self)
        sPol = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                 QtGui.QSizePolicy.Expanding)
        sPol.setHorizontalStretch(0)
        sPol.setVerticalStretch(0)
        self.cframe.setSizePolicy(sPol)
        self.cframe.setFrameShape(QtGui.QFrame.StyledPanel)
        self.cframe.setFrameShadow(QtGui.QFrame.Sunken)
        self.contents.addWidget(self.cframe)
        self.ctitle = QtGui.QLabel(self.cframe)
        self.ctitle.setText("Please Select a Worker")

        self.setGeometry(300, 300, 1080, 520)
        self.setWindowTitle('Machination GUI')
        self.show()

    def worker_button_clicked(self):
        btn = self.wkb.checkedButton()
        self.librarylist.clear()
        if btn.text() == "New":
            self.addnew = True
            self.librarylist.addItem("Environment")
            self.librarylist.addItem("Fetcher")
            self.librarylist.addItem("Firewall")
            self.librarylist.addItem("Packageman")
            self.librarylist.addItem("Shortcut")
            self.librarylist.addItem("Time")
            self.librarylist.addItem("Usergroup")
        else:
            self.addnew = False
            for li in self.get_li(btn.text()):
                self.librarylist.addItem(li["Name"])

    def worker_list_changed(self):
        itm = self.librarylist.selectedItems()
        if itm is None:
            #Clear contents of c_frame except buttons
            pass
        elif self.addnew == True:
            #Display entry fields
            pass
        else:
            #Display info fields
            pass

    def refresh_type_info(self):
        self.type_info = self.wc.call('TypeInfo')

class WCProxy(WebClient):

    def get_object(self, type_id, obj_id):
        # Create obj_map if it doesn't exist
        try:
            obj_map = self.obj_map
        except AttributeError:
            self.obj_map = obj_map = {}
        index = '{},{}'.format(type_id, obj_id)

        # Find any object in the map
        obj = obj_map.get(index)

        # Get object if not in map
        if obj is None:
            obj = HObject(self, type_id, obj_id)
            obj_map[index] = obj

        return obj

class HObject(object):

    def __init__(self, wcp, type_id = None, obj_id = None):
        self.wcp = wcp
        # lastsync needs to be before any possible modifications
        self.lastsync = 0
        self.type_id = type_id
        self.obj_id = obj_id
        if self.type_id and self.obj_id:
            self.sync()

    data_changed = QtCore.pyqtSignal()

    # Not sure if we want this method...
    def set_data(self, data, timestamp = None):
        if timestamp is None:
            timestamp = time.time()
        self.lastsync = timestamp
        self.data = data
        # TODO(colin) emit signal

    def sync(self, changes = None, timestamp = None):
        '''Check lastsync against server changes and sync if necessary.

        changes should be in the form:
        {
         # all objects
         'changetype': 'add' | 'remove' | 'update',
         'fields': {field_name: field_value, ...},
         # containers
         'contents': [
           {'id': oid, 'type_id': tid, 'name': oname, 'changetype': ct},
           ...
         ]
         'attachments': [
           {'id': oid, 'type_id': tid, 'name': oname, 'channel': c,
           'changetype': ct},
           ...
         ]
        '''
        if timestamp is None:
            timestamp = time.time()
        if not changes:
            changes = self.wcp.call(
                'ChangesSince',
                self.type_id,
                self.obj_id,
                self.lastsync
                )
        self.lastsync = timestamp

        if not changes: return

        # Sync any changes.
        self._sync_obj(changes, timestamp)

        # Something has changed, we'd better tell anyone who is
        # interested.
        self.data_changed.emit()

    def _sync_obj(self, changes, timestamp):
        '''Changes in the form:

        {
         'changetype': 'add' | 'remove' | 'update',
         'fields': {field_name: field_value, ... }
        }

        changetype indicates whether the object has been added,
        updated or removed since the last sync time. The type 'remove'
        should never be passed to this method, object removals are
        handled by deleting the appropriate HObject.
        '''
        if changes.get('changetype') == 'remove':
            raise AttributeError(
                '_sync_obj should never be called with remove change type'
                )
        self.lastsync = timestamp
        self.data = copy.copy(changes.get('fields'))

class HContainer(HObject):
    '''Data structure representing hcs

    self.data as HObject
    self.contents as {
      ord1: hitem1,
      ord2: hitem2,
      ...
    }
    self.attachments same form as self.contents
    '''

    def _sync_obj(self, changes, timestamp):
        '''Changes in the form:

        {
         'changetype': 'add' | 'remove' | 'update',
         'fields': {field_name: field_value, ... },
         'contents': {
           'remove' : [
             {
               'type_id': tid,
               'id': oid,
               'ordinal': ord,
             },
             ...
           ],
           'move': [
             {
               'type_id': tid,
               'id': oid,
               'old_ordinal': ord,
               'new_ordinal': ord,
             },
             ...
           ],
           'add' : [
             {
               'type_id': tid,
               'id': oid,
               'ordinal': ord,
             },
             ...
           ],
         ],
         'attachments': same form as contents
        }
        '''
        # Call _sync_obj from HObject to capture changes to data
        super()._sync_obj(changes, timestamp)

        # Apply changes to contents
        self.apply_collection_changes(self.contents, changes)

        # Apply changes to attachments
        self.apply_collection_changes(self.attachments, changes)

    def apply_collection_changes(self, col, changes):

        # Removes.
        for change in changes.get('remove', []):
            del col[change.get('ordinal')]

        # Moves.
        for change in changes.get('move', []):
            oldord = change.get('old_ordinal')
            item = col.get(oldord)
            del col[oldord]
            col[change.get('new_ordinal')] = item

        # Adds.
        for change in changes.get('add', []):
            col[change.get('new_ordinal')] = self.wcp.get_object(change.get('type_id'), change.get('id'))

class HModel(QtGui.QStandardItemModel):
    '''Model Machination hierarchy for QTreeView
    '''

    def __init__(self, wc = None):
        super().__init__(0,3)
        self.wcs = {}
        if wc is not None:
            self.add_service(wc)

        self.setHorizontalHeaderLabels(['name','type','id'])

    def add_service(self, wc):
        '''Add a new service at the root of the tree.'''
        self.wcs[wc.url] = wc
        name_index = self.add_object(
            self.invisibleRootItem(),
            {'name': wc.url,
             'type': 'machination:hc',
             'id': '0',
             },
            wc = wc
            )
        self.itemFromIndex(name_index).setEditable(False)

    def add_object(self, parent, obj, wc=None, get_children=True):
        '''Add an object to parent in tree'''
        if not isinstance(parent, QtGui.QStandardItem):
            # Assume parent is an index
            parent = self.itemFromIndex(parent)

        name_item = QtGui.QStandardItem(obj.get('name'))
        parent.appendRow(
            [
                name_item,
                QtGui.QStandardItem(obj.get('type')),
                QtGui.QStandardItem(obj.get('id')),
                ]
            )
        if obj.get('type') == 'machination:hc' and get_children:
            if wc is None:
                wc = self.get_wc(name_item)
            contents = wc.call(
                'ListContents', self.get_path(name_item)
                )
            for newobj in contents:
                self.add_object(name_item, newobj, wc=wc, get_children=False)
        return self.indexFromItem(name_item)

    def get_wc(self, thing):
        '''Find the webclient for an item or index'''
        obj_path = self.get_obj_path(thing)
        return self.wcs.get(obj_path[0].text())

    def get_obj_path(self, thing):
        '''Return list of StandardItem objects from index or item to root.'''
        if isinstance(thing, QtGui.QStandardItem):
            index = thing.index()
        else:
            index = thing

        if not index.isValid():
            return []

        path =  self.get_obj_path(index.parent())
        path.append(self.itemFromIndex(index))
        return path

    def get_path(self, thing):
        '''Return a string path to an index or StandardItem'''
        obj_path = self.get_obj_path(thing)
        path = ['']
        for obj in obj_path[1:]:
            path.append(obj.text())
        if len(path) == 1:
            return '/'
        return '/'.join(path)

    def on_expand(self, index):
        '''Slot for 'expanded' signal.'''
        self.refresh(index)

    def refresh(self, index):
        '''Refresh a node from the hierarchy'''
        print('refreshing {}'.format(self.get_path(index)))
        self.removeRows(0,self.rowCount(index),index)
        wc = self.get_wc(index)
        contents = wc.call(
            'ListContents', self.get_path(index)
            )
        for newobj in contents:
            self.add_object(index, newobj, wc=wc)

# Later we'll make a better model based on QAbstractItemModel. Right
# now, see HModel -- based on QStandardItemModel
class HierarchyModel(QtCore.QAbstractItemModel):

    def __init__(self, parent = None, wcp = None):
        super().__init__(parent = parent)
        if wcp is not None: self.setwcp(wcp)

    def setwcp(self, wcp):
        self.wcp = wcp

    def index(self, row, column, parent):
        pass

class FakeWc(object):
    '''Pretend to be a WebClient connected to a hierarchy

    For debugging purposes'''

    def __init__(self, lastchanged = None):
        self.lastchanged = lastchanged
        if self.lastchanged is None:
            self.lastchanged = time.time()
        self.type_info = {
            'machination:hc': {'name': 'hc'},
            '1': {'name': 'set'},
            '2': {'name': 'os_instance'}
            }
        self.data = {
            'machination:hc': {
                '1': {
                    'lastchanged': self.lastchanged,
                    'contents': [
                        ['machination:hc', '2'],
                        ['1', '1'],
                        ['2', '1']
                        ],
                    'attachments': [],
                    'fields': {
                        'name': 'machination:root'
                        }
                    },
                '2': {
                    'lastchanged': self.lastchanged,
                    'contents': [],
                    'attachments': [],
                    'fields': {
                        'name': 'system'
                        }
                    }
                },
            '1': {
                '1': {
                    'lastchanged': self.lastchanged,
                    'fields': {
                        'name': 'universal'
                        },
                    },
                },
            '2': {
                '1': {
                    'lastchanged': self.lastchanged,
                    'fields': {
                        'name': 'win7-test1'
                        },
                    },
                }
            }

    def call(self, fname, *args):
        return getattr(self, '_' + fname)(*args)

    def _GetObject(self, tid, oid):
        oftype = self.data.get(str(tid))
        if oftype is None: return None
        return oftype.get(str(oid))

    def _LastChanged(self, tid, oid):
        obj = self._GetObject(tid, oid)
        if obj: return obj.get('lastchanged')
        return None

    def _ChangesSince(self, tid, oid, tstamp,
                      contents = True,
                      attachments = True):
        obj = self._getObject(tid, oid)
        if obj is None: return []
        obj['id'] = oid
        obj['type_id'] = tid
        if tid == 'machination:hc':
            changed = False
            new = {
                    'id': oid,
                    'type_id': tid,
                    'contents': [],
                    'attachments': []
                    }
            if obj.get('lastchanged') < tstamp:
                new['fields'] = copy.copy(obj.get('fields'))
                changed = True
            if contents:
                for thing in obj.get('contents'):
                    newthing = self._ChangesSince(
                        thin.get('type_id')
                        )

        else:
            if obj.get('lastchanged') < tstamp:
                return copy.deepcopy(obj)

        # No changes.
        return None

def main():
    app = QtGui.QApplication(sys.argv)
    ex = MGUI()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()



