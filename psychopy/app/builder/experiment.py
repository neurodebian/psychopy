import StringIO, sys

class IndentingBuffer(StringIO.StringIO):
    def __init__(self, *args, **kwargs):
        StringIO.StringIO.__init__(self, *args, **kwargs)
        self.oneIndent="    "
        self.indentLevel=0
    def writeIndented(self,text):
        """Write to the StringIO buffer, but add the current indent.
        Use write() if you don't want the indent.
        
        To test if the prev character was a newline use::
            self.getvalue()[-1]=='\n'
            
        """
        self.write(self.oneIndent*self.indentLevel + text)
    def setIndentLevel(self, newLevel, relative=False):
        """Change the indent level for the buffer to a new value.
        
        Set relative to True if you want to increment or decrement the current value.
        """
        if relative:
            self.indentLevel+=newLevel
        else:
            self.indentLevel=newLevel
        
class Experiment:
    """
    An experiment contains a single Flow and at least one
    Routine. The Flow controls how Routines are organised
    e.g. the nature of repeats and branching of an experiment.
    """
    def __init__(self):
        self.flow = Flow()
        self.routines={}
        #this can be checked by the builder that this is an experiment and a compatible version
        self.psychopyExperimentVersion='0.1' 
        
    def addRoutine(self,routineName, routine=None):
        """Add a Routine to the current list of them. 
        
        Can take a Routine object directly or will create
        an empty one if none is given.
        """
        if routine==None:
            self.routines[routineName]=Routine(routineName)#create a deafult routine with this name
        else:
            self.routines[routineName]=routine
        
    def generateScript(self):
        """Generate a PsychoPy script for the experiment
        """
        s=IndentingBuffer(u'') #a string buffer object
        s.writeIndented('"""This experiment was created using PsychoPy2 (Experiment Builder) and will\n \
run on any platform on which PsychoPy (www.psychopy.org) can be installed\n \
\nIf you publish work using this script please cite the relevant papers (e.g. Peirce, 2007;2009)"""\n\n')
        
        #delegate most of the code-writing to Flow
        self.flow.generateCode(s)
        
        return s
    def getAllObjectNames(self):
        """Return the names of all objects (routines, loops and components) in the experiment
        """
        names=[]
        for thisRoutine in self.routines:
            names.append(thisRoutine.name)
            for thisEntry in thisRoutine: 
                if isinstance(thisEntry, LoopInitiator):
                    names.append( thisEntry.loop.name )
                    print 'found loop initiator: %s' %names[-1]
                elif hasattr(thisEntry, 'params'):
                    names.append(thisEntry.params['name'])
                    print 'found component: %s' %names[-1]
                    
class TrialHandler():    
    """A looping experimental control object
            (e.g. generating a psychopy TrialHandler or StairHandler).
            """
    def __init__(self, name, loopType, nReps, 
        trialList=[], trialListFile=''):
        """
        @param name: name of the loop e.g. trials
        @type name: string
        @param loopType:
        @type loopType: string ('rand', 'seq')
        @param nReps: number of reps (for all trial types)
        @type nReps:int
        @param trialList: list of different trial conditions to be used
        @type trialList: list (of dicts?)
        @param trialListFile: filename of the .csv file that contains trialList info
        @type trialList: string (filename)
        """
        self.type='TrialHandler'
        self.params={}
        self.params['loopType']=loopType
        self.params['name'] = name
        self.params['nReps']=nReps
        self.params['trialList']=trialList
        self.params['trialListFile']=trialListFile
        self.hints={}
        self.hints['loopType']="'random','sequential'"
        self.hints['name'] = 'Name of this loop'
        self.hints['nReps']='Number of repeats (for each type of trial)'
        self.hints['trialList']="A list of dictionaries describing the differences between each trial type"
        self.hints['trialListFile']='A comma-separated-value (.csv) file specifying the parameters for each trial'
        self.allowed={}
    def generateInitCode(self,buff):
        buff.writeIndented("%s=data.TrialHandler(trialList=%s,nReps=%i,\n)" \
            %(self.params['name'], self.params['trialList'], self.params['nReps']))
    def generateLoopStartCode(self,buff):
        #work out a name for e.g. thisTrial in trials:
        thisName = ("this"+self.params['name'].capitalize()[:-1])
        buff.writeIndented("\n")
        buff.writeIndented("for %s in %s:\n" %(thisName, self.params['name']))
    def getType(self):
        return 'LoopHandler'     
