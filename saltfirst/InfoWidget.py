"""
InfoWidget is a Qt4 Widget for displaying information about an image
"""
from PyQt5 import QtGui, QtCore, QtWidgets
from ObsLogWidget import headerList, printList
from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout, QFrame, QVBoxLayout


class InfoWidget(QWidget):
   def __init__(self, name, imlist, parent=None):
        super(InfoWidget, self).__init__(parent)
        self.imlist=imlist
        #set up the information panel
        self.infopanel=QWidget()

        #add the name of the file
        self.NameLabel = QLabel("Filename:")
        self.NameLabel.setFrameStyle(QFrame.Panel | QFrame.Raised )
        self.NameValueLabel = QLabel("%s" % name)
        self.NameValueLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken )

        #add target and proposal information

        #set up the info panel layout
        infoLayout=QGridLayout(self.infopanel)
        infoLayout.addWidget(self.NameLabel, 0, 0, 1, 1)
        infoLayout.addWidget(self.NameValueLabel, 0, 1, 1, 1)

        #add all teh other fields
        self.ValueList=[]
        for i, k in enumerate(headerList[1:]):
            Label = QLabel("%s:" % k)
            Label.setFrameStyle(QFrame.Panel | QFrame.Raised )
            ValueLabel = QLabel("%s" % self.getitem(k))
            ValueLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken )
            infoLayout.addWidget(Label, i+1, 0, 1, 1)
            infoLayout.addWidget(ValueLabel, i+1, 1, 1, 1)
            self.ValueList.append(ValueLabel)


        # Set up the layout
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.infopanel)
        self.setLayout(mainLayout)


   def update(self, name, imlist):
       self.imlist=imlist
       self.NameValueLabel.setText(name)
       for i, k in enumerate(headerList[1:]):
           self.ValueList[i].setText("%s" % self.getitem(k))

   def getitem(self, key):
       i=headerList.index(key)
       try:
           value=str(self.imlist[i])
       except IndexError:
           value=''
       return value

