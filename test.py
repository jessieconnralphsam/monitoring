import serial
import serial.tools.list_ports
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

class UsbDataCollectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("USB Data Collector")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        self.serial_conn = None
        self.is_connected = False
        self.is_collecting = False
        self.collection_thread = None
        
        self.create_widgets()
        self.refresh_ports()
        
    def create_widgets(self):

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        conn_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="10")
        conn_frame.pack(fill=tk.X, pady=5)
        
        port_frame = ttk.Frame(conn_frame)
        port_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT, padx=5)
        self.port_combo = ttk.Combobox(port_frame, width=30)
        self.port_combo.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(port_frame, text="Refresh", command=self.refresh_ports)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(pady=5)
        
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=5)
        
        self.request_btn = ttk.Button(control_frame, text="Request Data", command=self.request_data)
        self.request_btn.pack(side=tk.LEFT, padx=5)
        self.request_btn.config(state=tk.DISABLED)
        
        self.auto_collect_var = tk.BooleanVar(value=False)
        auto_collect_check = ttk.Checkbutton(control_frame, text="Auto Collect", 
                                           variable=self.auto_collect_var,
                                           command=self.toggle_auto_collect)
        auto_collect_check.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Interval (s):").pack(side=tk.LEFT, padx=5)
        self.interval_var = tk.StringVar(value="5")
        interval_entry = ttk.Entry(control_frame, textvariable=self.interval_var, width=5)
        interval_entry.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(control_frame, text="Save to CSV", command=self.save_data)
        self.save_btn.pack(side=tk.LEFT, padx=10)
        self.save_btn.config(state=tk.DISABLED)
        
        clear_btn = ttk.Button(control_frame, text="Clear Log", command=self.clear_log)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        viewport_frame = ttk.LabelFrame(main_frame, text="Response Viewport", padding="10")
        viewport_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(viewport_frame, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        data_frame = ttk.LabelFrame(main_frame, text="Parsed Data", padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.data_text = scrolledtext.ScrolledText(data_frame, height=10, wrap=tk.WORD)
        self.data_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.status_var = tk.StringVar(value="Disconnected")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.current_data = None

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
            
    def log_message(self, message):
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')}: {message}\n")
        self.log_text.see(tk.END)
        
    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()
            
    def connect(self):
        port = self.port_combo.get()
        if not port:
            messagebox.showerror("Error", "Please select a port")
            return
            
        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=19200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            self.is_connected = True
            self.connect_btn.config(text="Disconnect")
            self.request_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Connected to {port}")
            self.log_message(f"Connected to {port}")
            
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", str(e))
            self.log_message(f"Connection error: {e}")
            
    def disconnect(self):
        if self.is_collecting:
            self.toggle_auto_collect()  
            
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            
        self.is_connected = False
        self.connect_btn.config(text="Connect")
        self.request_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.status_var.set("Disconnected")
        self.log_message("Disconnected")
        
    def calculate_fcs(self, command):
        result = 0
        for char in command:
            result ^= ord(char)
        
        return format(result, '02X')
        
    def request_data(self):
        if not self.is_connected or not self.serial_conn:
            messagebox.showerror("Error", "Not connected to device")
            return
            
        command = "#RD@"
        fcs = self.calculate_fcs(command)
        full_command = f"{command}{fcs}\r\n"
        
        try:
            self.serial_conn.write(full_command.encode())
            self.log_message(f"Sent command: {full_command.strip()}")
            
            time.sleep(0.5)
            
            if self.serial_conn.in_waiting:
                response = self.serial_conn.read(self.serial_conn.in_waiting).decode('ascii')
                self.log_message(f"Received {len(response)} bytes")
                
                data = self.parse_response(response)
                if data:
                    self.display_data(data)
                    self.current_data = data
                    self.save_btn.config(state=tk.NORMAL)
            else:
                self.log_message("No response received")
                
        except Exception as e:
            self.log_message(f"Error: {e}")
            messagebox.showerror("Error", str(e))

    def parse_response(self, response):
        try:
            if not response.startswith('#RD'):
                self.log_message(f"Invalid response format: {response[:10]}...")
                return None
                
            site_name = response[3:23].strip()
            
            probe_status = response[23]
            probe_error = response[24]
            
            parameters = []
            for i in range(13):
                start_idx = 29 + (i * 11)
                
                param = {
                    'code': response[start_idx:start_idx+2],
                    'status': response[start_idx+2],
                    'error': response[start_idx+3],
                    'data': response[start_idx+4:start_idx+9].strip(),
                    'unit': response[start_idx+9]
                }
                parameters.append(param)
            
            date_idx = 173
            try:
                year = int(response[date_idx:date_idx+2])
                month = int(response[date_idx+2:date_idx+4])
                day = int(response[date_idx+4:date_idx+6])
                hour = int(response[date_idx+6:date_idx+8])
                minute = int(response[date_idx+8:date_idx+10])
                second = int(response[date_idx+10:date_idx+12])
                
                timestamp = datetime(2000 + year, month, day, hour, minute, second)
            except (ValueError, IndexError):
                timestamp = None
                self.log_message("Error parsing timestamp")
            
            try:
                lon_degrees = response[date_idx+12:date_idx+14]
                lon_minutes = response[date_idx+14:date_idx+16]
                lon_seconds = response[date_idx+16:date_idx+18]
                
                ns_indicator = response[date_idx+19]
                
                lat_degrees = response[date_idx+20:date_idx+23]
                lat_minutes = response[date_idx+23:date_idx+25]
                lat_seconds = response[date_idx+25:date_idx+27]
                
                ew_indicator = response[date_idx+28]
                
                if lon_degrees != "--" and lat_degrees != "---":
                    gps_coords = {
                        'latitude': {
                            'degrees': int(lat_degrees),
                            'minutes': int(lat_minutes),
                            'seconds': int(lat_seconds),
                            'direction': ns_indicator
                        },
                        'longitude': {
                            'degrees': int(lon_degrees),
                            'minutes': int(lon_minutes),
                            'seconds': int(lon_seconds),
                            'direction': ew_indicator
                        }
                    }
                else:
                    gps_coords = None
            except (ValueError, IndexError):
                gps_coords = None
                self.log_message("Error parsing GPS coordinates")
            
            result = {
                'site_name': site_name,
                'probe_status': probe_status,
                'probe_error': probe_error,
                'parameters': parameters,
                'timestamp': timestamp,
                'gps_coordinates': gps_coords
            }
            
            return result
        except Exception as e:
            self.log_message(f"Error parsing response: {e}")
            return None
    
    def display_data(self, data):
        if not data:
            return
            
        self.data_text.delete(1.0, tk.END)
        
        self.data_text.insert(tk.END, f"--- Data Summary ---\n")
        self.data_text.insert(tk.END, f"Site name: {data['site_name']}\n")
        self.data_text.insert(tk.END, f"Probe status: {data['probe_status']}, Error: {data['probe_error']}\n\n")
        
        self.data_text.insert(tk.END, "Parameters:\n")
        for i, param in enumerate(data['parameters']):
            if param['code'] != '  ' and param['code'] != '':
                self.data_text.insert(tk.END, f"{i+1}. Code: {param['code']}, Value: {param['data']} {param['unit']}, Status: {param['status']}, Error: {param['error']}\n")
        
        if data['timestamp']:
            self.data_text.insert(tk.END, f"\nTimestamp: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if data['gps_coordinates']:
            lat = data['gps_coordinates']['latitude']
            lon = data['gps_coordinates']['longitude']
            
            lat_str = f"{lat['degrees']}°{lat['minutes']}'{lat['seconds']}\"{lat['direction']}"
            lon_str = f"{lon['degrees']}°{lon['minutes']}'{lon['seconds']}\"{lon['direction']}"
            
            self.data_text.insert(tk.END, f"GPS Location: {lat_str}, {lon_str}\n")
    
    def save_data(self):
        if not self.current_data:
            messagebox.showerror("Error", "No data to save")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"U50PC_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filename: 
            return
            
        try:
            with open(filename, 'w') as f:
                # Header row 1
                f.write("U-50PC DataFile\tVersion\t1\t1\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\n")
                
                # Header row 2
                f.write("No.\tSITE\tDate\tTime\tLatitude\tLongitude\tProbe error\t")
                
                # Parameter headers
                parameter_headers = [
                    "Temperature\t10\tError",
                    "pH\t1\tError",
                    "pHmV\t24\tError",
                    "ORP\t2\tError",
                    "Conductivity\t6\tError",
                    "Turbidity\t3\tError",
                    "Dissolved Oxygen\t4\tError",
                    "DO%\t22\tError",
                    "TDS\t8\tError",
                    "Salinity\t7\tError",
                    "Specific gravity\t9\tError",
                    "Depth\t11\tError",
                    "---\t0\tError"
                ]
                
                f.write("\t".join(parameter_headers))
                f.write("\tBattery voltage\tDevice code\tDate code\tTime code\tUnit code\tFormat code\tStatus code\tSensor error code\n")
                
                # Data row
                # Row number
                f.write("1\t")
                
                # Site name
                f.write(f"{self.current_data['site_name']}\t")
                
                # Date and time
                if self.current_data['timestamp']:
                    f.write(f"{self.current_data['timestamp'].strftime('%Y/%m/%d')}\t")
                    f.write(f"{self.current_data['timestamp'].strftime('%H:%M:%S')}\t")
                else:
                    f.write("\t\t")
                
                # GPS coordinates
                if self.current_data['gps_coordinates']:
                    lat = self.current_data['gps_coordinates']['latitude']
                    lon = self.current_data['gps_coordinates']['longitude']
                    
                    lat_str = f"{lat['degrees']} {lat['minutes']} {lat['seconds']} {lat['direction']}"
                    lon_str = f"{lon['degrees']} {lon['minutes']} {lon['seconds']} {lon['direction']}"
                    
                    f.write(f"{lat_str}\t{lon_str}\t")
                else:
                    f.write("-- -- -- -\t--- -- -- -\t")
                
                # Probe error
                f.write(f"{self.current_data['probe_error']}\t")
                
                # Parameter values
                # Create a dictionary to map parameter codes to their positions in the output
                param_mapping = {
                    '10': 0,  # Temperature
                    '1': 1,   # pH
                    '24': 2,  # pHmV
                    '2': 3,   # ORP
                    '6': 4,   # Conductivity
                    '3': 5,   # Turbidity
                    '4': 6,   # Dissolved Oxygen
                    '22': 7,  # DO%
                    '8': 8,   # TDS
                    '7': 9,   # Salinity
                    '9': 10,  # Specific gravity
                    '11': 11, # Depth
                    '0': 12   # ---
                }
                
                # Initialize parameter valuesssss
                param_values = [""] * 13
                param_units = ["°C", "pH", "mV", "mV", "mS/cm", "NTU", "mg/L", "%", "g/L", "ppt", "Sigma t", "m", "-"]
                param_errors = [""] * 13
                
                # Fill in values from the data
                for param in self.current_data['parameters']:
                    code = param['code'].strip()
                    if code in param_mapping:
                        idx = param_mapping[code]
                        param_values[idx] = param['data']
                        param_errors[idx] = param['error']
                
                # Write parameter values, units, and errors
                for i in range(13):
                    if param_values[i]:
                        f.write(f"{param_values[i]}\t{param_units[i]}\t{param_errors[i]}\t")
                    else:
                        f.write(f"-\t{param_units[i]}\t-\t")
                
                # Additional fields
                f.write("    V\t")  # Battery voltage
                f.write("P30\t")    # Device code
                
                # Date and time codes
                if self.current_data['timestamp']:
                    f.write(f"D{self.current_data['timestamp'].strftime('%y%m%d')}\t")
                    f.write(f"T{self.current_data['timestamp'].strftime('%H%M%S')}\t")
                else:
                    f.write("D------\tT------\t")
                
                # Standard codes
                f.write("U0000000000000\t")  # Unit code
                f.write("F2200202131120\t")  # Format code
                f.write("S1111111111110\t")  # Status code
                f.write("A0000000000000\n")  # Sensor error code
                    
            self.log_message(f"Data saved to {filename}")
            messagebox.showinfo("Success", f"Data saved to {filename}")
        except Exception as e:
            self.log_message(f"Error saving data: {e}")
            messagebox.showerror("Error", f"Error saving data: {e}")
    
    def toggle_auto_collect(self):
        if self.is_collecting:
            self.is_collecting = False
            self.status_var.set("Auto-collection stopped")
            self.log_message("Auto-collection stopped")
        else:
            if not self.is_connected:
                messagebox.showerror("Error", "Not connected to device")
                self.auto_collect_var.set(False)
                return
                
            try:
                interval = float(self.interval_var.get())
                if interval < 1:
                    messagebox.showerror("Error", "Interval must be at least 1 second")
                    self.auto_collect_var.set(False)
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid interval value")
                self.auto_collect_var.set(False)
                return
                
            self.is_collecting = True
            self.status_var.set(f"Auto-collecting data every {interval} seconds")
            self.log_message(f"Started auto-collection every {interval} seconds")
            self.collection_thread = threading.Thread(target=self.auto_collect_data, daemon=True)
            self.collection_thread.start()
    
    def auto_collect_data(self):
        while self.is_collecting and self.is_connected:
            self.request_data()
            
            try:
                interval = float(self.interval_var.get())
                time.sleep(interval)
            except ValueError:
                time.sleep(5)  
                
            if not self.is_connected or not self.auto_collect_var.get():
                self.is_collecting = False
                break
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def on_closing(self):
        if self.is_connected:
            self.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = UsbDataCollectorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()