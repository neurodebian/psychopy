import wx
import wx.lib.scrolledpanel as scrolled
import wx.aui
import sys, os, glob
import experiment, numpy
#import psychopy
from keybindings import *

## global variables
homeDir = os.getcwd()
#on mac __file__ might be a local path
fullAppPath= os.path.abspath(__file__)
appDir, appName = os.path.split(fullAppPath)
#psychopyDir, junk = os.path.split(psychopy.__file__)
#get path to settings
join = os.path.join
if sys.platform=='win32':
    settingsFolder = join(os.environ['APPDATA'],'PsychoPy', 'Builder') #this is the folder that this file is stored in
else:
    settingsFolder = join(os.environ['HOME'], '.PsychoPy' , 'Builder')
    
if not os.path.isdir(settingsFolder):
    os.makedirs(settingsFolder)
optionsPath = join(settingsFolder, 'options.pickle')
#path to Resources (icons etc)
if os.path.isdir(join(appDir, '..','Resources')):
    iconDir = join(appDir, '..','Resources')
else:iconDir = appDir

eventTypes=['Patch','Text','Movie','Sound','Mouse','Keyboard']

#for demos we need a dict where the event ID will correspond to a filename
demoList = glob.glob(os.path.join(appDir,'demos','*.py'))
if '__init__.py' in demoList: demoList.remove('__init__.py')    
#demoList = glob.glob(os.path.join(appDir,'..','demos','*.py'))
ID_DEMOS = \
    map(lambda _makeID: wx.NewId(), range(len(demoList)))
demos={}
for n in range(len(demoList)):
    demos[ID_DEMOS[n]] = demoList[n]
    
#create wx event/object IDs
ID_EXIT=wx.NewId()
#edit menu
ID_CUT=wx.NewId()
ID_COPY=wx.NewId()
ID_PASTE=wx.NewId()
#experiment menu
ID_ADDROUTINE=wx.NewId()
#view menu
#tools menu
ID_OPEN_MONCENTER=wx.NewId()
ID_RUNFILE=wx.NewId()
ID_STOPFILE=wx.NewId()
#help menu
ID_ABOUT=wx.ID_ABOUT#wx.NewId()
ID_LICENSE=wx.NewId()
ID_PSYCHO_TUTORIAL=wx.NewId()
ID_PSYCHO_HOME=wx.NewId()
ID_PSYCHO_REFERENCE=wx.NewId()

#toolbar IDs
TB_FILENEW=10
TB_FILEOPEN=20
TB_FILESAVE=30
TB_FILESAVEAS=40
TB_UNDO= 70
TB_REDO= 80
TB_RUN = 100
TB_STOP = 110

