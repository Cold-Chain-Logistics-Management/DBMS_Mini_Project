
import tkinter as tk
from tkinter import ttk, messagebox
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone


# MongoDB configuration
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "ColdChainMonitoring"
COLLECTION_NAME = "sensor_readings"


def create_sensor_monitoring_section(parent, get_mysql_connection):
    """Create the MongoDB sensor monitoring interface."""

    # Connect to MongoDB
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000
        )
        client.admin.command("ping")

        mongo_db = client[DATABASE_NAME]
        collection = mongo_db[COLLECTION_NAME]

    except Exception as error:
        messagebox.showerror(
            "MongoDB Connection Error",
            str(error)
        )
        return

    # Main section
    section = tk.LabelFrame(
        parent,
        text="Sensor Monitoring (MongoDB)",
        font=("Arial", 12, "bold"),
        bg="#eef2f7",
        padx=10,
        pady=10
    )
    section.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    tk.Label(
        section,
        text="Sensor readings are stored in MongoDB and linked "
             "to shipments validated in MySQL.",
        bg="#eef2f7",
        font=("Arial", 9)
    ).pack(anchor="w", pady=5)

    # Filter controls
    filter_frame = tk.Frame(section, bg="#eef2f7")
    filter_frame.pack(fill=tk.X, pady=5)

    tk.Label(
        filter_frame,
        text="Shipment ID:",
        bg="#eef2f7"
    ).pack(side=tk.LEFT, padx=5)

    shipment_filter = ttk.Entry(filter_frame, width=12)
    shipment_filter.pack(side=tk.LEFT, padx=5)

    tk.Label(
        filter_frame,
        text="Temperature above (°C):",
        bg="#eef2f7"
    ).pack(side=tk.LEFT, padx=5)

    temperature_filter = ttk.Entry(filter_frame, width=10)
    temperature_filter.pack(side=tk.LEFT, padx=5)

    # Sensor records table
    table_frame = tk.Frame(section)
    table_frame.pack(fill=tk.BOTH, expand=True, pady=8)

    columns = (
        "id",
        "sensor_id",
        "shipment_id",
        "temperature",
        "humidity",
        "location",
        "timestamp",
        "device_status"
    )

    sensor_table = ttk.Treeview(
        table_frame,
        columns=columns,
        show="headings",
        height=8
    )

    headings = {
        "id": "Document ID",
        "sensor_id": "Sensor ID",
        "shipment_id": "Shipment ID",
        "temperature": "Temperature (°C)",
        "humidity": "Humidity (%)",
        "location": "Location",
        "timestamp": "Timestamp",
        "device_status": "Device Status"
    }

    widths = {
        "id": 180,
        "sensor_id": 130,
        "shipment_id": 90,
        "temperature": 120,
        "humidity": 100,
        "location": 180,
        "timestamp": 190,
        "device_status": 110
    }

    for column in columns:
        sensor_table.heading(column, text=headings[column])
        sensor_table.column(
            column,
            width=widths[column],
            anchor="center"
        )

    vertical_scroll = ttk.Scrollbar(
        table_frame,
        orient=tk.VERTICAL,
        command=sensor_table.yview
    )

    horizontal_scroll = ttk.Scrollbar(
        table_frame,
        orient=tk.HORIZONTAL,
        command=sensor_table.xview
    )

    sensor_table.configure(
        yscrollcommand=vertical_scroll.set,
        xscrollcommand=horizontal_scroll.set
    )

    vertical_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    horizontal_scroll.pack(side=tk.BOTTOM, fill=tk.X)
    sensor_table.pack(fill=tk.BOTH, expand=True)

    def refresh_readings(query=None):
        """Display MongoDB sensor readings."""

        try:
            for item in sensor_table.get_children():
                sensor_table.delete(item)

            readings = collection.find(
                query or {}
            ).sort("timestamp", -1)

            for reading in readings:
                sensor_table.insert(
                    "",
                    tk.END,
                    values=(
                        str(reading["_id"]),
                        reading.get("sensor_id", ""),
                        reading.get("shipment_id", ""),
                        reading.get("temperature", ""),
                        reading.get("humidity", ""),
                        reading.get("location", ""),
                        reading.get("timestamp", ""),
                        reading.get("device_status", "")
                    )
                )

        except Exception as error:
            messagebox.showerror(
                "MongoDB Error",
                str(error)
            )

    def validate_shipment(shipment_id):
        """Check whether a shipment exists in MySQL."""

        mysql_db = get_mysql_connection()

        if mysql_db is None or not mysql_db.is_connected():
            messagebox.showwarning(
                "MySQL Connection Required",
                "Connect to MySQL before adding or updating readings."
            )
            return False

        cursor = None

        try:
            cursor = mysql_db.cursor()

            cursor.execute(
                "SELECT Shipment_ID FROM shipment WHERE Shipment_ID = %s",
                (shipment_id,)
            )

            return cursor.fetchone() is not None

        except Exception as error:
            messagebox.showerror(
                "MySQL Validation Error",
                str(error)
            )
            return False

        finally:
            if cursor:
                cursor.close()

    def open_sensor_form(existing=None):
        """Open the Add or Update sensor reading form."""

        form = tk.Toplevel(section)
        form.title(
            "Update Sensor Reading"
            if existing else "Add Sensor Reading"
        )
        form.geometry("400x410")
        form.transient(section)
        form.grab_set()

        fields = [
            ("Sensor ID", "sensor_id"),
            ("Shipment ID", "shipment_id"),
            ("Temperature (°C)", "temperature"),
            ("Humidity (%)", "humidity"),
            ("Location", "location")
        ]

        entries = {}

        for row, (label, key) in enumerate(fields):
            tk.Label(
                form,
                text=label
            ).grid(
                row=row,
                column=0,
                padx=10,
                pady=10,
                sticky="w"
            )

            entry = ttk.Entry(form, width=27)
            entry.grid(
                row=row,
                column=1,
                padx=10,
                pady=10
            )

            if existing:
                entry.insert(
                    0,
                    str(existing.get(key, ""))
                )

            entries[key] = entry

        status_row = len(fields)

        tk.Label(
            form,
            text="Device Status"
        ).grid(
            row=status_row,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        status_box = ttk.Combobox(
            form,
            values=["Active", "Inactive", "Maintenance"],
            state="readonly",
            width=24
        )
        status_box.grid(
            row=status_row,
            column=1,
            padx=10,
            pady=10
        )

        status_box.set(
            existing.get("device_status", "Active")
            if existing else "Active"
        )

        def save_reading():
            try:
                sensor_id = entries["sensor_id"].get().strip()
                shipment_text = entries["shipment_id"].get().strip()
                location = entries["location"].get().strip()

                if not sensor_id or not shipment_text or not location:
                    raise ValueError("Fill in all required fields.")

                shipment_id = int(shipment_text)
                temperature = float(entries["temperature"].get())
                humidity = float(entries["humidity"].get())

                if not 0 <= humidity <= 100:
                    raise ValueError(
                        "Humidity must be between 0 and 100."
                    )

                if not -100 <= temperature <= 100:
                    raise ValueError(
                        "Enter a valid temperature."
                    )

                if not validate_shipment(shipment_id):
                    messagebox.showerror(
                        "Invalid Shipment",
                        "This Shipment ID does not exist in MySQL."
                    )
                    return

                document = {
                    "sensor_id": sensor_id,
                    "shipment_id": shipment_id,
                    "temperature": temperature,
                    "humidity": humidity,
                    "location": location,
                    "device_status": status_box.get(),
                    "reading_source": "Simulated",
                    "timestamp": datetime.now(timezone.utc)
                }

                if existing:
                    collection.update_one(
                        {"_id": existing["_id"]},
                        {"$set": document}
                    )

                    messagebox.showinfo(
                        "Success",
                        "Sensor reading updated successfully."
                    )

                else:
                    collection.insert_one(document)

                    messagebox.showinfo(
                        "Success",
                        "Sensor reading added successfully."
                    )

                form.destroy()
                refresh_readings()

            except ValueError as error:
                messagebox.showerror(
                    "Invalid Input",
                    str(error)
                )

            except Exception as error:
                messagebox.showerror(
                    "MongoDB Error",
                    str(error)
                )

        ttk.Button(
            form,
            text="Save Sensor Reading",
            command=save_reading
        ).grid(
            row=status_row + 1,
            column=0,
            columnspan=2,
            pady=20
        )

    def add_reading():
        open_sensor_form()

    def update_reading():
        selected = sensor_table.selection()

        if not selected:
            messagebox.showwarning(
                "Selection Required",
                "Select a sensor reading to update."
            )
            return

        values = sensor_table.item(selected[0], "values")

        try:
            existing = collection.find_one(
                {"_id": ObjectId(values[0])}
            )

            if existing:
                open_sensor_form(existing)
            else:
                messagebox.showerror(
                    "Not Found",
                    "The selected reading no longer exists."
                )

        except Exception as error:
            messagebox.showerror(
                "MongoDB Error",
                str(error)
            )

    def delete_reading():
        selected = sensor_table.selection()

        if not selected:
            messagebox.showwarning(
                "Selection Required",
                "Select a sensor reading to delete."
            )
            return

        values = sensor_table.item(selected[0], "values")

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Delete the selected sensor reading?"
        )

        if confirm:
            try:
                collection.delete_one(
                    {"_id": ObjectId(values[0])}
                )

                messagebox.showinfo(
                    "Success",
                    "Sensor reading deleted successfully."
                )

                refresh_readings()

            except Exception as error:
                messagebox.showerror(
                    "MongoDB Error",
                    str(error)
                )

    def filter_by_shipment():
        value = shipment_filter.get().strip()

        if not value:
            refresh_readings()
            return

        try:
            shipment_id = int(value)
            refresh_readings({"shipment_id": shipment_id})

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Enter a valid Shipment ID."
            )

    def filter_by_temperature():
        value = temperature_filter.get().strip()

        try:
            threshold = float(value)

            refresh_readings({
                "temperature": {"$gt": threshold}
            })

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Enter a valid temperature threshold."
            )

    ttk.Button(
        filter_frame,
        text="Filter Shipment",
        command=filter_by_shipment
    ).pack(side=tk.LEFT, padx=5)

    ttk.Button(
        filter_frame,
        text="Filter Temperature",
        command=filter_by_temperature
    ).pack(side=tk.LEFT, padx=5)

    ttk.Button(
        filter_frame,
        text="Show All",
        command=refresh_readings
    ).pack(side=tk.LEFT, padx=5)

    # CRUD buttons
    button_frame = tk.Frame(section, bg="#eef2f7")
    button_frame.pack(fill=tk.X, pady=5)

    ttk.Button(
        button_frame,
        text="Add Sensor Reading",
        command=add_reading
    ).pack(side=tk.LEFT, padx=8)

    ttk.Button(
        button_frame,
        text="Update Selected Reading",
        command=update_reading
    ).pack(side=tk.LEFT, padx=8)

    ttk.Button(
        button_frame,
        text="Delete Selected Reading",
        command=delete_reading
    ).pack(side=tk.LEFT, padx=8)

    ttk.Button(
        button_frame,
        text="Refresh Readings",
        command=refresh_readings
    ).pack(side=tk.LEFT, padx=8)

    # Load existing MongoDB records
    refresh_readings()
