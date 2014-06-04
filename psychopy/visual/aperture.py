#!/usr/bin/env python2

'''Restrict a stimulus visibility area to a basic shape
(circle, square, triangle)'''

# Part of the PsychoPy library
# Copyright (C) 2014 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

# Ensure setting pyglet.options['debug_gl'] to False is done prior to any
# other calls to pyglet or pyglet submodules, otherwise it may not get picked
# up by the pyglet GL engine and have no effect.
# Shaders will work but require OpenGL2.0 drivers AND PyOpenGL3.0+
import pyglet
pyglet.options['debug_gl'] = False
GL = pyglet.gl

import psychopy  # so we can get the __path__
from psychopy import logging
import psychopy.event

# tools must only be imported *after* event or MovieStim breaks on win32
# (JWP has no idea why!)
from psychopy.tools.monitorunittools import cm2pix, deg2pix, convertToPix
from psychopy.tools.attributetools import logAttrib
from psychopy.visual import polygon, shape
ShapeStim = shape.ShapeStim

import numpy

from psychopy.constants import STARTED, STOPPED


class Aperture:
    """Restrict a stimulus visibility area to a basic shape (circle, square, triangle)

    When enabled, any drawing commands will only operate on pixels within the
    Aperture. Once disabled, subsequent draw operations affect the whole screen
    as usual.

    If shape is 'square' or 'triangle' then that is what will be used (obviously)
    If shape is 'circle' or `None` then a polygon with nVerts will be used (120 for a rough circle)
    If shape is a list or numpy array (Nx2) then it will be used directly as the vertices to a :class:`~psychopy.visual.ShapeStim`

    See demos/stimuli/aperture.py for example usage

    :Author:
        2011, Yuri Spitsyn
        2011, Jon Peirce added units options, Jeremy Gray added shape & orientation
    """
    def __init__(self, win, size, pos=(0,0), ori=0, nVert=120, shape='circle', units=None,
            name='', autoLog=True):
        #what local vars are defined (these are the init params) for use by __repr__
        self._initParams = dir()
        self._initParams.remove('self')
        #set self params
        self.autoLog=False #set this False first and change after attribs are set
        self.win=win
        self.name = name
        self.ori = ori
        #unit conversions
        if units!=None and len(units):
            self.units = units
        else:
            self.units = win.units

        # ugly hack for setting vertices using combination of shape and nVerts
        if type(nVert) == int:
            self.nVert = nVert
        regularPolygon = True
        self.shape = shape
        unrecognized = False
        if shape is None:
            pass #just use the nVert we were given
        elif type(shape) in [str, unicode]:
            if shape.lower() == 'circle':
                pass #just use the nVert we were given
            elif shape.lower() == 'square':
                regularPolygon = False # if we use polygon then we have to hack the orientation
                vertices = [[0.5,-0.5],[-0.5,-0.5],[-0.5,0.5],[0.5,0.5]]
            elif shape.lower() == 'triangle':
                regularPolygon = False # if we use polygon then we have to hack the orientation
                vertices = [[0.5,-0.5],[0,0.5],[-0.5,-0.5]]
            else:
                unrecognized = True
        elif type(shape) in [tuple, list, numpy.ndarray]:
            regularPolygon = False
            vertices = shape
        else:
            unrecognized = True
        if unrecognized:
            logging.warn("Unrecognized shape for aperture. Expected 'circle', 'square', 'triangle', vertices or None but got %s" %(repr(shape)))
        if regularPolygon:
            self._shape = polygon.Polygon(win=self.win, edges=self.nVert,
                                          fillColor=1, lineColor=None,
                                          interpolate=False,
                                          pos=pos,
                                          size=size)
        else:
            self._shape = ShapeStim(win=self.win, vertices=vertices,
                                          fillColor=1, lineColor=None,
                                          interpolate=False,
                                          pos=pos,
                                          size=size)

        self._needVertexUpdate = True
        self._reset()#implicitly runs an self.enable()
        self.autoLog= autoLog
        if autoLog:
            logging.exp("Created %s = %s" %(self.name, str(self)))
    def _reset(self):
        self.enable()
        GL.glClearStencil(0)
        GL.glClear(GL.GL_STENCIL_BUFFER_BIT)

        GL.glPushMatrix()
        self.win.setScale('pix')

        GL.glDisable(GL.GL_LIGHTING)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(GL.GL_FALSE)
        GL.glStencilFunc(GL.GL_NEVER, 0, 0)
        GL.glStencilOp(GL.GL_INCR, GL.GL_INCR, GL.GL_INCR)
        self._shape.draw(keepMatrix=True) #draw without push/pop matrix
        GL.glStencilFunc(GL.GL_EQUAL, 1, 1)
        GL.glStencilOp(GL.GL_KEEP, GL.GL_KEEP, GL.GL_KEEP)

        GL.glPopMatrix()

    def setSize(self, size, needReset=True, log=True):
        """Set the size (diameter) of the Aperture
        """
        self.size = size
        self._shape.size = size
        if needReset:
            self._reset()
        logAttrib(self, log, 'size')
    def setOri(self, ori, needReset=True, log=True):
        """Set the orientation of the Aperture
        """
        self.ori = ori
        self._shape.ori = ori
        if needReset:
            self._reset()
        logAttrib(self, log, 'ori')
    def setPos(self, pos, needReset=True, log=True):
        """Set the pos (centre) of the Aperture
        """
        self.pos = numpy.array(pos)
        self._shape.pos = self.pos
        if needReset:
            self._reset()
        logAttrib(self, log, 'pos')
    @property
    def posPix(self):
        """The position of the aperture in pixels
        """
        return self._shape.posPix
    @property
    def sizePix(self):
        """The size of the aperture in pixels
        """
        return self._shape.sizePix
    def enable(self):
        """Enable the aperture so that it is used in future drawing operations

        NB. The Aperture is enabled by default, when created.

        """
        if self._shape._needVertexUpdate:
            self._shape._updateVertices()
        GL.glEnable(GL.GL_STENCIL_TEST)
        self.enabled=True#by default
        self.status=STARTED
    def disable(self):
        """Disable the Aperture. Any subsequent drawing operations will not be
        affected by the aperture until re-enabled.
        """
        GL.glDisable(GL.GL_STENCIL_TEST)
        self.enabled=False
        self.status=STOPPED
    def __del__(self):
        self.disable()