def addDlgField(self, sizer, label='', initial='', hint=''):
        """
        Adds a (labelled) input field to a dialogue box
        Returns a handle to the field (but not to the label).
        
        usage: field = addDlgField(sizer, label='', initial='', hint='')
        
        """
        if type(initial)==numpy.ndarray:
            initial=initial.tolist() #convert numpy arrays to lists
        labelLength = wx.Size(9*len(label)+16,25)#was 8*until v0.91.4
        container=wx.BoxSizer(wx.HORIZONTAL)
        inputLabel = wx.StaticText(self,-1,label,
                                        size=labelLength,
                                        style=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        if label=='text':
            #for text input we need a bigger (multiline) box
            inputBox = wx.TextCtrl(self,-1,str(initial),
                style=wx.TE_MULTILINE,
                size=wx.Size(30*self.maxFieldLength,-1))            
        else:
            inputBox = wx.TextCtrl(self,-1,str(initial),size=wx.Size(10*self.maxFieldLength,-1))
        inputBox.SetToolTipString(hint)
        container.Add(inputLabel, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, border=3)
        container.Add(inputBox,proportion=1, flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL, border=3)
        sizer.Add(container, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, border=3)
        
        return inputBox
    
class FlowPanel(scrolled.ScrolledPanel):
    def __init__(self, parent, id=-1,size = (600,100)):
        """A panel that shows how the routines will fit together
        """
        scrolled.ScrolledPanel.__init__(self, parent, id, (0, 0), size=size)
        self.panel = wx.Panel(self,-1,size=(600,200))
        self.parent=parent   
        self.needUpdate=True
        self.maxWidth  = 1000
        self.maxHeight = 200
        self.mousePos = None
        #if we're adding a loop or routine then add spots to timeline
        self.drawNearestRoutinePoint = True
        self.drawNearestLoopPoint = False
        self.pointsToDraw=[] #lists the x-vals of points to draw, eg loop locations
        
        self.btnSizer = wx.BoxSizer(wx.VERTICAL)
        self.btnInsertRoutine = wx.Button(self,-1,'Insert Routine')   
        self.btnInsertLoop = wx.Button(self,-1,'Insert Loop')    
        
        #bind events     
        self.Bind(wx.EVT_BUTTON, self.onInsertRoutine,self.btnInsertRoutine) 
        self.Bind(wx.EVT_BUTTON, self.onInsertLoop,self.btnInsertLoop) 
        self.Bind(wx.EVT_PAINT, self.onPaint)
        
        #self.SetAutoLayout(True)
        self.SetVirtualSize((self.maxWidth, self.maxHeight))
        self.SetScrollRate(20,20)
        
        self.btnSizer.Add(self.btnInsertRoutine)
        self.btnSizer.Add(self.btnInsertLoop) 
        self.SetSizer(self.btnSizer)
        
    def onInsertRoutine(self, evt):
        """Someone pushed the insert routine button.
        Fetch the dialog
        """
        exp = self.parent.exp
        
        #add routine points to the timeline
        self.setDrawPoints('routines')
        self.Refresh()
        
        #bring up listbox to choose the routine to add and/or create a new one
        addRoutineDlg = DlgAddRoutineToFlow(parent=self.parent, 
                    possPoints=self.pointsToDraw)
        if addRoutineDlg.ShowModal()==wx.ID_OK:
            newRoutine = exp.routines[addRoutineDlg.routine]#fetch the routine with the returned name
            exp.flow.addRoutine(newRoutine, addRoutineDlg.loc)
            
        #remove the points from the timeline
        self.setDrawPoints(None)
        self.Refresh()
        
    def onInsertLoop(self, evt):
        """Someone pushed the insert loop button.
        Fetch the dialog
        """
        exp = self.parent.exp
        
        #add routine points to the timeline
        self.setDrawPoints('loops')
        self.Refresh()
        
        #bring up listbox to choose the routine to add and/or create a new one
        addLoopDlg = DlgLoopProperties(parent=self.parent)
        #remove the points from the timeline
        self.setDrawPoints(None)
        self.Refresh()

    def onPaint(self, evt=None):
        """This should not be called. Use FlowPanel.Refresh()
        """                
        expFlow = self.parent.exp.flow #retrieve the current flow from the experiment
        
        #must create a fresh drawing context each frame (not store one)
        pdc = wx.PaintDC(self)
        try: dc = wx.GCDC(pdc)
        except: dc = pdc
        
        font = dc.GetFont()
        
        #draw the main time line
        linePos = 80
        dc.DrawLine(x1=100,y1=linePos,x2=500,y2=linePos)
        
        #step through components in flow
        currX=120; gap=40
        self.loopInits = []
        self.loopTerms = []
        self.gapMidPoints=[currX-gap/2]
        for entry in expFlow:
            if entry.getType()=='LoopInitiator':                
                self.loopInits.append(currX)
            if entry.getType()=='LoopTerminator':
                self.drawLoopAttach(dc,pos=[currX,linePos])
                self.loopTerms.append(currX)
            if entry.getType()=='Routine':
                currX = self.drawFlowBox(dc,entry.name, pos=[currX,linePos-40])
            self.gapMidPoints.append(currX+gap/2)
            currX+=gap
            
        #draw the loops second    
        self.loopTerms.reverse()#reverse the terminators, so that last term goes with first init   
        for n in range(len(self.loopInits)):
            self.drawFlowLoop(dc,'Flow1',startX=self.loopInits[n],
                        endX=self.loopTerms[n],base=linePos,height=20)
            self.drawLoopAttach(dc,pos=[self.loopInits[n],linePos])
            self.drawLoopAttach(dc,pos=[self.loopTerms[n],linePos])
        
        #draw all possible locations for routines 
        for n, xPos in enumerate(self.pointsToDraw):
            font.SetPointSize(8)
            dc.SetFont(font)
            w,h = dc.GetFullTextExtent(str(len(self.pointsToDraw)))[0:2]
            dc.SetPen(wx.Pen(wx.Colour(0,0,0, 255)))
            dc.SetBrush(wx.Brush(wx.Colour(0,0,0,255)))
            dc.DrawCircle(xPos,linePos, w+2)
            dc.SetPen(wx.Pen(wx.Colour(255,255,255,255)))
            dc.DrawText(str(n), xPos-w/2, linePos-h/2)
                
        self.needUpdate=False
    def setDrawPoints(self, ptType, startPoint=None):
        """Set the points of 'routines', 'loops', or None
        """
        if ptType=='routines':
            self.pointsToDraw=self.gapMidPoints
        elif ptType=='loops':
            self.pointsToDraw=self.gapMidPoints
        else:
            self.pointsToDraw=[]
    def drawLoopAttach(self, dc, pos):
        #draws a spot that a loop will later attach to
        dc.SetBrush(wx.Brush(wx.Colour(100,100,100, 250)))
        dc.SetPen(wx.Pen(wx.Colour(0,0,0, 255)))
        dc.DrawCirclePoint(pos,3)
    def drawFlowBox(self,dc, name,rgb=[200,50,50],pos=[0,0]):
        font = dc.GetFont()
        font.SetPointSize(24)
        r, g, b = rgb

        #get size based on text
        dc.SetFont(font)
        w,h = dc.GetFullTextExtent(name)[0:2]
        pad = 20
        #draw box
        rect = wx.Rect(pos[0], pos[1], w+pad,h+pad) 
        endX = pos[0]+w+20
        #the edge should match the text
        dc.SetPen(wx.Pen(wx.Colour(r, g, b, wx.ALPHA_OPAQUE)))
        #for the fill, draw once in white near-opaque, then in transp colour
        dc.SetBrush(wx.Brush(wx.Colour(255,255,255, 250)))
        dc.DrawRoundedRectangleRect(rect, 8)   
        dc.SetBrush(wx.Brush(wx.Colour(r,g,b,50)))
        dc.DrawRoundedRectangleRect(rect, 8)   
        #draw text        
        dc.SetTextForeground(rgb) 
        dc.DrawText(name, pos[0]+pad/2, pos[1]+pad/2)
        return endX
    def drawFlowLoop(self,dc,name,startX,endX,base,height,rgb=[200,50,50]):
        xx = [endX,  endX,   endX,   endX-5, endX-10, startX+10,startX+5, startX, startX, startX]
        yy = [base,height+10,height+5,height, height, height,  height,  height+5, height+10, base]
        pts=[]
        for n in range(len(xx)):
            pts.append([xx[n],yy[n]])
        dc.DrawSpline(pts)
class DlgAddRoutineToFlow(wx.Dialog):
    def __init__(self, parent, possPoints, id=-1, title='Add a routine to the flow',
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self,parent,id,title,pos,size,style)
        self.parent=parent
        self.Center()
        # setup choices of routines
        routineChoices=self.parent.exp.routines.keys()
        if len(routineChoices)==0:
            routineChoices=['NO PROCEDURES EXIST']
        self.choiceRoutine=wx.ComboBox(parent=self,id=-1,value=routineChoices[0],
                            choices=routineChoices, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.EvtRoutineChoice, self.choiceRoutine)
        
        #location choices
        ptStrings = []#convert possible points to strings
        for n, pt in enumerate(possPoints):
            ptStrings.append(str(n))
        self.choiceLoc=wx.ComboBox(parent=self,id=-1,value=ptStrings[0],
                            choices=ptStrings, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.EvtLocChoice, self.choiceLoc)
        
        #add OK, cancel
        self.btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btnOK = wx.Button(self, wx.ID_OK)
        if routineChoices==['NO PROCEDURES EXIST']:
            self.btnOK.Enable(False)
        self.btnCancel = wx.Button(self, wx.ID_CANCEL)
        self.btnSizer.Add(self.btnOK)
        self.btnSizer.Add(self.btnCancel)        
        
        #put into main sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.choiceRoutine)
        self.sizer.Add(self.choiceLoc)
        self.sizer.Add(self.btnSizer)
        self.SetSizerAndFit(self.sizer)
        
        self.routine=routineChoices[0]
        self.loc=0
                        
    def EvtRoutineChoice(self, event):
        name = event.GetString()
        self.routine=event.GetString() 
    def EvtLocChoice(self, event):
        name = event.GetString()        
        if event.GetString() == 'Select a location':
            self.btnOK.Enable(False)
            self.loc=None
        else:
            self.btnOK.Enable(True)
            self.loc=int(event.GetString())
                    
class RoutinePage(scrolled.ScrolledPanel):
    """A frame to represent a single routine
    """
    def __init__(self, parent, id=-1, routine=None):
        scrolled.ScrolledPanel.__init__(self, parent, id)
        self.panel = wx.Panel(self)
        self.parent=parent       
        self.routine=routine
        self.yPositions=None
        
        self.yPosTop=60
        self.componentStep=50#the step in Y between each component
        self.iconXpos = 100 #the left hand edge of the icons
        self.timeXposStart = 200
        self.timeXposEnd = 600
        self.timeMax = 10
        self.componentButtons={}
        self.componentLabels={}
        self.Bind(wx.EVT_PAINT, self.onPaint)
    def redrawComponentControls(self):
        ypos = self.yPosTop
        
        #delete the previous ones
        for btnName in self.componentButtons:
            self.componentButtons[btnName].Destroy()
            self.componentLabels[btnName].Destroy()
        self.componentButtons={}
        self.componentLabels={}
        
        #step through the components adding buttons
        for component in self.routine:
            name = component.params['name']
            ypos += self.componentStep
            
            bitmap = self.parent.parent.bitmaps[component.type]   
            btn = wx.BitmapButton(self, -1, bitmap, (self.iconXpos,ypos),
                    (bitmap.GetWidth()+10, bitmap.GetHeight()+10),style=wx.NO_BORDER,
                    name=name)  
            self.Bind(wx.EVT_BUTTON, self.editComponentProperties, btn)
            self.componentButtons[name] = btn
            
            h,w =self.GetTextExtent(name)
            label=wx.StaticText(self,-1, name, pos= (self.iconXpos-w*2,ypos+bitmap.GetHeight()/2),style=wx.ALIGN_RIGHT)
            self.componentLabels[name]=label
            
    def editComponentProperties(self, event=None):
        componentName=event.EventObject.GetName()
        component=self.routine.getComponentFromName(componentName)
        
        dlg = DlgComponentProperties(parent=self.parent,
            title=componentName+' Properties',
            params = component.params, hints=component.hints)
        self.Refresh()#just need to refresh timings section
        
    def getSecsPerPixel(self):
        return float(self.timeMax)/(self.timeXposEnd-self.timeXposStart)
    def redraw(self):
        self.redrawComponentControls()
        self.Refresh()#this will refresh the manually painted part (the timing)
        
    def onPaint(self, evt=None):
        
        #must create a fresh drawing context each frame (not store one)
        pdc = wx.PaintDC(self)
        try:
            dc = wx.GCDC(pdc)
        except:
            dc = pdc
        #draw timeline at bottom of page
        yPosBottom = max([300, self.yPosTop+len(self.routine)*self.componentStep])
        self.drawTimeLine(dc,self.yPosTop,yPosBottom)
        yPos = self.yPosTop
        
        for n, component in enumerate(self.routine):
            self.drawComponent(dc, component, yPos)
            yPos+=self.componentStep
            
            
    def drawTimeLine(self, dc, yPosTop, yPosBottom):  
        xScale = self.getSecsPerPixel()
        xSt=self.timeXposStart
        xEnd=self.timeXposEnd
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 150)))
        dc.DrawLine(x1=xSt,y1=yPosTop,
                    x2=xEnd,y2=yPosTop)
        dc.DrawLine(x1=xSt,y1=yPosBottom,
                    x2=xEnd,y2=yPosBottom)
        for lineN in range(10):
            dc.DrawLine(xSt+lineN/xScale, yPosTop,
                    xSt+lineN/xScale, yPosBottom+2)
        #add a label
        font = dc.GetFont()
        font.SetPointSize(12)
        dc.SetFont(font)
        dc.DrawText('t (secs)',xEnd+5, 
            yPosBottom-dc.GetFullTextExtent('t')[1]/2.0)#y is y-half height of text
    def drawComponent(self, dc, component, yPos):  
        """Draw the timing of one component on the timeline"""
        btn = self.componentButtons[component.params['name']]
        times = component.params['times']
        
        #draw entries on timeline
        xScale = self.getSecsPerPixel()
        dc.SetPen(wx.Pen(wx.Colour(200, 100, 100, 0)))
        #for the fill, draw once in white near-opaque, then in transp colour
        dc.SetBrush(wx.Brush(wx.Colour(200,100,100, 200)))
        h = self.componentStep/2
        if type(times[0]) in [int,float]:
            times=[times]
        for thisOcc in times:#each occasion/occurence
            st, end = thisOcc
            xSt = self.timeXposStart + st/xScale
            thisOccW = (end-st)/xScale
            dc.DrawRectangle(xSt, btn.GetPosition()[1]+h/2, thisOccW,h )
    def setComponentYpositions(self,posList):
        """receive the positions of the trak locations from the RoutinePage
        (which has created buttons for each track)
        """
        self.yPositions=posList
        
