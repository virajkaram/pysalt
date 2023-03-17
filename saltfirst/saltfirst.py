############################### LICENSE ##################################
# Copyright (c) 2009, South African Astronomical Observatory (SAAO)        #
# All rights reserved.                                                     #
#                                                                          #
############################################################################


#!/usr/bin/env python
#
#
# SALTFIRST--SALTFIRST provides first look capability and quick reductions for
# SALT data. The task initiates a GUI which then monitors the data directories
# for SCAM and RSS. Whenever, a new data file is created, the program will
# identify the file, process the file, display the file in ds9, and compute any
# important statistics for the file. The GUI should be able to display basic
# information about the data as well as print an observing log.
#
# Author                 Version      Date
# -----------------------------------------------
# S M Crawford (SAAO)    0.1          16 Mar 2010

# Ensure python 2.5 compatibility
from __future__ import with_statement



import os, shutil, time, ftplib, glob
from astropy.io import fits as pyfits
import pickle
import numpy as np
import scipy as sp
import warnings

# Gui library imports
from PyQt5 import QtGui, QtCore
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg


from pyraf import iraf
from pyraf.iraf import pysalt

import saltsafekey as saltkey
import saltsafeio as saltio
import saltsafemysql as saltmysql
import saltstat

#import plugins
from quickclean import quickclean
from quickphot  import quickphot
from quickspec  import quickspec, quickap
from display import display, regions
from seeing import seeing_stats
from sdbloadobslog import sdbloadobslog
from fpcal import fpcal
from findcal import findcal
from fastmode import runfast
from sdbloadfits import sdbloadfits

from saltgui import ImageDisplay, MplCanvas
from saltsafelog import logging
from salterror import SaltError, SaltIOError


from OrderedDict import OrderedDict
from ImageWidget import ImageWidget
from SpectraViewWidget import SpectraViewWidget
from InfoWidget import InfoWidget
from DQWidget import DQWidget
from ObsLogWidget import ObsLogWidget
from SpectraViewWidget import SpectraViewWidget
from ObsLogWidget import headerList, printList

debug=True

# -----------------------------------------------------------
# core routine


def saltfirst(obsdate, imdir, prodir, server='smtp.saao.ac.za', readme='readme.fast.template', sdbhost='sdb.salt', sdbname='sdb', sdbuser='', password='',imreduce=True, sexfile='/home/ccd/tools/qred.sex', update=True, clobber=False,logfile='salt.log',verbose=True):

   #Move into the working directory
   if os.path.isdir(prodir):
       if clobber:
           shutil.rmtree(prodir)
           os.mkdir(prodir)
   else:
       os.mkdir(prodir)
   os.chdir(prodir)


   with logging(logfile,debug) as log:

       #create GUI
       App = QtGui.QApplication([])

       #Add information to gui
       aw=FirstWindow(obsdate, imdir, prodir, server=server, readme=readme, sdbhost=sdbhost, sdbname=sdbname, sdbuser=sdbuser, password=password, imreduce=imreduce, sexfile=sexfile, update=update, clobber=clobber, log=log, verbose=verbose)
       aw.setMinimumHeight(800)
       aw.setMinimumWidth(500)
       aw.show()

       # Start application event loop
       exit=App.exec_()

       # Check if GUI was executed succesfully
       if exit!=0:
           raise SaltError('SALTFIRST GUI has unexpected exit status '+str(exit))

