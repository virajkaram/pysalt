"""
DQWidget is a Qt4 Widget for displaying information about the data quality 
of an image
"""
import numpy as np 
import pyfits

from PyQt5 import QtWidgets, QtCore
from ObsLogWidget import headerList, printList

from saltstat import iterstat


#import plugins
from rssinfo import rssinfo
from seeing import seeing_stats, airmass

class DQWidget(QtWidgets.QWidget):
   def __init__(self, name, imlist, parent=None):
       super(DQWidget, self).__init__(parent)
       self.imlist=imlist
       self.name=name
       #set up the information panel
       self.infopanel=QtWidgets.QWidget()
       self.infopanel.setFixedHeight(50)
 
       #set up some needed variables
       self.obsmode=self.getitem('OBSMODE')

       #add the name of the file
       self.NameLabel = QtWidgets.QLabel("Filename:")
       self.NameLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised )
       self.NameValueLabel = QtWidgets.QLabel("%s" % self.name)
       self.NameValueLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken )

       #set up the info panel layout
       infoLayout=QtWidgets.QGridLayout(self.infopanel)
       infoLayout.addWidget(self.NameLabel, 0, 0, 1, 1)
       infoLayout.addWidget(self.NameValueLabel, 0, 1, 1, 1)

       #set up the panel for the different modes
       if self.obsmode=='IMAGING':
          self.datapanel=self.set_imaging()
       elif self.obsmode=='SPECTROSCOPY': 
          self.datapanel=self.set_spectroscopy()
       else:
          self.datapanel=QtWidgets.QWidget()

       # Set up the layout
       mainLayout = QtWidgets.QVBoxLayout()
       mainLayout.addWidget(self.infopanel)
       mainLayout.addWidget(self.datapanel)
       self.setLayout(mainLayout)

   def updatetab(self, name, imlist):
       print "STRARTING UPDATE OF DQ"
       self.imlist=imlist
       self.name=name
       self.obsmode=self.getitem('OBSMODE')

       #add the name of the file
       self.NameValueLabel.setText(("%s" % self.name))
       self.NameValueLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken )

       #set up the panel for the different modes
       if self.obsmode=='IMAGING':
          self.datapanel=self.set_imaging()
       elif self.obsmode=='SPECTROSCOPY': 
          self.datapanel=self.set_spectroscopy()
       else:
          self.datapanel=QtWidgets.QWidget()

       # Set up the layout

       j=self.layout().indexOf(self.datapanel)
       print "INDEX", j
       self.layout().itemAt(1).widget().close()
       self.layout().insertWidget(1, self.datapanel)

   def set_datardx(self):
       """Set up the information from the data reduction

          number of cr clean
          bias levels removed
       """
            

   def set_spectroscopy(self):

       #set up the data panel
       datapanel=QtWidgets.QWidget()

       #get the infomration that you need about the image
       grating=self.getitem('GRATING').strip()
       slitname=self.getitem('MASKID').strip()
       graang=float(self.getitem('GR-ANGLE'))
       artang=float(self.getitem('AR-ANGLE'))
       xbin, ybin=self.getitem('CCDSUM').split()

       #get the information about the model
       wcen, w1, w2, res, R, slitsize=rssinfo(grating, graang, artang, slitname, xbin, ybin)
       print grating, slitname, graang, artang, xbin, ybin

       #Information to include in the data panel
       #central w, w1, w2, resolution, dw
       self.gratingLabel = QtWidgets.QLabel("Grating")
       self.gratingLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.graangLabel = QtWidgets.QLabel("GR-ANGLE")
       self.graangLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.artangLabel = QtWidgets.QLabel("AR-ANGLE")
       self.artangLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.slitnameLabel = QtWidgets.QLabel("SLIT")
       self.slitnameLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.slitsizeLabel = QtWidgets.QLabel("SIZE")
       self.slitsizeLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.gratingValueLabel = QtWidgets.QLabel(grating)
       self.gratingValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.graangValueLabel = QtWidgets.QLabel(u"%5.3f \u00B0" % graang)
       self.graangValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.artangValueLabel = QtWidgets.QLabel(u"%5.3f \u00B0" % artang)
       self.artangValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.slitnameValueLabel = QtWidgets.QLabel(slitname)
       self.slitnameValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.slitsizeValueLabel = QtWidgets.QLabel("%3.2f''" % slitsize)
       self.slitsizeValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)

       self.bluewaveLabel = QtWidgets.QLabel("Blue Edge")
       self.bluewaveLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.centwaveLabel = QtWidgets.QLabel("Center Wave")
       self.centwaveLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.redwaveLabel = QtWidgets.QLabel("Red Edge")
       self.redwaveLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.resolutionLabel = QtWidgets.QLabel("Resolution")
       self.resolutionLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.reselementLabel = QtWidgets.QLabel("Resolution element")
       self.reselementLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.bluewaveValueLabel = QtWidgets.QLabel(u"%7.2f \u00c5" % w1)
       self.bluewaveValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.centwaveValueLabel = QtWidgets.QLabel(u"%7.2f \u00c5" % wcen)
       self.centwaveValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.redwaveValueLabel = QtWidgets.QLabel(u"%7.2f \u00c5" % w2)
       self.redwaveValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.resolutionValueLabel = QtWidgets.QLabel("%5i" % R)
       self.resolutionValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.reselementValueLabel = QtWidgets.QLabel(u"%4.2f \u00c5" % res)
       self.reselementValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)

       #set up the signal to noise
       
       specfile='smbxp'+self.name.replace('fits', 'txt')
       try:
           w,f,s=np.loadtxt(specfile, usecols=(0,1,2), unpack=True)
           med_sn=np.median(s)
           try:
               s.sort()
               peak_sn=np.median(s[-100:])
           except:
               peak_sn=s.max()
       except:
          med_sn=0
          peak_sn=0

       self.snLabel = QtWidgets.QLabel("Median S/N")
       self.snLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Raised)
       self.snValueLabel = QtWidgets.QLabel("%5.2f" % med_sn)
       self.snValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.psnLabel = QtWidgets.QLabel("Median Peak S/N")
       self.psnLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Raised)
       self.psnValueLabel = QtWidgets.QLabel("%5.2f" % peak_sn)
       self.psnValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)

       #set the layout
       dataLayout=QtWidgets.QGridLayout(datapanel)
       dataLayout.addWidget(self.gratingLabel, 0, 0, 1, 1)
       dataLayout.addWidget(self.graangLabel, 0, 1, 1, 1)
       dataLayout.addWidget(self.artangLabel, 0, 2, 1, 1)
       dataLayout.addWidget(self.slitnameLabel, 0, 3, 1, 1)
       dataLayout.addWidget(self.slitsizeLabel, 0, 4, 1, 1)
       dataLayout.addWidget(self.gratingValueLabel, 1, 0, 1, 1)
       dataLayout.addWidget(self.graangValueLabel, 1, 1, 1, 1)
       dataLayout.addWidget(self.artangValueLabel, 1, 2, 1, 1)
       dataLayout.addWidget(self.slitnameValueLabel, 1, 3, 1, 1)
       dataLayout.addWidget(self.slitsizeValueLabel, 1, 4, 1, 1)
       dataLayout.addWidget(self.bluewaveLabel, 2, 0, 1, 1)
       dataLayout.addWidget(self.centwaveLabel, 2, 1, 1, 1)
       dataLayout.addWidget(self.redwaveLabel, 2, 2, 1, 1)
       dataLayout.addWidget(self.resolutionLabel, 2, 3, 1, 1)
       dataLayout.addWidget(self.reselementLabel, 2, 4, 1, 1)
       dataLayout.addWidget(self.bluewaveValueLabel, 3, 0, 1, 1)
       dataLayout.addWidget(self.centwaveValueLabel, 3, 1, 1, 1)
       dataLayout.addWidget(self.redwaveValueLabel, 3, 2, 1, 1)
       dataLayout.addWidget(self.resolutionValueLabel, 3, 3, 1, 1)
       dataLayout.addWidget(self.reselementValueLabel, 3, 4, 1, 1)
   
       dataLayout.addWidget(self.snLabel, 4, 0, 2, 3)
       dataLayout.addWidget(self.snValueLabel, 4, 3, 2, 2)
       dataLayout.addWidget(self.psnLabel, 6, 0, 2, 3)
       dataLayout.addWidget(self.psnValueLabel, 6, 3, 2, 2)

       datapanel.setFixedHeight(400)
       return datapanel

   def set_imaging(self):
       #set up the data panel
       datapanel=QtWidgets.QWidget()

       #get some variables from the data
       exptime=float(self.getitem('EXPTIME'))
       filtername=self.getitem('FILTER')
       telalt=float(self.getitem('TELALT'))
       ccdbin=float(self.getitem('CCDSUM').split()[0])
       print ccdbin
       pix_scale=0.14*ccdbin
       z=90-telalt 
       am=airmass(z)

       #determine the background
       try:
          bmean=float(self.getitem('BMEAN'))
          bmidpt=float(self.getitem('BMIDPT'))
          bstd=float(self.getitem('BSTD'))
       except Exception, e:
          outimg='mbxp'+self.name
          #hdu=pyfits.open(outimg)
          #bmean, bmidpt, bstd=iterstat(hdu[1].data, 5, 3)
          #hdu.close()
          bmean, bmidpt, bstd=(-1,-1,-1)

       #calculate the seeing
       try: 
          see=float(self.getitem('SEEING'))
          nsource=float(self.getitem('NSOURCES'))
       except Exception, e:
          outtxt='mbxp'+self.name.replace('fits', 'cat')
          try:
             mag_arr, fwhm_arr=np.loadtxt(outtxt, usecols=(2,10), unpack=True)
          except IOError:
             mag_arr=np.zeros([0])
             fwhm_arr=np.zeros([0])
          nsource=0 #len(mag_arr)
          mean, std, norm, peak=seeing_stats(fwhm_arr)
          see=mean*pix_scale
          print e
          seeing=-1

       #Display the filter, pix_scale, airmass, exptime
       self.filterLabel = QtWidgets.QLabel("FILTER")
       self.filterLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.exptimeLabel = QtWidgets.QLabel("EXPTIME")
       self.exptimeLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.pixscaleLabel = QtWidgets.QLabel("PIXSCALE")
       self.pixscaleLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.airmassLabel = QtWidgets.QLabel("AIRMASS")
       self.airmassLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)

       self.filterValueLabel = QtWidgets.QLabel(filtername)
       self.filterValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.exptimeValueLabel = QtWidgets.QLabel('%6.2f s' % exptime)
       self.exptimeValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.pixscaleValueLabel = QtWidgets.QLabel("%3.2f ''/pix" % pix_scale)
       self.pixscaleValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.airmassValueLabel = QtWidgets.QLabel('%3.2f' % am)
       self.airmassValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)

       #display  the background stats
       self.bmeanLabel = QtWidgets.QLabel("BACKGROUND MEAN")
       self.bmeanLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.bmidptLabel = QtWidgets.QLabel("BACKGROUND MIDPT")
       self.bmidptLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.bstdLabel = QtWidgets.QLabel("BACKGROUND STD")
       self.bstdLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.bmeanValueLabel = QtWidgets.QLabel('%5.2f' % bmean)
       self.bmeanValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.bmidptValueLabel = QtWidgets.QLabel('%5.2f' % bmidpt)
       self.bmidptValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.bstdValueLabel = QtWidgets.QLabel('%5.2f' % bstd)
       self.bstdValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       
       #display seeing, number of sources
       self.seeLabel = QtWidgets.QLabel("SEEING")
       self.seeLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.seeValueLabel = QtWidgets.QLabel("%3.2f'' " % see)
       self.seeValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)
       self.sourceLabel = QtWidgets.QLabel("SOURCES Detected")
       self.sourceLabel.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Raised)
       self.sourceValueLabel = QtWidgets.QLabel("%i" % nsource)
       self.sourceValueLabel.setFrameStyle(QtWidgets.QFrame.Panel |  QtWidgets.QFrame.Sunken)

       #add it to the panel
       dataLayout=QtWidgets.QGridLayout(datapanel)
       dataLayout.addWidget(self.filterLabel, 0, 0, 1, 1)
       dataLayout.addWidget(self.exptimeLabel, 0, 1, 1, 1)
       dataLayout.addWidget(self.pixscaleLabel, 0, 2, 1, 1)
       dataLayout.addWidget(self.airmassLabel, 0, 3, 1, 1)

       dataLayout.addWidget(self.filterValueLabel, 1, 0, 1, 1)
       dataLayout.addWidget(self.exptimeValueLabel, 1, 1, 1, 1)
       dataLayout.addWidget(self.pixscaleValueLabel, 1, 2, 1, 1)
       dataLayout.addWidget(self.airmassValueLabel, 1, 3, 1, 1)

       dataLayout.addWidget(self.bmeanLabel, 2, 0, 1, 1)
       dataLayout.addWidget(self.bmidptLabel, 2, 1, 1, 1)
       dataLayout.addWidget(self.bstdLabel, 2, 2, 1, 1)

       dataLayout.addWidget(self.bmeanValueLabel, 3, 0, 1, 1)
       dataLayout.addWidget(self.bmidptValueLabel, 3, 1, 1, 1)
       dataLayout.addWidget(self.bstdValueLabel, 3, 2, 1, 1)

       dataLayout.addWidget(self.seeLabel, 4, 0, 1, 1)
       dataLayout.addWidget(self.seeValueLabel, 4, 1, 1, 1)
       dataLayout.addWidget(self.sourceLabel, 5, 0, 1, 1)
       dataLayout.addWidget(self.sourceValueLabel, 5, 1, 1, 1)

       datapanel.setFixedHeight(400)

       return datapanel

   def getitem(self, key):
       i=headerList.index(key)
       try:
           value=str(self.imlist[i])
       except IndexError:
           value=''
       return value

