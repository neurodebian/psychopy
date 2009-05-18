import wx
import wx.lib.scrolledpanel as scrolled
import wx.aui
import sys, os, glob, copy, pickle
import csv, pylab #these are used to read in csv files
import experiment, numpy
#import psychopy
from keybindings import *

#TODO: this should be loaded from prefs rather than hard-coded
componentTypes=['Patch','Text','Movie','Sound','Mouse','Keyboard']

#todo: need to implement right-click context menus for flow and routine canvas!
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
TB_COMPILE=120

class FlowPanel(wx.ScrolledWindow):
    def __init__(self, frame, id=-1,size = (600,100)):
        """A panel that shows how the routines will fit together
        """
        wx.ScrolledWindow.__init__(self, frame, id, (0, 0), size=size)
        self.panel = wx.Panel(self,-1,size=(600,200))
        self.frame=frame   
        self.app=frame.app
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
        self.hitradius=5
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
            handler=loopDlg.currentHandler
            exec("ends=%s" %handler.params['endPoints'])#creates a copy of endPoints as an array
            self.frame.exp.flow.addLoop(handler, startPos=ends[0], endPos=ends[1])
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
            title=loop.params['name'].val+' Properties', loop=loop)
        if loopDlg.OK:
            if loopDlg.params['loopType'].val=='staircase': #['random','sequential','staircase']
                loop= loopDlg.stairHandler
            else:
                loop=loopDlg.trialHandler
            loop.params=loop.params
            self.frame.setIsModified(True)
        #remove the points from the timeline
        self.setDrawPoints(None)
        self.redrawFlow()
    def onRemLoop(self, event=None):
        #todo: implement the removal of loops!
        print 'removing loops not implemented yet'
    
    def OnMouse(self, event):
        if event.LeftDown():
            x,y = self.ConvertEventCoords(event)
            #l = self.pdc.FindObjectsByBBox(x, y)
            icons = self.pdc.FindObjects(x, y, self.hitradius)
            if len(icons): 
                self.editLoopProperties(loop=self.loopFromID[icons[0]])
        elif event.RightDown():
            x,y = self.ConvertEventCoords(event)
            #l = self.pdc.FindObjectsByBBox(x, y)
            l = self.pdc.FindObjects(x, y, self.hitradius)
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
        
        #step through components in flow
        currX=120; gap=40
        pdc.DrawLine(x1=100,y1=linePos,x2=100+gap,y2=linePos)
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
            pdc.DrawLine(x1=currX,y1=linePos,x2=currX+gap,y2=linePos)
            currX+=gap
            
        #draw the loops second    
        self.loopInits.reverse()#start with last initiator (paired with first terminator)   
        for n, loopInit in enumerate(self.loopInits):
            name = self.loops[n].params['name'].val#name of the trialHandler/StairHandler
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
        self.app=self.frame.app
        self.lines = []
        self.maxWidth  = 200
        self.maxHeight = 100
        self.x = self.y = 0
        self.curLine = []
        self.drawing = False

        self.SetVirtualSize((self.maxWidth, self.maxHeight))
        self.SetScrollRate(20,20)
        self.hitradius=5
        
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
        
        if event.LeftDown():
            x,y = self.ConvertEventCoords(event)
            #l = self.pdc.FindObjectsByBBox(x, y)
            icons = self.pdc.FindObjects(x, y, self.hitradius)
            if len(icons): 
                self.editComponentProperties(component=self.componentFromID[icons[0]])
        elif event.RightDown():
            x,y = self.ConvertEventCoords(event)
            #l = self.pdc.FindObjectsByBBox(x, y)
            l = self.pdc.FindObjects(x, y, self.hitradius)
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
        
        name = component.params['name'].val
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
        exec("times=%s" %component.params['times'])
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
            title=component.params['name'].val+' Properties',
            params = component.params)
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
        self.app=frame.app
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
        #todo: check that the user really wants the routine deleted
        routine = self.GetPage(event.GetSelection()).routine
        #update experiment object and flow window (if this is being used)
        if routine.name in self.frame.exp.routines.keys(): 
            del self.frame.exp.routines[routine.name]
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
        self.app=frame.app  
        self.sizer=wx.BoxSizer(wx.VERTICAL)        
        
        # add a button for each type of event that can be added
        self.componentButtons={}; self.componentFromID={}
        for componentType in componentTypes:
            img =wx.Bitmap(
                os.path.join(self.app.dirResources,"%sAdd.png" %componentType.lower()))    
            btn = wx.BitmapButton(self, -1, img, (20, 20),
                           (img.GetWidth()+10, img.GetHeight()+10),
                           name=componentType)  
            self.componentFromID[btn.GetId()]=componentType
            self.Bind(wx.EVT_BUTTON, self.onComponentAdd,btn)  
            self.sizer.Add(btn, 0,wx.EXPAND|wx.ALIGN_CENTER )
            self.componentButtons[componentType]=btn#store it for elsewhere
            
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.SetupScrolling()
        
    def onComponentAdd(self,evt):
        componentName = self.componentFromID[evt.GetId()]
        newClassStr = componentName+'Component'
        exec('newComp = experiment.%s()' %newClassStr)
        dlg = DlgComponentProperties(frame=self.frame,
            title=componentName+' Properties',
            params = newComp.params)
        if dlg.OK:
            currRoutinePage = self.frame.routinePanel.getCurrentPage()
            currRoutine = self.frame.routinePanel.getCurrentRoutine()
            currRoutine.append(newComp)#add to the actual routing
            currRoutinePage.redrawRoutine()#update the routine's view with the new component too
