import tkinter as tk
from tkinter import ttk, messagebox
import serial
import time
import logging
import requests
from serial.tools import list_ports

class ArduinoMonitor(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Arduino Sensor Monitor")
        self.geometry("450x600")

        self.logger = logging.getLogger("ArduinoMonitor")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.port_label = tk.Label(self, text="Select COM Port:", font=("Arial", 12))
        self.port_label.pack(pady=(20, 5))

        self.port_combobox = ttk.Combobox(self, values=self.get_serial_ports(), state="readonly", font=("Arial", 12))
        self.port_combobox.pack(pady=5)
        self.port_combobox.set("Select a port")

        self.url_label = tk.Label(self, text="Webhook URL:", font=("Arial", 12))
        self.url_label.pack(pady=(10, 2))
        self.url_entry = tk.Entry(self, font=("Arial", 12), width=50)
        self.url_entry.pack(pady=2)
        self.url_entry.insert(0, "https://example.com/api/series/your_id/v1")

        self.token_label = tk.Label(self, text="Auth Token:", font=("Arial", 12))
        self.token_label.pack(pady=(10, 2))
        self.token_entry = tk.Entry(self, font=("Arial", 12), width=50, show='*')
        self.token_entry.pack(pady=2)
        self.token_entry.insert(0, "your_token_here")

        self.status_label = tk.Label(self, text="Status: Not Monitoring", font=("Arial", 14))
        self.status_label.pack(pady=20)

        self.webhook_status_label = tk.Label(self, text="", font=("Arial", 12), fg="blue")
        self.webhook_status_label.pack(pady=(0, 10))

        self.start_button = tk.Button(self, text="Start Monitoring", command=self.start_monitoring, font=("Arial", 12))
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(self, text="Stop Monitoring", command=self.stop_monitoring, font=("Arial", 12), state=tk.DISABLED)
        self.stop_button.pack(pady=10)

        self.refresh_button = tk.Button(self, text="Refresh Ports", command=self.refresh_ports, font=("Arial", 12))
        self.refresh_button.pack(pady=10)

        self.ser = None
        self.is_monitoring = False

    def get_serial_ports(self):
        ports = list_ports.comports()
        return [port.device for port in ports]

    def refresh_ports(self):
        self.port_combobox['values'] = self.get_serial_ports()
        self.port_combobox.set("Select a port")
        self.logger.info("Serial ports refreshed.")

    def start_monitoring(self):
        selected_port = self.port_combobox.get()

        if not selected_port or selected_port == "Select a port":
            messagebox.showwarning("No Port Selected", "Please select a COM port to start monitoring.")
            return

        try:
            self.ser = serial.Serial(selected_port, 9600, timeout=1)
            self.logger.info(f"Serial connection established on {selected_port}.")
            self.is_monitoring = True
            self.status_label.config(text="Status: Monitoring...", fg="green")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.monitor_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start serial connection: {e}")
            self.logger.error(f"Error setting up serial connection: {str(e)}")

    def stop_monitoring(self):
        self.is_monitoring = False
        if self.ser:
            self.ser.close()
        self.status_label.config(text="Status: Monitoring Stopped", fg="red")
        self.webhook_status_label.config(text="", fg="blue")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.logger.info("Monitoring stopped.")

    def monitor_data(self):
        temperature = None
        ph = None
        turbidity = None
        dissolved_oxygen = None
        tds = None

        while self.is_monitoring:
            try:
                data = self.ser.readline().decode('utf-8').strip()

                if data:
                    self.logger.info(f"Received data: {data}")

                    if data.startswith("Temperature"):
                        temperature = data.split(":")[1].strip()
                    elif data.startswith("pH"):
                        ph = data.split(":")[1].strip()
                    elif data.startswith("Turbidity"):
                        turbidity = data.split(":")[1].strip()
                    elif data.startswith("Dissolved Oxygen"):
                        dissolved_oxygen = data.split(":")[1].strip()
                    elif data.startswith("TDS"):
                        tds = data.split(":")[1].strip()

                    if temperature and ph and turbidity and dissolved_oxygen and tds:
                        data_string = f"{temperature}/{ph}/{turbidity}/{dissolved_oxygen}/{tds}"
                        self.send_to_webhook(data_string)

                        temperature = None
                        ph = None
                        turbidity = None
                        dissolved_oxygen = None
                        tds = None

            except Exception as e:
                self.logger.error(f"Error reading data: {str(e)}")
            time.sleep(1)

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

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                self.logger.info("Data successfully sent to the webhook.")
                self.webhook_status_label.config(text="Data successfully sent!", fg="green")
            else:
                self.logger.error(f"Failed to send data. Status code: {response.status_code}")
                self.webhook_status_label.config(text=f"Failed to send data. Status: {response.status_code}", fg="red")
        except Exception as e:
            self.logger.error(f"Error sending data to the webhook: {str(e)}")
            self.webhook_status_label.config(text="Error sending data to webhook.", fg="red")

if __name__ == "__main__":
    app = ArduinoMonitor()
    app.mainloop()
