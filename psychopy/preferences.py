import ConfigParser, wx, os

#prefs are stored as config files for easy modification by users
prefs = ConfigParser.SafeConfigParser()
prefs.loadfp(open('prefs.cfg'))#load the defaults
prefs.load('

#app data isn't useful to user and might include arbitrary serialised python objects
#maybe we should use pickle instead of configs?
appData=ConfigParser.SafeConfigParser()

import wx, sys, os, cPickle, urllib

RUN_SCRIPTS = 'process' #'process', or 'thread' or 'dbg'
IMPORT_LIBS='none'# should be 'thread' or 'inline' or 'none'
ANALYSIS_LEVEL=1
if sys.platform=='darwin':
    ALLOW_MODULE_IMPORTS=False
else:
    ALLOW_MODULE_IMPORTS=True

#set default values
generalDefaults = dict(loadPrevFiles=True,
            defaultView='builder',
            )
coderDefaults=dict(codeFont="",
            codeFontSize="",
            outputFont="",
            outputFontSize="",
            prevFiles=[],
            recentFiles=[],
            showSourceAsst=False,
            analyseAuto=True,
            showOutput=True,
            )
builderDefaults=dict(defaultTimeUnits='secs'
            )
connectionDefaults = dict(sendStats=True,
            proxy="",#but will be updated by autoproxy setting
            autoProxy=True)

#SETUP PATHS------------------
homeDir = os.getcwd()
#on mac __file__ might be a local path
fullAppPath= os.path.abspath(__file__)
dirApp, appName = os.path.split(fullAppPath)
#get path to settings
join = os.path.join
if sys.platform=='win32':
    dirPrefs = join(os.environ['APPDATA'],'PsychoPy2') #this is the folder that this file is stored in
else:
    dirPrefs = join(os.environ['HOME'], '.PsychoPy2')
#from the directory for preferences wor out the path for preferences (incl filename)
if not os.path.isdir(dirPrefs):
    os.makedirs(dirPrefs)
pathPrefs = join(dirPrefs, 'prefs.pickle')
#path to Resources (icons etc)
if os.path.isdir(join(dirApp, 'Resources')):
    dirResources = join(dirApp, 'Resources')
else:dirResources = dirApp
#path to PsychoPy's root folder
dirPsychopy = os.path.split(dirApp)[0]
 
class Preferences:
    def __init__(self, prefsPath):
        self.general=generalDefaults
        self.coder=coderDefaults
        self.builder=builderDefaults
        self.connections=connectionDefaults        
        self.path=prefsPath
        #connections
        if self.connections['autoProxy']: self.connections['proxy'] = self.getAutoProxy()
        
        if os.path.isfile(self.path):
            self.load()
    def load(self):
        """A function to allow a class with attributes to be loaded from a 
        pickle file necessarily without having the same attribs (so additional 
        attribs can be added in future).
        """
        prefFile=fromPickle(self.path)
        for sectionName in ['general','coder','builder','connections']:#each section (builder, coder...)
            exec("current=self.%s; imported=self.%s" %(sectionName,sectionName))
            for thisPrefName in imported.keys():#a dictionary entry
                current[thisPrefName]=imported[thisPrefName]
    def save(self):
        toPickle(self.path, self)
        
    def getAutoProxy(self):
        """Fetch the proxy from the the system environment variables
        """
        if urllib.getproxies().has_key('http'):
            return urllib.getproxies()['http']
        else:
            return ""
        
class PreferencesDlg(wx.Frame):
    def __init__(self, parent, ID, title, files=[]):
        pass
def toPickle(filename, data):
    """save data (of any sort) as a pickle file
    
    simple wrapper of the cPickle module in core python
    """
    f = open(filename, 'w')
    cPickle.dump(data,f)
    f.close()

def fromPickle(filename):
    """load data (of any sort) from a pickle file
    
    simple wrapper of the cPickle module in core python
    """
    f = open(filename)
    contents = cPickle.load(f)
    f.close()
    return contents

