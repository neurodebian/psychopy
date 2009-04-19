import wx
import wx.lib.scrolledpanel as scrolled
import wx.aui
import sys, os, glob, copy, pickle
import csv, pylab #these are used to read in csv files
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
ID_NEW_ROUTINE=wx.NewId()
ID_ADD_ROUTINE_TO_FLOW=wx.NewId()
ID_ADD_LOOP_TO_FLOW=wx.NewId()
ID_REM_ROUTINE_FROM_FLOW=wx.NewId()
ID_REM_LOOP_FROM_FLOW=wx.NewId()
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


global hitradius
hitradius=5
class FlowPanel(wx.ScrolledWindow):
    def __init__(self, frame, id=-1,size = (600,100)):
        """A panel that shows how the routines will fit together
        """
        wx.ScrolledWindow.__init__(self, frame, id, (0, 0), size=size)
        self.panel = wx.Panel(self,-1,size=(600,200))
        self.frame=frame   
        self.needUpdate=True
        self.maxWidth  = 1000
        self.maxHeight = 200
        self.mousePos = None
        #if we're adding a loop or routine then add spots to timeline
        self.drawNearestRoutinePoint = True
        self.drawNearestLoopPoint = False
        self.pointsToDraw=[] #lists the x-vals of points to draw, eg loop locations
        
        # create a PseudoDC to record our drawing
        self.pdc = wx.PseudoDC()
        self.pen_cache = {}
        self.brush_cache = {}
        # vars for handling mouse clicks
        self.dragid = -1
        self.lastpos = (0,0)
        self.loopFromID={}#use the ID of the drawn icon to retrieve loop object
        
        self.btnSizer = wx.BoxSizer(wx.VERTICAL)
        self.btnInsertRoutine = wx.Button(self,-1,'Insert Routine')   
        self.btnInsertLoop = wx.Button(self,-1,'Insert Loop')    
        
        self.redrawFlow()
        
        #bind events     
        self.panel.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)
        self.Bind(wx.EVT_BUTTON, self.onInsertRoutine,self.btnInsertRoutine) 
        self.Bind(wx.EVT_BUTTON, self.onInsertLoop,self.btnInsertLoop) 
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        
        #self.SetAutoLayout(True)
        self.SetVirtualSize((self.maxWidth, self.maxHeight))
        self.SetScrollRate(20,20)
        
        self.btnSizer.Add(self.btnInsertRoutine)
        self.btnSizer.Add(self.btnInsertLoop) 
        self.SetSizer(self.btnSizer)
        
    def ConvertEventCoords(self, event):
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        return (event.GetX() + (xView * xDelta),
            event.GetY() + (yView * yDelta))

    def OffsetRect(self, r):
        """Offset the rectangle, r, to appear in the given position in the window
        """
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        r.OffsetXY(-(xView*xDelta),-(yView*yDelta))

    def onInsertRoutine(self, evt):
        """Someone pushed the insert routine button.
        Fetch the dialog
        """
        
        #add routine points to the timeline
        self.setDrawPoints('routines')
        self.redrawFlow()
        
        #bring up listbox to choose the routine to add and/or create a new one
        addRoutineDlg = DlgAddRoutineToFlow(frame=self.frame, 
                    possPoints=self.pointsToDraw)
        if addRoutineDlg.ShowModal()==wx.ID_OK:
            print 'routines', self.frame.exp.routines, addRoutineDlg.routine
            newRoutine = self.frame.exp.routines[addRoutineDlg.routine]#fetch the routine with the returned name
            self.frame.exp.flow.addRoutine(newRoutine, addRoutineDlg.loc)
            self.frame.setIsModified(True)
            
        #remove the points from the timeline
        self.setDrawPoints(None)
        self.redrawFlow()
    def onRemRoutine(self,evt=None,routineName=None):
        #todo: implement removal of routines from flow
        print 'removal of routines form flow not yet implemented'
    def onInsertLoop(self, evt):
        """Someone pushed the insert loop button.
        Fetch the dialog
        """
        
        #add routine points to the timeline
        self.setDrawPoints('loops')
        self.redrawFlow()
        
        #bring up listbox to choose the routine to add and/or create a new one
        loopDlg = DlgLoopProperties(frame=self.frame)
        if loopDlg.OK:
            params = loopDlg.params
            if params['loopType']=='staircase': #['random','sequential','staircase']
                handler= loopDlg.stairHandler
            else:
                handler=loopDlg.trialHandler
            handler.params=params
            self.frame.exp.flow.addLoop(handler, startPos=loopDlg.params['endPoints'][0], endPos=loopDlg.params['endPoints'][1])
            self.frame.setIsModified(True)
        #remove the points from the timeline
        self.setDrawPoints(None)
        self.redrawFlow()
    
    def editLoopProperties(self, event=None, loop=None):
        if event:#we got here from a wx.button press (rather than our own drawn icons)
            loopName=event.EventObject.GetName()
            loop=self.routine.getLoopFromName(loopName)
        
        #add routine points to the timeline
        self.setDrawPoints('loops')
        self.redrawFlow()
        
        loopDlg = DlgLoopProperties(frame=self.frame,
            title=loop.params['name']+' Properties', loop=loop)
        if loopDlg.OK:
            params = loopDlg.params
            if params['loopType']=='staircase': #['random','sequential','staircase']
                handler= loopDlg.stairHandler
            else:
                handler=loopDlg.trialHandler
            loop.params=params
            self.frame.setIsModified(True)
        #remove the points from the timeline
        self.setDrawPoints(None)
        self.redrawFlow()
    def onRemLoop(self, event=None):
        #todo: implement the removal of loops
        print 'removing loops not implemented yet'
    
    def OnMouse(self, event):
        global hitradius
        if event.LeftDown():
            x,y = self.ConvertEventCoords(event)
            #l = self.pdc.FindObjectsByBBox(x, y)
            icons = self.pdc.FindObjects(x, y, hitradius)
            if len(icons): 
                self.editLoopProperties(loop=self.loopFromID[icons[0]])
        elif event.RightDown():
            x,y = self.ConvertEventCoords(event)
            #l = self.pdc.FindObjectsByBBox(x, y)
            l = self.pdc.FindObjects(x, y, hitradius)
            if l:
                self.pdc.SetIdGreyedOut(l[0], not self.pdc.GetIdGreyedOut(l[0]))
                r = self.pdc.GetIdBounds(l[0])
                r.Inflate(4,4)
                self.OffsetRect(r)
                self.RefreshRect(r, False)
        elif event.Dragging() or event.LeftUp():
            if self.dragid != -1:
                x,y = self.lastpos
                dx = event.GetX() - x
                dy = event.GetY() - y
                r = self.pdc.GetIdBounds(self.dragid)
                self.pdc.TranslateId(self.dragid, dx, dy)
                r2 = self.pdc.GetIdBounds(self.dragid)
                r = r.Union(r2)
                r.Inflate(4,4)
                self.OffsetRect(r)
                self.RefreshRect(r, False)
                self.lastpos = (event.GetX(),event.GetY())
            if event.LeftUp():
                self.dragid = -1
            
    
    def OnPaint(self, event):
        # Create a buffered paint DC.  It will create the real
        # wx.PaintDC and then blit the bitmap to it when dc is
        # deleted.  
        dc = wx.BufferedPaintDC(self)
        # use PrepateDC to set position correctly
        self.PrepareDC(dc)
        # we need to clear the dc BEFORE calling PrepareDC
        bg = wx.Brush(self.GetBackgroundColour())
        dc.SetBackground(bg)
        dc.Clear()
        # create a clipping rect from our position and size
        # and the Update Region
        xv, yv = self.GetViewStart()
        dx, dy = self.GetScrollPixelsPerUnit()
        x, y   = (xv * dx, yv * dy)
        rgn = self.GetUpdateRegion()
        rgn.Offset(x,y)
        r = rgn.GetBox()
        # draw to the dc using the calculated clipping rect
        self.pdc.DrawToDCClipped(dc,r)

    def redrawFlow(self, evt=None):
        expFlow = self.frame.exp.flow #retrieve the current flow from the experiment
        pdc=self.pdc
        
        pdc.Clear()#clear the screen
        pdc.RemoveAll()#clear all objects (icon buttons)
        pdc.BeginDrawing()
        
        font = self.GetFont()
        
        #draw the main time line
        linePos = 120
        pdc.DrawLine(x1=100,y1=linePos,x2=500,y2=linePos)
        
        #step through components in flow
        currX=120; gap=40
        self.loopInits = []#these will be entry indices
        self.loopTerms = []
        self.loops=[]#these will be copies of the actual loop obects
        self.gapMidPoints=[currX-gap/2]
        for entry in expFlow:
            if entry.getType()=='LoopInitiator':                
                self.loopInits.append(currX)
            if entry.getType()=='LoopTerminator':
                self.loops.append(entry.loop)
                self.loopTerms.append(currX)
            if entry.getType()=='Routine':
                currX = self.drawFlowBox(pdc,entry.name, pos=[currX,linePos-40])
            self.gapMidPoints.append(currX+gap/2)
            currX+=gap
            
        #draw the loops second    
        self.loopInits.reverse()#start with last initiator (paired with first terminator)   
        for n, loopInit in enumerate(self.loopInits):
            name = self.loops[n].params['name']#name of the trialHandler/StairHandler
            self.drawLoop(pdc,name,self.loops[n], 
                        startX=self.loopInits[n], endX=self.loopTerms[n],
                        base=linePos,height=linePos-60-n*15)
            self.drawLoopStart(pdc,pos=[self.loopInits[n],linePos])
            self.drawLoopEnd(pdc,pos=[self.loopTerms[n],linePos])
        
        #draw all possible locations for routines 
        for n, xPos in enumerate(self.pointsToDraw):
            font.SetPointSize(10)
            self.SetFont(font); pdc.SetFont(font)
            w,h = self.GetFullTextExtent(str(len(self.pointsToDraw)))[0:2]
            pdc.SetPen(wx.Pen(wx.Colour(0,0,0, 255)))
            pdc.SetBrush(wx.Brush(wx.Colour(0,0,0,255)))
            pdc.DrawCircle(xPos,linePos, w+2)
            pdc.SetTextForeground([255,255,255])   
            pdc.DrawText(str(n), xPos-w/2, linePos-h/2)
                
        pdc.EndDrawing()
        self.Refresh()#refresh the visible window after drawing (using OnPaint)
            
    def setDrawPoints(self, ptType, startPoint=None):
        """Set the points of 'routines', 'loops', or None
        """
        if ptType=='routines':
            self.pointsToDraw=self.gapMidPoints
        elif ptType=='loops':
            self.pointsToDraw=self.gapMidPoints
        else:
            self.pointsToDraw=[]
    def drawLoopEnd(self, dc, pos):
        #draws a spot that a loop will later attach to
        dc.SetBrush(wx.Brush(wx.Colour(0,0,0, 250)))
        dc.SetPen(wx.Pen(wx.Colour(0,0,0, 255)))
        dc.DrawPolygon([[5,5],[0,0],[-5,5]], pos[0],pos[1]-5)#points up
