import sys

HAS_VGAMEPAD = False
try:
    import vgamepad as vg
    HAS_VGAMEPAD = True
except ImportError:
    pass

class RealControllerHardware:
    def __init__(self):
        self.gamepad = None
        self.enabled = False
        if HAS_VGAMEPAD:
            try:
                # Switched to VDS4Gamepad for native PS Remote Play compatibility
                self.gamepad = vg.VDS4Gamepad() 
                self.enabled = True
                print("[SUCCESS] Production Live Virtual DualShock 4 Driver Hooked.")
            except Exception as e:
                print(f"[FATAL DEVICE ERROR] DualShock 4 registration failed: {e}")
        else:
            print("[CRITICAL] 'vgamepad' missing. Run: pip install vgamepad")

    def send_stick_input(self, stick_x, stick_y):
        if not self.enabled or not self.gamepad:
            return False
            
        try:
            # vgamepad VDS4 uses float values directly from -1.0 to 1.0 for sticks
            # Inverting y value to match standard controller configurations
            self.gamepad.right_stick_float(x_value=stick_x, y_value=-stick_y)
            self.gamepad.update()
            return True
        except Exception as e:
            print(f"[DEVICE WRITE EXCEPTION] Failed sending axes updates: {e}")
            return False
            
    def shutdown(self):
        if self.gamepad:
            try:
                self.gamepad.reset()
                self.gamepad.update()
            except:
                pass
            del self.gamepad
            self.gamepad = None
            self.enabled = False
