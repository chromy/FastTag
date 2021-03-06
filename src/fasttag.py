'''
Created on 23 Jun 2010

@author: hex
'''

import os
import webbrowser
import wx
import wx.lib.newevent
import wx.lib.delayedresult as delayedresult
#Eventually replace custom event with this
#from wx.lib.pubsub import Publisher as pub 


import facebook
import image

TITLE = 'FastTag'
PERMISSIONS = 'user_photos,user_photo_video_tags,friends_photos'
NOALBUM = -1

#Got to find a better way to do ident
FACEBOOK_APP_ID = "137838529566876"
FACEBOOK_APP_SECRET = "9967dec5239d2180356f6413df87bd53"

url = ''.join(('https://graph.facebook.com/oauth/authorize?'
         'client_id=' + FACEBOOK_APP_ID +'&',
         'redirect_uri=http://www.facebook.com/connect/login_success.html&',
         'scope=user_photos,user_photo_video_tags,friends_photos'
         ))


# This creates a new Event class and a EVT binder function
(FacebookDataEvent, EVT_FACEBOOK_DATA) = wx.lib.newevent.NewEvent()

class Model(object):
    def __init__(self):
        self.albums = {}
        self.photos = {}
        self.images = {}
    
    def AddAlbum(self, album):
        pass
    def AddPhoto(self, photo):
        pass
        

class FacebookCtrl(object):
    def __init__(self, window):
        self.window = window
        self.jobID = 0

        self.loggedin = False
        self.albums = {}
        self.photos = {}
        self.images = {}
        self.fb = facebook.Facebook(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)

    def loginstart(self):
        self.fb.auth.createToken()
        self.fb.login()

    def logindone(self):
        if self.loggedin == False:       
            self.fb.auth.getSession()
            # TODO: Do something cleverer here
            print self.fb.ext_perms
            self.fb.request_extended_permission(PERMISSIONS, popup=False)
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
        # 
        self.jobID += 1
        delayedresult.startWorker(self._resultConsumer, self._resultProducer, 
                                  wargs=(self.jobID, task), wkwargs=kargs,
                                  cargs=(task,), ckwargs=kargs, jobID=self.jobID)

    def _resultProducer(self, jobID, task, theaid=None, thepid=None, theurl=None):
        """"""
        if task == 'albums':
            data = self.fb.photos.getAlbums(self.fb.uid)
        elif task == 'photos':
            data = self.fb.photos.get(aid=theaid)
        elif task == 'image':
            data = image.retrieveimage(theurl)

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

class ImagePanelDC(wx.Panel):
    """This Panel"""
    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        #Event
        self.Bind(wx.EVT_SIZE, self.OnResize)
        self.Bind(wx.EVT_PAINT,  self.OnPaint)

        #picture
        self.baseimage = wx.EmptyImage(1, 1, True) 
        self.bitmap = self.baseimage.ConvertToBitmap()
        self.showbit = False

    def OnResize(self, event):
        sw, sh = self.GetSizeTuple()
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

        if self.showbit == True:
            self.bitmap = self.baseimage.Scale(nw,nh).ConvertToBitmap()
        self.Refresh()
        event.Skip()

    def OnPaint(self,  event):
        dc = wx.PaintDC(self)
        brush = wx.Brush('black')
        dc.SetBackground(brush)
        dc.Clear()
        sx,  sy = self.GetSizeTuple()
        ix,  iy = self.baseimage.GetSize()
        x,  y = (sx/2)-(ix/2),  (sy/2)-(iy/2)
        dc.DrawBitmap(self.bitmap,  x,  y, True)

    def ShowItem(self, data):
        if isinstance(data, str):
            self.bitshow = False
        else:
            self.bitshow = True
            self.baseimage = data
            self.bitmap = self.baseimage.ConvertToBitmap()
        self.Refresh()