class RoutinesNotebook(wx.aui.AuiNotebook):
    """A notebook that stores one or more routines
    """
    def __init__(self, parent, id=-1):
        self.parent=parent
        wx.aui.AuiNotebook.__init__(self, parent, id)
        exp=self.parent.exp
        for routineName in exp.routines:         
            self.addRoutinePage(routineName, exp.routines[routineName])
    def getCurrentRoutine(self):
        return self.getCurrentPage().routine
    def getCurrentPage(self):
        return self.GetPage(self.GetSelection())
    def addRoutinePage(self, routineName, routine):
        routinePage = RoutinePage(parent=self, routine=routine)
        self.AddPage(routinePage, routineName)
    def createNewRoutine(self):
        dlg = wx.TextEntryDialog(self, message="What is the name for the new Routine? (e.g. instr, trial, feedback)",
            caption='New Routine')
        exp = self.parent.exp
        if dlg.ShowModal() == wx.ID_OK:
            routineName=dlg.GetValue()
            exp.addRoutine(routineName)#add to the experiment
            self.addRoutinePage(routineName, exp.routines[routineName])#then to the notebook

        dlg.Destroy()
class ComponentsPanel(scrolled.ScrolledPanel):
    def __init__(self, parent, id=-1):
        """A panel that shows how the routines will fit together
        """
        scrolled.ScrolledPanel.__init__(self,parent,id,size=(80,800))
        self.parent=parent    
        self.sizer=wx.BoxSizer(wx.VERTICAL)        
        
        # add a button for each type of event that can be added
        self.componentButtons={}; self.componentFromID={}
        for eventType in eventTypes:
            img =wx.Bitmap(
                os.path.join(iconDir,"%sAdd.png" %eventType.lower()))    
            btn = wx.BitmapButton(self, -1, img, (20, 20),
                           (img.GetWidth()+10, img.GetHeight()+10),
                           name=eventType)  
            self.componentFromID[btn.GetId()]=eventType
            self.Bind(wx.EVT_BUTTON, self.onComponentAdd,btn)  
            self.sizer.Add(btn, 0,wx.EXPAND|wx.ALIGN_CENTER )
            self.componentButtons[eventType]=btn#store it for elsewhere
            
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.SetupScrolling()
        
    def onComponentAdd(self,evt):
        componentName = self.componentFromID[evt.GetId()]
        newClassStr = componentName+'Component'
        exec('newComp = ExperimentObjects.%s()' %newClassStr)
        dlg = DlgComponentProperties(parent=self.parent,
            title=componentName+' Properties',
            params = newComp.params, hints=newComp.hints)
        if dlg.OK:
            currRoutinePage = self.parent.routinePanel.getCurrentPage()
            currRoutine = self.parent.routinePanel.getCurrentRoutine()
            currRoutine.append(newComp)#add to the actual routing
            currRoutinePage.redraw()#update the routine's view with the new component too

