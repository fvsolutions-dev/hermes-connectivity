# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'manager_interface.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox, QHBoxLayout,
    QLineEdit, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(368, 515)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.connectLayout = QVBoxLayout()
        self.connectLayout.setObjectName(u"connectLayout")

        self.verticalLayout.addLayout(self.connectLayout)

        self.devicesGroupBox = QGroupBox(Form)
        self.devicesGroupBox.setObjectName(u"devicesGroupBox")
        self.verticalLayout_2 = QVBoxLayout(self.devicesGroupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")

        self.verticalLayout.addWidget(self.devicesGroupBox)

        self.discovery_group_box = QGroupBox(Form)
        self.discovery_group_box.setObjectName(u"discovery_group_box")
        self.verticalLayout_3 = QVBoxLayout(self.discovery_group_box)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(3, -1, 3, 3)
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.filter_lineedit = QLineEdit(self.discovery_group_box)
        self.filter_lineedit.setObjectName(u"filter_lineedit")

        self.horizontalLayout_2.addWidget(self.filter_lineedit)

        self.auto_init_checkbox = QCheckBox(self.discovery_group_box)
        self.auto_init_checkbox.setObjectName(u"auto_init_checkbox")

        self.horizontalLayout_2.addWidget(self.auto_init_checkbox)

        self.add_btn = QPushButton(self.discovery_group_box)
        self.add_btn.setObjectName(u"add_btn")

        self.horizontalLayout_2.addWidget(self.add_btn)


        self.verticalLayout_3.addLayout(self.horizontalLayout_2)


        self.verticalLayout.addWidget(self.discovery_group_box)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.devicesGroupBox.setTitle(QCoreApplication.translate("Form", u"Devices", None))
        self.discovery_group_box.setTitle(QCoreApplication.translate("Form", u"Discovery", None))
        self.filter_lineedit.setPlaceholderText(QCoreApplication.translate("Form", u"Filter Regex", None))
        self.auto_init_checkbox.setText(QCoreApplication.translate("Form", u"Auto init", None))
        self.add_btn.setText(QCoreApplication.translate("Form", u"Add", None))
    # retranslateUi

