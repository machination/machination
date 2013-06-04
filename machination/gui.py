#! /usr/bin/python3

#Force sip to use API version 2. Should just work on Python3, but let's not
#take any chances
import sip
sip.setapi("QString",2)
sip.setapi("QVariant",2)

import sys
import time
import copy
import functools
import os
import context
from lxml import etree
from PyQt4 import QtGui
from PyQt4 import QtCore
from machination.webclient import WebClient
from collections import OrderedDict

class CredentialsDialog(QtGui.QDialog):
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
        '''Make a QLineEdit widget with the 'Password' echo mode.'''
        box = QtGui.QLineEdit()
        box.setEchoMode(QtGui.QLineEdit.Password)
        return box

    def setAuthMethodsList(self, methods):
        '''Set the list of authentication methods to choose from.'''
        self.auth_methods.clear()
        self.auth_methods.addItems(methods)
        self.default_auth_method = methods[0]

    def setAuthMethod(self, method):
        '''Set the current choice of authentication method.'''
        self.auth_methods.setCurrentIndex(
            self.auth_methods.findText(method, QtCore.Qt.MatchExactly)
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
            layout = QtGui.QHBoxLayout()
            data.get('label').show()
            data.get('widget').show()
            layout.addWidget(data.get('label'))
            layout.addWidget(data.get('widget'))
            self.cred_layout.addLayout(layout)

    def getCred(self):
        '''Get the captured credentials for the current authentication method.'''
        cred_tmp = self.cred_inputs.get(self.current_auth_method)
        return {x:y.get('widget').text() for x,y in cred_tmp.items()}

class MGUI(QtGui.QWidget):

    def __init__(self):
        super().__init__()
        self.init_ui()

        self.wcs = {}

        QtCore.QDir.addSearchPath("icons","")
        print(QtCore.QDir.searchPaths("icons"))

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
        self.view.setIconSize(QtCore.QSize(22,22))
        self.hbox.addWidget(self.view)
        self.view.setModel(self.model)
        self.view.expanded.connect(self.model.on_expand)
        # TODO: hide these after coding/debugging is finished
        self.view.hideColumn(1)
        self.view.hideColumn(2)
        self.view.hideColumn(3)
#        self.view.hideColumn(4)
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

class HModel(QtGui.QStandardItemModel):
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
        return QtGui.QIcon(os.path.join(context.resources_dir(),'{}.svg'.format(name)))

    def add_object(self, parent, obj, wc=None,
                   peek_children=True):
        '''Add an object to parent in tree'''
        if not isinstance(parent, QtGui.QStandardItem):
            # Assume parent is an index
            parent = self.itemFromIndex(parent)
        if wc is None:
            wc = self.get_wc(parent)

        name_item = QtGui.QStandardItem(obj.get('name'))
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
            QtGui.QStandardItem(type_id),
            QtGui.QStandardItem(obj.get('obj_id')),
            QtGui.QStandardItem(obj.get('channel_id')),
            QtGui.QStandardItem(obj.get('__branch__')),
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
        if isinstance(thing, QtGui.QStandardItem):
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

def main():
    app = QtGui.QApplication(sys.argv)
    ex = MGUI()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()