class StairHandler():    
    """A staircase experimental control object.
    """
    def __init__(self, name, nReps, nReversals, stepSizes, stepType):
        """
        @param name: name of the loop e.g. trials
        @type name: string
        @param nReps: number of reps (for all trial types)
        @type nReps:int
        """
        self.params={}
        self.params['name'] = name
        self.params['nReps']=nReps
        self.params['step sizes']=stepSizes
        self.params['step type']=stepType
        self.params['nReversals']=nReversals
        self.hints={}
        self.hints['name'] = 'Name of this loop'
        self.hints['nReps']='Minimum number of trials in the staircase'
        self.hints['nReversals']='Minimum number of times the staircase must change direction before ending'
        self.hints['step type']="The units of the step size (e.g. 'linear' will add/subtract that value each step, whereas 'log' will ad that many log units)"
        self.hints['step sizes']="The size of the jump at each step (can change on each 'reversal')"
        self.allowed={}
        self.allowed['step types']=['linear','log','db']
    def generateInitCode(self,buff):
        buff.writeIndented("init loop '%s' (%s)\n" %(self.params['name'], self.loopType))
        buff.writeIndented("%s=data.StairHandler(nReps=%i,\n)" \
            %(self.name, self.nReps))
    def generateLoopStartCode(self,buff):
        #work out a name for e.g. thisTrial in trials:
        thisName = ("this"+self.params['name'].capitalize()[:-1])
        buff.writeIndented("for %s in %s:\n" %(thisName, self.params['name']))
    def getType(self):
        return 'StairHandler'   
class LoopInitiator:
    """A simple class for inserting into the flow.
    This is created automatically when the loop is created"""
    def __init__(self, loop):
        self.loop=loop        
    def generateInitCode(self,buff):
        self.loop.generateInitCode(buff)
    def generateMainCode(self,buff):
        self.loop.generateLoopStartCode(buff)
        buff.setIndentLevel(1, relative=True)#we started a loop so increment indent        
    def getType(self):
        return 'LoopInitiator'
class LoopTerminator:
    """A simple class for inserting into the flow.
    This is created automatically when the loop is created"""
    def __init__(self, loop):
        self.loop=loop
    def generateInitCode(self,buff):
        pass
    def generateMainCode(self,buff):
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndented("# end of '%s' after %i repeats (of each entry in trialList)\n" %(self.loop.params['name'], self.loop.params['nReps']))
    def getType(self):
        return 'LoopTerminator'
class Flow(list):
    """The flow of the experiment is a list of L{Routine}s, L{LoopInitiator}s and
    L{LoopTerminator}s, that will define the order in which events occur
    """
    def addLoop(self, loop, startPos, endPos):
        """Adds initiator and terminator objects for the loop
        into the Flow list"""
        self.insert(int(endPos), LoopTerminator(loop))
        self.insert(int(startPos), LoopInitiator(loop))
    def addRoutine(self, newRoutine, pos):
        """Adds the routine to the Flow list"""
        self.insert(int(pos), newRoutine)
        
    def generateCode(self, s):
        s.writeIndented("from PsychoPy import visual, core, event, sound\n")
        s.writeIndented("win = visual.Window([400,400])\n")
        
        #initialise components
        for entry in self:
            entry.generateInitCode(s)
        
        #run-time code  
        for entry in self:
            entry.generateMainCode(s)
        
class Routine(list):
    """
    A Routine determines a single sequence of events, such
    as the presentation of trial. Multiple Routines might be
    used to comprise an Experiment (e.g. one for presenting
    instructions, one for trials, one for debriefing subjects).
    
    In practice a Routine is simply a python list of Components,
    each of which knows when it starts and stops.
    """
    def __init__(self, name):
        self.name=name
        list.__init__(self)
    def generateInitCode(self,buff):
        buff.writeIndented('\n')
        buff.writeIndented('#Initialise components for %s routine\n' %self.name)
        for thisEvt in self:
            thisEvt.generateInitCode(buff)
        
    def generateMainCode(self,buff):
        """This defines the code for the frames of a single routine
        """
        clockName=self.name+"Clock"
        #create the frame loop for this routine
        buff.writeIndented('%s=core.Clock()\n' %(clockName))
        buff.writeIndented('t=0\n')
        buff.writeIndented('while t<maxTime:\n')
        buff.setIndentLevel(1,True)
        
        #on each frame
        buff.writeIndented('#get current time\n')
        buff.writeIndented('t=%s.getTime()\n\n' %clockName)
        
        #write the code for each component during frame
        for event in self:
            event.generateFrameCode(buff)
            
        #update screen
        buff.writeIndented('\n')
        buff.writeIndented('#refresh the screen\n')
        buff.writeIndented('win.flip()\n')
        
        #that's done decrement indent to end loop
        buff.setIndentLevel(-1,True)
    def getType(self):
        return 'Routine'
    def getComponentFromName(self, name):
        for comp in self:
            if comp.params['name']==name:
                return comp
        return None
    
