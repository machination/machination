# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'machgui.ui'
#
# Created: Wed Nov  7 15:45:02 2012
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(1085, 520)
        
        self.addnew = False
        
        self.wkb = QtGui.QButtonGroup()
        self.wkb.buttonClicked.connect(self.worker_button_clicked)
        
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.horizontalLayoutWidget = QtGui.QWidget(self.centralwidget)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(0, 8, 1081, 461))
        self.horizontalLayoutWidget.setObjectName(_fromUtf8("horizontalLayoutWidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.treeView = QtGui.QTreeView(self.horizontalLayoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeView.sizePolicy().hasHeightForWidth())
        self.treeView.setSizePolicy(sizePolicy)
        self.treeView.setObjectName(_fromUtf8("treeView"))
        self.horizontalLayout.addWidget(self.treeView)
        self.vbox = QtGui.QVBoxLayout()
        self.vbox.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.vbox.setObjectName(_fromUtf8("vbox"))
        
        self.b_new = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.b_new.setCheckable(True)
        self.b_new.setObjectName(_fromUtf8("b_new"))
        self.wkb.addButton(b_new)
        self.vbox.addWidget(self.b_new)
        self.b_environment = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.b_environment.setCheckable(True)
        self.b_environment.setObjectName(_fromUtf8("b_environment"))
        self.wkb.addButton(b_environment)
        self.vbox.addWidget(self.b_environment)
        self.b_fetcher = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.b_fetcher.setCheckable(True)
        self.b_fetcher.setObjectName(_fromUtf8("b_fetcher"))
        self.wkb.addButton(b_fetcher)
        self.vbox.addWidget(self.b_fetcher)
        self.b_firewall = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.b_firewall.setCheckable(True)
        self.b_firewall.setObjectName(_fromUtf8("b_firewall"))
        self.wkb.addButton(b_firewall)
        self.vbox.addWidget(self.b_firewall)
        self.b_packageman = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.b_packageman.setCheckable(True)
        self.b_packageman.setObjectName(_fromUtf8("b_packageman"))
        self.wkb.addButton(b_packageman)
        self.vbox.addWidget(self.b_packageman)
        self.b_shortcut = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.b_shortcut.setCheckable(True)
        self.b_shortcut.setObjectName(_fromUtf8("b_shortcut"))
        self.wkb.addButton(b_shortcut)
        self.vbox.addWidget(self.b_shortcut)
        self.b_time = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.b_time.setCheckable(True)
        self.b_time.setObjectName(_fromUtf8("b_time"))
        self.wkb.addButton(b_time)
        self.vbox.addWidget(self.b_time)
        self.b_usergroup = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.b_usergroup.setCheckable(True)
        self.b_usergroup.setObjectName(_fromUtf8("b_usergroup"))
        self.wkb.addButton(b_usergroup)
        self.b_usergroup.buttonClicked.connect(self.worker_button_clicked)
        self.vbox.addWidget(self.b_usergroup)
        self.horizontalLayout.addLayout(self.vbox)
        self.wk_list = QtGui.QListWidget(self.horizontalLayoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.wk_list.sizePolicy().hasHeightForWidth())
        self.wk_list.setSizePolicy(sizePolicy)
        self.wk_list.setObjectName(_fromUtf8("wk_list"))
        self.wk_list.itemSelectionChanged.connect(self.worker_list_changed)
        self.horizontalLayout.addWidget(self.wk_list)
        self.c_frame = QtGui.QFrame(self.horizontalLayoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.c_frame.sizePolicy().hasHeightForWidth())
        self.c_frame.setSizePolicy(sizePolicy)
        self.c_frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.c_frame.setFrameShadow(QtGui.QFrame.Sunken)
        self.c_frame.setObjectName(_fromUtf8("c_frame"))
        self.wkr_buttons = QtGui.QDialogButtonBox(self.c_frame)
        self.wkr_buttons.setGeometry(QtCore.QRect(230, 420, 176, 27))
        self.wkr_buttons.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.wkr_buttons.setObjectName(_fromUtf8("wkr_buttons"))
        self.horizontalLayout.addWidget(self.c_frame)
        MainWindow.setCentralWidget(self.centralwidget)
        #self.menubar = QtGui.QMenuBar(MainWindow)
        #self.menubar.setGeometry(QtCore.QRect(0, 0, 1085, 29))
        #self.menubar.setObjectName(_fromUtf8("menubar"))
        #MainWindow.setMenuBar(self.menubar)
        #self.statusbar = QtGui.QStatusBar(MainWindow)
        #self.statusbar.setObjectName(_fromUtf8("statusbar"))
        #MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.wkr_buttons, QtCore.SIGNAL("accepted()"), MainWindow.accept)
        QtCore.QObject.connect(self.wkr_buttons, QtCore.SIGNAL("rejected()"), MainWindow.reject)
        
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
    def worker_button_clicked(self):
        btn = self.wkb.checkedButton()
        self.wk_list.clear()
        if btn.text() == "New":
            self.addnew = True
            self.wk_list.addItem("Environment")
            self.wk_list.addItem("Fetcher")
            self.wk_list.addItem("Firewall")
            self.wk_list.addItem("Packageman")
            self.wk_list.addItem("Shortcut")
            self.wk_list.addItem("Time")
            self.wk_list.addItem("Usergroup")
        else:
            self.addnew = False
            for li in self.get_li(btn.text()):
                self.wk_list.addItem(li["Name"])

    def worker_list_changed(self):
        itm = self.wk_list.selectedItems()
        if itm is None:
            #Clear contents of c_frame except buttons
            pass
        elif self.addnew == True:
            #Display entry fields
            pass
        else:
            #Display info fields
            pass


    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Machination GUI", None, QtGui.QApplication.UnicodeUTF8))
        self.b_new.setText(QtGui.QApplication.translate("MainWindow", "New", None, QtGui.QApplication.UnicodeUTF8))
        self.b_environment.setText(QtGui.QApplication.translate("MainWindow", "Environment", None, QtGui.QApplication.UnicodeUTF8))
        self.b_fetcher.setText(QtGui.QApplication.translate("MainWindow", "Fetcher", None, QtGui.QApplication.UnicodeUTF8))
        self.b_firewall.setText(QtGui.QApplication.translate("MainWindow", "Firewall", None, QtGui.QApplication.UnicodeUTF8))
        self.b_packageman.setText(QtGui.QApplication.translate("MainWindow", "Packages", None, QtGui.QApplication.UnicodeUTF8))
        self.b_shortcut.setText(QtGui.QApplication.translate("MainWindow", "Shortcut", None, QtGui.QApplication.UnicodeUTF8))
        self.b_time.setText(QtGui.QApplication.translate("MainWindow", "Time", None, QtGui.QApplication.UnicodeUTF8))
        self.b_usergroup.setText(QtGui.QApplication.translate("MainWindow", "Users and Groups", None, QtGui.QApplication.UnicodeUTF8))

