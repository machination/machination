import sys
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

class HItem(object):

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
        '''Check lastsync against server changes and sync if necessary'''
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
        if self.obj_type_id == 'machination:hc':
            _sync_hc(changes)
        else:
            _sync_obj(changes)
        self.data_changed.emit()

    def _sync_obj(self, changes):
        pass

    def _sync_hc(self, changes):
        pass

class HierarchyModel(QtCore.QAbstractItemModel):

    def __init__(self, parent = None):
        super().__init__(parent = parent)

class FakeWc(object):
    '''Pretend to be a WebClient connected to a hierarchy

    For debugging purposes'''

    def __init__(self):
        self.type_info = {
            'machination:hc': {'name': 'hc'},
            '1': {'name': 'set'},
            '2': {'name': 'os_instance'}
            }
        self.data = {
            'machination:hc': {
                '1': {
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
                    'contents': [],
                    'attachments': [],
                    'fields': {
                        'name': 'system'
                        }
                    }
                },
            '1': {
                '1': {
                    'name': 'universal'
                    },
                },
            '2': {
                '1': {
                    'name': 'win7-test1'
                    }
                }
            }

    def call(self, fname, *args):
        return getattr(self, '_' + fname)(*args)

    def _GetObject(self, tid, oid):
        print(self)
        print('{} {}'.format(tid, oid))
        oftype = self.data.get(str(tid))
        if oftype is None: return None
        return oftype.get(str(oid))


def main():
    app = QtGui.QApplication(sys.argv)
    ex = MGUI()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()