#        dc.DrawPolygon([[5,0],[0,5],[-5,0]], pos[0],pos[1]-5)#points down
    def drawLoopStart(self, dc, pos):
        #draws a spot that a loop will later attach to
        dc.SetBrush(wx.Brush(wx.Colour(0,0,0, 250)))
        dc.SetPen(wx.Pen(wx.Colour(0,0,0, 255)))
#        dc.DrawPolygon([[5,5],[0,0],[-5,5]], pos[0],pos[1]-5)
        dc.DrawPolygon([[5,0],[0,5],[-5,0]], pos[0],pos[1]-5)
    def drawFlowBox(self,dc, name,rgb=[200,50,50],pos=[0,0]):
        font = self.GetFont()
        font.SetPointSize(24)
        r, g, b = rgb
        
        #get size based on text
        self.SetFont(font); dc.SetFont(font)
        w,h = self.GetFullTextExtent(name)[0:2]
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
    def drawLoop(self,dc,name,loop,
            startX,endX,
            base,height,rgb=[0,0,0]):
        xx = [endX,  endX,   endX,   endX-5, endX-10, startX+10,startX+5, startX, startX, startX]
        yy = [base,height+10,height+5,height, height, height,  height,  height+5, height+10, base]
        pts=[]
        r,g,b=rgb
        pad=3
        dc.SetPen(wx.Pen(wx.Colour(r, g, b, 200)))
        for n in range(len(xx)):
            pts.append([xx[n],yy[n]])
        dc.DrawSpline(pts)
        
        #add a name label that can be clicked on
        font = self.GetFont()
        font.SetPointSize(12)
        self.SetFont(font); dc.SetFont(font)
        #get size based on text
        w,h = self.GetFullTextExtent(name)[0:2] 
        x = startX+(endX-startX)/2-w/2
        y = height-h/2 
        
        #draw box
        rect = wx.Rect(x-pad, y-pad, w+pad*2,h+pad*2) 
        #the edge should match the text
        dc.SetPen(wx.Pen(wx.Colour(r, g, b, 100)))
        #for the fill, draw once in white near-opaque, then in transp colour
        dc.SetBrush(wx.Brush(wx.Colour(255,255,255, 250)))
        dc.DrawRoundedRectangleRect(rect, 8)   
        dc.SetBrush(wx.Brush(wx.Colour(r,g,b,20)))
        dc.DrawRoundedRectangleRect(rect, 8)
        #draw text
        dc.SetTextForeground([r,g,b]) 
        dc.DrawText(name, x, y)
        
        ##set an id for the region where the bitmap falls (so it can act as a button)
        #see if we created this already
        id=None
        for key in self.loopFromID.keys():
            if self.loopFromID[key]==loop: 
                id=key
        if not id: #then create one and add to the dict
            id = wx.NewId()
            self.loopFromID[id]=loop
        dc.SetId(id)
        #set the area for this component
        dc.SetIdBounds(id,rect)
        
