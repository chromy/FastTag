'''
Created on 23 Jun 2010

@author: hex
'''

import os
import time
import threading
import webbrowser
#import PIL
import wx
import wx.lib.newevent
import wx.lib.delayedresult as delayedresult
#import wx.lib.mixins.listctrl as listmix
#import thumbnail as TC

#import pyfacebook as facebook
import facebook
import image

#Got to find a better way to do ident
FACEBOOK_APP_ID = "137838529566876"
FACEBOOK_APP_SECRET = "9967dec5239d2180356f6413df87bd53"

#url = ''.join(('https://graph.facebook.com/oauth/authorize?'
#               'client_id=' + FACEBOOK_APP_ID +'&',
#               'redirect_uri=http://www.facebook.com/connect/login_success.html&',
#               'type=user_agent&',
#               'display=popup'))

url = ''.join(('https://graph.facebook.com/oauth/authorize?'
         'client_id=' + FACEBOOK_APP_ID +'&',
         'redirect_uri=http://www.facebook.com/connect/login_success.html&',
         'scope=user_photos,user_photo_video_tags,friends_photos'
         ))


# This creates a new Event class and a EVT binder function
(FacebookDataEvent, EVT_FACEBOOK_DATA) = wx.lib.newevent.NewEvent()
#(ForwardEvent, EVT_FORWARD) = wx.lib.newevent.NewEvent()
#(ForwardEvent, EVT_BACK) = wx.lib.newevent.NewEvent()

