# name=Alesis V Series

import transport
import device
import ui
import midi


current_mode = None

# factory layout
PAD = [ # factory drum pad layout
    49, 41, 42, 46,
    36, 37, 38, 39,
]


class Mode():
    def __init__(self):
        ui.setHintMsg("Alesis V Series: " + self.__class__.__name__.replace("M", " M"))
        self.padsChan = 9
        self.lights_off()
        self.set_lights()
    
    def lights_off(self):
        if device.isAssigned():
            for i in range(len(PAD)):
                device.midiOutMsg(128, 9, PAD[i], 0)

    def set_lights(self):
        pass
        
    def OnNoteOn(self, event):
        # adjusting velocity curve to make response more aggressive
        event.velocity = int((event.velocity*127)**0.5)
    
    def OnNoteOff(self, event):
        pass


class TransportMode(Mode):
    def __init__(self):
        super().__init__()
        self.map = {
            # default values of first pad row
            PAD[0]: lambda: transport.globalTransport(midi.FPT_Loop, 1),            # pattern/song mode
            PAD[1]: lambda: transport.globalTransport(midi.FPT_Play, 1),            # play/pause
            PAD[2]: lambda: transport.globalTransport(midi.FPT_Stop, 1),            # stop
            PAD[3]: lambda: transport.globalTransport(midi.FPT_Record, 1),          # recording
            PAD[4]: lambda: transport.globalTransport(midi.FPT_Metronome, 1),       # metronome
            PAD[5]: lambda: transport.globalTransport(midi.FPT_WaitForInput, 1),    # wait for input
            PAD[6]: lambda: transport.globalTransport(midi.FPT_CountDown, 1),       # countdown before recording
            PAD[7]: lambda: transport.globalTransport(midi.FPT_LoopRecord, 1),      # loop recording
        }
        
    def set_lights(self):
        if device.isAssigned():
            switch = lambda cond: (144*cond + 128*(not cond), 127*cond)
            
            status, velocity = switch(transport.getLoopMode())
            device.midiOutMsg(status, 9, PAD[0], velocity)

            status, velocity = switch(transport.isPlaying())
            device.midiOutMsg(status, 9, PAD[1], velocity)

            status, velocity = switch(transport.isRecording())
            device.midiOutMsg(status, 9, PAD[3], velocity)

            status, velocity = switch(ui.isMetronomeEnabled())
            device.midiOutMsg(status, 9, PAD[4], velocity)

            status, velocity = switch(ui.isStartOnInputEnabled())
            device.midiOutMsg(status, 9, PAD[5], velocity)

            status, velocity = switch(ui.isPrecountEnabled())
            device.midiOutMsg(status, 9, PAD[6], velocity)

            status, velocity = switch(ui.isLoopRecEnabled())
            device.midiOutMsg(status, 9, PAD[7], velocity)

    def OnNoteOn(self, event):
        if event.midiChan == self.padsChan:
            trigger = self.map.get(event.data1, lambda:None)
            if event.data2 > 0:
                trigger()
            event.handled = True
        else: super().OnNoteOn(event)
    
    def OnNoteOff(self, event):
        if event.midiChan == self.padsChan:
            self.set_lights() # needed, because note off may trigger leds to turn off
            event.handled = True
        else: super().OnNoteOff(event)


class FPCMode(Mode):
    def __init__(self):
        super().__init__()
        self.map = {
            PAD[0]: 49, PAD[1]: 42, PAD[2]: 44, PAD[3]: 46,
            PAD[4]: 36, PAD[5]: 38, PAD[6]: 40, PAD[7]: 37, 
        }

    def OnNoteOn(self, event):
        if event.midiChan == self.padsChan:
            event.data1 = self.map.get(event.data1, 0)
        else: super().OnNoteOn(event)
    
    def OnNoteOff(self, event):
        if event.midiChan == self.padsChan:
            event.data1 = self.map[event.data1]
        else: super().OnNoteOff(event)


class TapTempoMode(Mode):
    def __init__(self):
        super().__init__()

    def OnNoteOn(self, event):
        if event.midiChan == self.padsChan:
            transport.globalTransport(midi.FPT_TapTempo, 1)
            event.handled = True
        else: super().OnNoteOn(event)
    
    def OnNoteOff(self, event):
        if event.midiChan == self.padsChan:
            event.handled = True
        else: super().OnNoteOff(event)


class DeactivatedMode(Mode):
    def __init__(self):
        super().__init__()

    def OnNoteOn(self, event):
        if event.midiChan == self.padsChan:
            event.handled = True # ignore pads
        else: super().OnNoteOn(event)
    
    def OnNoteOff(self, event):
        if event.midiChan == self.padsChan:
            event.handled = True # ignore pads
        else: super().OnNoteOff(event)


modes = { # map buttons to modes
    48: TransportMode,
    49: FPCMode,
    50: TapTempoMode,
    51: DeactivatedMode,
}


# built-in functions
def OnInit():
    global current_mode
    device_assigned = device.isAssigned()
    print("Output device assigned. Everything should work fine."*device_assigned
        + "Not output device assigned. LEDs might not work. "
            "Set input and output device to same port."*(not device_assigned))
    current_mode = TransportMode()

def OnRefresh(flags):
    current_mode.set_lights()

def OnNoteOn(event):
    current_mode.OnNoteOn(event)
def OnNoteOff(event):
    current_mode.OnNoteOff(event)


def OnControlChange(event):
    # setting button led unfortunately does not work.
    global current_mode

    event.handled = False
    next_mode = modes.get(event.data1, False)
    if next_mode and event.data2 == 127:
        current_mode = next_mode()
    event.handled = bool(next_mode) # maybe "or event.handled" needed