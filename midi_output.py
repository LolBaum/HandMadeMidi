# midi_output.py
import mido
import time

class MidiOutput:
    def __init__(self, port_name="Motion Controller", virtual=True):
        """
        Opens a MIDI output port.
        virtual=True means we expect a virtual port like loopMIDI.
        """
        self.port_name = port_name
        self.port = None
        self._connect()

    def _connect(self):
        """Attempt to open the MIDI port."""
        try:
            # List all available output ports
            output_names = mido.get_output_names()
            print("Available MIDI outputs:", output_names)

            # Find the port by name (exact match or partial)
            for name in output_names:
                if self.port_name in name:
                    self.port = mido.open_output(name)
                    print(f"Opened MIDI port: {name}")
                    return

            # If not found, try to open by the exact name (fallback)
            self.port = mido.open_output(self.port_name)
            print(f"Opened MIDI port: {self.port_name}")

        except Exception as e:
            print(f"Could not open MIDI port '{self.port_name}': {e}")
            self.port = None

    def send_cc(self, control, value):
        """Send a single Control Change message."""
        if self.port is None:
            return
        # Clamp value to 0-127
        value = max(0, min(127, int(round(value))))
        msg = mido.Message('control_change', control=control, value=value)
        self.port.send(msg)

    def send_messages(self, messages):
        """
        Send a list of (control, value) pairs.
        messages: list of tuples (cc, value)
        """
        if self.port is None:
            return
        for cc, val in messages:
            self.send_cc(cc, val)

    def close(self):
        if self.port:
            self.port.close()
            self.port = None