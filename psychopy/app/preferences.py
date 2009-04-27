import wx, sys, os, cPickle, urllib

## global variables
homeDir = os.getcwd()
#on mac __file__ might be a local path
fullAppPath= os.path.abspath(__file__)
dirApp, appName = os.path.split(fullAppPath)
#get path to settings
join = os.path.join
if sys.platform=='win32':
    dirSettings = join(os.environ['APPDATA'],'PsychoPy') #this is the folder that this file is stored in
else:
    dirSettings = join(os.environ['HOME'], '.PsychoPy')
    
if not os.path.isdir(dirSettings):
    os.makedirs(dirSettings)
prefsPath = join(dirSettings, 'PsychoPy2.0.prefs')
#path to Resources (icons etc)
if os.path.isdir(join(dirApp, 'Resources')):
    dirRes = join(dirApp, 'Resources')
else:dirRes = dirApp
#path to PsychoPy's root folder
dirPsychopy = os.path.split(dirApp)[0]

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



#set default values
generalDefaults = dict(loadPrevFiles=True,
            )
coderDefaults=dict(codeFont="",
            codeFontSize="",
            outputFont="",
            outputFontSize="",
            )
builderDefaults=dict(defaultTimeUnits='secs'
            )
connectionDefaults = dict(sendStats=True,
            proxy="",#but will be updated by autoproxy setting
            autoProxy=True)

class Preferences:
    def __init__(self, prefsPath):
        self.general=generalDefaultsdict(loadPrevFiles=True,
            )
        self.coder=coderDefaults
        self.builder=builderDefaults
        self.connections=connectionDefaults
        self.psychopy=dict()
        
        self.path=prefsPath
        
        ##set some defaults
        #coder
        
        #connections
        if autoProxy: self.connections['proxy'] = self.getAutoProxy()
        #builder
        
    def loadFromPickle(self, pickleFile):
        """A function to allow a class with attributes to be loaded from a 
        pickle file necessarily without having the same attribs (so additional 
        attribs can be added in future).
        """
        prefFile=fromPickle(self.path)
        for sectionName in prefFile.keys():#each section (builder, coder...)
            section = prefFile[sectionName]
            for thisPrefName in section.keys():#a dictionary entry
                exec("self.%s[thisPrefName]=section[thisPrefName]")
                
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