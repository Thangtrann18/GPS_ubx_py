import serial
import requests
import pynmea2
from datetime import datetime, timezone, timedelta


class GPS:
    deviceId = "GPS_test"
    transToken = "132456"

    def __init__(self, port="COM3", baudrate=115200):
        self.hdop = None
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            print(f"Opened serial port {port} at {baudrate}")
        except Exception as e:
            print(f"Error opening serial port: {e}")
            self.ser = None

    def parse_gga(self, msg):
        """Parse NMEA GGA → lat, lon, hdop, alt"""
        try:
            lat = self.convert_to_decimal(float(msg.lat), msg.lat_dir) if msg.lat else None
            lon = self.convert_to_decimal(float(msg.lon), msg.lon_dir) if msg.lon else None
            hdop = float(msg.horizontal_dil) if msg.horizontal_dil else None
            alt = float(msg.altitude) if msg.altitude else None

            self.hdop = hdop
            print(f"NMEA-GGA updated: lat={lat}, lon={lon}, hdop={hdop}, alt={alt}")
            return lat, lon, alt, hdop
        except Exception as e:
            print(f"Error parsing GGA: {e}")
            return None, None, None, None

    def parse_rmc(self, msg, deviceId, transToken):
        """Parse NMEA RMC → gửi dữ liệu lên API"""
        try:
            lat = self.convert_to_decimal(float(msg.lat), msg.lat_dir) if msg.lat else None
            lon = self.convert_to_decimal(float(msg.lon), msg.lon_dir) if msg.lon else None

            # Nếu chưa có hdop từ GGA → bỏ qua
            hdop = self.hdop if self.hdop else None

            # Thời gian UTC từ câu RMC
            if msg.datestamp and msg.timestamp:
                utc_time = datetime.combine(msg.datestamp, msg.timestamp, tzinfo=timezone.utc)
            else:
                utc_time = datetime.now(timezone.utc)

            vietnam_time = utc_time.astimezone(timezone(timedelta(hours=7)))
            timestamp = vietnam_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

            if lat and lon and hdop and hdop < 5.0:  # ngưỡng chất lượng
                gps_data = {
                    "latitude": lat,
                    "longitude": lon,
                    "hdop": hdop,
                    "deviceId": deviceId,
                    "transToken": transToken,
                    "trackingDate": timestamp
                }

                url = "Nhập API"
                try:
                    response = requests.post(url, json=gps_data, timeout=5)
                    if response.status_code == 200:
                        print("GPS uploaded successfully (API1)!")
                    else:
                        print(f"API1 error: {response.status_code} {response.text}")
                except Exception as e:
                    print(f"API1 request error: {e}")

        except Exception as e:
            print(f"Error parsing RMC: {e}")

    def convert_to_decimal(self, raw_value, direction):
        """Chuyển NMEA ddmm.mmmm sang độ thập phân"""
        if not raw_value or raw_value == 0:
            return None
        degrees = int(raw_value / 100)
        minutes = raw_value - degrees * 100
        decimal = degrees + minutes / 60
        if direction in ['S', 'W']:
            decimal = -decimal
        return decimal

    def run(self, deviceId="TEST_DEVICE", transToken="TEST_TOKEN"):
        if not self.ser:
            return
        try:
            while True:
                try:
                    line = self.ser.readline().decode("ascii", errors="ignore").strip()
                    if not line.startswith("$"):
                        continue

                    try:
                        msg = pynmea2.parse(line)
                    except pynmea2.ParseError:
                        continue

                    if isinstance(msg, pynmea2.types.talker.GGA):
                        self.parse_gga(msg)
                    elif isinstance(msg, pynmea2.types.talker.RMC):
                        self.parse_rmc(msg, deviceId, transToken)

                except KeyboardInterrupt:
                    print("Stopped by user")
                    break
                except Exception as e:
                    print(f"Error parsing GPS: {e}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
                print("Serial port closed")


if __name__ == "__main__":
    gps = GPS("COM3", 115200) 
    gps.run("GPS_9012_Thang", "MY_TRANS_TOKEN")