class DlgAddRoutineToFlow(wx.Dialog):
    def __init__(self, frame, possPoints, id=-1, title='Add a routine to the flow',
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self,frame,id,title,pos,size,style)
        self.frame=frame
        self.Center()
        # setup choices of routines
        routineChoices=self.frame.exp.routines.keys()
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
                    

class RoutineCanvas(wx.ScrolledWindow):
    """Represents a single routine (used as page in RoutinesNotebook)"""
    def __init__(self, notebook, id=-1, routine=None):
        """This window is based heavily on the PseudoDC demo of wxPython
        """
        wx.ScrolledWindow.__init__(self, notebook, id, (0, 0), style=wx.SUNKEN_BORDER)
        
        self.notebook=notebook
        self.frame=notebook.frame
        self.lines = []
        self.maxWidth  = 200
        self.maxHeight = 100
        self.x = self.y = 0
        self.curLine = []
        self.drawing = False

        self.SetVirtualSize((self.maxWidth, self.maxHeight))
        self.SetScrollRate(20,20)
        
        self.routine=routine
        self.yPositions=None        
        self.yPosTop=60
        self.componentStep=50#the step in Y between each component
        self.iconXpos = 100 #the left hand edge of the icons
        self.timeXposStart = 200
        self.timeXposEnd = 600
        self.timeMax = 10
        
        # create a PseudoDC to record our drawing
        self.pdc = wx.PseudoDC()
        self.pen_cache = {}
        self.brush_cache = {}
        # vars for handling mouse clicks
        self.dragid = -1
        self.lastpos = (0,0)
        self.componentFromID={}#use the ID of the drawn icon to retrieve component name 
    
        self.redrawRoutine()

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda x:None)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)
        
    def ConvertEventCoords(self, event):
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        return (event.GetX() + (xView * xDelta),
            event.GetY() + (yView * yDelta))

    def OffsetRect(self, r):
        """Offset the rectangle, r, to appear in the given position in the window
        """
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        r.OffsetXY(-(xView*xDelta),-(yView*yDelta))

    def OnMouse(self, event):
        global hitradius
        if event.LeftDown():
            x,y = self.ConvertEventCoords(event)
            #l = self.pdc.FindObjectsByBBox(x, y)
            icons = self.pdc.FindObjects(x, y, hitradius)
            if len(icons): 
                self.editComponentProperties(component=self.componentFromID[icons[0]])
        elif event.RightDown():
            x,y = self.ConvertEventCoords(event)
            #l = self.pdc.FindObjectsByBBox(x, y)
            l = self.pdc.FindObjects(x, y, hitradius)
            if l:
                self.pdc.SetIdGreyedOut(l[0], not self.pdc.GetIdGreyedOut(l[0]))
                r = self.pdc.GetIdBounds(l[0])
                r.Inflate(4,4)
                self.OffsetRect(r)
                self.RefreshRect(r, False)
        elif event.Dragging() or event.LeftUp():
            if self.dragid != -1:
                x,y = self.lastpos
                dx = event.GetX() - x
                dy = event.GetY() - y
                r = self.pdc.GetIdBounds(self.dragid)
                self.pdc.TranslateId(self.dragid, dx, dy)
                r2 = self.pdc.GetIdBounds(self.dragid)
                r = r.Union(r2)
                r.Inflate(4,4)
                self.OffsetRect(r)
                self.RefreshRect(r, False)
                self.lastpos = (event.GetX(),event.GetY())
            if event.LeftUp():
                self.dragid = -1

    def OnPaint(self, event):
        # Create a buffered paint DC.  It will create the real
        # wx.PaintDC and then blit the bitmap to it when dc is
        # deleted.  
        dc = wx.BufferedPaintDC(self)
        # use PrepateDC to set position correctly
        self.PrepareDC(dc)
        # we need to clear the dc BEFORE calling PrepareDC
        bg = wx.Brush(self.GetBackgroundColour())
        dc.SetBackground(bg)
        dc.Clear()
        # create a clipping rect from our position and size
        # and the Update Region
        xv, yv = self.GetViewStart()
        dx, dy = self.GetScrollPixelsPerUnit()
        x, y   = (xv * dx, yv * dy)
        rgn = self.GetUpdateRegion()
        rgn.Offset(x,y)
        r = rgn.GetBox()
        # draw to the dc using the calculated clipping rect
        self.pdc.DrawToDCClipped(dc,r)

    def redrawRoutine(self):
        
        self.pdc.Clear()#clear the screen
        self.pdc.RemoveAll()#clear all objects (icon buttons)
        
        self.pdc.BeginDrawing()
        #draw timeline at bottom of page
        yPosBottom = self.yPosTop+len(self.routine)*self.componentStep
        self.drawTimeLine(self.pdc,self.yPosTop,yPosBottom)
        yPos = self.yPosTop
        
        for n, component in enumerate(self.routine):
            self.drawComponent(self.pdc, component, yPos)
            yPos+=self.componentStep
        
        self.SetVirtualSize((self.maxWidth, yPos))
        self.pdc.EndDrawing()
        self.Refresh()#refresh the visible window after drawing (using OnPaint)
            
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
        font = self.GetFont()
        font.SetPointSize(12)
        dc.SetFont(font)
        dc.DrawText('t (secs)',xEnd+5, 
            yPosBottom-self.GetFullTextExtent('t')[1]/2.0)#y is y-half height of text
    def drawComponent(self, dc, component, yPos):  
        """Draw the timing of one component on the timeline"""   
        
        bitmap = self.frame.bitmaps[component.type]        
        dc.DrawBitmap(bitmap, self.iconXpos,yPos, True)
        
        font = self.GetFont()
        font.SetPointSize(12)
        dc.SetFont(font)
        
        name = component.params['name']
        #get size based on text
        w,h = self.GetFullTextExtent(name)[0:2]  
        #draw text
        x = self.iconXpos-5-w
        y = yPos+bitmap.GetHeight()/2-h/2
        dc.DrawText(name, x, y)
        
        #draw entries on timeline
        xScale = self.getSecsPerPixel()
        dc.SetPen(wx.Pen(wx.Colour(200, 100, 100, 0)))
        #for the fill, draw once in white near-opaque, then in transp colour
        dc.SetBrush(wx.Brush(wx.Colour(200,100,100, 200)))
        h = self.componentStep/2
        times = component.params['times']
        if type(times[0]) in [int,float]:
            times=[times]
        for thisOcc in times:#each occasion/occurence
            st, end = thisOcc
            xSt = self.timeXposStart + st/xScale
            thisOccW = (end-st)/xScale
            dc.DrawRectangle(xSt, y, thisOccW,h )
        
        ##set an id for the region where the bitmap falls (so it can act as a button)
        #see if we created this already
        id=None
        for key in self.componentFromID.keys():
            if self.componentFromID[key]==component: 
                id=key
        if not id: #then create one and add to the dict
            id = wx.NewId()
            self.componentFromID[id]=component
        dc.SetId(id)
        #set the area for this component
        r = wx.Rect(self.iconXpos, yPos, bitmap.GetWidth(),bitmap.GetHeight())
        dc.SetIdBounds(id,r)
                
    def editComponentProperties(self, event=None, component=None):
        if event:#we got here from a wx.button press (rather than our own drawn icons)
            componentName=event.EventObject.GetName()
            component=self.routine.getComponentFromName(componentName)
        
        dlg = DlgComponentProperties(frame=self.frame,
            title=component.params['name']+' Properties',
            params = component.params, hints=component.hints)
        if dlg.OK:
            self.redrawRoutine()#need to refresh timings section
            self.Refresh()#then redraw visible
            self.frame.setIsModified(True)
            
    def getSecsPerPixel(self):
        return float(self.timeMax)/(self.timeXposEnd-self.timeXposStart)

        