class DlgLoopProperties(wx.Dialog):    
    def __init__(self,parent,title="Loop properties",params=None,
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE|wx.DIALOG_NO_PARENT):
        style=style|wx.RESIZE_BORDER
        
        wx.Dialog.__init__(self, parent,-1,title,pos,size,style)
        self.parent=parent
        self.Center()
        
        self.loopTypes=['random','sequential','staircase']
        self.currentType=self.loopTypes[0]
        typeLabel = wx.StaticText(parent=self,id=-1,label='loop type')
        typeChooser=wx.Choice(parent=self, id=-1,choices=self.loopTypes)
        self.Bind(wx.EVT_CHOICE, self.onTypeChanged)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.AddMany([(typeLabel,wx.ALIGN_RIGHT), typeChooser])
        
        self.makeStaircaseCtrls()
        self.makeRandAndSeqCtrls()
        self.setCtrls(self.currentType)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(True)
        self.showAndGetData()
        
    def makeRandAndSeqCtrls(self):
        #a list of controls for the random/sequential versions
        #that can be hidden or shown
        self.randParamNames=
        self.randCtrls = []
        self.ctrlNreps=wx.TextCtrl(parent=self, value='5', size=(100,20))
        self.randCtrls.append(self.ctrlNreps)
        self.sizer.AddMany([self.ctrlNreps])
    def makeStaircaseCtrls(self):
        """Setup the controls for a StairHandler"""
        self.staircaseCtrls=[]
        self.ctrlStairNreps=wx.TextCtrl(parent=self, value='50', size=(100,20))
        self.staircaseCtrls.append(self.ctrlStairNreps)
        self.sizer.AddMany([self.ctrlStairNreps])
            
    def setCtrls(self, ctrlType):
        if ctrlType=='staircase':
            for ctrl in self.randCtrls:
                ctrl.Hide()
            for ctrl in self.staircaseCtrls:
                ctrl.Show()
        else:
            for ctrl in self.staircaseCtrls:
                ctrl.Hide()
            for ctrl in self.randCtrls:
                ctrl.Show()
        self.sizer.Layout()
    def onTypeChanged(self, evt=None):
        newType = evt.GetString()
        if newType==self.currentType:
            return
        self.setCtrls(newType)
        self.currentType = newType
    def showAndGetData(self):
        #add buttons for OK and Cancel
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        OK = wx.Button(self, wx.ID_OK, " OK ")
        OK.SetDefault()
        CANCEL = wx.Button(self, wx.ID_CANCEL, " Cancel ")
        self.sizer.AddMany([OK, CANCEL])#,1,flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.ALL,border=3)
        
        self.SetSizerAndFit(self.sizer)
        if self.ShowModal() == wx.ID_OK:
            print 'loop props returned OK'
