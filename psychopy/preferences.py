import wx, wx.stc
import os, sys, urllib
from shutil import copyfile
from psychopy import configobj, configobjValidate
from keybindings import *

#GET PATHS------------------
join = os.path.join

class Preferences:
    def __init__(self):
        self.prefsCfg=None#the config object for the preferences
        self.appDataCfg=None #the config object for the app data (users don't need to see)
        
        self.general=None
        self.coder=None
        self.builder=None
        self.connections=None        
        self.paths={}#this will remain a dictionary
        
        self.getPaths()
        self.loadAll()            
        
    def getPaths(self):
        #on mac __file__ might be a local path, so make it the full path
        thisFileAbsPath= os.path.abspath(__file__)
        dirPsychoPy = os.path.split(thisFileAbsPath)[0]
        #paths to user settings
        if sys.platform=='win32':
            dirUserPrefs = join(os.environ['APPDATA'],'psychoy2') #the folder where the user cfg file is stored
        else:
            dirUserPrefs = join(os.environ['HOME'], '.psychopy2')
        #from the directory for preferences work out the path for preferences (incl filename)
        if not os.path.isdir(dirUserPrefs):
            os.makedirs(dirUserPrefs)
        #path to Resources (icons etc)
        dirApp = join(dirPsychoPy, 'app')
        if os.path.isdir(join(dirApp, 'Resources')):
            dirResources = join(dirApp, 'Resources')
        else:dirResources = dirApp
        
        self.paths['psychopy']=dirPsychoPy
        self.paths['appDir']=dirApp
        self.paths['appFile']=join(dirApp, 'PsychoPy.py')
        self.paths['demos'] = join(dirPsychoPy, 'demos')
        self.paths['resources']=dirResources
        self.paths['userPrefs']=dirUserPrefs
        self.paths['userPrefsFile']=join(dirUserPrefs, 'prefsUser.cfg')
        self.paths['appDataFile']=join(dirUserPrefs,'appData.cfg')
        self.paths['sitePrefsFile']=join(self.paths['psychopy'], 'sitePrefs.cfg')

    def loadAll(self):
        """A function to allow a class with attributes to be loaded from a 
        pickle file necessarily without having the same attribs (so additional 
        attribs can be added in future).
        """
        #load against the spec, then validate and save to a file 
        #(this won't overwrite existing values, but will create additional ones if necess)
        prefsSpec = configobj.ConfigObj(join(self.paths['psychopy'], 'prefsSpec.cfg'), encoding='UTF8', list_values=False)
        vdt=configobjValidate.Validator()
        self.prefsCfg = configobj.ConfigObj(self.paths['sitePrefsFile'], configspec=prefsSpec)
        self.prefsCfg.validate(vdt, copy=True)#copy means all settings get saved
        if len(self.prefsCfg['general']['userPrefsFile'])==0:
            self.prefsCfg['general']['userPrefsFile']=self.paths['userPrefsFile']#set path to home
        else:
            self.paths['userPrefsFile']=self.prefsCfg['general']['userPrefsFile']#set app path to user override
        self.prefsCfg.write()#so the user can see what's (now) available
        
        #then add user prefs
        if not os.path.isfile(self.paths['userPrefsFile']):
            self.generateUserPrefsFile()#create an empty one
        self.userPrefsCfg = configobj.ConfigObj(self.paths['userPrefsFile'])
        
        #merge site prefs and user prefs
        self.prefsCfg.merge(self.userPrefsCfg)
        
        #fetch appData too against a config spec
        appDataSpec = configobj.ConfigObj(join(self.paths['appDir'], 'appDataSpec.cfg'), encoding='UTF8', list_values=False)
        self.appDataCfg = configobj.ConfigObj(self.paths['appDataFile'], configspec=appDataSpec)
        self.appDataCfg.validate(vdt, copy=True)
        
        #simplify namespace
        self.general=self.prefsCfg['general']
        self.app = self.prefsCfg['app'] 
        self.coder=self.prefsCfg['coder']
        self.builder=self.prefsCfg['builder']
        self.connections=self.prefsCfg['connections'] 
        self.appData = self.appDataCfg
        #override some platfrom-specific settings
        if sys.platform=='darwin':
            self.prefsCfg['app']['allowImportModules']=False            
        #connections
        if self.connections['autoProxy']: self.connections['proxy'] = self.getAutoProxy()
    def saveAppData(self):
        """Save the various setting to the appropriate files (or discard, in some cases)
        """
        vdt=configobjValidate.Validator()
        self.appDataCfg.validate(vdt, copy=True)#copy means all settings get saved
        self.appDataCfg.write()
    def resetSitePrefs():
        """Reset the site preferences to the original defaults (to reset user prefs, just delete entries)
        """
        copyfile(self.paths['defaultPrefs.cfg'], self.paths['sitePrefs'])
    def getAutoProxy(self):
        """Fetch the proxy from the the system environment variables
        """
        if urllib.getproxies().has_key('http'):
            return urllib.getproxies()['http']
        else:
            return ""
    def generateUserPrefsFile(self):
        """Generate a preferences file for the user (and any necessary directories)
        """
        #check for folder
        if not os.path.isdir(self.paths['userPrefs']):
            os.makedirs(self.paths['userPrefs'])
        f = open(self.paths['userPrefsFile'], 'w')
        f.write("#this file allows you to override various settings. Any setting defined in"+\
                "\n#%s\n#can be added here to override\n" %self.paths['sitePrefsFile'])
        f.close()
        
class PreferencesDlg(wx.Frame):
    def __init__(self, parent=None, ID=-1, app=None, title="PsychoPy Preferences"):
        wx.Frame.__init__(self, parent, ID, title, size=(500,700))
        panel = wx.Panel(self)
        self.nb = wx.Notebook(panel)
        self.paths = app.prefs.paths
        
        sitePage = self.makePage(self.paths['sitePrefsFile'])
        self.nb.AddPage(sitePage,"site")
        userPage = self.makePage(self.paths['userPrefsFile'])
        self.nb.AddPage(userPage, "user")

        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, wx.EXPAND)
        panel.SetSizer(sizer)
    
        self.menuBar = wx.MenuBar()
        self.fileMenu = wx.Menu()
        self.fileMenu.Append(wx.ID_CLOSE,   "&Close file\t%s" %key_close)
        wx.EVT_MENU(self, wx.ID_CLOSE,  self.fileClose)
#        wx.EVT_MENU(self, wx.ID_SAVE,  self.fileSave)
#        self.fileMenu.Enable(wx.ID_SAVE, False)
        self.menuBar.Append(self.fileMenu, "&File")
        self.SetMenuBar(self.menuBar)
        
    def makePage(self, path):
        page = wx.stc.StyledTextCtrl(parent=self.nb)
        
        # setup the style
        if sys.platform=='darwin':
            page.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,     "face:Courier New,size:10d")
        else:
            page.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,     "face:Courier,size:12d")
        page.StyleClearAll()  # Reset all to be like the default
        page.SetLexer(wx.stc.STC_LEX_PROPERTIES)
        page.StyleSetSpec(wx.stc.STC_PROPS_SECTION,"fore:#FF0000")
        page.StyleSetSpec(wx.stc.STC_PROPS_COMMENT,"fore:#007F00")
        f = open(path, 'r+')
        page.SetText(f.read())
        f.close()
        
        return page
    def fileClose(self, event):
        self.Destroy()
    def fileClose(self, event):
        self.Destroy()