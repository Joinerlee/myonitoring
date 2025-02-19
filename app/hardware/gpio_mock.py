class GPIOMock:
    BCM = "BCM"
    OUT = "OUT"
    IN = "IN"
    HIGH = 1
    LOW = 0
    
    def __init__(self):
        self.mode = None
        self.pins = {}
        self.pwm_instances = {}
    
    def setmode(self, mode):
        self.mode = mode
    
    def setwarnings(self, flag):
        pass
    
    def setup(self, pin, mode):
        self.pins[pin] = {"mode": mode, "value": 0}
    
    def output(self, pin, value):
        if pin in self.pins:
            self.pins[pin]["value"] = value
    
    def input(self, pin):
        return self.pins.get(pin, {}).get("value", 0)
    
    def cleanup(self):
        self.pins.clear()
        self.pwm_instances.clear()
    
    def PWM(self, pin, frequency):
        pwm = PWMMock(pin, frequency)
        self.pwm_instances[pin] = pwm
        return pwm

class PWMMock:
    def __init__(self, pin, frequency):
        self.pin = pin
        self.frequency = frequency
        self.duty_cycle = 0
        self.running = False
    
    def start(self, dc):
        self.duty_cycle = dc
        self.running = True
    
    def ChangeDutyCycle(self, dc):
        self.duty_cycle = dc
    
    def stop(self):
        self.running = False 