#            currRoutinePage.Refresh()#done at the end of redrawRoutine
            self.frame.setIsModified(True)
            
class ParamCtrls:
    def __init__(self, dlg, label, param, browse=False, noCtrls=False):
        """Create a set of ctrls for a particular Component Parameter, to be
        used in Component Properties dialogs. These need to be positioned 
        by the calling dlg.
        
        e.g.::
            param = experiment.Param(val='boo', valType='str')
            ctrls=ParamCtrls(dlg=self, label=fieldName,param=param)
            self.paramCtrls[fieldName] = ctrls #keep track of them in the dlg
            self.sizer.Add(ctrls.nameCtrl, (self.currRow,0), (1,1),wx.ALIGN_RIGHT )
            self.sizer.Add(ctrls.valueCtrl, (self.currRow,1) )
            #these are optional (the parameter might be None)
            if ctrls.typeCtrl: self.sizer.Add(ctrls.typeCtrl, (self.currRow,2) )
            if ctrls.updateCtrl: self.sizer.Add(ctrls.updateCtrl, (self.currRow,3))  
            
        If browse is True then a browseCtrl will be added (you need to bind events yourself)
        If noCtrls is True then no actual wx widgets are made, but attribute names are created
        """
        self.param = param
        self.dlg = dlg
        self.valueWidth = 150
        #param has the fields:
        #val, valType, allowedVals=[],allowedTypes=[], hint="", updates=None, allowedUpdates=None
        # we need the following
        self.nameCtrl = self.valueCtrl = self.typeCtrl = self.updateCtrl = None
        self.browseCtrl = None
        if noCtrls: return#we don't need to do any more
        
        if type(param.val)==numpy.ndarray:
            initial=initial.tolist() #convert numpy arrays to lists
        labelLength = wx.Size(self.valueWidth,25)#was 8*until v0.91.4
        self.nameCtrl = wx.StaticText(self.dlg,-1,label,size=labelLength,
                                        style=wx.ALIGN_RIGHT)
                                        
        if label=='text':
            #for text input we need a bigger (multiline) box
            self.valueCtrl = wx.TextCtrl(self.dlg,-1,str(param.val),
                style=wx.TE_MULTILINE,
                size=wx.Size(self.valueWidth,-1))     
        elif param.valType=='bool': 
            #only True or False - use a checkbox   
             self.valueCtrl = wx.CheckBox(self.dlg, size = wx.Size(self.valueWidth,-1))
             self.valueCtrl.SetValue(param.val)             
        elif len(param.allowedVals)>1:
            #there are limitted options - use a Choice control
            self.valueCtrl = wx.Choice(self.dlg, choices=param.allowedVals, size=wx.Size(self.valueWidth,-1))
            self.valueCtrl.SetStringSelection(unicode(param.val))
        else:
            #create the full set of ctrls
            self.valueCtrl = wx.TextCtrl(self.dlg,-1,str(param.val),
                        size=wx.Size(self.valueWidth,-1))

        self.valueCtrl.SetToolTipString(param.hint)
        
        #create the type control
        if len(param.allowedTypes)==0: 
            pass
        else: 
            self.typeCtrl = wx.Choice(self.dlg, choices=param.allowedTypes)
            self.typeCtrl.SetStringSelection(param.valType)
        if len(param.allowedTypes)==1: 
            self.typeCtrl.Disable()#visible but can't be changed
            
        #create update control
        if param.allowedUpdates==None or len(param.allowedUpdates)==0:
            pass
        else:
            self.updateCtrl = wx.Choice(self.dlg, choices=param.allowedUpdates)
            self.updateCtrl.SetStringSelection(param.updates)
        if param.allowedUpdates!=None and len(param.allowedUpdates)==1: 
            self.updateCtrl.Disable()#visible but can't be changed
        #create browse control
        if browse:
            self.browseCtrl = wx.Button(self.dlg, -1, "Browse...") #we don't need a label for this  
        
