import wx, sys, os, cPickle
from keybindings import *
import psychopy, coder, builder

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
optionsPath = join(dirSettings, 'PsychoPyAppOptions.pickle')
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
class PsychoSplashScreen(wx.SplashScreen):
    """
    Create a splash screen widget.
    """
    def __init__(self, parent=None):
        # This is a recipe to a the screen.
        # Modify the following variables as necessary.
        self.parent=parent
        splashFile = os.path.join(dirRes, 'psychopySplash.png')
        aBitmap = wx.Image(name = splashFile).ConvertToBitmap()
        splashStyle = wx.SPLASH_CENTRE_ON_SCREEN | wx.NO_BORDER
        # Call the constructor with the above arguments in exactly the
        # following order.
        wx.SplashScreen.__init__(self, aBitmap, splashStyle,
                                 0, parent)
        #setup statusbar  
        self.SetBackgroundColour('WHITE')
        self.status = wx.StaticText(self, -1, "Initialising PsychoPy and Libs", 
                                    wx.Point(0,250),#splash image is 640x240
                                    wx.Size(520, 20), wx.ALIGN_LEFT|wx.ALIGN_TOP)
        self.status.SetMinSize(wx.Size(520,20))
        self.Fit()
        self.Close()
        
class PsychoPyApp(wx.App):
    def OnInit(self):
        mainFrame = 'coder'
        if len(sys.argv)>1:
            if sys.argv[1]==__name__:
                args = sys.argv[2:] # program was excecuted as "python.exe PsychoPyIDE.py %1'
            else:
                args = sys.argv[1:] # program was excecuted as "PsychoPyIDE.py %1'

            #choose which frame to start with
            if args[0] in ['builder', '--builder', '-b']:
                    mainFrame='builder'
                    args = args[1:]#can remove that argument
            elif args[0][-7:]=='.psyExp':
                    mainFrame='builder'
            elif args[0] in ['coder','--coder', '-c']:
                    mainFrame='coder'
                    args = args[1:]#can remove that argument
            elif args[0][-3:]=='.py':
                    mainFrame='coder'
        else:
            args=[]
        
        #set default paths and import options
        self.dirApp = dirApp
        self.dirRes = dirRes
        self.dirPsychopy = dirPsychopy
        try:
            self.options = fromPickle(optionsPath)
        except: 
            self.options={}
            self.options['winSize']=[800,800]
            self.options['analyseAuto']=True
            self.options['showOutput']=True   
            self.options['auiPerspective']=None
            self.options['winPos']=wx.DefaultPosition
            self.options['recentFiles']={}    
            self.options['prevFiles']=[]
            if sys.platform=='darwin':
                self.options['showSourceAsst']=False  
            else:
                self.options['showSourceAsst']=True
        
        if False:# force reinitialise (don't use file)
            self.options={}
            self.options['winSize']=[800,800]
            self.options['analyseAuto']=True
            self.options['showOutput']=True   
            self.options['auiPerspective']=None
            self.options['winPos']=wx.DefaultPosition
            self.options['recentFiles']={}   
            self.options['prevFiles']=[]        
            if sys.platform=='darwin':
                self.options['showSourceAsst']=False  
            else:
                self.options['showSourceAsst']=True
                
        if mainFrame == 'coder':
            #NB a frame doesn't have an app as a parent
            self.frame = coder.CoderFrame(None, -1, 
                                      title="PsychoPy Coder (IDE) (v%s)" %psychopy.__version__,
                                      files = args, app=self)  
        else:
            #NB a frame doesn't have an app as a parent
            self.frame = builder.BuilderFrame(None, -1, 
                                      title="PsychoPy Experiment Builder",
                                      files = args, app=self)
        splash = PsychoSplashScreen(self.frame)
        if splash:
            splash.Show()
        
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True
    def MacOpenFile(self,fileName):
        self.frame.setCurrentDoc(fileName)
    def Quit(self):
        
        print 'prevFiles', self.options['prevFiles']
        toPickle(optionsPath, self.options)
        self.frame.Destroy()
#        self.Destroy()
#        sys.exit(0)
        
if __name__=='__main__':
    app = PsychoPyApp(0)
    app.MainLoop()