class BaseComponent:
    """A general template for components"""
    def __init__(self, name='', times=[0,1]):
        self.type='Base'
        self.params['name']=name
        self.hints['name']= 'A name for the component'
        #for choiceboxes what are the allowed options?
        self.allowed={}
    def generateInitCode(self,buff):
        pass
    def generateRoutineCode(self,buff):
        """Generate the code that will be called at the beginning of 
        a routine (e.g. to update stimulus parameters)
        """
        pass
    def generateFrameCode(self,buff):
        """Generate the code that will be called every frame
        """
        pass
    def generateTimeTestCode(self, buff):
        """Generate the code for each frame that tests whether the component is being
        drawn/used.
        """
        times=self.params['times']
        if type(times[0]) in [int, float]:
            times=[times]#make a list of lists
        
        #write the code for the first repeat of the stimulus
        buff.writeIndented("if (%.f <= t < %.f)" %(times[0][0], times[0][1]))
        if len(times)>1:
            for epoch in times[1:]: 
                buff.write("\n")
                buff.writeIndented("    or (%.f <= t < %.f)" %(epoch[0], epoch[1]))
        buff.write(':\n')#the condition is done add the : and new line to finish        
        
class VisualComponent(BaseComponent):
    """Base class for most visual stimuli
    """
    def generateFrameCode(self,buff):
        """Generate the code that will be called every frame
        """    
        self.generateTimeTestCode(buff)#writes an if statement to determine whether to draw etc
        buff.writeIndented("    %s.draw()\n" %(self.params['name']))
        
class TextComponent(VisualComponent):
    """An event class for presenting image-based stimuli"""
    def __init__(self, name='', text='', font='arial', 
        pos=[0,0], size=[0,0], ori=0, times=[0,1]):
        self.params={}
        self.type='Text'
        self.params['name']=name
        self.params['text']= text
        self.params['font']= font
        self.params['pos']=pos
        self.params['size']=size
        self.params['ori']=ori
        self.params['times']=times
        
        self.hints={}
        self.hints['name']="A name for the component e.g. 'thanksMsg'"
        self.hints['text']="The text to be displayed"
        self.hints['font']= "The font name, or a list of names, e.g. ['arial','verdana']"
        self.hints['pos']= "Position of the text as [X,Y], e.g. [-2.5,3]"
        self.hints['size']= "Specifies the height of the letter (the width is then determined by the font)"
        self.hints['ori']= "The orientation of the text in degrees"
        self.hints['times']="A series of one or more onset/offset times, e.g. [2.0,2.5] or [[2.0,2.5],[3.0,3.8]]"
        
        #for choiceboxes what are the allowed options?
        self.allowed={}
        self.allowed['units']=['as window','deg','pix','cm']        
        
        #params that can change in time
        self.changeable=['ori','pos','rgb','size']
        
    def generateInitCode(self,buff):
        s = "%s=TextStim(win=win, pos=%s, size=%s" %(self.params['name'], self.params['pos'],self.params['size'])
        buff.writeIndented(s)   
        
        buff.writeIndented(")\n")
    def generateRoutineCode(self,buff):
        """Generate the code that will be called at the beginning of 
        a routine (e.g. to update stimulus parameters)
        """
        pass
        
class PatchComponent(VisualComponent):
    """An event class for presenting image-based stimuli"""
    def __init__(self, name='', image='sin', mask='none', pos=[0,0], 
            sf=1, size=1, ori=0, times=[0,1]):
        self.type='Patch'
        self.params={}
        self.hints={}
        self.params['name']=name
        self.params['mask']=mask
        self.params['image']= image
        self.params['pos']=pos
        self.params['size']=size
        self.params['sf']=sf
        self.params['ori']=ori
        self.params['times']=times
        self.params['interpolate']=False
        
        self.hints['name']="A name for the component e.g. 'fixationPt'"
        self.hints['image']="The image to use (a filename or 'sin', 'sqr'...)"
        self.hints['mask']= "The image that defines the mask (a filename or 'gauss', 'circle'...)"
        self.hints['pos']= "Position of the image centre as [X,Y], e.g. [-2.5,3]"
        self.hints['size']= "Specifies the size of the stimulus (a single value or [w,h] )"
        self.hints['ori']= "The orientation of the stimulus in degrees"
        self.hints['sf']= "The spatial frequency of cycles of the image on the stimulus"
        self.hints['times']="A series of one or more onset/offset times, e.g. [2.0,2.5] or [[2.0,2.5],[3.0,3.8]]"
        self.hints['interpolate']="If checked then, if the image is scaled up and down, linear interpolation will be used instead of nearest neighbour" 
        
        #for choiceboxes what are the allowed options?
        self.allowed={}
        self.allowed['units']=['as window','deg','pix','cm'] 
        self.allowed['interpolate']=[False,True]
        
    def generateInitCode(self,buff):
        s = "%s=PatchStim(win=win, pos=%s, size=%s" %(self.params['name'], self.params['pos'],self.params['size'])
        buff.writeIndented(s)   
        
        buff.writeIndented(")\n")

