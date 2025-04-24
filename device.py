import tkinter as tk
from tkinter import ttk, messagebox
import serial
import logging
import requests
import csv
import time
from serial.tools import list_ports
from tkinter import font as tkfont

CSV_FILE_PATH = r"build\vcs\1.csv"

class ArduinoMonitor(tk.Tk):
    def __init__(self):
        super().__init__()

        # Set up the window
        self.title("Arduino Sensor Monitor")
        self.geometry("550x680")
        self.configure(bg="#f0f0f0")
        
        # Initialize colors
        self.primary_color = "#4a6fa5"  # blue
        self.success_color = "#4CAF50"  # green
        self.warning_color = "#ff9800"  # orange
        self.error_color = "#f44336"    # red
        self.bg_color = "#f0f0f0"       # light gray
        
        # Configure logging
        self.logger = logging.getLogger("ArduinoMonitor")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Create main frame
        main_frame = tk.Frame(self, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create title
        title_font = tkfont.Font(family="Arial", size=16, weight="bold")
        title = tk.Label(main_frame, text="Monitoring", font=title_font, bg=self.bg_color, fg=self.primary_color)
        title.pack(pady=(0, 20))
        
        # Connection settings frame
        conn_frame = tk.LabelFrame(main_frame, text="Connection Settings", bg=self.bg_color, fg=self.primary_color, padx=10, pady=10)
        conn_frame.pack(fill=tk.X, pady=(0, 15))
        
        # COM Port selection
        port_frame = tk.Frame(conn_frame, bg=self.bg_color)
        port_frame.pack(fill=tk.X, pady=5)
        
        self.port_label = tk.Label(port_frame, text="COM Port:", bg=self.bg_color, font=("Arial", 11))
        self.port_label.pack(side=tk.LEFT, padx=(5, 10))
        
        self.port_combobox = ttk.Combobox(port_frame, values=self.get_serial_ports(), state="readonly", font=("Arial", 11), width=25)
        self.port_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.port_combobox.set("Select a port")
        
        self.refresh_button = ttk.Button(port_frame, text="Refresh", command=self.refresh_ports, width=10)
        self.refresh_button.pack(side=tk.RIGHT, padx=(10, 5))
        
        # Configure webhook settings
        webhook_frame = tk.LabelFrame(main_frame, text="Webhook Settings", bg=self.bg_color, fg=self.primary_color, padx=10, pady=10)
        webhook_frame.pack(fill=tk.X, pady=(0, 15))
        
        # URL
        self.url_label = tk.Label(webhook_frame, text="URL:", bg=self.bg_color, font=("Arial", 11))
        self.url_label.pack(anchor=tk.W, pady=(5, 2))
        
        self.url_entry = tk.Entry(webhook_frame, font=("Arial", 11), width=50)
        self.url_entry.pack(fill=tk.X, pady=(0, 10))
        self.url_entry.insert(0, "https://example.com/api/series/your_id/v1")
        
        # Token
        self.token_label = tk.Label(webhook_frame, text="Auth Token:", bg=self.bg_color, font=("Arial", 11))
        self.token_label.pack(anchor=tk.W, pady=(5, 2))
        
        self.token_entry = tk.Entry(webhook_frame, font=("Arial", 11), width=50, show='•')
        self.token_entry.pack(fill=tk.X, pady=(0, 5))
        self.token_entry.insert(0, "your_token_here")
        
        # Monitoring frame
        monitor_frame = tk.LabelFrame(main_frame, text="Monitoring Status", bg=self.bg_color, fg=self.primary_color, padx=10, pady=10)
        monitor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Status indicators
        self.status_frame = tk.Frame(monitor_frame, bg=self.bg_color)
        self.status_frame.pack(fill=tk.X, pady=10)
        
        status_font = tkfont.Font(family="Arial", size=12, weight="bold")
        self.status_label = tk.Label(self.status_frame, text="Status: Not Monitoring", font=status_font, bg=self.bg_color, fg=self.warning_color)
        self.status_label.pack()
        
        # Data visualization frame
        data_frame = tk.Frame(monitor_frame, bg=self.bg_color)
        data_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Sensor readings display
        self.sensor_frame = tk.Frame(data_frame, bg=self.bg_color)
        self.sensor_frame.pack(fill=tk.X, pady=5)
        
        self.sensor_display = tk.Text(self.sensor_frame, height=5, width=40, font=("Consolas", 11), bg="#f8f8f8", state="disabled")
        self.sensor_display.pack(fill=tk.BOTH, expand=True)
        
        # Webhook status with icon
        webhook_status_frame = tk.Frame(monitor_frame, bg=self.bg_color)
        webhook_status_frame.pack(fill=tk.X, pady=5)
        
        self.webhook_indicator = tk.Canvas(webhook_status_frame, width=15, height=15, bg=self.bg_color, highlightthickness=0)
        self.webhook_indicator.pack(side=tk.LEFT, padx=(5, 10))
        self.webhook_indicator.create_oval(2, 2, 13, 13, fill="gray", outline="")
        
        self.webhook_status_label = tk.Label(webhook_status_frame, text="Awaiting data transmission", font=("Arial", 11), bg=self.bg_color)
        self.webhook_status_label.pack(side=tk.LEFT)
        
        # Progress frame
        progress_frame = tk.Frame(monitor_frame, bg=self.bg_color)
        progress_frame.pack(fill=tk.X, pady=10)
        
        # Countdown with progress bar
        self.countdown_label = tk.Label(progress_frame, text="Next data send in: 5s", font=("Arial", 11), bg=self.bg_color)
        self.countdown_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=100, mode="determinate")
        self.progress_bar.pack(fill=tk.X)
        
        # Control buttons
        button_frame = tk.Frame(main_frame, bg=self.bg_color)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Monitoring", command=self.start_monitoring, width=15)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Monitoring", command=self.stop_monitoring, width=15, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
        
        # Class variables
        self.ser = None
        self.is_monitoring = False
        self.sensor_lines = None
        self.data_send_interval = 5  # interval in seconds
        self.countdown = self.data_send_interval
        self.last_send_time = 0
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 11))
        self.style.configure("TCombobox", font=("Arial", 11))
        
        # Apply custom theme
        self.configure_styles()

    def configure_styles(self):
        self.style.configure("TProgressbar", thickness=8, troughcolor="#e0e0e0", background=self.primary_color)

    def get_serial_ports(self):
        ports = list_ports.comports()
        return [port.device for port in ports]

    def refresh_ports(self):
        self.port_combobox['values'] = self.get_serial_ports()
        self.port_combobox.set("Select a port")
        self.logger.info("Serial ports refreshed.")

    def update_sensor_display(self, sensor_data):
        self.sensor_display.config(state="normal")
        self.sensor_display.delete(1.0, tk.END)
        for line in sensor_data:
            self.sensor_display.insert(tk.END, f"{line}\n")
        self.sensor_display.config(state="disabled")

    def start_monitoring(self):
        selected_port = self.port_combobox.get()

        if not selected_port or selected_port == "Select a port":
            messagebox.showwarning("No Port Selected", "Please select a COM port to start monitoring.")
            return

        try:
            self.ser = serial.Serial(selected_port, 9600, timeout=1)
            self.ser.close()  # immediately close after checking connection
            self.logger.info(f"Serial port {selected_port} detected (not used for data).")
            
            # Update UI
            self.status_label.config(text="Status: Sending Data", fg=self.success_color)
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Initialize monitoring
            self.is_monitoring = True
            self.sensor_lines = self.load_csv_data(CSV_FILE_PATH)
            
            # Update sensor display
            if self.sensor_lines and "Error" not in self.sensor_lines[0]:
                self.update_sensor_display(self.sensor_lines)
            
            # Start countdown
            self.countdown = self.data_send_interval
            self.progress_bar["maximum"] = self.data_send_interval
            self.progress_bar["value"] = self.data_send_interval
            self.send_csv_data()  # Start sending data
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to detect serial connection: {e}")
            self.logger.error(f"Serial error: {str(e)}")

    def stop_monitoring(self):
        self.is_monitoring = False
        self.status_label.config(text="Status: Monitoring Stopped", fg=self.warning_color)
        self.webhook_status_label.config(text="Monitoring stopped", fg=self.warning_color)
        self.webhook_indicator.create_oval(2, 2, 13, 13, fill="gray", outline="")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.logger.info("Monitoring stopped.")

    def send_csv_data(self):
        if not self.is_monitoring:
            return

        if self.sensor_lines and "Error" not in self.sensor_lines[0]:
            try:
                # Extract just the values in the same order: Temperature, pH, Turbidity, Dissolved Oxygen, TDS
                values = [line.split(":")[1].strip() for line in self.sensor_lines]
                data_string = "/".join(values)
                self.send_to_webhook(data_string)

                # Update last send time
                self.last_send_time = time.time()
                
                # Reset countdown
                self.countdown = self.data_send_interval
                self.progress_bar["value"] = self.data_send_interval
                self.countdown_label.config(text=f"Next data send in: {self.countdown}s")
                
                # Start countdown update
                self.update_countdown()

            except Exception as e:
                self.logger.error(f"Error parsing sensor lines: {str(e)}")
                self.webhook_status_label.config(text=f"Error: {str(e)}", fg=self.error_color)
                self.webhook_indicator.create_oval(2, 2, 13, 13, fill=self.error_color, outline="")

    def update_countdown(self):
        if not self.is_monitoring:
            return
            
        # Calculate remaining time
        elapsed = time.time() - self.last_send_time
        self.countdown = max(0, self.data_send_interval - int(elapsed))
        
        # Update progress bar
        self.progress_bar["value"] = self.countdown
        
        # Update countdown label
        self.countdown_label.config(text=f"Next data send in: {self.countdown}s")
        
        # Send data when countdown reaches zero
        if self.countdown <= 0:
            self.send_csv_data()
        else:
            # Update every 100ms for smoother countdown
            self.after(100, self.update_countdown)

    def load_csv_data(self, filepath):
        wanted = ["Temperature", "pH", "Turbidity", "Dissolved Oxygen", "TDS"]
        try:
            with open(filepath, newline='', encoding='latin-1') as csvfile:
                reader = list(csv.reader(csvfile))
                headers = reader[1]
                values = reader[2]
                sensor_data = []
                for i in range(len(headers)):
                    name = headers[i].strip()
                    if name in wanted:
                        value = values[i].strip()
                        sensor_data.append(f"{name}: {value}")
                return sensor_data
        except Exception as e:
            return [f"Error loading file: {e}"]

    def send_to_webhook(self, data):
        base_url = self.url_entry.get().strip()
        token = self.token_entry.get().strip()

        if not base_url or not token:
            self.logger.error("Webhook URL or token is missing.")
            messagebox.showerror("Error", "Webhook URL or Authorization Token is missing.")
            return

        url = f"{base_url}/{data}"
        headers = {
            "Authorization": f"{token}"
        }

        # Show sending status
        self.webhook_status_label.config(text="Sending data...", fg=self.primary_color)
        self.webhook_indicator.create_oval(2, 2, 13, 13, fill=self.primary_color, outline="")
        self.update()  # Force update to show sending status

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                self.logger.info("Data successfully sent to the webhook.")
                self.webhook_status_label.config(text="Data successfully sent!", fg=self.success_color)
                self.webhook_indicator.create_oval(2, 2, 13, 13, fill=self.success_color, outline="")
                
                # Create temporary success flash effect
                self.status_label.config(fg=self.success_color, text="Status: Data Sent Successfully")
                self.after(1500, lambda: self.status_label.config(fg=self.success_color, text="Status: Monitoring Active"))
            else:
                self.logger.error(f"Failed to send data. Status code: {response.status_code}")
                self.webhook_status_label.config(text=f"Failed: Status {response.status_code}", fg=self.error_color)
                self.webhook_indicator.create_oval(2, 2, 13, 13, fill=self.error_color, outline="")
        except Exception as e:
            self.logger.error(f"Error sending data to the webhook: {str(e)}")
            self.webhook_status_label.config(text="Connection error", fg=self.error_color)
            self.webhook_indicator.create_oval(2, 2, 13, 13, fill=self.error_color, outline="")


if __name__ == "__main__":
    app = ArduinoMonitor()
    app.mainloop()