class RoutinesNotebook(wx.aui.AuiNotebook):
    """A notebook that stores one or more routines
    """
    def __init__(self, frame, id=-1):
        self.frame=frame
        wx.aui.AuiNotebook.__init__(self, frame, id)
        
        for routineName in self.frame.exp.routines:         
            self.addRoutinePage(routineName, self.frame.exp.routines[routineName])
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.onClosePane, self)
    def getCurrentRoutine(self):
        return self.getCurrentPage().routine
    def getCurrentPage(self):
        return self.GetPage(self.GetSelection())
    def addRoutinePage(self, routineName, routine):
#        routinePage = RoutinePage(parent=self, routine=routine)
        routinePage = RoutineCanvas(notebook=self, routine=routine)
        self.AddPage(routinePage, routineName)
#        self.frame.setIsModified(True)
    def removePages(self):
        for ii in range(self.GetPageCount()):
            currId = self.GetSelection()
            self.DeletePage(currId)            
    def createNewRoutine(self):
        dlg = wx.TextEntryDialog(self, message="What is the name for the new Routine? (e.g. instr, trial, feedback)",
            caption='New Routine')
        exp = self.frame.exp
        if dlg.ShowModal() == wx.ID_OK:
            routineName=dlg.GetValue()
            exp.addRoutine(routineName)#add to the experiment
            self.addRoutinePage(routineName, exp.routines[routineName])#then to the notebook
            self.frame.setIsModified(True)
        dlg.Destroy()
    def onClosePane(self, event=None):
        """Close the pane and remove the routine from the exp
        """
        #todo: check that the user really wants this!?
        routine = self.GetPage(event.GetSelection()).routine
        #update experiment object and flow window (if this is being used)
        if routine.name in self.frame.exp.routines.keys(): 
            junk=self.frame.exp.routines.pop(routine.name)
        if routine in self.frame.exp.flow:
            self.frame.exp.flow.remove(routine)
            self.frame.flowPanel.redrawFlow()
        self.frame.setIsModified(True)