class DlgComponentProperties(wx.Dialog):    
    def __init__(self,parent,title,params,hints,fixed=[],
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE|wx.DIALOG_NO_PARENT):
        style=style|wx.RESIZE_BORDER
        
        wx.Dialog.__init__(self, parent,-1,title,pos,size,style)
        self.parent=parent
        self.Center()
        
        self.params=params
        self.fixed=fixed
        self.hints=hints
        self.inputFields = []
        self.inputFieldTypes= []
        self.inputFieldNames= []
        self.data = []
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        keys = self.params.keys()
        keys.sort()
        
        self.maxFieldLength = 10#max( len(str(self.params[x])) for x in keys )
        types=dict([])
        
        #for components with names (all?) we want that a the top of the dlg
        if 'name' in keys:
            keys.remove('name')
            keys.insert(0,'name')
        #loop through the params    
        for field in keys:
            #create it (with a label)
            fieldCtrl=self.addField(field,self.params[field],self.hints[field]))
            if field in fixed: fieldCtrl.Disable()
            #store info abou the field
            self.inputFieldNames.append(label)
            self.inputFieldTypes.append(self.params[field])
            self.inputField.append(fieldCtrl)
                
        #show it and collect data
        self.sizer.Fit(self)
        self.showAndGetData()
        if self.OK:
            for n,thisKey in enumerate(keys):
                self.params[thisKey]=self.data[n]
                
    def addText(self, text):
        textLength = wx.Size(8*len(text)+16, 25)
        myTxt = wx.StaticText(self,-1,
                                label=text,
                                style=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL,
                                size=textLength)
        self.sizer.Add(myTxt,0,wx.ALIGN_CENTER)
        
    
        
    def showAndGetData(self):
        #add buttons for OK and Cancel
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        OK = wx.Button(self, wx.ID_OK, " OK ")
        OK.SetDefault()
        buttons.Add(OK, 0, wx.ALL,border=3)
        CANCEL = wx.Button(self, wx.ID_CANCEL, " Cancel ")
        buttons.Add(CANCEL, 0, wx.ALL,border=3)
        self.sizer.Add(buttons,1,flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.ALL,border=3)
        
        self.SetSizerAndFit(self.sizer)
        if self.ShowModal() == wx.ID_OK:
            self.data=[]
            #get data from input fields
            for n in range(len(self.inputFields)):
                thisVal = self.inputFields[n].GetValue()
                thisType= self.inputFieldTypes[n]
                #try to handle different types of input from strings
                if thisType in [tuple,list,float,int]:
                    #probably a tuple or list
                    exec("self.data.append("+thisVal+")")#evaluate it
                elif thisType==numpy.ndarray:
                    exec("self.data.append(numpy.array("+thisVal+"))")
                elif thisType==str:#a num array or string?
                    self.data.append(thisVal)
                else:
                    self.data.append(thisVal)
            self.OK=True
        else: 
            self.OK=False
        self.Destroy()
        