class _BaseParamsDlg(wx.Dialog):   
    def __init__(self,frame,title,params,
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE|wx.DIALOG_NO_PARENT|wx.TAB_TRAVERSAL):        
        wx.Dialog.__init__(self, frame,-1,title,pos,size,style)
        self.frame=frame
        self.app=frame.app
        self.Center()
        self.panel = wx.Panel(self, -1)
        self.params=params   #dict
        self.paramCtrls={}
        self.data = []
        self.sizer= wx.GridBagSizer(vgap=2,hgap=2)
        self.currRow = 0
        
        keys = sorted(self.params.keys())
        
        self.maxFieldLength = 10#max( len(str(self.params[x])) for x in keys )
        types=dict([])
        
        #for components with names (all?) we want that at the top of the dlg
        if 'name' in keys:
            keys.remove('name')
            keys.insert(0,'name')
        #create a header row of titles        
        size=wx.Size(100,-1)
        self.sizer.Add(wx.StaticText(self,-1,'Parameter',size=size, style=wx.ALIGN_CENTER),(self.currRow,0))
        self.sizer.Add(wx.StaticText(self,-1,'Value',size=size, style=wx.ALIGN_CENTER),(self.currRow,1))
        self.sizer.Add(wx.StaticText(self,-1,'Value Type',size=size, style=wx.ALIGN_CENTER),(self.currRow,2))
        self.sizer.Add(wx.StaticText(self,-1,'Update Frequency',size=size, style=wx.ALIGN_CENTER),(self.currRow,3))
        self.currRow+=1
        self.sizer.Add(wx.StaticLine(self,-1), (self.currRow,0), (1,4))
        self.currRow+=1
        
        #loop through the params
        for fieldName in keys:
            param=self.params[fieldName]
            ctrls=ParamCtrls(dlg=self, label=fieldName,param=param)
            self.paramCtrls[fieldName] = ctrls
            # self.valueCtrl = self.typeCtrl = self.updateCtrl
            self.sizer.Add(ctrls.nameCtrl, (self.currRow,0), (1,1),wx.ALIGN_RIGHT )
            self.sizer.Add(ctrls.valueCtrl, (self.currRow,1) )
            if ctrls.typeCtrl: 
                self.sizer.Add(ctrls.typeCtrl, (self.currRow,2) )
            if ctrls.updateCtrl: 
                self.sizer.Add(ctrls.updateCtrl, (self.currRow,3))      
            self.currRow+=1
        
    def addText(self, text, size=None):
        if size==None:
            size = wx.Size(8*len(text)+16, 25)
        myTxt = wx.StaticText(self,-1,
                                label=text,
                                style=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL,
                                size=size)
        self.sizer.Add(myTxt,wx.EXPAND)#add to current row spanning entire
        return myTxt
        
    def show(self):
        """Adds an OK and cancel button, shows dialogue. 
        
        This method returns wx.ID_OK (as from ShowModal), but also 
        sets self.OK to be True or False
        """
        #add buttons for OK and Cancel
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        OK = wx.Button(self, wx.ID_OK, " OK ")
        OK.SetDefault()
        buttons.Add(OK, 0, wx.ALL,border=3)
        CANCEL = wx.Button(self, wx.ID_CANCEL, " Cancel ")
        buttons.Add(CANCEL, 0, wx.ALL,border=3)
        if hasattr(self, 'currRow'):#then we are using as GridBagSizer
            self.sizer.Add(buttons, (self.currRow,2), (1,2)) 
        else:#we are using a box sizer
            self.sizer.Add(buttons)
        self.SetSizerAndFit(self.sizer)
        #do show and process return
        retVal = self.ShowModal() 
        if retVal== wx.ID_OK: self.OK=True
        else:  self.OK=False
        return wx.ID_OK
        
    def getParams(self):
        """retrieves data from any fields in self.paramCtrls 
        (populated during the __init__ function)
        
        The new data from the dlg get inserted back into the original params
        used in __init__ and are also returned from this method.
        """
        #get data from input fields
        for fieldName in self.params.keys():
            param=self.params[fieldName]
            ctrls = self.paramCtrls[fieldName]#the various dlg ctrls for this param            
            param.val = self.getCtrlValue(ctrls.valueCtrl)
            if ctrls.typeCtrl: param.valType = self.getCtrlValue(ctrls.typeCtrl)
            if ctrls.updateCtrl: param.updates = self.getCtrlValue(ctrls.updateCtrl)
        return self.params
        
    def getCtrlValue(self, ctrl):
        """Different types of control have different methods for retrieving value. 
        This function checks them all and returns the value or None.
        """
        if ctrl==None: return None
        elif hasattr(ctrl, 'GetValue'): #e.g. TextCtrl
            return ctrl.GetValue()
        elif hasattr(ctrl, 'GetStringSelection'): #for wx.Choice
            return ctrl.GetStringSelection()
        elif hasattr(ctrl, 'GetLabel'): #for wx.StaticText
            return ctrl.GetLabel()
        else:
            print "failed to retrieve the value for %s: %s" %(fieldName, ctrls.valueCtrl)
            return None