class ComponentsPanel(scrolled.ScrolledPanel):
    def __init__(self, frame, id=-1):
        """A panel that shows how the routines will fit together
        """
        scrolled.ScrolledPanel.__init__(self,frame,id,size=(80,800))
        self.frame=frame    
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
        exec('newComp = experiment.%s()' %newClassStr)
        dlg = DlgComponentProperties(frame=self.frame,
            title=componentName+' Properties',
            params = newComp.params, hints=newComp.hints)
        if dlg.OK:
            currRoutinePage = self.frame.routinePanel.getCurrentPage()
            currRoutine = self.frame.routinePanel.getCurrentRoutine()
            currRoutine.append(newComp)#add to the actual routing
            currRoutinePage.redrawRoutine()#update the routine's view with the new component too
#            currRoutinePage.Refresh()#done at the end of redrawRoutine
            self.frame.setIsModified(True)
class _BaseParamsDlg(wx.Dialog):   
    def __init__(self,frame,title,params,hints,fixed=[],allowed={},
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE|wx.DIALOG_NO_PARENT):
        style=style|wx.RESIZE_BORDER
        
        wx.Dialog.__init__(self, frame,-1,title,pos,size,style)
        self.frame=frame
        self.Center()
        
        self.params=params   #dict
        self.fixed=fixed     #list
        self.allowed=allowed # dict
        self.hints=hints     # dict
        self.inputFields = {}
        self.inputFieldTypes= {}
        self.data = []
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        keys = sorted(self.params.keys())
        
        self.maxFieldLength = 10#max( len(str(self.params[x])) for x in keys )
        types=dict([])
        
        #for components with names (all?) we want that at the top of the dlg
        if 'name' in keys:
            keys.remove('name')
            keys.insert(0,'name')
        #loop through the params    
        for fieldName in keys:
            #check if it has limited set of options
            if fieldName in self.allowed.keys(): allowed=self.allowed[fieldName]
            else: allowed=[]
            #create the field (with a label)
            fieldCtrl, fieldLabel= self.addField(fieldName,self.params[fieldName], allowed,self.hints[fieldName])
            if fieldName in fixed: fieldCtrl.Disable()
            #store info about the field
            self.inputFields[fieldName] = fieldCtrl
            self.inputFieldTypes[fieldName]=type(self.params[fieldName])
            
        #show it and collect data
        self.sizer.Fit(self)
    
    def addText(self, text, size=None):
        if size==None:
            size = wx.Size(8*len(text)+16, 25)
        myTxt = wx.StaticText(self,-1,
                                label=text,
                                style=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL,
                                size=size)
        self.sizer.Add(myTxt,0,wx.ALIGN_CENTER)
        return myTxt
        
    def show(self):
        """Adds an OK and cancel button, shows dialogue. After showing a .OK
        attribute is created which is simply True or False (unlike wx.OK)
        """
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
            self.OK=True
        else: 
            self.OK=False
    def getData(self):
        """retrieves data from any fields in self.inputFields 
        (self.inputFields was populated during the __init__ function)
        """
        #get data from input fields
        self.data={}              
        for thisFieldName in self.inputFields.keys():
            thisVal = self.inputFields[thisFieldName].GetValue()
            
            thisType= self.inputFieldTypes[thisFieldName]
            #try to handle different types of input from strings
            if thisType in [tuple,list,float,int]:
                #probably a tuple or list
                exec("self.data[thisFieldName]="+thisVal+"")#evaluate it
            elif thisType==numpy.ndarray:
                exec("self.data[thisFieldName]=numpy.array("+thisVal+")")
            elif thisType==bool:
                self.data[thisFieldName] = bool(thisVal)
            elif thisType in [str, unicode]:
                self.data[thisFieldName]=thisVal
            else:
                print "GOT %s (type=%s) for %s" %(thisVal, thisType, self.inputFields[n])
            self.params[thisFieldName]=self.data[thisFieldName]
                
    def addField(self, label='', initial='',allowed=[], hint=''):
        """
        Adds a (labelled) input field to a dialogue box
        Returns a handle to the field (but not to the label)
                
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
        elif len(allowed)==2 and (True in allowed) and (False in allowed): 
            #only True or False - use a checkbox   
             inputBox = wx.CheckBox(self)
             inputBox.SetValue(initial)
        elif len(allowed)>1:
            #there are limitted options - use a Choice control
            inputBox = wx.Choice(self, choices=allowed)
        else:
            inputBox = wx.TextCtrl(self,-1,str(initial),size=wx.Size(10*self.maxFieldLength,-1))
        inputBox.SetToolTipString(hint)
        container.Add(inputLabel, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, border=3)
        container.Add(inputBox,proportion=1, flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL, border=3)
        self.sizer.Add(container, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, border=3)
        
        return inputBox, inputLabel
class DlgLoopProperties(_BaseParamsDlg):    
    def __init__(self,frame,title="Loop properties",loop=None,
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE|wx.DIALOG_NO_PARENT):
        style=style|wx.RESIZE_BORDER
        #if the loop is being created there should be no parameters
        if hasattr(loop,'type') and loop.type in ['TrialHandler','StairHandler']:
            paramsInit=loop.params; hintsInit=loop.hints
        else:
            print type(loop)
            paramsInit={'name':''}; hintsInit={'name':'e.g. trials, epochs, trialLoop'}
            
        _BaseParamsDlg.__init__(self, frame,title,
                    params={},hints={})
        self.frame=frame
        self.Center()
        self.sizer = wx.BoxSizer(wx.VERTICAL)#needs to be done before any addField calls
        
        self.maxFieldLength = 10 #max( len(str(self.params[x])) for x in keys )
        self.nameField, label = self.addField(label='name',initial=paramsInit['name'],
                    allowed=[],hint=hintsInit['name'])
        
        #create instances of the two loop types
        if hasattr(loop,'type') and loop.type=='TrialHandler':
            self.trialHandler = loop
        else:
            self.trialHandler=experiment.TrialHandler(name=paramsInit['name'],loopType='random',nReps=5,trialList=[]) #for 'random','sequential'
        if hasattr(loop,'type') and loop.type=='StairHandler':
            self.trialHandler = loop
        else:
            self.stairHandler=experiment.StairHandler(name=paramsInit['name'], 
            nReps=50, nReversals=12,
            stepSizes=[0.8,0.8,0.4,0.4,0.2], stepType='log') #for staircases
        #setup the chooser to set which type we need
        self.loopTypes=['random','sequential','staircase']
        self.currentType=self.loopTypes[0]
        self.choiceLoop, label = self.addField(label='loop type',initial=self.currentType, allowed=self.loopTypes,
            hint='How does the next trial get chosen?')
        self.endpointField, label2 = self.addField(label='endpoints',initial=[0,1], 
            hint='Where to loop from and to (see values currently shown in the flow view)')
        self.Bind(wx.EVT_CHOICE, self.onTypeChanged, self.choiceLoop)
        
        #self.makeGlobalCtrls()
        self.makeStaircaseCtrls()
        self.makeRandAndSeqCtrls()
        self.setCtrls(self.currentType)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(True)
        
        #show dialog and get most of the data
        self.show()
        if self.OK:
            self.getData()#standard data (from self.inputFields)
            #need to get additional data from non-standard fields
            self.params['name']=self.nameField.GetValue()
            exec("self.params['endPoints']= %s" %(self.endpointField.GetValue()))
            self.params['loopType']=self.currentType
            if self.currentType in ['random','sequential']:
                self.params['nReps']= int(self.randFields['nReps'].GetValue())
            else:
                self.params['nReversals']= int(self.stairFields['nReversals'].GetValue())
                self.params['nReps']= int(self.stairFields['nReps'].GetValue())                
        
    def makeRandAndSeqCtrls(self):
        #a list of controls for the random/sequential versions
        #that can be hidden or shown
        self.randFields = {}
        self.randFieldLabels={}
        self.randFieldTypes={} 
        handler=self.trialHandler
        
        #loop through the params 
        keys = handler.params.keys()  
        #add trialList stuff to the end      
        if 'trialListFile' in keys:
            keys.remove('trialListFile')
            keys.insert(-1,'trialListFile')
        if 'trialList' in keys:
            keys.remove('trialList')
            keys.insert(-1,'trialList')
        #then step through them    
        for thisFieldName in keys:
            if thisFieldName in ['name','loopType']: continue
            elif thisFieldName=='trialListFile':                
                container=wx.BoxSizer(wx.HORIZONTAL)
                if self.params.has_key('trialListFile'):
                    initPth=self.params['trialListFile']
                else: initPth='Need a .csv file'
                fieldCtrl = wx.StaticText(self,-1,self.getAbbriev(initPth),
                    style=wx.ALIGN_RIGHT,
                    size=wx.Size(30*self.maxFieldLength,-1))          
                fieldLabelCtrl=wx.Button(self, -1, "Browse...") #we don't need a label for this  
                self.Bind(wx.EVT_BUTTON, self.onBrowseTrialsFile,fieldLabelCtrl)  
                fieldType=str
                container.Add(fieldCtrl)
                container.Add(fieldLabelCtrl)
                self.sizer.Add(container)
            elif thisFieldName=='trialList':
                text = """No parameters set  """
                size = wx.Size(200, 50)
                fieldCtrl = self.trialListCtrl = self.addText(text, size)
                fieldLabelCtrl=fieldCtrl #we don't need a label for this   
                fieldType=str
            else: #normal text entry field
                #check if it has limited set of options
                if thisFieldName in handler.allowed.keys(): allowed=handler.allowed[thisFieldName]
                else: allowed=[]
                #create the field (with a label)
                fieldCtrl, fieldLabelCtrl= self.addField(thisFieldName,
                    handler.params[thisFieldName], allowed,handler.hints[thisFieldName])
                fieldType = type(handler.params[thisFieldName])
            #store info about the field
            self.randFields[thisFieldName]=fieldCtrl
            self.randFieldLabels[thisFieldName]=fieldLabelCtrl
            self.randFieldTypes[thisFieldName] =fieldType
    def getAbbriev(self, longStr, n=30):
        """for a filename (or any string actually), give the first
        5 characters, an ellipsis and then n of the final characters"""
        if len(longStr)>20:
            return longStr[0:10]+'...'+longStr[(-n+10):]
        else: return longStr
    def importTrialTypes(self, fileName):
        """Import the trial data from fileName to generate a list of dicts.
        Insert this immediately into self.params['trialList']
        """
        #use csv import library to fetch the fieldNames
        f = open(fileName,'rU')#the U converts lineendings to os.linesep
        #lines = f.read().split(os.linesep)#csv module is temperamental with line endings
        reader = csv.reader(f)#.split(os.linesep))
        fieldNames = reader.next()
        #use pylab to import data and intelligently check for data types
        #all data in one column will be given a single type (e.g. if one cell is string, all will be set to string)
        trialsArr = pylab.csv2rec(f)
        f.close()
        #convert the record array into a list of dicts
        trialList = []
        for trialN, trialType in enumerate(trialsArr):
            thisTrial ={}
            for fieldN, fieldName in enumerate(fieldNames):
                thisTrial[fieldName] = trialsArr[trialN][fieldN]
            trialList.append(thisTrial)            
        self.params['trialList']=trialList
    def makeStaircaseCtrls(self):
        """Setup the controls for a StairHandler"""
        self.stairFields = {}
        self.stairFieldTypes={}
        self.stairFieldLabels={}     
        handler=self.stairHandler
        #loop through the params
        for thisFieldName in handler.params.keys():
            if thisFieldName in ['name','loopType']: continue
            #check if it has limited set of options
            if thisFieldName in handler.allowed.keys(): allowed=handler.allowed[thisFieldName]
            else: allowed=[]
            #create the field (with a label)
            if thisFieldName=='loopType': 
                continue
            else:
                fieldCtrl, fieldLabelCtrl= self.addField(thisFieldName,
                    handler.params[thisFieldName], handler.allowed, handler.hints[thisFieldName])
                #store info about the field
                self.stairFields[thisFieldName] = fieldCtrl
                self.stairFieldLabels[thisFieldName] =fieldLabelCtrl
                self.stairFieldTypes[thisFieldName] = type(handler.params[thisFieldName])
            
            
    def setCtrls(self, ctrlType):
        #take a copy of the input fields and append the label fields        
#        randFields=copy.copy(self.randFields)#this was used when we had lists of fields instead of dicts
#        randFields.extend(self.randFieldLabels)
#        stairFields=copy.copy(self.stairFields)
#        stairFields.extend(self.stairFieldLabels)

        randFields=self.randFields.values()
        randFields.extend(self.randFieldLabels.values())
        stairFields=self.stairFields.values()
        stairFields.extend(self.stairFieldLabels.values())
        if ctrlType=='staircase':
            for ctrl in randFields: ctrl.Hide()
            for ctrl in stairFields:ctrl.Show()
        else:
            for ctrl in stairFields: ctrl.Hide()
            for ctrl in randFields: ctrl.Show()
        self.sizer.Layout()
        self.Fit()       
    def onTypeChanged(self, evt=None):
        newType = evt.GetString()
        if newType==self.currentType:
            return
        self.setCtrls(newType)
        self.currentType = newType
        
    def onBrowseTrialsFile(self, event):
        dlg = wx.FileDialog(
            self, message="Open file ...", style=wx.OPEN
            )        
        if dlg.ShowModal() == wx.ID_OK:
            newPath = dlg.GetPath()
            self.params['trialListFile'] = newPath
            self.importTrialTypes(newPath)
            self.randFields['trialListFile'].SetLabel(self.getAbbriev(newPath))
            self.randFields['trialList'].SetLabel(
                '%i trial types, with %i parameters\n%s' \
                    %(len(self.params['trialList']), \
                        len(self.params['trialList'][0]), \
                            self.params['trialList'][0].keys()))
class DlgComponentProperties(_BaseParamsDlg):    
    def __init__(self,frame,title,params,hints,fixed=[],allowed={},
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE|wx.DIALOG_NO_PARENT):
        style=style|wx.RESIZE_BORDER
        
        _BaseParamsDlg.__init__(self,frame,title,params,hints,fixed,allowed,
            pos,size,style)
        
        self.show()
        if self.OK:
            self.getData()
        self.Destroy()
        
class BuilderFrame(wx.Frame):

    def __init__(self, frame, id=-1, title='PsychoPy (Experiment Builder)',
                 pos=wx.DefaultPosition, size=(800, 600),files=None,
                 style=wx.DEFAULT_FRAME_STYLE, app=None):
        wx.Frame.__init__(self, frame, id, title, pos, size, style)
        self.panel = wx.Panel(self)
        self.app=app
        #load icons for the various stimulus events 
        self.bitmaps={}
        for eventType in eventTypes:
            self.bitmaps[eventType]=wx.Bitmap( \
                os.path.join(iconDir,"%s.png" %eventType.lower()))      
                
        #setup a blank exp
        self.filename='untitled.py'
        self.fileNew(closeCurrent=False)#don't try to close before opening
        self.exp.addRoutine('trial') #create the trial routine
        self.exp.flow.addRoutine(self.exp.routines['trial'], pos=1)#add it to flow 
        # create our panels
        self.flowPanel=FlowPanel(frame=self, size=(600,200))
        self.routinePanel=RoutinesNotebook(self)
        self.componentButtons=ComponentsPanel(self)
        self.setIsModified(False)
        self.updateWindowTitle()
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
            
        self.makeToolbar()
        self.makeMenus()
        self.SetAutoLayout(True)
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
        self.expMenu.Append(ID_NEW_ROUTINE, "New Routine", "Create a new routine (e.g. the trial definition)")
        wx.EVT_MENU(self, ID_NEW_ROUTINE,  self.addRoutine)
        self.expMenu.AppendSeparator()
        
        self.expMenu.Append(ID_ADD_ROUTINE_TO_FLOW, "Insert Routine in Flow", "Select one of your routines to be inserted into the experiment flow")
        wx.EVT_MENU(self, ID_ADD_ROUTINE_TO_FLOW,  self.flowPanel.onInsertRoutine)
        self.expMenu.Append(ID_REM_ROUTINE_FROM_FLOW, "Remove Routine from Flow", "Create a new loop in your flow window")
        wx.EVT_MENU(self, ID_REM_ROUTINE_FROM_FLOW,  self.flowPanel.onRemRoutine)
        self.expMenu.Append(ID_ADD_LOOP_TO_FLOW, "Insert Loop in Flow", "Create a new loop in your flow window")
        wx.EVT_MENU(self, ID_ADD_LOOP_TO_FLOW,  self.flowPanel.onInsertLoop)
        self.expMenu.Append(ID_REM_LOOP_FROM_FLOW, "Remove Loop from Flow", "Remove a loop from your flow window")
        wx.EVT_MENU(self, ID_REM_LOOP_FROM_FLOW,  self.flowPanel.onRemLoop)
        
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
        
    def OnClose(self, event):
        # delete the frame
        self.Destroy()
    def fileNew(self, event=None, closeCurrent=True):
        """Create a default experiment (maybe an empty one instead)"""   
        # check whether existing file is modified
        if closeCurrent: self.fileClose()          
        self.filename=='untitled.py'
        self.exp = experiment.Experiment() 
    def fileOpen(self, event=None):
        """Open a FileDialog, then load the file if possible.
        """
        #todo: check whether current file has been modified and recommend save
        dlg = wx.FileDialog(
            self, message="Open file ...", style=wx.OPEN
            )
        
        if dlg.ShowModal() != wx.ID_OK: 
            return 0
        newPath = dlg.GetPath()
        f = open(newPath)
        exp = pickle.load(f)
        f.close()
        if not hasattr(exp,'psychopyExperimentVersion'):#this indicates we have a PsychoPy Experiment object
            print 'not a valid PsychoPy builder experiment'
            return 0
        self.fileClose()#close the existing (and prompt for save if necess)
        #update exp vals
        self.exp=exp
        self.setIsModified(False)  
        #update the views
        self.flowPanel.redrawFlow()
        for thisRoutineName in self.exp.routines.keys():
            routine = self.exp.routines[thisRoutineName]
            self.routinePanel.addRoutinePage(thisRoutineName, routine)
        self.filename = newPath
        self.updateWindowTitle()
    def updateWindowTitle(self, newTitle=None):
        if newTitle==None:
            shortName = os.path.split(self.filename)[-1]
            newTitle='PsychoPy (Experiment Builder) - %s' %(shortName)
        self.SetTitle(newTitle)
    def setIsModified(self, newVal=True):
        self.isModified=newVal
        if hasattr(self, 'toolbar'):#initially there is no toolbar or menu
            self.toolbar.EnableTool(TB_FILESAVE, newVal)
            self.fileMenu.Enable(wx.ID_SAVE, newVal)
    def fileSave(self,event=None, filename=None):
        """Save file, revert to SaveAs if the file hasn't yet been saved 
        """
        if filename==None: 
            filename = self.filename
        if filename=='untitled.py':
            self.fileSaveAs(filename)
        else:
            f = open(filename, 'w')
            pickle.dump(self.exp,f)
            f.close()
        self.setIsModified(False)        
        
    def fileSaveAs(self,event=None, filename=None):
        """
        """
        if filename==None: filename = self.filename
        initPath, filename = os.path.split(filename)
        os.getcwd()
        if sys.platform=='darwin':
            wildcard="PsychoPy experiments (*.psyexp)|*.psyexp|Any file (*.*)|*"
        else:
            wildcard="PsychoPy experiments (*.psyexp)|*.psyexp|Any file (*.*)|*.*"

        dlg = wx.FileDialog(
            self, message="Save file as ...", defaultDir=initPath, 
            defaultFile=filename, style=wx.SAVE, wildcard=wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            newPath = dlg.GetPath()
            self.fileSave(event=None, filename=newPath)
            self.filename = newPath            
            self.setIsModified(False)
        try: #this seems correct on PC, but not on mac   
            dlg.destroy()
        except:
            pass
        self.updateWindowTitle()
    def fileClose(self, event=None):
        """Close the current file (and warn if it hasn't been saved)"""
        if hasattr(self, 'isModified') and self.isModified:
            dlg = wx.MessageDialog(self, message='Save changes to %s before quitting?' %self.filename,
                caption='Warning', style=wx.YES_NO|wx.CANCEL )
            resp = dlg.ShowModal()
            sys.stdout.flush()
            dlg.Destroy()
            if resp  == wx.ID_CANCEL:
                return -1 #return, don't quit
            elif resp == wx.ID_YES:
                #save then quit
                self.fileSave()
            elif resp == wx.ID_NO:
                pass #don't save just quit
        self.routinePanel.removePages()
        self.filename = 'untitled.psyexp'          
        self.setIsModified(False)
        self.updateWindowTitle()
        return 1
    def undo(self, event=None):
        #todo: undo
        pass
    def redo(self, event=None):
        #todo: redo
        pass
    def loadDemo(self, event=None):
        #todo: loadDemo
        pass
    def showAbout(self, event):
        msg = """PsychoPy %s \nWritten by Jon Peirce.\n
        It has a liberal license; basically, do what you like with it, 
        don't kill me if something doesn't work! :-) But do let me know...
        psychopy-users@googlegroups.com
        """ %psychopy.__version__
        dlg = wx.MessageDialog(None, message=msg,
                              caption = "About PsychoPy", style=wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
    def showLicense(self, event):
        licFile = open(os.path.join(self.app.dirPsychopy,'LICENSE.txt'))
        licTxt = licFile.read()
        licFile.close()
        dlg = wx.MessageDialog(self, licTxt,
                              "PsychoPy License", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
    def followLink(self, event=None):
        #todo: add links to help menu and a method her to follow them
        pass
    def runFile(self, event=None):
        #todo: runFile
        script = self.exp.generateScript()
        print script.getvalue()      
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
                                      title="PsychoPy (Experiment Builder)",
                                      files = args)
                                     
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True
    def MacOpenFile(self,fileName):
        self.frame.setCurrentDoc(fileName) 

if __name__=='__main__':
    app = BuilderApp(0)
    app.MainLoop()