class BuilderFrame(wx.Frame):

    def __init__(self, parent, id=-1, title='PsychoPy Builder',
                 pos=wx.DefaultPosition, size=(800, 600),files=None,
                 style=wx.DEFAULT_FRAME_STYLE, app=None):
        wx.Frame.__init__(self, parent, id, title, pos, size, style)
        self.panel = wx.Panel(self)
        self.app=app
        #load icons for the various stimulus events 
        self.bitmaps={}
        for eventType in eventTypes:
            self.bitmaps[eventType]=wx.Bitmap( \
                os.path.join(iconDir,"%sAdd.png" %eventType.lower()))      
        
        
        #create a default experiment (maybe an empty one instead)
        self.exp = ExperimentObjects.Experiment()
        self.exp.addRoutine('trial') #create the trial routine
        self.exp.flow.addRoutine(self.exp.routines['trial'], pos=1)#add it to flow
        #adda loop to the flow as well
        trialInfo = [ {'ori':5, 'sf':1.5}, {'ori':2, 'sf':1.5},{'ori':5, 'sf':3}, ] 
        self.exp.flow.addLoop(
            ExperimentObjects.LoopHandler(name='trialLoop', loopType='rand', nReps=5, trialList = trialInfo),
            startPos=0.5, endPos=1.5,#specify positions relative to the
            )
        
        # create our panels
        self.flowPanel=FlowPanel(parent=self, size=(600,200))
        self.routinePanel=RoutinesNotebook(self)
        self.componentButtons=ComponentsPanel(self)
        
        if True: #control the panes using aui manager
            self._mgr = wx.aui.AuiManager(self)
            self._mgr.AddPane(self.routinePanel,wx.CENTER, 'Routines')
            self._mgr.AddPane(self.componentButtons, wx.RIGHT)
            self._mgr.AddPane(self.flowPanel,wx.BOTTOM, 'Flow')
