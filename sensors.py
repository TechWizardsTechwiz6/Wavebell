import threading
import time
import smbus2
from RPLCD import i2c
import RPi.GPIO as GPIO
from firebase_client import log_event
import os

PIR_PIN = 23
TRIG_PIN = 25
ECHO_PIN = 24
BUZZER_PIN = 26
RELAY_PIN = 19
LDR_PIN = 22
LIGHT_PIN = 17

class Sensors(threading.Thread):
    def __init__(self, alert_callback=None, pir_cooldown=5, alert_cooldown=30):
        super().__init__()
        self.daemon = True
        self.alert_callback = alert_callback
        self.monitoringActive = False
        self.lcd = None
        self.lcd_addr = None
        self.last_pir_time = 0
        self.pir_cooldown = pir_cooldown
        self.last_alert_time = 0
        self.alert_cooldown = alert_cooldown
        self.is_dark = False
        self.light_state = False
        self.door_locked = True
        self.lcd_refresh_counter = 0
        self.lcd_refresh_interval = 300
        self.last_lcd_content = ["", ""]
        self.lcd_error_count = 0
        self.max_lcd_errors = 3
        self.setup_gpio()
        self.init_lcd()

    def setup_gpio(self):
        try:
            GPIO.cleanup()
            time.sleep(0.1)
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
            self.door_locked = True
            print("Door initialized: LOCKED")
            
            GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(TRIG_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(ECHO_PIN, GPIO.IN)
            GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(LDR_PIN, GPIO.IN)
            GPIO.setup(LIGHT_PIN, GPIO.OUT, initial=GPIO.LOW)
            
            print("GPIO setup complete")
        except Exception as e:
            print(f"GPIO setup error: {e}")

    def scan_i2c(self):
        try:
            bus = smbus2.SMBus(1)
            for addr in [0x27, 0x3f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26]:
                try:
                    bus.write_quick(addr)
                    bus.close()
                    return addr
                except:
                    continue
            bus.close()
        except Exception as e:
            print(f"I2C bus error: {e}")
        return None

    def init_lcd(self):
        try:
            addr = self.scan_i2c()
            if addr:
                self.lcd_addr = addr
                time.sleep(0.2)
                
                if self.lcd:
                    try:
                        self.lcd.close(clear=True)
                        time.sleep(0.1)
                    except:
                        pass
                
                self.lcd = i2c.CharLCD('PCF8574', address=addr, port=1, cols=16, rows=2, 
                                     dotsize=8, charmap='A02', auto_linebreaks=True)
                time.sleep(0.5)
                
                self.lcd.clear()
                time.sleep(0.3)
                self.lcd.cursor_mode = 'hide'
                time.sleep(0.1)
                
                self.lcd_error_count = 0
                self.lcd_refresh_counter = 0
                
                self.lcd_write("System Ready", "LCD Initialized")
                print(f"LCD initialized at address 0x{addr:02x}")
            else:
                print("No I2C LCD found.")
                self.lcd = None
        except Exception as e:
            print(f"LCD init error: {e}")
            self.lcd = None
            self.lcd_error_count += 1

    def lcd_write(self, line1="", line2=""):
        if not self.lcd:
            if self.lcd_error_count < self.max_lcd_errors:
                self.init_lcd()
            return
        
        try:
            line1_clean = self.sanitize_lcd_text(str(line1))[:16]
            line2_clean = self.sanitize_lcd_text(str(line2))[:16]
            
            if self.last_lcd_content[0] == line1_clean and self.last_lcd_content[1] == line2_clean:
                return
            
            self.lcd.clear()
            time.sleep(0.1)
            
            if line1_clean:
                self.lcd.cursor_pos = (0, 0)
                self.lcd.write_string(line1_clean.ljust(16))
                time.sleep(0.05)
            
            if line2_clean:
                self.lcd.cursor_pos = (1, 0)
                self.lcd.write_string(line2_clean.ljust(16))
                time.sleep(0.05)
            
            self.last_lcd_content = [line1_clean, line2_clean]
            self.lcd_error_count = 0
                
        except Exception as e:
            print(f"LCD write error: {e}")
            self.lcd_error_count += 1
            
            if self.lcd_error_count >= self.max_lcd_errors:
                print("Too many LCD errors, reinitializing...")
                self.lcd = None
                time.sleep(0.2)
                self.init_lcd()
            else:
                time.sleep(0.1)

    def sanitize_lcd_text(self, text):
        if not text:
            return ""
        
        text = str(text).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        clean_text = ""
        for char in text:
            if ord(char) >= 32 and ord(char) <= 126:
                clean_text += char
            else:
                clean_text += " "
        
        return clean_text.strip()

    def refresh_lcd_display(self):
        if self.lcd and self.last_lcd_content[0]:
            try:
                self.lcd.clear()
                time.sleep(0.2)
                
                self.lcd.cursor_pos = (0, 0)
                self.lcd.write_string(self.last_lcd_content[0].ljust(16))
                time.sleep(0.05)
                
                if self.last_lcd_content[1]:
                    self.lcd.cursor_pos = (1, 0)
                    self.lcd.write_string(self.last_lcd_content[1].ljust(16))
                    time.sleep(0.05)
                    
                print("LCD display refreshed")
                
            except Exception as e:
                print(f"LCD refresh error: {e}")
                self.lcd_error_count += 1

    def get_distance(self):
        GPIO.output(TRIG_PIN, False)
        time.sleep(0.002)
        GPIO.output(TRIG_PIN, True)
        time.sleep(0.00001)
        GPIO.output(TRIG_PIN, False)

        pulse_start = pulse_end = None
        timeout = time.time() + 0.03
        while GPIO.input(ECHO_PIN) == 0 and time.time() < timeout:
            pulse_start = time.time()
        while GPIO.input(ECHO_PIN) == 1 and time.time() < timeout:
            pulse_end = time.time()

        if pulse_start is None or pulse_end is None:
            return -1
        duration = pulse_end - pulse_start
        return duration * 34300 / 2

    def check_light_level(self):
        try:
            ldr_value = GPIO.input(LDR_PIN)
            self.is_dark = ldr_value == 0
            return self.is_dark
        except Exception as e:
            print(f"LDR read error: {e}")
            return False

    def control_light(self, state):
        try:
            if state != self.light_state:
                GPIO.output(LIGHT_PIN, GPIO.HIGH if state else GPIO.LOW)
                self.light_state = state
                status = "ON" if state else "OFF"
                print(f"Light turned {status}")
                log_event("light_control", {"state": status, "dark": self.is_dark})
        except Exception as e:
            print(f"Light control error: {e}")

    def turn_on_light(self, reason="Manual control"):
        try:
            GPIO.output(LIGHT_PIN, GPIO.HIGH)
            self.light_state = True
            print(f"Light turned ON: {reason}")
            self.lcd_write("Light ON", reason[:15])
            log_event("light_on", {"reason": reason, "dark": self.is_dark})
        except Exception as e:
            print(f"Turn on light error: {e}")

    def turn_off_light(self, reason="Manual control"):
        try:
            GPIO.output(LIGHT_PIN, GPIO.LOW)
            self.light_state = False
            print(f"Light turned OFF: {reason}")
            self.lcd_write("Light OFF", reason[:15])
            log_event("light_off", {"reason": reason, "dark": self.is_dark})
        except Exception as e:
            print(f"Turn off light error: {e}")

    def beep(self, ms=300):
        try:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(ms / 1000.0)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
        except Exception as e:
            print(f"Beep error: {e}")

    def unlock(self, seconds=5):
        try:
            print(f"Unlocking door for {seconds} seconds")
            self.lcd_write("Door Unlocked", "")
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            self.door_locked = False
            log_event("door_unlocked", {"duration": seconds})
            
            time.sleep(seconds)
            
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.door_locked = True
            self.lcd_write("Door Locked", "")
            log_event("door_locked", {"auto_lock": True})
            print("Door locked again")
        except Exception as e:
            print(f"Unlock error: {e}")
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.door_locked = True

    def manual_unlock(self, seconds=5):
        if not self.door_locked:
            print("Door already unlocked")
            return
        threading.Thread(target=self.unlock, args=(seconds,), daemon=True).start()

    def lock_door(self):
        try:
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.door_locked = True
            self.lcd_write("Door Locked", "Manual Lock")
            log_event("door_locked", {"manual": True})
            print("Door manually locked")
        except Exception as e:
            print(f"Lock error: {e}")

    def run(self):
        print("Sensors thread running.")
        try:
            while True:
                try:
                    pir = GPIO.input(PIR_PIN)
                    current_time = time.time()
                    
                    self.lcd_refresh_counter += 1
                    if self.lcd_refresh_counter >= self.lcd_refresh_interval:
                        self.refresh_lcd_display()
                        self.lcd_refresh_counter = 0
                    
                    is_dark = self.check_light_level()
                    if is_dark:
                        self.control_light(True)
                    else:
                        self.control_light(False)

                    if pir == GPIO.HIGH and not self.monitoringActive:
                        if current_time - self.last_pir_time >= self.pir_cooldown:
                            self.monitoringActive = True
                            self.last_pir_time = current_time
                            print("PIR triggered: monitoring active")
                            self.lcd_write("Motion Detected", "Scanning...")
                            log_event("motion", {"msg": "PIR triggered"})

                    if self.monitoringActive:
                        dist = self.get_distance()
                        if 0 < dist <= 40:
                            self.lcd_write("Verification...", f"Range: {int(dist)}cm")
                            if self.alert_callback and (current_time - self.last_alert_time >= self.alert_cooldown):
                                threading.Thread(target=self.alert_callback, args=(dist,), daemon=True).start()
                                self.last_alert_time = current_time
                        else:
                            self.lcd_write("Scanning Area", "No Person")
                            if pir == GPIO.LOW:
                                self.monitoringActive = False
                                self.lcd_write("System Ready", "Monitoring...")
                                log_event("motion_reset", {"msg": "monitor reset"})
                        time.sleep(0.5)
                    else:
                        current_hour = time.localtime().tm_hour
                        time_str = f"{current_hour:02d}:{time.localtime().tm_min:02d}"
                        status = "Dark" if self.is_dark else "Light"
                        self.lcd_write(f"DoorCam {time_str}", f"Ready - {status}")
                        time.sleep(0.5)
                except Exception as e:
                    print(f"Sensor loop error: {e}")
                    time.sleep(1)
        except KeyboardInterrupt:
            print("Sensors stopped by user")
        except Exception as e:
            print(f"Fatal sensor error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        try:
            print("Starting cleanup...")
            self.control_light(False)
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.door_locked = True
            print("Door locked on cleanup")
            
            if self.lcd:
                try:
                    self.lcd.clear()
                    self.lcd.write_string("System Shutdown")
                    time.sleep(1)
                    self.lcd.close(clear=True)
                    print("LCD cleanup complete")
                except:
                    pass
            
            GPIO.cleanup()
            print("GPIO cleanup complete")
        except Exception as e:
            print(f"Cleanup error: {e}")


