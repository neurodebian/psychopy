import wx, sys, os
from keybindings import *
import psychopy, coder, builder
from preferences import *

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
        self.dirApp = dirApp#defined in the prefs
        self.dirResources = dirResources
        self.dirPsychopy = dirPsychopy
        self.pathPrefs=pathPrefs
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