class FirstWindow(QtGui.QMainWindow):

   def __init__(self, obsdate, imdir, prodir, server='smtp.saao.ac.za', readme='readme.fast.template',  \
                sdbhost='sdb.salt', sdbname='sdb', sdbuser='', \
                password='', hmin=350,  wmin=400, cmap='gray', \
                sexfile='/home/ccd/tools/qred.sex', update=True,
                scale='zscale', contrast=0.1, imreduce=True, clobber=False, log=None, verbose=True):

        #set up the variables
        self.obsdate=obsdate
        self.imdir=imdir
        self.prodir=prodir
        self.imreduce=imreduce
        self.clobber=clobber
        self.scamwatch=True
        self.rsswatch=True
        self.hrswatch=True 
        self.hrbwatch=True
        self.objsection=None
        self.sdbhost=sdbhost
        self.sdbname=sdbname
        self.sdbuser=sdbuser
        self.password=password
        self.server=server
        self.readme=readme
        self.sexfile=sexfile
        self.update=update
        self.headfiles=[]
        self.pickle_file='%s_obslog.p' % self.obsdate

        # Setup widget
        QtGui.QMainWindow.__init__(self)

        # Set main widget
        self.main = QtGui.QWidget(self)

        # Set window title
        self.setWindowTitle("SALTFIRST")

        #set up observation log from database
        self.create_obslog()

        #look for any initial data
        self.checkfordata(self.obsdate, self.imdir)

        #example data
        #image='../salt/scam/data/2006/1016/raw/S200610160009.fits'
        #self.hdu=saltio.openfits(image)
        #name=getbasename(self.hdu)
        #imlist=getimagedetails(self.hdu)
        #obsdict={}
        #obsdict[name]=imlist

        #set up each of the tabs
        if len(self.obsdict)>0:
           name=self.obsdict.order()[-1]
           imlist=self.obsdict[name]
        else:
           name=''
           imlist=[]
           self.hdu=None
        self.infoTab=InfoWidget(name, imlist)
        self.dqTab=DQWidget(name, imlist)
        #self.imageTab=ImageWidget(self.hdu, hmin=hmin, wmin=wmin, cmap=cmap, scale=scale, contrast=contrast)
        self.specTab=SpectraViewWidget(None, None, None, hmin=hmin, wmin=wmin)
        self.obsTab=ObsLogWidget(self.obsdict, obsdate=self.obsdate)
        #create the tabs
        self.tabWidget=QtGui.QTabWidget()
        self.tabWidget.addTab(self.infoTab, 'Info')
        self.tabWidget.addTab(self.dqTab, 'DQ')
        #self.tabWidget.addTab(self.imageTab, 'Image')
        self.tabWidget.addTab(self.specTab, 'Spectra')
        self.tabWidget.addTab(self.obsTab, 'Log')
        #create button to reset the filewatcher
        self.checkButton = QtGui.QPushButton("Check for Data")
        self.checkButton.clicked.connect(self.clickfordata)
     
        #layout the widgets
        mainLayout = QtGui.QVBoxLayout(self.main)
        mainLayout.addWidget(self.tabWidget)
        mainLayout.addWidget(self.checkButton)
        #set up thrading
        self.threadlist=[]
        self.thread=QtCore.QThread()
        self.nothread=False

        #add the file watching capability
        self.addwatcher()

        #add a timer to check on data and update obslog in database
        self.ctimer=QtCore.QTimer()
        ctime=5*60*1000
        self.ctimer.start(ctime)
        self.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.updatetime)
        #add signal catches
        self.connect(self, QtCore.SIGNAL('updatespec(QString)'), self.updatespecview)
        self.connect(self.thread, QtCore.SIGNAL('finishedthread(QString)'), self.updatetabs)
        self.connect(self.obsTab, QtCore.SIGNAL('cellclicked(QString)'), self.updatetabs)
        self.connect(self.obsTab, QtCore.SIGNAL('updateobslogdb(QString)'), self.updateobslogdb)
        self.connect(self.obsTab, QtCore.SIGNAL('updatecals(QString)'), self.updatecals)
        self.connect(self.specTab, QtCore.SIGNAL('updateextract(int,int)'), self.updateextract)
        # Set the main widget as the central widget
        self.setCentralWidget(self.main)

        # Destroy widget on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

   def create_obslog(self):
       """Check to see if there are any files in the database, and if so, create the observing log"""
       if os.path.isfile(self.pickle_file) and 0:
          self.obsdict = pickle.load( open( self.pickle_file, "rb" ) )
       else:
          self.obsdict = OrderedDict()

   def updateextract(self, y1, y2):
       print y1, y2
       name=self.specTab.name
       iminfo=self.obsdict[name]
       lampid=iminfo[headerList.index('LAMPID')].strip().upper()
       objsection='[%i:%i]' % (y1, y2)
       if self.specTab.defaultBox.checkState():
               print "Updating Object Section"
               self.objsection=objsection
       else:
               self.objsection=None
       outpath='./'
       outfile=outpath+'smbxp'+name
       logfile='saltclean.log'
       verbose=True
       y1, y2=quickap(outfile, objsection=objsection, clobber=True, logfile=logfile, verbose=verbose)
       #quickspec(outfile, lampid, findobj=False, objsection=objsection, clobber=True, logfile=logfile, verbose=verbose)
       self.specTab.updaterange(y1,y2)
       self.updatespecview(name)


   def updatetime(self):
       """Check to see if the data or logs need updating"""
       print "Checking for updates at %s" % time.asctime()

       #check for any new data
       self.clickfordata('')

       #update the obstab to the sdb
       self.obsTab.printfornightlog()

       self.updatecals()

   def updateobslogdb(self, logstr):
       #print logstr
       print "Updating Obslog for ", self.obsdate
       sdbloadobslog(logstr, self.obsdate, self.sdbhost, self.sdbname, self.sdbuser, self.password)
       pickle.dump(self.obsdict, open(self.pickle_file, 'wb'))
       

   def updatecals(self):
       print "Loading Calibration Data"
       findcal(self.obsdate, self.sdbhost, self.sdbname, self.sdbuser, self.password)


   def updateimlist(self, name, key, value):
       print "UPDATE:", name, key, value

   def updatespecview(self, name):
       name = str(name)
       print "UPDATING SPECVIEW with %s" % name
       specfile='./smbxp'+name.split('.fits')[0]+'.txt'
       warr, farr, snarr=np.loadtxt(specfile, usecols=(0,1,2), unpack=True)
       self.specTab.loaddata(warr, farr, snarr, name)
       self.specTab.redraw_canvas()

   def converttoname(self, infile): 
       """Given a file name, find the raw salt file name"""

   def updatetabs(self, infile):
       name=str(infile)
       imlist=self.obsdict[name]
       detmode=imlist[headerList.index('DETMODE')].strip().upper()
       obsmode=imlist[headerList.index('OBSMODE')].strip().upper()

       #update the information panel
       try:
           self.infoTab.update(name, self.obsdict[name])
           print "UPDATING tabs with %s" % name
       except Exception, e:
           print e
           return

       if self.thread.isRunning() and self.nothread:
           self.nothread=False

       #update the DQ tab
       try:
           self.dqTab.updatetab(name, self.obsdict[name])
           #self.dqTab=DQWidget(name, self.obsdict[name])
           #self.tabWidget.removeTab(1)
           #self.tabWidget.insertTab(1, self.dqTab, 'DQ')
       except Exception, e:
           print e
           return

       #display the image
       try:
           if name.startswith('S') or name.startswith('P'):
              rfile='mbxp'+name
              cfile=rfile.replace('.fits', '.cat')
           else:
              rfile = name + 's'
              cfile = None
    
           display(rfile, cfile)
       except  Exception, e:
           print e


       #update the spectra plot
       if obsmode=='SPECTROSCOPY':
          self.updatespecview(name)




   def clickfordata(self, event):
       #print self.watcher, dir(self.watcher)
       #look for new data
       self.checkfordata(self.obsdate, self.imdir)

       #reset the obslog
       self.obsTab.set_obsdict(self.obsdict)
       #print self.obsTab.obsdict.keys()
       self.obsTab.obstable.setRowCount(self.obsTab.nrow)
       for i in range(self.obsTab.nrow):
           self.obsTab.setrow(i)

       #reset the watcher
       self.disconnect(self.watcher, QtCore.SIGNAL('directoryChanged (const QString&)'), self.newfileEvent)
       self.addwatcher()

   def addwatcher(self):
        self.watcher=QtCore.QFileSystemWatcher(self)
        watchpath=[]
        if self.scamwatch:
            watchpath.append(self.scamdir)
        else:
            watchpath.append('%sscam/data/%s/' % (self.imdir, self.obsdate[0:4]))
        if self.rsswatch:
            watchpath.append(self.rssdir)
        else:
            watchpath.append('%srss/data/%s/' % (self.imdir, self.obsdate[0:4]))

        if self.hrswatch:
            watchpath.append(self.hrsdir)
        else:
            watchpath.append('%shrdet/data/%s/' % (self.imdir, self.obsdate[0:4]))

        if self.hrbwatch:
            watchpath.append(self.hrbdir)
        else:
            watchpath.append('%shbdet/data/%s/' % (self.imdir, self.obsdate[0:4]))

        print watchpath
        self.watcher.addPaths(watchpath)
        self.connect(self.watcher, QtCore.SIGNAL('directoryChanged (const QString&)'), self.newfileEvent)
        #watcher.directoryChanged.connect(self.newfileEvent)
        #self.connect(watcher, QtCore.SIGNAL("fileChanged(const QString&)"), self.newfileEvent)


   def newfileEvent(self, event):
       """Handles the event when a new file is created"""
       #look for new files
       edir='%s' % event
       if not self.scamwatch and edir.count('scam'):
           self.watcher.addPath(self.scamdir)
           edir=self.scamdir
       if not self.rsswatch and edir.count('rss'):
           self.watcher.addPath(self.rssdir)
           edir=self.rssdir

       #Perhaps edit to turn off? 
       if self.hrswatch and edir.count('hrdet'):
           self.watcher.addPath(self.hrsdir)
           edir=self.hrsdir
       if self.hrbwatch and edir.count('hbdet'):
           self.watcher.addPath(self.hrbdir)
           edir=self.hrbdir

       #check the directory for new files
       files=glob.glob(edir+'*')
       files.sort()
       newfile=self.findnewfile(files)
       if not newfile: return
       #skip over an files that are .bin files
       if newfile.count('.bin'):
           msg="Sorry I can't handle slotmode files like %s, yet" % files[-1]
           print msg
           return
       print newfile
       
       if not newfile.count('.fit'): return
       #see if the new file can be opened and added to obsdict
       name=self.addtoobsdict(newfile)
       print 'Added to obs:', name

       #if it fails, return
       if name is None: return
       print edir
       #check to see if it is a new file and if so, add it to the files
       #if not return
       if edir==self.scamdir:
          if len(self.scamfiles)==len(files): return
          self.scamfiles.append(newfile)
       if edir==self.rssdir:
          if len(self.rssfiles)==len(files): return
          self.rssfiles.append(newfile)
       if edir==self.hrsdir:
          if len(self.hrsfiles)==len(files): return
          self.hrsfiles.append(newfile)
       if edir==self.hrbdir:
          if len(self.hrbfiles)==len(files): return
          self.hrbfiles.append(newfile)
       self.allfiles=self.scamfiles+self.rssfiles+self.hrsfiles+self.hrbfiles

       #update tables
       self.updatetables(name)

       #add head files to the list
       if newfile.count('.head'):
          self.headfiles.append(newfile)

       #start to reduct the data
       if self.imreduce and newfile.count('.fit') and newfile.count(self.obsdate):
           self.newname=name
           self.newfile=newfile
           self.thread.run=self.runcleandata
           print 'Setting up thread'
           self.thread.start()
           print 'Thread Started'
           
   def runcleandata(self):
           self.nothread=True 
           self.obsdict[self.newname]=self.cleandata(self.newfile, iminfo=self.obsdict[self.newname],
                     clobber=self.clobber, display_image=True)
           if self.nothread:
               self.nothread=False
               print "emitting signal"
               self.thread.emit(QtCore.SIGNAL("finishedthread(QString)"), self.newname)


   def updatetables(self, name):
       #update the Observing log table
       self.obsTab.addobsdict(name, self.obsdict[name])

   def findnewfile(self, files):
       """Find the newest file in a directory and return it"""
       newfile=None
       for l in files:
           if l not in self.allfiles and not l.count('disk.file') and not l.count('log'):
               newfile=l

       return newfile

   def checkfordata(self, obsdate, imdir):
       """If we are starting up, look for any existing data and load that data"""

       #set up some of the data
       self.obsdate=obsdate
       self.imdir=imdir
       if imdir[-1]!='/': imdir += '/'

       #set up the directories scam data
       self.scamdir='%sscam/data/%s/%s/raw/' % (imdir, obsdate[0:4], obsdate[4:])
       #self.scamdir='%sscam/data/%s/' % (imdir, obsdate[0:4])
       if os.path.isdir(self.scamdir):
           self.scamfiles=glob.glob(self.scamdir+'S*')
           self.scamfiles.sort()
       else:
           #createdirectories(self.scamdir)
           self.scamwatch=False
           self.scamfiles=[]

       #set up the RSS files
       self.rssdir ='%srss/data/%s/%s/raw/' % (imdir, obsdate[0:4], obsdate[4:])
       if os.path.isdir(self.rssdir):
           self.rssfiles=glob.glob(self.rssdir+'P*')
           self.rssfiles.sort()
       else:
           #createdirectories(self.rssdir)
           self.rsswatch=False
           self.rssfiles=[]

       #set up the HRS files
       self.hrsdir ='%shrdet/data/%s/%s/raw/' % (imdir, obsdate[0:4], obsdate[4:])
       if os.path.isdir(self.hrsdir) and self.hrswatch:
           self.hrsfiles=glob.glob(self.hrsdir+'R*')
           self.hrsfiles.sort()
       else:
           #createdirectories(self.rssdir)
           self.hrswatch=False
           self.hrsfiles=[]

       #set up the HRS files
       self.hrbdir ='%shbdet/data/%s/%s/raw/' % (imdir, obsdate[0:4], obsdate[4:])
       if os.path.isdir(self.hrbdir) and self.hrbwatch:
           self.hrbfiles=glob.glob(self.hrbdir+'H*')
           self.hrbfiles.sort()
       else:
           #createdirectories(self.rssdir)
           self.hrbwatch=False
           self.hrbfiles=[]


       self.allfiles=self.scamfiles+self.rssfiles+self.hrsfiles+self.hrbfiles
       #create the obsdict
       for i in range(len(self.allfiles)):
           if self.allfiles[i][-5:]==".fits" and self.allfiles[i].count(self.obsdate):
             name=os.path.basename(self.allfiles[i])
             if name not in self.obsdict.keys(): # or not os.path.isfile('mbxp'+name): 
               name=self.addtoobsdict(self.allfiles[i])
               if self.imreduce:
                   self.obsdict[name]=self.cleandata(self.allfiles[i], iminfo=self.obsdict[name],
                             clobber=self.clobber)
           elif self.allfiles[i].count(".head"):
               name=self.addtoobsdict(self.allfiles[i])
               self.headfiles.append(self.allfiles[i])
           elif self.allfiles[i][-4:]==".fit": #for hrs
             name=os.path.basename(self.allfiles[i])
             if name not in self.obsdict.keys(): # or not os.path.isfile('mbxp'+name): 
                name=self.addtoobsdict(self.allfiles[i])
                if self.imreduce:
                   self.obsdict[name]=self.cleandata(self.allfiles[i], iminfo=self.obsdict[name],
                             reduce_image=False, clobber=self.clobber)
           elif self.allfiles[i].count(".bin"):
               msg="Sorry I can't handle slotmode files like %s, yet" % self.allfiles[i]
               print msg

   def addtoobsdict(self, infile):
       try:
           warnings.warn('error')
           self.hdu=saltio.openfits(infile)
           self.hdu.verify('exception')
           warnings.warn('default')
           name=getbasename(self.hdu)
           imlist=getimagedetails(self.hdu)
           self.hdu.close()
       except IndexError:
           time.sleep(10)
           name=self.addtoobsdict(infile)
           return name
       except Exception, e:
           print 'Returning none due to: %s' % (str(e))
           return None
       self.obsdict[name]=imlist
       return name

   def cleandata(self, filename, iminfo=None, prodir='.', interp='linear', cleanup=True,
              clobber=False, 
              logfile='saltclean.log', reduce_image=True,
              display_image=False, verbose=True):
      """Start the process to reduce the data and produce a single mosaicked image"""
      #print filename
      status=0
      #create the input file name
      infile=os.path.basename(filename)
      rawpath=os.path.dirname(filename)
      outpath='./'
      outfile=outpath+'mbxp'+infile
      #print infile, rawpath, outpath

      #If it is a bin file, pre-process the data
      if filename.count('.bin'):
          print "I can't handle this yet"

      #ignore bcam files
      if infile.startswith('B'):
          return iminfo


      #check to see if it exists and return if clobber is no
      if os.path.isfile(outfile) and not clobber: return iminfo

      #handle HRS data 
      print filename
      if infile.startswith('H') or infile.startswith('R'):
          outfile = os.path.basename(filename) +'s'
          print filename, outfile
          if not os.path.isfile(outfile): os.symlink(filename, outfile)

          #display the image
          if display_image:
              print "Displaying %s" % outfile
              try:
                 display(outfile)
              except Exception, e:
                 print e

          try:
              log=None #open(logfile, 'a')
              sdb=saltmysql.connectdb(self.sdbhost, self.sdbname, self.sdbuser, self.password)
              sdbloadfits(outfile, sdb, log, False)
              print 'SDBLOADFITS: SUCCESS'
          except Exception, e:
              print 'SDBLOADFITSERROR:', e
          return iminfo

      if filename.count('.txt'): return iminfo

      #remove frame transfer data
      #detmode=iminfo[headerList.index('DETMODE')].strip().upper()
      #if detmode=='FT' or detmode=='FRAME TRANSFER': return iminfo


      #reduce the data
      if reduce_image:
         try:
           quickclean(filename, interp, cleanup, clobber, logfile, verbose)
         except Exception, e:
           print e
           return iminfo

      #load the data into the SDB
      if self.sdbhost and self.update:
           try:
               log=None #open(logfile, 'a')
               sdb=saltmysql.connectdb(self.sdbhost, self.sdbname, self.sdbuser, self.password)
               sdbloadfits(filename, sdb, log, False)
               print 'SDBLOADFITS: SUCCESS'
           except Exception, e:
               print 'SDBLOADFITSERROR:', e

      #display the image
      if display_image:
          print "Displaying %s" % outfile
          try:
             display(outfile)
          except Exception, e:
             print e

      #if the images are imaging data, run sextractor on them
      name=iminfo[0]
      propcode=iminfo[headerList.index('PROPID')].strip().upper()
      obsmode=iminfo[headerList.index('OBSMODE')].strip().upper()
      detmode=iminfo[headerList.index('DETMODE')].strip().upper()
      obstype=iminfo[headerList.index('CCDTYPE')].strip().upper()
      target=iminfo[headerList.index('OBJECT')].strip().upper()
      lampid=iminfo[headerList.index('LAMPID')].strip().upper()
      print detmode
      if (obsmode=='IMAGING' or obsmode=='FABRY-PEROT' ) and (detmode=='NORMAL' or detmode=='FT' or detmode=='FRAME TRANSFER'):
          i=headerList.index('CCDSUM')
          ccdbin=int(iminfo[i].split()[0])
          pix_scale=0.14*ccdbin
          r_ap=1.5/pix_scale

          #measure the photometry
          print "RUNNING PHOTOMETRY"
          quickphot(outfile, r_ap, pix_scale, self.sexfile, clobber, logfile, verbose)

          #load the regions
          #if display_image: regions(outfile)

          #measure the background statistics
          #hdu=pyfits.open(outfile)
          #bmean, bmidpt, bstd=saltstat.iterstat(hdu[1].data, 5, 3)
	  bmean, bmidpt, bstd=(-1,-1,-1)
          #hdu.close()
          print "---------Background Statistics---------"
          print "%10s %10s %10s" % ('Mean', 'MidPoint', 'STD')
          print "%10.2f %10.2f %10.2f" % (bmean, bmidpt, bstd)
          iminfo[headerList.index('BMEAN')]='%f' % (bmean)
          iminfo[headerList.index('BMIDPT')]='%f' % (bmidpt)
          iminfo[headerList.index('BSTD')]='%f' % (bstd)

          #measure the seeing
          outtxt=outfile.replace('fits', 'cat')
          try:
              mag_arr, fwhm_arr=np.loadtxt(outtxt, usecols=(2,10), unpack=True)
              mean, std, norm, peak=seeing_stats(fwhm_arr)
              see=mean*pix_scale
              nsources=len(mag_arr)
          except:
              see=-1
              nsources=-1
          iminfo[headerList.index('NSOURCES')]='%i' % nsources
          iminfo[headerList.index('SEEING')]='%f' % see
          #self.emit(QtCore.SIGNAL("updateimlist(str,str,str)"), (name, 'SEEING', '%f' % see))
          #self.emit(QtCore.SIGNAL("updatespec(QString)"), name)

      #If the images are spectral images, run specreduce on them
      if obsmode=='SPECTROSCOPY': # and not(target in ['FLAT', 'BIAS']):
          solfile = iraf.osfn('pysalt$data/rss/RSSwave.db')
          print solfile
          y1,y2=quickspec(outfile, lampid, solfile=solfile, objsection=self.objsection, findobj=True, clobber=True, logfile=logfile, verbose=verbose)
          print y1,y2
          specfile=outpath+'smbxp'+infile.split('.fits')[0]+'.txt'
          #In here, so it doesn't break when the first checkdata  runs
          try:
              self.specTab.updaterange(y1,y2)
              self.emit(QtCore.SIGNAL("updatespec(QString)"), infile)
          except Exception,e:
              message="SALTFIRST--ERROR:  Could not wavelength calibrate %s because %s" % (infile, e)
              fout=open(logfile, 'a')
              fout.write(message)
              print message

      if obsmode=='FABRY-PEROT' and obstype=='ARC':
           try:
              flatimage='/home/ccd/smc/FPFLAT.fits'
              profile=os.path.basename(outfile)
              fpcal(profile, flatimage=flatimage, minflat=18000, niter=5, bthresh=5, displayimage=True, clobber=True, logfile=logfile, verbose=verbose)
           except Exception,e:
              message="SALTFIRST--ERROR:  Could not calibrate FP data te %s because %s" % (infile, e)
              fout=open(logfile, 'a')
              fout.write(message)
              print message

      #check for fast mode operation
      if self.update:
          runfast(name, propcode,self.obsdate,self.server, self.readme, self.sdbhost,self.sdbname, self.sdbuser, self.password)
      return iminfo

def createdirectories(f):
    """Step through all the levels of a path and creates all the directories"""
    d=f.split('/')
    for i in range(len(d)):
       odir=''.join('%s/' % x for x in d[:i])
       if odir:
           if not os.path.isdir(odir):
               os.mkdir(odir)


def getbasename(hdu):
    return os.path.basename(hdu._HDUList__file.name)

def getimagedetails(hdu):
   """Return all the pertinant image header details"""
   filename=hdu._HDUList__file.name
   imlist=[filename]
   print filename
   for k in headerList[1:]:
       try:
           value=saltkey.get(k, hdu[0])
       except SaltIOError:
           value=''
       imlist.append(value)
   return imlist



# -----------------------------------------------------------
# main code

#parfile = iraf.osfn("saltfirst$saltfirst.par")
#t = iraf.IrafTaskFactory(taskname="saltfirst",value=parfile,function=saltfirst, pkgname='pipetools')
