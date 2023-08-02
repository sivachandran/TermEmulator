#!/usr/bin/python

from __future__ import print_function

import os
import sys
import pty
import threading
import select
import wx

import fcntl
import termios
import struct
import tty

import TermEmulator

ID_TERMINAL = 1

def PrintStringAsAscii(s):
    import string
    for ch in s:
        if ch in string.printable:
            print(ch, end="")
        else:
            print(ord(ch), end="")

class TermEmulatorDemo(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "TermEmulator Demo", \
                          size = (700, 500))
        
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.st1 = wx.StaticText(self, wx.ID_ANY, "Program path:")
        hbox1.Add(self.st1, 0, wx.ALIGN_CENTER | wx.LEFT, 10)
        
        self.tc1 = wx.TextCtrl(self, wx.ID_ANY)
        self.tc1.SetValue("/bin/bash")
        hbox1.Add(self.tc1, 1, wx.ALIGN_CENTER)

        self.st2 = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        hbox1.Add(self.st2, 0, wx.ALIGN_CENTER | wx.LEFT, 10)

        self.tc2 = wx.TextCtrl(self, wx.ID_ANY)
        hbox1.Add(self.tc2, 1, wx.ALIGN_CENTER)

        self.b1 = wx.Button(self, wx.ID_ANY, "Run")
        hbox1.Add(self.b1, 0, wx.LEFT | wx.RIGHT, 10)
        self.b1.Bind(wx.EVT_BUTTON, self.OnRun, id = self.b1.GetId())
        
        vbox.Add(hbox1, 0, wx.EXPAND | wx.HORIZONTAL | wx.TOP | wx.BOTTOM, 5)
        
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.st3 = wx.StaticText(self, wx.ID_ANY, "Terminal Size, Rows:")
        hbox2.Add(self.st3, 0, wx.ALIGN_CENTER | wx.LEFT, 10)
        
        self.tc3 = wx.TextCtrl(self, wx.ID_ANY)
        self.tc3.SetValue("24")
        hbox2.Add(self.tc3, 1, wx.ALIGN_CENTER)

        self.st4 = wx.StaticText(self, wx.ID_ANY, "Columns:")
        hbox2.Add(self.st4, 0, wx.ALIGN_CENTER | wx.LEFT, 10)

        self.tc4 = wx.TextCtrl(self, wx.ID_ANY)
        self.tc4.SetValue("80")
        hbox2.Add(self.tc4, 1, wx.ALIGN_CENTER)

        self.b2 = wx.Button(self, wx.ID_ANY, "Resize")
        hbox2.Add(self.b2, 0, wx.LEFT | wx.RIGHT, 10)
        self.b2.Bind(wx.EVT_BUTTON, self.OnResize, id = self.b2.GetId())
        
        self.cb1 = wx.CheckBox(self, wx.ID_ANY, "Disable text coloring")
        hbox2.Add(self.cb1, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 10)
        
        vbox.Add(hbox2, 0, wx.EXPAND | wx.HORIZONTAL | wx.TOP | wx.BOTTOM, 5)
        
        self.txtCtrlTerminal = wx.TextCtrl(self, ID_TERMINAL, 
                                           style = wx.TE_MULTILINE 
                                                   | wx.TE_DONTWRAP)
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL,
                       wx.FONTWEIGHT_NORMAL, False)
        self.txtCtrlTerminal.SetFont(font)
        
        self.txtCtrlTerminal.Bind(wx.EVT_CHAR, self.OnTerminalChar,
                                  id = ID_TERMINAL)
        
        self.txtCtrlTerminal.Bind(wx.EVT_KEY_DOWN, self.OnTerminalKeyDown,
                                  id = ID_TERMINAL)
        
        self.txtCtrlTerminal.Bind(wx.EVT_KEY_UP, self.OnTerminalKeyUp,
                                  id = ID_TERMINAL)
        
        vbox.Add(self.txtCtrlTerminal, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(vbox)
        
        self.termRows = 24
        self.termCols = 80
        
        self.FillScreen()
        
        self.linesScrolledUp = 0
        self.scrolledUpLinesLen = 0
        
        self.termEmulator = TermEmulator.V102Terminal(self.termRows,
                                                      self.termCols)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_SCROLL_UP_SCREEN,
                                      self.OnTermEmulatorScrollUpScreen)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_UPDATE_LINES,
                                      self.OnTermEmulatorUpdateLines)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_UPDATE_CURSOR_POS,
                                      self.OnTermEmulatorUpdateCursorPos)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_UPDATE_WINDOW_TITLE,
                                      self.OnTermEmulatorUpdateWindowTitle)
        self.termEmulator.SetCallback(self.termEmulator.CALLBACK_UNHANDLED_ESC_SEQ,
                                      self.OnTermEmulatorUnhandledEscSeq)
        
        self.isRunning = False
        self.UpdateUI()
        
        self.Show(True)
        
    def FillScreen(self):
        """
        Fills the screen with blank lines so that we can update terminal
        dirty lines quickly.
        """
        text = ""
        for i in range(self.termRows):
            for j in range(self.termCols):
                text += ' '
            text += '\n'
            
        text = text.rstrip('\n')
        self.txtCtrlTerminal.SetValue(text)
        
    def UpdateUI(self):
        self.tc1.Enable(not self.isRunning)
        self.tc2.Enable(not self.isRunning)
        self.b1.Enable(not self.isRunning)
        self.b2.Enable(self.isRunning)
        self.txtCtrlTerminal.Enable(self.isRunning)
        
    def OnRun(self, event):
        path = self.tc1.GetValue()
        basename = os.path.basename(path)
        arglist = [ basename ]
        
        arguments = self.tc2.GetValue()
        if arguments != "":
            for arg in arguments.split(' '):
                arglist.append(arg)
        
        self.termRows = int(self.tc3.GetValue())
        self.termCols = int(self.tc4.GetValue())
        
        rows, cols = self.termEmulator.GetSize()
        if rows != self.termRows or cols != self.termCols:
            self.termEmulator.Resize (self.termRows, self.termCols)
        
        processPid, processIO = pty.fork()
        if processPid == 0: # child process
            os.execl(path, *arglist)
        
        print("Child process pid {}".format(processPid))
        
        # Sets raw mode
        #tty.setraw(processIO)
        
        # Sets the terminal window size
        fcntl.ioctl(processIO, termios.TIOCSWINSZ,
                    struct.pack("hhhh", self.termRows, self.termCols, 0, 0))
        
        tcattrib = termios.tcgetattr(processIO)
        tcattrib[3] = tcattrib[3] & ~termios.ICANON
        termios.tcsetattr(processIO, termios.TCSAFLUSH, tcattrib)
                    
        self.processPid = processPid
        self.processIO = processIO
        self.processOutputNotifierThread = threading.Thread(
                                        target = self.__ProcessOuputNotifierRun)
        self.waitingForOutput = True
        self.stopOutputNotifier = False
        self.processOutputNotifierThread.start()
        self.isRunning = True
        self.UpdateUI()
        
    def OnResize(self, event):        
        self.termRows = int(self.tc3.GetValue())
        self.termCols = int(self.tc4.GetValue())
        
        # Resize emulator
        self.termEmulator.Resize(self.termRows, self.termCols)
        
        # Resize terminal
        fcntl.ioctl(self.processIO, termios.TIOCSWINSZ,
                    struct.pack("hhhh", self.termRows, self.termCols, 0, 0))
        
        self.FillScreen()
        self.UpdateDirtyLines(range(self.termRows))
        
    def __ProcessIsAlive(self):
        try:
            pid, status = os.waitpid(self.processPid, os.WNOHANG)
            if pid == self.processPid and os.WIFEXITED(status):
                return False
        except:
            return False
        
        return True
    
    def __ProcessOuputNotifierRun(self):
        inpSet = [ self.processIO ]
        while (not self.stopOutputNotifier and self.__ProcessIsAlive()):
            if self.waitingForOutput:
                inpReady, outReady, errReady = select.select(inpSet, [], [], 0)
                if self.processIO in inpReady:
                    self.waitingForOutput = False
                    wx.CallAfter(self.ReadProcessOutput)
                
        if not self.__ProcessIsAlive():
            self.isRunning = False
            wx.CallAfter(self.ReadProcessOutput)
            wx.CallAfter(self.UpdateUI)
            print("Process exited")
            
        print("Notifier thread exited")
        
    def SetTerminalRenditionStyle(self, style):
        fontStyle = wx.FONTSTYLE_NORMAL
        fontWeight = wx.FONTWEIGHT_NORMAL
        underline = False
        
        if style & self.termEmulator.RENDITION_STYLE_BOLD:
            fontWeight = wx.FONTWEIGHT_BOLD
        elif style & self.termEmulator.RENDITION_STYLE_DIM:
            fontWeight = wx.FONTWEIGHT_LIGHT
            
        if style & self.termEmulator.RENDITION_STYLE_ITALIC:
            fontStyle = wx.FONTSTYLE_ITALIC
        
        if style & self.termEmulator.RENDITION_STYLE_UNDERLINE:
            underline = True
        
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, fontStyle, fontWeight,
                       underline)
        
        self.txtCtrlTerminal.SetFont(font)
                    
    def SetTerminalRenditionForeground(self, fgcolor):
        if fgcolor != 0:
            if fgcolor == 1:
                self.txtCtrlTerminal.SetForegroundColour((0, 0, 0))
            elif fgcolor == 2:
                self.txtCtrlTerminal.SetForegroundColour((255, 0, 0))
            elif fgcolor == 3:
                self.txtCtrlTerminal.SetForegroundColour((0, 255, 0))
            elif fgcolor == 4:
                self.txtCtrlTerminal.SetForegroundColour((255, 255, 0))
            elif fgcolor == 5:
                self.txtCtrlTerminal.SetForegroundColour((0, 0, 255))
            elif fgcolor == 6:
                self.txtCtrlTerminal.SetForegroundColour((255, 0, 255))
            elif fgcolor == 7:
                self.txtCtrlTerminal.SetForegroundColour((0, 255, 255))                
            elif fgcolor == 8:
                self.txtCtrlTerminal.SetForegroundColour((255, 255, 255))
        else:
            self.txtCtrlTerminal.SetForegroundColour((0, 0, 0))

    def SetTerminalRenditionBackground(self, bgcolor):
        if bgcolor != 0:
            if bgcolor == 1:
                self.txtCtrlTerminal.SetBackgroundColour((0, 0, 0))
            elif bgcolor == 2:
                self.txtCtrlTerminal.SetBackgroundColour((255, 0, 0))
            elif bgcolor == 3:
                self.txtCtrlTerminal.SetBackgroundColour((0, 255, 0))
            elif bgcolor == 4:
                self.txtCtrlTerminal.SetBackgroundColour((255, 255, 0))
            elif bgcolor == 5:
                self.txtCtrlTerminal.SetBackgroundColour((0, 0, 255))
            elif bgcolor == 6:
                self.txtCtrlTerminal.SetBackgroundColour((255, 0, 255))
            elif bgcolor == 7:
                self.txtCtrlTerminal.SetBackgroundColour((0, 255, 255))                
            elif bgcolor == 8:
                self.txtCtrlTerminal.SetBackgroundColour((255, 255, 255))
        else:
            self.txtCtrlTerminal.SetBackgroundColour((255, 255, 255))
    
    def GetTextCtrlLineStart(self, lineNo):
        lineStart = self.scrolledUpLinesLen        
        lineStart += (self.termCols + 1) * (lineNo - self.linesScrolledUp)
        return lineStart
        
    def UpdateCursorPos(self):
        row, col = self.termEmulator.GetCursorPos()
        
        lineNo = self.linesScrolledUp + row
        insertionPoint = self.GetTextCtrlLineStart(lineNo)
        insertionPoint += col 
        self.txtCtrlTerminal.SetInsertionPoint(insertionPoint)
        
    def UpdateDirtyLines(self, dirtyLines = None):
        text = ""
        curStyle = 0
        curFgColor = 0
        curBgColor = 0
        
        #self.SetTerminalRenditionStyle(curStyle)
        self.SetTerminalRenditionForeground(curFgColor)
        self.SetTerminalRenditionBackground(curBgColor)
        
        screen = self.termEmulator.GetRawScreen()
        screenRows = self.termEmulator.GetRows()
        screenCols = self.termEmulator.GetCols()
        if dirtyLines == None:
            dirtyLines = self.termEmulator.GetDirtyLines()
        
        disableTextColoring = self.cb1.IsChecked()
        
        for row in dirtyLines:
            text = ""

            # finds the line starting and ending index
            lineNo = self.linesScrolledUp + row
            lineStart = self.GetTextCtrlLineStart(lineNo)
            #lineText = self.txtCtrlTerminal.GetLineText(lineNo)
            #lineEnd = lineStart + len(lineText)
            lineEnd = lineStart + self.termCols
            
            # delete the line content
            self.txtCtrlTerminal.Replace(lineStart, lineEnd, "")
            self.txtCtrlTerminal.SetInsertionPoint(lineStart)
            
            for col in range(screenCols):
                style, fgcolor, bgcolor = self.termEmulator.GetRendition(row,
                                                                         col)
                
                if not disableTextColoring and (curStyle != style 
                                                or curFgColor != fgcolor \
                                                or curBgColor != bgcolor):
                    
                    if text != "":
                        self.txtCtrlTerminal.WriteText(text)
                        text = ""
                    
                    if curStyle != style:
                        curStyle = style
                        #print("Setting style {}".format(curStyle))
                        if style == 0:
                            self.txtCtrlTerminal.SetForegroundColour((0, 0, 0))
                            self.txtCtrlTerminal.SetBackgroundColour((255, 255, 255))
                        elif style & self.termEmulator.RENDITION_STYLE_INVERSE:
                            self.txtCtrlTerminal.SetForegroundColour((255, 255, 255))
                            self.txtCtrlTerminal.SetBackgroundColour((0, 0, 0))
                        else:
                            # skip other styles since TextCtrl doesn't support
                            # multiple fonts(bold, italic and etc)
                            pass
                        
                    if curFgColor != fgcolor:
                        curFgColor = fgcolor
                        #print("Setting foreground {}".format(curFgColor))
                        self.SetTerminalRenditionForeground(curFgColor)
                        
                    if curBgColor != bgcolor:
                        curBgColor = bgcolor
                        #print("Setting background {}".format(curBgColor))
                        self.SetTerminalRenditionBackground(curBgColor)
                
                text += screen[row][col]
            
            self.txtCtrlTerminal.WriteText(text)
            
        
    def OnTermEmulatorScrollUpScreen(self):
        blankLine = "\n"
        
        for i in range(self.termEmulator.GetCols()):
            blankLine += ' '
        
        #lineLen =  len(self.txtCtrlTerminal.GetLineText(self.linesScrolledUp))
        lineLen = self.termCols
        self.txtCtrlTerminal.AppendText(blankLine)
        self.linesScrolledUp += 1
        self.scrolledUpLinesLen += lineLen + 1
        
    def OnTermEmulatorUpdateLines(self):
        self.UpdateDirtyLines()
        wx.YieldIfNeeded()
        
    def OnTermEmulatorUpdateCursorPos(self):
        self.UpdateCursorPos()
        
    def OnTermEmulatorUpdateWindowTitle(self, title):
        self.SetTitle(title)
        
    def OnTermEmulatorUnhandledEscSeq(self, escSeq):
        print("Unhandled escape sequence: [{}".format(escSeq))
        
    def ReadProcessOutput(self):
        output = bytes("",'utf8')
        
        try:
            while True:
                data = os.read(self.processIO, 512)
                datalen = len(data)
                output += data
                
                if datalen < 512:
                    break
        except:
            output = bytes("",'utf8')
         
        #print("Received: ", end="")
        #PrintStringAsAscii(output)
        #print("")
        
        self.termEmulator.ProcessInput(output.decode())

        # resets text control's foreground and background
        self.txtCtrlTerminal.SetForegroundColour((0, 0, 0))
        self.txtCtrlTerminal.SetBackgroundColour((255, 255, 255))
        
        self.waitingForOutput = True
        
    def OnTerminalKeyDown(self, event):
        #print("KeyDown {}".format(event.GetKeyCode()))
        event.Skip()

    def OnTerminalKeyUp(self, event):
        #print("KeyUp {}".format(event.GetKeyCode()))
        event.Skip()
        
    def OnTerminalChar(self, event):
        if not self.isRunning:
            return
            
        ascii = event.GetKeyCode()
        #print("ASCII = {}".format(ascii))
        
        keystrokes = None
        
        if ascii < 256:
             keystrokes = chr(ascii)
        elif ascii == wx.WXK_UP:
            keystrokes = "\033[A"
        elif ascii == wx.WXK_DOWN:
            keystrokes = "\033[B"
        elif ascii == wx.WXK_RIGHT:
            keystrokes = "\033[C"
        elif ascii == wx.WXK_LEFT:
            keystrokes = "\033[D"

        if keystrokes != None:
            #print("Sending:", end="")
            #PrintStringAsAscii(keystrokes)
            #print("")
            os.write(self.processIO, bytes(keystrokes,'utf-8'))
                
    def OnClose(self, event):
        if self.isRunning:
            self.stopOutputNotifier = True
            self.processOutputNotifierThread.join(None)
        
        event.Skip()

if __name__ == '__main__':
    app = wx.App(0);
    termEmulatorDemo = TermEmulatorDemo()
    
    app.SetTopWindow(termEmulatorDemo)
    app.MainLoop()