#             tell the manager to 'commit' all the changes just made
            self._mgr.Update()
        else:
            self.routineSizer = wx.BoxSizer(wx.HORIZONTAL)
            self.routineSizer.Add(self.routinePanel, 0, wx.ALIGN_LEFT|wx.EXPAND, 15)
            self.routineSizer.Add(self.componentButtons,0, wx.ALIGN_RIGHT, 15) 
            self.mainSizer = wx.BoxSizer(wx.VERTICAL)
            self.mainSizer.Add(self.routineSizer, 1)
            self.mainSizer.Add(self.flowPanel, 1, wx.ALIGN_BOTTOM)
            self.SetSizer(self.mainSizer)
            
        self.SetAutoLayout(True)
        self.makeToolbar()
        self.makeMenus()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
    def makeToolbar(self):
        #---toolbar---#000000#FFFFFF----------------------------------------------
        self.toolbar = self.CreateToolBar( (wx.TB_HORIZONTAL
            | wx.NO_BORDER
            | wx.TB_FLAT))
            
        if sys.platform=='win32':
            toolbarSize=32
        else:
            toolbarSize=32 #size 16 doesn't work on mac wx
        self.toolbar.SetToolBitmapSize((toolbarSize,toolbarSize))
        new_bmp = wx.Bitmap(os.path.join(iconDir, 'filenew%i.png' %toolbarSize))
        open_bmp = wx.Bitmap(os.path.join(iconDir, 'fileopen%i.png' %toolbarSize))
        save_bmp = wx.Bitmap(os.path.join(iconDir, 'filesave%i.png' %toolbarSize))
        saveAs_bmp = wx.Bitmap(os.path.join(iconDir, 'filesaveas%i.png' %toolbarSize), wx.BITMAP_TYPE_PNG)
        undo_bmp = wx.Bitmap(os.path.join(iconDir, 'undo%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
        redo_bmp = wx.Bitmap(os.path.join(iconDir, 'redo%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
        stop_bmp = wx.Bitmap(os.path.join(iconDir, 'stop%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
        run_bmp = wx.Bitmap(os.path.join(iconDir, 'run%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
            
        self.toolbar.AddSimpleTool(TB_FILENEW, new_bmp, "New [Ctrl+N]", "Create new python file")
        self.toolbar.Bind(wx.EVT_TOOL, self.fileNew, id=TB_FILENEW)
        self.toolbar.AddSimpleTool(TB_FILEOPEN, open_bmp, "Open [Ctrl+O]", "Open an existing file'")
        self.toolbar.Bind(wx.EVT_TOOL, self.fileOpen, id=TB_FILEOPEN)
        self.toolbar.AddSimpleTool(TB_FILESAVE, save_bmp, "Save [Ctrl+S]", "Save current file")        
        self.toolbar.EnableTool(TB_FILESAVE, False)
        self.toolbar.Bind(wx.EVT_TOOL, self.fileSave, id=TB_FILESAVE)
        self.toolbar.AddSimpleTool(TB_FILESAVEAS, saveAs_bmp, "Save As... [Ctrl+Shft+S]", "Save current python file as...")
        self.toolbar.Bind(wx.EVT_TOOL, self.fileSaveAs, id=TB_FILESAVEAS)
        self.toolbar.AddSimpleTool(TB_UNDO, undo_bmp, "Undo [Ctrl+U]", "Undo last action")
        self.toolbar.Bind(wx.EVT_TOOL, self.undo, id=TB_UNDO)
        self.toolbar.AddSimpleTool(TB_REDO, redo_bmp, "Redo [Ctrl+R]", "Redo last action")
        self.toolbar.Bind(wx.EVT_TOOL, self.redo, id=TB_REDO)
        self.toolbar.AddSeparator()
        self.toolbar.AddSimpleTool(TB_RUN, run_bmp, "Run [F5]",  "Run current script")
        self.toolbar.Bind(wx.EVT_TOOL, self.runFile, id=TB_RUN)
        self.toolbar.AddSimpleTool(TB_STOP, stop_bmp, "Stop [Shift+F5]",  "Stop current script")
        self.toolbar.Bind(wx.EVT_TOOL, self.stopFile, id=TB_STOP)
        self.toolbar.EnableTool(TB_STOP,False)
        self.toolbar.Realize()
        
    def makeMenus(self):
        #---Menus---#000000#FFFFFF--------------------------------------------------
        menuBar = wx.MenuBar()
        #---_file---#000000#FFFFFF--------------------------------------------------
        self.fileMenu = wx.Menu()
        menuBar.Append(self.fileMenu, '&File')
        self.fileMenu.Append(wx.ID_NEW,     "&New\t%s" %key_new)
        self.fileMenu.Append(wx.ID_OPEN,    "&Open...\t%s" %key_open)
        self.fileMenu.Append(wx.ID_SAVE,    "&Save\t%s" %key_save)
        self.fileMenu.Append(wx.ID_SAVEAS,  "Save &as...\t%s" %key_saveas)
        self.fileMenu.Append(wx.ID_CLOSE,   "&Close file\t%s" %key_close)
        wx.EVT_MENU(self, wx.ID_NEW,  self.fileNew)
        wx.EVT_MENU(self, wx.ID_OPEN,  self.fileOpen)
        wx.EVT_MENU(self, wx.ID_SAVE,  self.fileSave)
        self.fileMenu.Enable(wx.ID_SAVE, False)
        wx.EVT_MENU(self, wx.ID_SAVEAS,  self.fileSaveAs)
        wx.EVT_MENU(self, wx.ID_CLOSE,  self.fileClose)
        
        self.editMenu = wx.Menu()
        menuBar.Append(self.editMenu, '&Edit')
        self.editMenu.Append(wx.ID_UNDO, "Undo\t%s" %key_undo, "Undo last action", wx.ITEM_NORMAL)
        wx.EVT_MENU(self, wx.ID_UNDO,  self.undo)
        self.editMenu.Append(wx.ID_REDO, "Redo\t%s" %key_redo, "Redo last action", wx.ITEM_NORMAL)
        wx.EVT_MENU(self, wx.ID_REDO,  self.redo)
        
        #---_tools---#000000#FFFFFF--------------------------------------------------
        self.toolsMenu = wx.Menu()
        menuBar.Append(self.toolsMenu, '&Tools')
        self.toolsMenu.Append(ID_OPEN_MONCENTER, "Monitor Center", "To set information about your monitor")
        wx.EVT_MENU(self, ID_OPEN_MONCENTER,  self.openMonitorCenter)
        
        self.toolsMenu.Append(ID_RUNFILE, "Run\t%s" %key_runscript, "Run the current script")
        wx.EVT_MENU(self, ID_RUNFILE,  self.runFile)        
        self.toolsMenu.Append(ID_STOPFILE, "Stop\t%s" %key_stopscript, "Run the current script")
        wx.EVT_MENU(self, ID_STOPFILE,  self.stopFile)

        #---_view---#000000#FFFFFF--------------------------------------------------
        self.viewMenu = wx.Menu()
        menuBar.Append(self.viewMenu, '&View')
                
        #---_experiment---#000000#FFFFFF--------------------------------------------------
        self.expMenu = wx.Menu()    
        menuBar.Append(self.expMenu, '&Experiment')
        self.expMenu.Append(ID_ADDROUTINE, "Add Routine", "Add a routine (e.g. the trial definition) to the experiment")
        wx.EVT_MENU(self, ID_ADDROUTINE,  self.addRoutine)
        
        #---_demos---#000000#FFFFFF--------------------------------------------------
        self.demosMenu = wx.Menu()
        #menuBar.Append(self.demosMenu, '&Demos') 
        for thisID in ID_DEMOS:
            junk, shortname = os.path.split(demos[thisID])
            self.demosMenu.Append(thisID, shortname)
            wx.EVT_MENU(self, thisID, self.loadDemo)
        
        #---_help---#000000#FFFFFF--------------------------------------------------
        self.helpMenu = wx.Menu()
        menuBar.Append(self.helpMenu, '&Help') 
        self.helpMenu.Append(ID_PSYCHO_HOME, "&PsychoPy Homepage", "Go to the PsychoPy homepage")
        wx.EVT_MENU(self, ID_PSYCHO_HOME, self.followLink)
        self.helpMenu.Append(ID_PSYCHO_TUTORIAL, "&PsychoPy Tutorial", "Go to the online PsychoPy tutorial")
        wx.EVT_MENU(self, ID_PSYCHO_TUTORIAL, self.followLink)
        
        self.helpMenu.AppendSeparator()       
        self.helpMenu.Append(ID_ABOUT, "&About...", "About PsychoPy")
        wx.EVT_MENU(self, ID_ABOUT, self.showAbout)
        self.helpMenu.Append(ID_LICENSE, "License...", "PsychoPy License")
        wx.EVT_MENU(self, ID_LICENSE, self.showLicense)
        
        self.helpMenu.AppendSubMenu(self.demosMenu, 'PsychoPy Demos')
        self.SetMenuBar(menuBar)
        
    def buildToolbar(self):
        pass

    def OnClose(self, event):
        # delete the frame
        self.Destroy()
    def fileOpen(self, event=None):
        #todo: fileOpen
        pass
    def fileNew(self, event=None):
        #todo: fileNew
        pass
    def fileClose(self, event=None):
        #todo: fileClose
        pass
    def fileSave(self, event=None):
        #todo: fileSave
        pass
    def fileSaveAs(self, event=None):
        #todo: fileSaveAs
        pass
    def undo(self, event=None):
        #todo: undo
        pass
    def redo(self, event=None):
        #todo: redo
        pass
    def loadDemo(self, event=None):
        #todo: loadDemo
        pass
    def showLicense(self, event=None):
        #todo: showLicense
        pass
    def showAbout(self, event=None):
        #todo: showAbout
        pass
    def followLink(self, event=None):
        #todo: followLink
        pass
    def runFile(self, event=None):
        #todo: runFile
        pass        
    def stopFile(self, event=None):
        #todo: stopFile
        pass
    def exportScript(self, event=None):
        #todo: exportScript
        pass
    def openMonitorCenter(self, event=None):
        #todo: openMonitorCenter
        pass
    def addRoutine(self, event=None):
        self.routinePanel.createNewRoutine()

class BuilderApp(wx.App):
    def OnInit(self):
        if len(sys.argv)>1:
            if sys.argv[1]==__name__:
                args = sys.argv[2:] # program was excecuted as "python.exe PsychoPyIDE.py %1'
            else:
                args = sys.argv[1:] # program was excecuted as "PsychoPyIDE.py %1'
        else:
            args=[]
        self.frame = BuilderFrame(None, -1, 
                                      title="PsychoPy Experiment Builder",
                                      files = args)
                                     
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True
    def MacOpenFile(self,fileName):
        self.frame.setCurrentDoc(fileName) 

if __name__=='__main__':
    app = BuilderApp(0)
    app.MainLoop()