class CtrlPanel(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        #Controls
        self.fwd = wx.Button(self, id=wx.ID_FORWARD)
        self.bk = wx.Button(self, id=wx.ID_BACKWARD)
        self.lbl = wx.StaticText(self, -1, 'No Photos', (15, 10))

        #Sizers
        self.sizeracross = wx.BoxSizer(wx.HORIZONTAL)
        items = ((self.bk, 1, wx.ALL), (20,1), (self.lbl, 0, wx.ALL|wx.CENTER), (20,1), (self.fwd, 1, wx.ALL))
        self.sizeracross.AddMany(items)
        
        #Layout sizers
        self.SetSizer(self.sizeracross)
        self.SetAutoLayout(1)
        self.sizeracross.Fit(self)

    def SetText(self, text):
        self.lbl.SetLabel(text)
        self.sizeracross.Layout()
        #self.sizerdown.Layout()

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
        self.image = ImagePanelDC(self)
        self.ctrls = CtrlPanel(self)

        #buttons
        self.loginbutton = wx.Button(self, label='Login')
        lblalbum = wx.StaticText(self, -1, "Album Selection:", (15, 10))
        self.albumch = wx.Choice(self, -1, (100, 50), choices=[])

        # Set events.
        self.Bind(EVT_FACEBOOK_DATA, self.OnFacebookData)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnCloseWindow, menuExit)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.loginbutton.Bind(wx.EVT_BUTTON, self.OnLoginButton)
        self.ctrls.fwd.Bind(wx.EVT_BUTTON, self.OnForward)
        self.ctrls.bk.Bind(wx.EVT_BUTTON, self.OnBack)
        self.Bind(wx.EVT_CHOICE, self.EvtChoice, self.albumch)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        #
        self.albumch.Disable()

        #Sizers
        self.sizerlogin = wx.BoxSizer(wx.HORIZONTAL)
        self.sizerdown = wx.BoxSizer(wx.VERTICAL)
        items = ((self.loginbutton, 0, wx.ALL),(20,1),(lblalbum, 0, wx.ALL|wx.CENTER),(10,1),(self.albumch, 1, wx.ALL))
        self.sizerlogin.AddMany(items)
        items = [(10,10),(self.sizerlogin, 0, wx.ALL),(1,10),(self.image, 1, wx.EXPAND), (1,10), (self.ctrls, 0, wx.CENTER), (1,10)] 
        self.sizerdown.AddMany(items)

        #Layout sizers
        self.SetSizer(self.sizerdown)
        self.SetAutoLayout(1)
        self.sizerdown.Fit(self)

        self.Show(True)

    def OnAbout(self, event):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog( self, "FastTag", "About", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.
        
    def OnKeyDown(self, event):
        print '!!!'
        code = event.GetKeyCode()
        if  code == wx.WXK_RIGHT:
            self.OnForward(None) # FIXME: abuse of callback
        elif code == wx.WXK_LEFT:
            self.OnBack(None) # FIXME: abuse of callback    
        event.Skip()

    def OnLoginButton(self, event):
        if self.fbctrl.loggedin == False:
            self.SetStatusText("Logging in to Facebook")
            self.fbctrl.loginstart()

            dlg = wx.MessageDialog(self, "Login to Facebook then press 'Ok'",
                'Login',
                wx.CANCEL | wx.OK 
                )
            result = dlg.ShowModal()
            dlg.Destroy()
            if result == wx.ID_OK:
                self.SetStatusText("Getting Album Data...")
                self.fbctrl.logindone()
                self.fbctrl.getalbums()
                self.loginbutton.SetLabel('Logout')
        else:
            print 'logout'


    def OnForward(self, event):
        if self.currentalbum != NOALBUM:
            album = self.fbctrl.albums[self.currentalbum]
            pid = album.nextphoto()
            self.ChangePhoto(pid)

    def OnBack(self, event):
        if self.currentalbum != NOALBUM:
            album = self.fbctrl.albums[self.currentalbum]
            pid = album.lastphoto()
            self.ChangePhoto(pid)


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
                self.UpdateLbl()

        elif event.value == 'image':
            pid = event.pid
            self.pendingrequests.discard(pid)
            if len(self.pendingrequests) == 0:
                if len(self.toberequsted) > 0:
                    requestnow = self.toberequsted[:40]
                    self.toberequsted = self.toberequsted[40:]
                    self.RequestImg(*requestnow)
            self.UpdateImg()
            self.UpdateLbl()

    def ChangePhoto(self, pid):
        self.currentphoto = pid
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
        self.sizerdown.Layout()

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
    app = wx.App(redirect=False) # Don't redirect exceptions to gui
    frame = MainWindow(None, TITLE)
    app.MainLoop()
