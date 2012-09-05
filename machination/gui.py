import sys
from PyQt4 import QtGui
from PyQt4 import QtCore

class MGUI(QtGui.QMainWindow):

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.model = QtGui.QFileSystemModel()
        self.model.setRootPath('/')
        self.view = QtGui.QTreeView(self)
        self.view.setModel(self.model)
        self.view.resize(self.view.sizeHint())

        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle('Machination GUI')
        self.show()

def main():
    app = QtGui.QApplication(sys.argv)
    ex = MGUI()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()