class DlgLoopProperties(_BaseParamsDlg):    
    def __init__(self,frame,title="Loop properties",loop=None,
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE|wx.DIALOG_NO_PARENT|wx.RESIZE_BORDER):       
        wx.Dialog.__init__(self, frame,-1,title,pos,size,style)
        self.frame=frame
        self.app=frame.app
        self.Center()
        self.panel = wx.Panel(self, -1)
        self.globalCtrls={}
        self.constantsCtrls={}
        self.staircaseCtrls={}
        self.data = []
        self.sizer= wx.BoxSizer(wx.VERTICAL)
        
        #create instances of the two loop types
        if loop==None:
            self.trialHandler=experiment.TrialHandler('trials',loopType='random',nReps=5,trialList=[]) #for 'random','sequential'
            self.stairHandler=experiment.StairHandler('trials', nReps=50, nReversals=12,
                stepSizes=[0.8,0.8,0.4,0.4,0.2], stepType='log', startVal=0.5) #for staircases
            self.currentType='random'
            self.currentHandler=self.trialHandler
        elif loop.type=='TrialHandler':
            self.trialHandler = self.currentHandler = loop
            self.currentType=loop.params['loopType']#could be 'random' or 'sequential'
            self.stairHandler=experiment.StairHandler('trials', nReps=50, nReversals=12,
                stepSizes=[0.8,0.8,0.4,0.4,0.2], stepType='log', startVal=0.5) #for staircases
        elif loop.type=='StairHandler':
            self.stairHandler = self.currentHandler = loop            
            self.currentType='staircase'
            experiment.TrialHandler(name=paramsInit['name'],loopType='random',nReps=5,trialList=[]) #for 'random','sequential'

        self.makeGlobalCtrls()
        self.makeConstantsCtrls()#the controls for Method of Constants
        self.makeStaircaseCtrls()
        self.setCtrls(self.currentType)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(True)
        
        #show dialog and get most of the data
        self.show()
        if self.OK:
            self.params = self.getParams()
            
    def makeGlobalCtrls(self):
        for fieldName in ['name','loopType','endPoints']: 
            container=wx.BoxSizer(wx.HORIZONTAL)#to put them in     
            self.globalCtrls[fieldName] = ctrls = ParamCtrls(self, fieldName, self.currentHandler.params[fieldName])
            container.AddMany( (ctrls.nameCtrl, ctrls.valueCtrl))
            self.sizer.Add(container)
            
        self.Bind(wx.EVT_CHOICE, self.onTypeChanged, self.globalCtrls['loopType'].valueCtrl)
        
    def makeConstantsCtrls(self):
        #a list of controls for the random/sequential versions
        #that can be hidden or shown
        handler=self.trialHandler
        #loop through the params 
        keys = handler.params.keys()  
        #add trialList stuff to the *end*      
        if 'trialListFile' in keys:
            keys.remove('trialListFile')
            keys.insert(-1,'trialListFile')
        if 'trialList' in keys:
            keys.remove('trialList')
            keys.insert(-1,'trialList')
        #then step through them    
        for fieldName in keys:
            if fieldName in self.globalCtrls.keys():
                #these have already been made and inserted into sizer
                ctrls=self.globalCtrls[fieldName]
            elif fieldName=='trialListFile':          
                container=wx.BoxSizer(wx.HORIZONTAL)
                ctrls=ParamCtrls(self, fieldName, handler.params[fieldName], browse=True) 
                self.Bind(wx.EVT_BUTTON, self.onBrowseTrialsFile,ctrls.browseCtrl)  
                container.AddMany((ctrls.nameCtrl, ctrls.valueCtrl, ctrls.browseCtrl))
                self.sizer.Add(container)
            elif fieldName=='trialList':
                if handler.params.has_key('trialList'):
                    text=self.getTrialsSummary(handler.params['trialList'])
                else: 
                    text = """No parameters set  """
                ctrls = ParamCtrls(self, 'trialList',text,noCtrls=True)#we'll create our own widgets
                size = wx.Size(200, 50)
                ctrls.valueCtrl = self.addText(text, size)#NB this automatically adds to self.sizer
                #self.sizer.Add(ctrls.valueCtrl)
            else: #normal text entry field
                container=wx.BoxSizer(wx.HORIZONTAL)
                ctrls=ParamCtrls(self, fieldName, handler.params[fieldName])
                container.AddMany((ctrls.nameCtrl, ctrls.valueCtrl))
                self.sizer.Add(container)
            #store info about the field
            self.constantsCtrls[fieldName] = ctrls
    def makeStaircaseCtrls(self):
        """Setup the controls for a StairHandler"""
        handler=self.stairHandler
        #loop through the params
        for fieldName in handler.params.keys():
            if fieldName in self.globalCtrls.keys():
                #these have already been made and inserted into sizer
                ctrls=self.globalCtrls[fieldName]
            else: #normal text entry field
                container=wx.BoxSizer(wx.HORIZONTAL)
                ctrls=ParamCtrls(self, fieldName, handler.params[fieldName])
                container.AddMany((ctrls.nameCtrl, ctrls.valueCtrl))
                self.sizer.Add(container)
            #store info about the field
            self.staircaseCtrls[fieldName] = ctrls
            
    def getAbbriev(self, longStr, n=30):
        """for a filename (or any string actually), give the first
        5 characters, an ellipsis and then n of the final characters"""
        if len(longStr)>20:
            return longStr[0:10]+'...'+longStr[(-n+10):]
        else: return longStr
    def getTrialsSummary(self, trialList):
        if type(trialList)==list and len(trialList)>0:
            return '%i trial types, with %i parameters\n%s' \
                %(len(trialList),len(trialList[0]), trialList[0].keys())
        else:
            return "No parameters set"
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
    def setCtrls(self, ctrlType):
        #choose the ctrls to show/hide
        if ctrlType=='staircase': 
            self.currentHandler = self.stairHandler
            self.currentCtrls = self.staircaseCtrls
            toHideCtrls = self.constantsCtrls
        else: 
            self.currentHandler = self.trialHandler
            self.currentCtrls = self.constantsCtrls
            toHideCtrls = self.staircaseCtrls
        #hide them
        for paramName in toHideCtrls.keys():
            ctrls = toHideCtrls[paramName]
            if ctrls.nameCtrl: ctrls.nameCtrl.Hide()
            if ctrls.valueCtrl: ctrls.valueCtrl.Hide()
            if ctrls.browseCtrl: ctrls.browseCtrl.Hide()
        #show them
        for paramName in self.currentCtrls.keys():
            ctrls = self.currentCtrls[paramName]
            if ctrls.nameCtrl: ctrls.nameCtrl.Show()
            if ctrls.valueCtrl: ctrls.valueCtrl.Show()
            if ctrls.browseCtrl: ctrls.browseCtrl.Show()
        self.sizer.Layout()
        self.Fit()       
        self.Refresh()
    def onTypeChanged(self, evt=None):
        newType = evt.GetString()
        if newType==self.currentType:
            return
        self.setCtrls(newType)
    def onBrowseTrialsFile(self, event):
        dlg = wx.FileDialog(
            self, message="Open file ...", style=wx.OPEN
            )        
        if dlg.ShowModal() == wx.ID_OK:
            newPath = dlg.GetPath()
            self.params['trialListFile'] = newPath
            self.importTrialTypes(newPath)
            self.randFields['trialListFile'].SetLabel(self.getAbbriev(newPath))
            self.randFields['trialList'].SetLabel(self.getTrialsSummary(self.params['trialList']))
    def getParams(self):
        """retrieves data and re-inserts it into the handler and returns those handler params
        """
        #get data from input fields
        for fieldName in self.currentHandler.params.keys():
            param=self.currentHandler.params[fieldName]
            ctrls = self.currentCtrls[fieldName]#the various dlg ctrls for this param     
            param.val = self.getCtrlValue(ctrls.valueCtrl)#from _baseParamsDlg (handles diff control types)
            if ctrls.typeCtrl: param.valType = ctrls.typeCtrl.GetValue()
            if ctrls.updateCtrl: param.updates = ctrls.updateCtrl.getValue()
        return self.currentHandler.params
