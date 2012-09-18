import sys
import time
import copy
from PyQt4 import QtGui
from PyQt4 import QtCore
#from machination.webclient import WebClient

class MGUI(QtGui.QWidget):

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.model = QtGui.QFileSystemModel()
        self.model.setRootPath('/')

        self.hmodel = HierarchyModel()

        self.hbox = QtGui.QHBoxLayout(self)
        self.view = QtGui.QTreeView()
        self.hbox.addWidget(self.view)
        self.view.setModel(self.model)
        self.view.sizePolicy().setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
        self.view.sizePolicy().setHorizontalStretch(1)
        self.view.resize(self.view.sizeHint())

        self.setLayout(self.hbox)

        self.setGeometry(300, 300, 600, 400)
        self.setWindowTitle('Machination GUI')
        self.show()

    def refresh_type_info(self):
        self.type_info = self.wc.call('TypeInfo')

class HObject(object):

    def __init__(self, wc, obj_type_id = None, obj_id = None):
        self.wc = wc
        # lastsync needs to be before any possible modifications
        self.lastsync = 0
        self.obj_type_id = obj_type_id
        self.obj_id = obj_id
        if self.obj_type_id and self.obj_id:
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
            changes = wc.call(
                'ChangesSince',
                self.obj_type_id,
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
        self.data = changes.get('fields')

class HContainer(HItem):

    def _sync_obj(self, changes, timestamp):
        '''Changes in the form:

        {
         'changetype': 'add' | 'remove' | 'update',
         'fields': {field_name: field_value, ... },
         'contents': [
           {
             'type_id': tid,
             'id': oid,
             'changetype': 'addafter' | 'moveafter' | 'remove',
             'old_ordinal': ord,
             'new_ordinal': ord
           },
           ...
         ],
         'attachments': [
           {
             'type_id': tid,
             'id': oid,
             'changetype': 'addafter' | 'moveafter' | 'remove',
             'old_ordinal': ord,
             'new_ordinal': ord
           },
           ...
         ]
        }
        '''
        # Call _sync_obj from HObject to capture changes to data
        super()._sync_obj(changes, timestamp)

        # Apply changes to contents

        # Apply changes to contents


class HierarchyModel(QtCore.QAbstractItemModel):

    def __init__(self, parent = None):
        super().__init__(parent = parent)

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



