'''
Created on 30 Jul 2010

@author: hex
'''
import urllib2
import wx
from cStringIO import StringIO

def retrieveimage(url):
    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    img = wx.ImageFromStream(StringIO(data))
    return img


if __name__ == '__main__':
    url = 'http://sphotos.ak.fbcdn.net/hphotos-ak-snc1/hs082.snc1/4555_91899928983_604133983_1819310_2688128_n.jpg'
    retrieveimage(url)
    print 'done'
    