"""
SpectraViewWidget is a Qt4 Widget for displaying a spectra either in terms of signal or signal to noise
it expects to be given the wavelenght, flux, and sn arrays for the data
"""
import numpy as np
from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QTAgg
from saltgui import MplCanvas
from InterIdentify import ArcDisplay


class SpectraViewWidget(QtWidgets.QWidget):
   def __init__(self, warr, farr, snarr, name='', y1=1010, y2=1030, hmin=150, wmin=400, smooth=5, parent=None):
       super(SpectraViewWidget, self).__init__(parent)

       self.y1=y1
       self.y2=y2
       self.smooth = smooth
       self.name=name

       #set up the arc display 
       self.arcfigure=MplCanvas()

       # Add central axes instance
       self.axes = self.arcfigure.figure.add_subplot(111)

       #set up the variables
       self.loaddata(warr, farr, snarr, name)

       #force a re-draw
       self.redraw_canvas()

       # Add navigation toolbars for each widget to enable zooming
       self.toolbar=NavigationToolbar2QTAgg(self.arcfigure,self)

       #set up the information panel
       self.infopanel=QtWidgets.QWidget()

       #add the name of the file
       self.NameLabel = QtWidgets.QLabel("Filename:")
       self.NameLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised )
       self.NameValueLabel = QtWidgets.QLabel(self.name)
       self.NameValueLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken )

       #add extraction window

       self.y1Label = QtWidgets.QLabel("y1:")
       self.y1Label.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised )
       self.y1ValueLabel = QtWidgets.QLineEdit(str(self.y1))
       self.y2Label = QtWidgets.QLabel("y2:")
       self.y2Label.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised )
       self.y2ValueLabel = QtWidgets.QLineEdit(str(self.y2))
       self.apButton = QtWidgets.QPushButton('Extract')
       self.apButton.clicked.connect(self.extractspectra)

       #add default button
       self.defaultBox = QtWidgets.QCheckBox('Use values as default')
       self.defaultBox.stateChanged.connect(self.updatedefaults)
 
       #add smoothing
       self.smoothLabel = QtWidgets.QLabel("Smooth")
       self.smoothLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised )
       self.smoothValueLabel = QtWidgets.QLineEdit(str(self.smooth))
       self.smoothValueLabel.textChanged.connect(self.updatesmooth)

       #set up the info panel layout
       infoLayout=QtWidgets.QGridLayout(self.infopanel)
       infoLayout.addWidget(self.NameLabel, 0, 0, 1, 1)
       infoLayout.addWidget(self.NameValueLabel, 0, 1, 1, 5)
       infoLayout.addWidget(self.y1Label, 1, 0, 1, 1)
       infoLayout.addWidget(self.y1ValueLabel, 1, 1, 1, 1)
       infoLayout.addWidget(self.y2Label, 1, 2, 1, 1)
       infoLayout.addWidget(self.y2ValueLabel, 1, 3, 1, 1)
       infoLayout.addWidget(self.apButton, 1, 4, 1, 1)
       infoLayout.addWidget(self.defaultBox, 2, 0, 1, 2)
       infoLayout.addWidget(self.smoothLabel, 2, 2, 1, 1)
       infoLayout.addWidget(self.smoothValueLabel, 2, 3, 1, 1)

       # Set up the layout
       mainLayout = QtWidgets.QVBoxLayout()
       mainLayout.addWidget(self.arcfigure)
       mainLayout.addWidget(self.toolbar)
       mainLayout.addWidget(self.infopanel)
       self.setLayout(mainLayout)

   def updatedefaults(self):
       print self.defaultBox.checkState()
       return

   def updatesmooth(self):
       try:
          self.smooth = int(self.smoothValueLabel.text())
       except ValueError:
          return
       print self.smooth
       self.redraw_canvas()
 
   def updatename(self, name):
       self.name=name
       self.NameValueLabel.setText(self.name)
       print self.name

   def updaterange(self, y1, y2):
       self.y1=y1
       self.y2=y2
       self.y1ValueLabel.setText(str(self.y1))
       self.y2ValueLabel.setText(str(self.y2))

   def extractspectra(self):
       y1=int(self.y1ValueLabel.text())
       y2=int(self.y2ValueLabel.text())
       print self.name
       self.emit(QtCore.SIGNAL("updateextract(int, int)"), y1,y2)

   def loaddata(self, warr, farr, snarr, name=''):
       print "Loading data"
       self.warr=warr
       self.farr=farr
       self.snarr=snarr
       self.name=name
       return

   def plotSpectra(self):
       if self.smooth > 0 and self.farr is not None:
           farr = np.convolve(self.farr, np.ones(self.smooth), mode='same')/self.smooth
       else:
           farr = self.farr
       self.splot=self.axes.plot(self.warr, farr, linewidth=0.5,linestyle='-',
                                marker='None',color='b')

   def redraw_canvas(self,keepzoom=False):
       if keepzoom:
            # Store current zoom level
            xmin, xmax = self.axes.get_xlim()
            ymin, ymax = self.axes.get_ylim()

       # Clear plot
       self.axes.clear()

       # Draw image
       self.plotSpectra()

       # Restore zoom level
       if keepzoom:
           self.axes.set_xlim((self.xmin,self.xmax))
           self.axes.set_ylim((self.ymin,self.ymax))

       # Force redraw
       self.arcfigure.draw()

