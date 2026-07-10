# midi_output.py
import mido

class MidiOutput:
    def __init__(self, port_name="Motion Controller", virtual=True):
        self.port_name = port_name
        self.port = None
        self._connect()

    def _connect(self):
        try:
            output_names = mido.get_output_names()
            print("Available MIDI outputs:", output_names)
            for name in output_names:
                if self.port_name in name:
                    self.port = mido.open_output(name)
                    print(f"Opened MIDI port: {name}")
                    return
            self.port = mido.open_output(self.port_name)
            print(f"Opened MIDI port: {self.port_name}")
        except Exception as e:
            print(f"Could not open MIDI port '{self.port_name}': {e}")
            self.port = None

    def send_cc(self, channel, control, value):
        """Send a Control Change on a specific MIDI channel (0-15)."""
        if self.port is None:
            return
        value = max(0, min(127, int(round(value))))
        msg = mido.Message('control_change', channel=channel, control=control, value=value)
        self.port.send(msg)

    def send_messages(self, messages):
        """
        Send a list of (channel, control, value) tuples.
        """
        if self.port is None:
            return
        for ch, cc, val in messages:
            self.send_cc(ch, cc, val)

    def close(self):
        if self.port:
            self.port.close()
            self.port = None