class MovieComponent(VisualComponent):
    """An event class for presenting image-based stimuli"""
    def __init__(self, name='', movie='', pos=[0,0], 
            size=1, ori=0, times=[0,1]):
        
        self.type='Movie'
        self.params={}
        self.hints={}
        self.params['name']=name
        self.params['movie']= movie
        self.params['pos']=pos
        self.params['size']=size
        self.params['ori']=ori
        self.params['times']=times
        
        self.hints['name']="A name for the component e.g. 'mainMovie'"
        self.hints['movie']="The filename/path for the movie)"
        self.hints['pos']= "Position of the image centre as [X,Y], e.g. [-2.5,3]"
        self.hints['size']= "Specifies the size of the stimulus (a single value or [w,h] )"
        self.hints['ori']= "The orientation of the stimulus in degrees"
        self.hints['times']="A series of one or more onset/offset times, e.g. [2.0,2.5] or [[2.0,2.5],[3.0,3.8]]"
                
        #for choiceboxes what are the allowed options?
        self.allowed={}
        self.allowed['units']=['window','deg','pix','cm'] 
    def generateInitCode(self,buff):
        s = "%s=MovieStim(win=win, pos=%s, movie=%s, size=%s" %(self.params['name'], self.params['movie'],self.params['pos'],self.params['size'])
        buff.writeIndented(s)   
        
        buff.writeIndented(")\n")

class SoundComponent(BaseComponent):
    """An event class for presenting image-based stimuli"""
    def __init__(self, name='', sound='', 
            size=1, ori=0, times=[0,1]):
        
        self.type='Sound'
        self.params={}
        self.hints={}
        self.params['name']=name
        self.params['sound']= ''
        self.params['times']=times
        
        self.hints['name']="A name for the component e.g. 'ping'"
        self.hints['sound']="A sound can be a string (e.g. 'A' or 'Bf') or a number to specify Hz, or a filename"
        self.hints['times']="A series of one or more onset/offset times, e.g. [2.0,2.5] or [[2.0,2.5],[3.0,3.8]]"
                
        #for choiceboxes what are the allowed options?
        self.allowed={}
    def generateInitCode(self,buff):
        s = "%s=Sound(%s, secs=%s" %(self.params['name'], self.params['sound'],self.params['times'][1]-self.params['times'][0])
        buff.writeIndented(s)   
        
        buff.writeIndented(")\n")
    def generateRoutineCode(self,buff):
        """Generate the code that will be called at the beginning of 
        a routine (e.g. to update stimulus parameters)
        """
        pass
    def generateFrameCode(self,buff):
        """Generate the code that will be called every frame
        """
        buff.writeIndented("playing Sound '%s'\n" %(self.params['name'])) 
            
class KeyboardComponent(BaseComponent):
    """An event class for checking the keyboard at given times"""
    def __init__(self, name='', allowedKeys='q,left,right',times=[0,1]):
        self.type='Keyboard'
                
        self.params={}
        self.params['name']=name
        self.params['allowedKeys']=allowedKeys
        self.params['times']=times
        
        self.hints={}
        self.hints['name']=""
        self.hints['allowedKeys']="The keys the user may press, e.g. a,b,q,left,right"
        self.hints['times']="A series of one or more periods to read the keyboard, e.g. [2.0,2.5] or [[2.0,2.5],[3.0,3.8]]"
        #for choiceboxes what are the allowed options?
        self.allowed={}
    def generateInitCode(self,buff):
        pass#no need to initialise keyboards?
    def generateFrameCode(self,buff):
        """Generate the code that will be called every frame
        """
        buff.writeIndented("Checking keys")
        

class MouseComponent(BaseComponent):
    """An event class for checking the mouse location and buttons at given times"""
    def __init__(self, name='mouse', times=[0,1]):
        self.type='Mouse'
        self.params={}
        self.params['name']=name
        self.params['times']=times
        
        self.hints={}
        self.hints['name']="Even mice have names"
        self.hints['times']="A series of one or more periods to read the mouse, e.g. [2.0,2.5] or [[2.0,2.5],[3.0,3.8]]"
        #for choiceboxes what are the allowed options?
        self.allowed={}
    def generateInitCode(self,buff):
        pass#no need to initialise?
    def generateFrameCode(self,buff):
        """Generate the code that will be called every frame
        """
        buff.writeIndented("Checking keys")
        
                
