import serial
import serial.tools.list_ports
import time
import threading
import json
import requests
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
        self.is_sending_webhook = False
        self.webhook_thread = None
        
        # Webhook configuration
        self.webhook_url = tk.StringVar(value="http://127.0.0.1:8000/api/series/SuUgBtTElYwClk07RimZpO4YDxWcvTLN/v1")
        self.webhook_auth = tk.StringVar(value="Bearer 1|XbPw6M7kVD7SwyXxjgF5QheqgET1pFJANMYTaV5i4e3b5bad")
        self.webhook_param_map = {
            'd1': 0,  # Temperature (parameter 1) maps to d1
            'd2': 1,  # pH (parameter 2) maps to d2
            'd3': 2,  # pHmv (parameter 3) maps to d3
            'd4': 3,  # ORP (parameter 4) maps to d4
            'd5': 4,  # Conductivity (parameter 5) maps to d5
            'd6': 5,  # Turbidity (parameter 6) maps to d6
            'd7': 6,  # DO (parameter 7) maps to d7
            'd8': 7,  # TDS (parameter 8) maps to d8
            'd9': 8,  # Spec Gravity (parameter 9) maps to d9
            'd10': 9,  # Depth (parameter 10) maps to d10
            'd11': 10, # Parameter 11 maps to d11
            'd12': 11  # Parameter 12 maps to d12
        }
        
        # Store parsed data for webhook use
        self.parsed_values = {}
        
        self.create_widgets()
        self.refresh_ports()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Connection settings
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
        
        # Main controls
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
        
        clear_btn = ttk.Button(control_frame, text="Clear Log", command=self.clear_log)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Webhook Configuration
        webhook_frame = ttk.LabelFrame(main_frame, text="Webhook Configuration", padding="10")
        webhook_frame.pack(fill=tk.X, pady=5)
        
        url_frame = ttk.Frame(webhook_frame)
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=5)
        url_entry = ttk.Entry(url_frame, textvariable=self.webhook_url, width=60)
        url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        auth_frame = ttk.Frame(webhook_frame)
        auth_frame.pack(fill=tk.X, pady=5)
        ttk.Label(auth_frame, text="Auth:").pack(side=tk.LEFT, padx=5)
        auth_entry = ttk.Entry(auth_frame, textvariable=self.webhook_auth, width=60)
        auth_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        mapping_frame = ttk.Frame(webhook_frame)
        mapping_frame.pack(fill=tk.X, pady=5)
        
        # Create parameter mapping widgets
        param_frame1 = ttk.Frame(mapping_frame)
        param_frame1.pack(fill=tk.X, pady=2)
        self.create_param_mapping(param_frame1, 'd1', 'd2', 'd3', 'd4', 'd5', 'd6')
        
        param_frame2 = ttk.Frame(mapping_frame)
        param_frame2.pack(fill=tk.X, pady=2)
        self.create_param_mapping(param_frame2, 'd7', 'd8', 'd9', 'd10', 'd11', 'd12')
        
        webhook_btn_frame = ttk.Frame(webhook_frame)
        webhook_btn_frame.pack(fill=tk.X, pady=5)
        
        self.send_webhook_btn = ttk.Button(webhook_btn_frame, text="Send Data Now", command=self.send_webhook_manual)
        self.send_webhook_btn.pack(side=tk.LEFT, padx=5)
        self.send_webhook_btn.config(state=tk.DISABLED)
        
        self.auto_webhook_var = tk.BooleanVar(value=False)
        auto_webhook_check = ttk.Checkbutton(webhook_btn_frame, text="Auto Send", 
                                           variable=self.auto_webhook_var,
                                           command=self.toggle_auto_webhook)
        auto_webhook_check.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(webhook_btn_frame, text="Webhook Interval (s):").pack(side=tk.LEFT, padx=5)
        self.webhook_interval_var = tk.StringVar(value="30")
        webhook_interval_entry = ttk.Entry(webhook_btn_frame, textvariable=self.webhook_interval_var, width=5)
        webhook_interval_entry.pack(side=tk.LEFT, padx=5)
        
        # Response Viewport with both horizontal and vertical scrolling
        viewport_frame = ttk.LabelFrame(main_frame, text="Response Viewport", padding="10")
        viewport_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create container frame for the text and scrollbars
        viewport_container = ttk.Frame(viewport_frame)
        viewport_container.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbars
        viewport_vscroll = ttk.Scrollbar(viewport_container, orient=tk.VERTICAL)
        viewport_hscroll = ttk.Scrollbar(viewport_container, orient=tk.HORIZONTAL)
        
        # Create text widget with both scrollbars
        self.log_text = tk.Text(viewport_container, height=20, wrap=tk.NONE,
                               yscrollcommand=viewport_vscroll.set,
                               xscrollcommand=viewport_hscroll.set)
        
        # Configure scrollbars
        viewport_vscroll.config(command=self.log_text.yview)
        viewport_hscroll.config(command=self.log_text.xview)
        
        # Place the scrollbars and text widget
        viewport_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        viewport_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Parsed Data with both horizontal and vertical scrolling
        data_frame = ttk.LabelFrame(main_frame, text="Parsed Data", padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create container frame for the text and scrollbars
        data_container = ttk.Frame(data_frame)
        data_container.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbars
        data_vscroll = ttk.Scrollbar(data_container, orient=tk.VERTICAL)
        data_hscroll = ttk.Scrollbar(data_container, orient=tk.HORIZONTAL)
        
        # Create text widget with both scrollbars
        self.data_text = tk.Text(data_container, height=10, wrap=tk.NONE,
                                yscrollcommand=data_vscroll.set,
                                xscrollcommand=data_hscroll.set)
        
        # Configure scrollbars
        data_vscroll.config(command=self.data_text.yview)
        data_hscroll.config(command=self.data_text.xview)
        
        # Place the scrollbars and text widget
        data_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        data_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.data_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.status_var = tk.StringVar(value="Disconnected")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.current_data = None

    def create_param_mapping(self, parent, *fields):
        param_names = ["Temperature", "pH", "pHmv", "ORP", "Conductivity", "Turbidity", 
                      "DO", "TDS", "Spec Gravity", "Depth", "Param 11", "Param 12"]
        
        for i, field in enumerate(fields):
            frame = ttk.Frame(parent)
            frame.pack(side=tk.LEFT, padx=5)
            
            ttk.Label(frame, text=f"{field}:").pack(side=tk.TOP)
            
            # Create combobox for parameter selection
            param_combo = ttk.Combobox(frame, width=10, values=param_names)
            param_combo.current(self.webhook_param_map[field])  # Set default selection
            param_combo.pack(side=tk.TOP)
            
            # Store reference to combobox
            setattr(self, f"{field}_combo", param_combo)

    def update_webhook_param_map(self):
        # Update the parameter mapping from UI selections
        for field in ['d1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'd10', 'd11', 'd12']:
            combo = getattr(self, f"{field}_combo")
            param_index = combo.current()
            if param_index >= 0:
                self.webhook_param_map[field] = param_index

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
            self.send_webhook_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Connected to {port}")
            self.log_message(f"Connected to {port}")
            
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", str(e))
            self.log_message(f"Connection error: {e}")
            
    def disconnect(self):
        if self.is_collecting:
            self.toggle_auto_collect()  
            
        if self.is_sending_webhook:
            self.toggle_auto_webhook()
            
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            
        self.is_connected = False
        self.connect_btn.config(text="Connect")
        self.request_btn.config(state=tk.DISABLED)
        self.send_webhook_btn.config(state=tk.DISABLED)
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

            # Process the response according to the new parsing method
            raw = response.strip()
            parts = raw.split()

            labels = [
                "Code",
                "Temperature",
                "pH",
                "pHmv",
                "ORP",
                "mS/cm",
                "NTU",
                "mg/L DO",
                "g/L TDS",
                "ppt",
                "O' T",
                "m",
                "%DO"
            ]

            # Clear previous parsed values
            self.parsed_values = {}

            def parse_temperature(value):
                return f"{float(value) % 1000:.2f}"

            def parse_others(value, is_orp=False):
                return value[:3] if is_orp else value[:4]

            for i in range(1, min(13, len(parts))):
                try:
                    value = parts[i]
                    if labels[i] == "Temperature":
                        parsed_value = parse_temperature(value)
                    elif labels[i] == "ORP":
                        parsed_value = parse_others(value, is_orp=True)
                    else:
                        parsed_value = parse_others(value)
                    
                    # Store the parsed values for webhook use
                    self.parsed_values[labels[i]] = parsed_value
                    self.log_message(f"{labels[i]}: {parsed_value}")
                except Exception as e:
                    self.log_message(f"Error parsing parameter {i}: {e}")

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
        
        # Display parsed values from the new parsing method
        self.data_text.insert(tk.END, "Parameters (New Parsing Method):\n")
        for label, value in self.parsed_values.items():
            self.data_text.insert(tk.END, f"{label}: {value}\n")
        
        if data['timestamp']:
            self.data_text.insert(tk.END, f"\nTimestamp: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if data['gps_coordinates']:
            lat = data['gps_coordinates']['latitude']
            lon = data['gps_coordinates']['longitude']
            
            lat_str = f"{lat['degrees']}°{lat['minutes']}'{lat['seconds']}\"{lat['direction']}"
            lon_str = f"{lon['degrees']}°{lon['minutes']}'{lon['seconds']}\"{lon['direction']}"
            
            self.data_text.insert(tk.END, f"GPS Location: {lat_str}, {lon_str}\n")
    
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
    
    def toggle_auto_webhook(self):
        if self.is_sending_webhook:
            self.is_sending_webhook = False
            self.status_var.set("Auto-webhook stopped")
            self.log_message("Auto-webhook stopped")
        else:
            if not self.is_connected:
                messagebox.showerror("Error", "Not connected to device")
                self.auto_webhook_var.set(False)
                return
                
            try:
                interval = float(self.webhook_interval_var.get())
                if interval < 1:
                    messagebox.showerror("Error", "Interval must be at least 1 second")
                    self.auto_webhook_var.set(False)
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid interval value")
                self.auto_webhook_var.set(False)
                return
                
            self.is_sending_webhook = True
            self.status_var.set(f"Auto-sending webhook data every {interval} seconds")
            self.log_message(f"Started auto-webhook every {interval} seconds")
            self.webhook_thread = threading.Thread(target=self.auto_send_webhook, daemon=True)
            self.webhook_thread.start()
    
    def auto_send_webhook(self):
        while self.is_sending_webhook and self.is_connected:
            # First request fresh data if not already auto-collecting
            if not self.is_collecting:
                self.request_data()
            
            # Send webhook if we have data
            if self.parsed_values:  # Use parsed_values instead of current_data
                self.send_webhook_data()
            
            try:
                interval = float(self.webhook_interval_var.get())
                time.sleep(interval)
            except ValueError:
                time.sleep(30)  # Default to 30 seconds if invalid
                
            if not self.is_connected or not self.auto_webhook_var.get():
                self.is_sending_webhook = False
                break
    
    def send_webhook_manual(self):
        if not self.parsed_values:  # Use parsed_values instead of current_data
            messagebox.showerror("Error", "No data available to send")
            return
            
        self.send_webhook_data()
    
    def send_webhook_data(self):
        try:
            # Update parameter mapping from UI
            self.update_webhook_param_map()
            
            # Map from parameter names to webhook fields
            param_name_to_index = {
                "Temperature": 0,
                "pH": 1,
                "pHmv": 2,
                "ORP": 3,
                "mS/cm": 4,  # Conductivity
                "NTU": 5,     # Turbidity
                "mg/L DO": 6, # DO
                "g/L TDS": 7, # TDS
                "ppt": 8,     # Spec Gravity
                "m": 9,       # Depth
                "O' T": 10,   # Parameter 11
                "%DO": 11     # Parameter 12
            }
            
            # Prepare critical data (d1-d5)
            critical_data = {}
            for i in range(1, 6):
                field_name = f'd{i}'
                param_idx = self.webhook_param_map[field_name]
                
                # Find the corresponding parameter name
                param_name = None
                for name, idx in param_name_to_index.items():
                    if idx == param_idx:
                        param_name = name
                        break
                
                # Get the parsed value if available
                if param_name and param_name in self.parsed_values:
                    try:
                        critical_data[field_name] = float(self.parsed_values[param_name])
                    except ValueError:
                        critical_data[field_name] = 0.0
                else:
                    critical_data[field_name] = 0.0
            
            # Prepare non-critical data (d6-d12)
            non_critical_data = {}
            for i in range(6, 13):
                field_name = f'd{i}'
                param_idx = self.webhook_param_map[field_name]
                
                # Find the corresponding parameter name
                param_name = None
                for name, idx in param_name_to_index.items():
                    if idx == param_idx:
                        param_name = name
                        break
                
                # Get the parsed value if available
                if param_name and param_name in self.parsed_values:
                    try:
                        non_critical_data[field_name] = float(self.parsed_values[param_name])
                    except ValueError:
                        non_critical_data[field_name] = 0.0
                else:
                    non_critical_data[field_name] = 0.0
            
            # Build the webhook payload
            payload = [
                {
                    "name": "critical",
                    "value": critical_data
                },
                {
                    "name": "non-critical",
                    "value": non_critical_data
                }
            ]
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": self.webhook_auth.get()
            }
            
            # Log the webhook request
            self.log_message(f"Sending webhook to: {self.webhook_url.get()}")
            self.log_message(f"Webhook payload: {json.dumps(payload)}")
            print(json.dumps(payload))
            
            # Send the webhook request
            response = requests.post(
                self.webhook_url.get(),
                headers=headers,
                json=payload,
                timeout=10
            )
            
            # Handle the response
            if response.status_code >= 200 and response.status_code < 300:
                self.log_message(f"Webhook sent successfully. Response: {response.status_code}")
            else:
                self.log_message(f"Webhook failed. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_message(f"Error sending webhook: {e}")
            if not self.is_sending_webhook:  # Only show error message for manual sends
                messagebox.showerror("Webhook Error", str(e))
    
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