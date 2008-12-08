import wx, sys, os
from keybindings import *
import psychopy, coder, builder

## global variables
homeDir = os.getcwd()
#on mac __file__ might be a local path
fullAppPath= os.path.abspath(__file__)
appDir, appName = os.path.split(fullAppPath)
#get path to settings
join = os.path.join
if sys.platform=='win32':
    settingsFolder = join(os.environ['APPDATA'],'PsychoPy', 'IDE') #this is the folder that this file is stored in
else:
    settingsFolder = join(os.environ['HOME'], '.PsychoPy' , 'IDE')
    
if not os.path.isdir(settingsFolder):
    os.makedirs(settingsFolder)
optionsPath = join(settingsFolder, 'options.pickle')
#path to Resources (icons etc)
if os.path.isdir(join(appDir, 'Resources')):
    iconDir = join(appDir, 'Resources')
else:iconDir = appDir

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
        splashFile = os.path.join(iconDir, 'psychopySplash.png')
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
            print args
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
        
        if mainFrame == 'coder':
            self.frame = coder.CoderFrame(None, -1, 
                                      title="PsychoPy Coder (IDE) (v%s)" %psychopy.__version__,
                                      files = args)  
        else:
            print 'running builder'
            self.frame = builder.BuilderFrame(None, -1, 
                                      title="PsychoPy Experiment Builder",
                                      files = args)
        splash = PsychoSplashScreen(self.frame)
        if splash:
            splash.Show()
        
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True
    def MacOpenFile(self,fileName):
        self.frame.setCurrentDoc(fileName)
        
if __name__=='__main__':
    app = PsychoPyApp(0)
    app.MainLoop()