class FacebookCtrl(object):
    def __init__(self, window):
        self.window = window
        self.jobID = 0
        
        self.threads = []
        self.loggedin = False
        self.albums = {}
        self.photos = {}
        self.images = {}
        self.fb = facebook.Facebook(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
        
    def loginstart(self):
        self.fb.auth.createToken()
        self.fb.login()
        webbrowser.open_new_tab(url)
            
    def logindone(self):
        if self.loggedin == False:       
            self.fb.auth.getSession()
            self.loggedin = True
        
    def getalbums(self):
        self.handleGet('albums')
    
    def getphotos(self, aid):
        self.handleGet('photos', theaid=aid)
        
    def getimage(self, pid):
        theurl = self.photos[pid].src_big
        self.handleGet('image', thepid=pid, theurl=theurl)
        
    def logout(self):
        pass
                
    def handleGet(self, task, **kargs): 
        """Compute result in separate thread, doesn't affect GUI response."""
        self.jobID += 1
        print "Starting job %s in producer thread: GUI remains responsive" % self.jobID
        delayedresult.startWorker(self._resultConsumer, self._resultProducer, 
                                  wargs=(self.jobID, task), wkwargs=kargs,
                                  cargs=(task,), ckwargs=kargs, jobID=self.jobID)
         
    def _resultProducer(self, jobID, task, theaid=None, thepid=None, theurl=None):
        """Pretend to be a complex worker function or something that takes 
        long time to run due to network access etc. GUI will freeze if this 
        method is not called in separate thread."""
        if task == 'albums':
            data = self.fb.photos.getAlbums(self.fb.uid)
        elif task == 'photos':
            data = self.fb.photos.get(aid=theaid)
        elif task == 'image':
            data = image.retrieveimage(theurl)
            print data
        else:
            raise NotImplementedError
        return data

    def _resultConsumer(self, delayedResult, task, theaid=None, thepid=None, theurl=None):
        jobID = delayedResult.getJobID()
        try:
            result = delayedResult.get()
        except KeyError: #Exception, exc:
            #print "Result for job %s raised exception: %s" % (jobID, exc)
            return
        
        #task = result['task']
        if task == 'albums':
            albums = dict([(a['aid'], Album(a)) for a in result])
            self.albums = albums
            evt = FacebookDataEvent(value=task)
        elif task == 'photos':
            rawphotos = result
            photos = dict([(p['pid'],Photo(p)) for p in rawphotos])
            pids = [p['pid'] for p in rawphotos]
            self.albums[theaid].photos = pids
            self.albums[theaid].gotphotos = True
            self.albums[theaid].currentphoto = 0 if len(pids) > 0 else None
            self.photos.update(photos)
            evt = FacebookDataEvent(value=task, aid=theaid)
        elif task == 'image':
            self.images[thepid] = result
            evt = FacebookDataEvent(value=task, pid=thepid)
        else:
            raise NotImplementedError        
     
        wx.PostEvent(self.window, evt)

class ImagePanel(wx.Panel):
    """This Panel"""
    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        
        self.SetBackgroundColour((0,0,0))
        
        #Event
        self.Bind(wx.EVT_SIZE, self.OnResize)
       
        #Label
        self.lbl = wx.StaticText(self, -1, '', (15, 10))
        self.lbl.SetForegroundColour((255,255,255))
        
        #picture
        self.baseimage = wx.EmptyImage(1, 1, True) 
        self.bitmap = wx.StaticBitmap(parent=self, bitmap=self.baseimage.ConvertToBitmap())
        self.bitmap.Show(False)

        #Sizers
        self.sizeracross = wx.BoxSizer(wx.HORIZONTAL)
        self.sizerdown = wx.BoxSizer(wx.VERTICAL)
        self.sizeracross.Add(self.bitmap, 1, wx.CENTER)
        self.sizerdown.Add(self.sizeracross, 1, wx.CENTER)
        
        #Layout sizers
        self.SetSizer(self.sizerdown)
        self.SetAutoLayout(1)
        self.sizerdown.Fit(self)

    def OnResize(self, event):
        sw, sh = self.sizerdown.GetSize()
        iw, ih = self.baseimage.GetSize()
        if (sw > iw) and (sh > ih) :
            nh = ih
            nw = iw
        else:
            if  (sw - iw) < (sh - ih):
                nh = (sw - iw) + ih
                nw = sw
            else:
                nw = (sh - ih) + iw
                nh = sh
        
        if self.bitmap.Shown == True:
            self.bitmap.SetBitmap(self.baseimage.Scale(nw,nh).ConvertToBitmap())
        self.sizerdown.Layout()
        
        event.Skip()

    def ShowItem(self, data):
        if isinstance(data, str):
            self.bitmap.Show(False)
            self.lbl.Show(True)
            self.lbl.SetLabel(data)
            item = self.lbl
        else:
            self.lbl.Show(False)
            self.bitmap.Show(True)
            self.lbl.SetLabel('')
            self.baseimage = data
            self.bitmap.SetBitmap(self.baseimage.ConvertToBitmap())
            
            item = self.bitmap
            
        self.sizeracross.Remove(0)
        self.sizeracross.Add(item, 1, wx.CENTER)
        self.sizerdown.Layout()
    
        
class CtrlPanel(wx.Panel):
    """This Panel"""
    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        
        #
        self.fwd = wx.Button(self, id=wx.ID_FORWARD)
        self.bk = wx.Button(self, id=wx.ID_BACKWARD)
        self.lbl = wx.StaticText(self, -1, 'No Photos', (15, 10))
        
        #events
        #self.fwd.Bind(wx.EVT_BUTTON, self.OnLoginButton)
        #self.bk.Bind(wx.EVT_BUTTON, self.OnLoginDone)
        
        #Sizers
        self.sizeracross = wx.BoxSizer(wx.HORIZONTAL)
        self.sizerdown = wx.BoxSizer(wx.VERTICAL)
        
        self.sizeracross.Add(self.bk, 1, wx.ALL)
        #self.sizeracross.Add((1,1), 1, wx.EXPAND)
        self.sizeracross.AddSpacer(20,1)
        self.sizeracross.Add(self.lbl, 0, wx.ALL|wx.CENTER)
        self.sizeracross.AddSpacer(20,1)
        self.sizeracross.Add(self.fwd, 1, wx.ALL)
        self.sizerdown.Add(self.sizeracross, 1, wx.ALL)

        #Layout sizers
        self.SetSizer(self.sizerdown)
        self.SetAutoLayout(1)
        self.sizerdown.Fit(self)
        
    def SetText(self, text):
        self.lbl.SetLabel(text)
        self.sizerdown.Layout()
        
class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(200,100))
        
        #
        self.fbctrl = FacebookCtrl(self)
        self.currentalbum = -1
        self.currentphoto = None
        self.pendingrequests = set()
        self.threadcount = 0
    
        # A StatusBar in the bottom of the window
        self.CreateStatusBar() 

        # Setting up the menu.
        filemenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard ids provided by wxWidgets.
        menuImport = filemenu.Append(wx.ID_OPEN, "&Import"," Import photos")
        filemenu.AppendSeparator()
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        #Panels
        self.image = ImagePanel(self)
        self.ctrls = CtrlPanel(self)

        #buttons
        self.loginbutton = wx.Button(self, label='Login')
        self.logindone = wx.Button(self, label='Done')
        lblalbum = wx.StaticText(self, -1, "Album Selection:", (15, 10))
        self.albumch = wx.Choice(self, -1, (100, 50), choices=[])
        
        # Set events.
        self.Bind(EVT_FACEBOOK_DATA, self.OnFacebookData)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnCloseWindow, menuExit)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(EVT_FACEBOOK_DATA, self.OnFacebookData)
        self.loginbutton.Bind(wx.EVT_BUTTON, self.OnLoginButton)
        self.logindone.Bind(wx.EVT_BUTTON, self.OnLoginDone)
        self.ctrls.fwd.Bind(wx.EVT_BUTTON, self.OnForward)
        self.ctrls.bk.Bind(wx.EVT_BUTTON, self.OnBack)
        self.Bind(wx.EVT_CHOICE, self.EvtChoice, self.albumch)  
        
        #
        self.logindone.Disable()
        self.albumch.Disable()

        #Sizers
        self.sizeracross_login = wx.BoxSizer(wx.HORIZONTAL)
        self.sizeracross_img = wx.BoxSizer(wx.HORIZONTAL)
        self.sizeracross_ctrl = wx.BoxSizer(wx.HORIZONTAL)
        self.sizerdown = wx.BoxSizer(wx.VERTICAL)
        
        self.sizeracross_login.Add(self.loginbutton, 0, wx.ALL)
        self.sizeracross_login.Add(self.logindone, 0, wx.ALL)
        self.sizeracross_login.AddSpacer(20,1)
        self.sizeracross_login.Add(lblalbum, 0, wx.ALL|wx.CENTER)
        self.sizeracross_login.AddSpacer(10,1)
        self.sizeracross_login.Add(self.albumch, 1, wx.ALL)
        self.sizeracross_img.Add(self.image, 1, wx.EXPAND)
        self.sizeracross_ctrl.Add(self.ctrls, 1, wx.CENTER)
        
        self.sizerdown.Add((1,10))
        self.sizerdown.Add(self.sizeracross_login, 0, wx.ALL)
        self.sizerdown.Add((1,10))
        self.sizerdown.Add(self.sizeracross_img, 1, wx.EXPAND)
        self.sizerdown.Add((1,10))
        self.sizerdown.Add(self.sizeracross_ctrl, 0, wx.CENTER)
        self.sizerdown.Add((1,10))
        
        #Layout sizers
        self.SetSizer(self.sizerdown)
        self.SetAutoLayout(1)
        self.sizerdown.Fit(self)

        self.Show(True)
        
    def OnAbout(self,e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog( self, "FastTag", "About", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.
        
    def OnLoginButton(self, event):
        if self.fbctrl.loggedin == False:
            self.loginbutton.Disable()
            self.logindone.Enable()
            self.SetStatusText("Wait for Facebook login page too load.")
            self.fbctrl.loginstart()

    def OnLoginDone(self, event):
        self.loginbutton.Disable()
        self.logindone.Enable()
        self.SetStatusText("Getting Album Data")
        self.fbctrl.logindone()
        self.fbctrl.getalbums()

    def OnForward(self, event):
        pid = self.fbctrl.albums[self.currentalbum].nextphoto()
        self.currentphoto = pid
        self.UpdateImg()
        self.UpdateLbl()
        
    
    def OnBack(self, event):
        pid = self.fbctrl.albums[self.currentalbum].lastphoto()
        self.currentphoto = pid
        self.UpdateImg()
        self.UpdateLbl()

    def OnFacebookData(self, event):
        self.threadcount = self.threadcount - 1
        if event.value == 'albums':
            self.albumch.Enable()
            self.nametoaid = {}
            self.nametoaid = dict([(a.name, a.aid) for a in self.fbctrl.albums.values()])
            print self.nametoaid
            for name in self.nametoaid.keys():    
                self.albumch.Append(name)
                    
        elif event.value == 'photos':
            aid = event.aid
            if aid == self.currentalbum:
                self.GotPhotos()
            
        elif event.value == 'image':
            pid = event.pid
            self.pendingrequests.discard(pid)
            if len(self.pendingrequests) == 0:
                if len(self.toberequsted) > 0:
                    requestnow = self.toberequsted[:10]
                    self.toberequsted = self.toberequsted[10:]
                    self.RequestImg(*requestnow)
            self.UpdateImg()
            self.UpdateLbl()
            
    def UpdateLbl(self):
        album = self.fbctrl.albums[self.currentalbum]
        if album.gotphotos == True:
            if len(album.photos) == 0: 
                text = 'No Photos'
            else:
                num = self.fbctrl.albums[self.currentalbum].currentphoto
                total = len(self.fbctrl.albums[self.currentalbum].photos)
                text = ' '.join(('Photo', str(num+1), 'of', str(total)))
        else:
            text = 'Unknown'
        self.ctrls.SetText(text)
        
    def UpdateImg(self):
        requesting = False
        try:
            item = self.fbctrl.images[self.currentphoto]
        except KeyError:
            album = self.fbctrl.albums[self.currentalbum]
            if album.gotphotos == True:
                if len(album.photos) == 0: 
                    item = 'Album is empty'
                else:
                    item = 'Image Loading'
                    requesting = True
                    
            else:
                item = 'Requesting Photo Data'
        if requesting and self.currentphoto != None:               
            self.RequestImg(self.currentphoto)
        
        self.image.ShowItem(item)
                    
    def GotPhotos(self):
        pids = self.fbctrl.albums[self.currentalbum].photos
        if len(pids) > 0:
            self.currentphoto = self.fbctrl.albums[self.currentalbum].thisphoto()
        self.toberequsted = pids
        requestnow = self.toberequsted[:10]
        self.toberequsted = self.toberequsted[10:]
        self.RequestImg(*requestnow)
                
    def SelectAlbum(self, aid):
        self.currentalbum = aid
        self.currentphoto = None
        gotphotos = False
        if self.fbctrl.albums[self.currentalbum].gotphotos == False:
            self.fbctrl.getphotos(self.currentalbum)
        else:
            gotphotos = True
    
        if gotphotos:        
            self.GotPhotos()
        self.UpdateImg()
        self.UpdateLbl()
        
    def RequestImg(self, *pids):
        for pid in pids:
            if pid not in self.pendingrequests:
                self.pendingrequests.add(pid)
                self.fbctrl.getimage(pid)
                
    def RequestTags(self, *pids):
        for pid in pids:
            if pid not in self.requestedphotos:
                self.requestedphotos.add(pid)
                self.fbctrl.getimage(pid)
                
    def OnOpen(self,e):
        """ Open a file"""
        self.dirname = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            f = open(os.path.join(self.dirname, self.filename), 'r')
            self.control.SetValue(f.read())
            f.close()
        dlg.Destroy()
        
    def EvtChoice(self, event):
        name = event.GetString()
        aid = self.nametoaid[name]
        self.SelectAlbum(aid)

    def OnCloseWindow(self, evt):
        #busy = wx.BusyInfo("One moment please, waiting for threads to die...")
        #wx.Yield()
        #
        #while self.threadcount > 0:
        #    time.sleep(0.1)

        self.Destroy()
        

class Album(object):
    def __init__(self, albumdetails, photos=None):
        for key, value in albumdetails.items():
            self.__dict__[key] = value
        self.gotphotos = False
        self.photos = photos if photos != None else []
        self.currentphoto = None
        
    def nextphoto(self):
        if len(self.photos) != 0:
            self.currentphoto = (self.currentphoto + 1) % len(self.photos)
            result = self.photos[self.currentphoto]
        else:
            result = None
        return result
    
    def thisphoto(self):
        return self.photos[self.currentphoto]
            
    def lastphoto(self):
        if len(self.photos) != 0:
            self.currentphoto = (self.currentphoto - 1) % len(self.photos)
            result = self.photos[self.currentphoto]
        else:
            result = None
        return result
           
class Photo(object):
    def __init__(self, photodetails):
        for key, value in photodetails.items():
            self.__dict__[key] = value
            

if __name__ == '__main__':
    app = wx.App(False)
    frame = MainWindow(None, "FastTag")
    app.MainLoop()

    