class DlgComponentProperties(_BaseParamsDlg):    
    def __init__(self,frame,title,params,
            pos=wx.DefaultPosition, size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE|wx.DIALOG_NO_PARENT):
        style=style|wx.RESIZE_BORDER
        
        _BaseParamsDlg.__init__(self,frame,title,params,pos,size,style)
        self.frame=frame        
        self.app=frame.app
        self.show()
        if self.OK:
            self.params = self.getParams()#get new vals from dlg
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
        for componentType in componentTypes:
            self.bitmaps[componentType]=wx.Bitmap( \
                os.path.join(self.app.dirResources,"%s.png" %componentType.lower()))      
                
        #setup a blank exp
        self.filename='untitled.psyexp'
        initPath, shortname = os.path.split(self.filename)
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
        new_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'filenew%i.png' %toolbarSize))
        open_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'fileopen%i.png' %toolbarSize))
        save_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'filesave%i.png' %toolbarSize))
        saveAs_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'filesaveas%i.png' %toolbarSize), wx.BITMAP_TYPE_PNG)
        undo_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'undo%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
        redo_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'redo%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
        stop_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'stop%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
        run_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'run%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
        compile_bmp = wx.Bitmap(os.path.join(self.app.dirResources, 'compile%i.png' %toolbarSize),wx.BITMAP_TYPE_PNG)
            
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
        self.toolbar.AddSimpleTool(TB_COMPILE, compile_bmp, "Comile Script [F4]",  "Run current script")
        self.toolbar.Bind(wx.EVT_TOOL, self.compileScript, id=TB_COMPILE)
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
        #for demos we need a dict where the event ID will correspond to a filename
        demoList = glob.glob(os.path.join(self.app.dirApp,'demos','*.psyexp'))   
        #demoList = glob.glob(os.path.join(appDir,'..','demos','*.py'))
        ID_DEMOS = \
            map(lambda _makeID: wx.NewId(), range(len(demoList)))
        self.demos={}
        for n in range(len(demoList)):
            self.demos[ID_DEMOS[n]] = demoList[n]
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
        
        self.demosMenu
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
            self, message="Open file ...", style=wx.OPEN,
            wildcard="PsychoPy experiments (*.psyexp)|*.psyexp|Any file (*.*)|*",
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
        dlg = wx.MessageDialog(self, licTxt, "PsychoPy License", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
    def followLink(self, event=None):
        #todo: add links to help menu and a method her to follow them
        pass
    def runFile(self, event=None):
        #todo: runFile
        script = self.exp.writeScript()
        print script.getvalue()      
    def stopFile(self, event=None):
        #todo: stopFile
        pass
    def compileScript(self, event=None):
        #todo: exportScript
        script = self.exp.writeScript()
        if not self.app.coder:#it doesn't exist so make one
            self.app.newCoderFrame()
        name = os.path.splitext(self.filename)[0]+".py"
        self.app.coder.fileNew(filepath=name)
        self.app.coder.currentDoc.SetText(script.getvalue())
        self.app.coder.currentDoc.setFileModified(False)#it won't need saving unless user changes
    def openMonitorCenter(self, event=None):
        #todo: openMonitorCenter
        pass
    def addRoutine(self, event=None):
        self.routinePanel.createNewRoutine()
