
import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from sensor_monitoring import create_sensor_monitoring_section

# Database configuration
DATABASE = "ColdChainLogistics"

# Main application window
root = tk.Tk()
root.title("Cold Chain Logistics Management System")
root.geometry("1400x1100")
root.configure(bg="#eef2f7")

# Main Scrollable Container
main_canvas = tk.Canvas(root, bg="#eef2f7", highlightthickness=0)
main_scrollbar = ttk.Scrollbar(
    root,
    orient="vertical",
    command=main_canvas.yview
)

main_frame = tk.Frame(main_canvas, bg="#eef2f7")

main_frame.bind(
    "<Configure>",
    lambda event: main_canvas.configure(
        scrollregion=main_canvas.bbox("all")
    )
)

canvas_window = main_canvas.create_window(
    (0, 0),
    window=main_frame,
    anchor="nw"
)

main_canvas.bind(
    "<Configure>",
    lambda event: main_canvas.itemconfig(
        canvas_window,
        width=event.width
    )
)

main_canvas.configure(yscrollcommand=main_scrollbar.set)

def on_mousewheel(event):
    main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

main_canvas.bind_all("<MouseWheel>", on_mousewheel)

main_canvas.pack(side="left", fill="both", expand=True)
main_scrollbar.pack(side="right", fill="y")

# Database connection
db = None
def get_supplier_options():
    cursor = db.cursor()
    cursor.execute(
        "SELECT Supplier_ID, Supplier_Name FROM Supplier ORDER BY Supplier_ID"
    )
    suppliers = cursor.fetchall()
    cursor.close()
    return suppliers


def refresh_products():
    load_data("products")


def add_product():
    if db is None or not db.is_connected():
        messagebox.showwarning("Connection Required", "Connect to the database first.")
        return

    open_product_form("Add Product")


def update_product():
    if db is None or not db.is_connected():
        messagebox.showwarning("Connection Required", "Connect to the database first.")
        return

    selected = data_table.selection()
    if not selected:
        messagebox.showwarning("Select Product", "Select a product from the table first.")
        return

    values = data_table.item(selected[0], "values")
    open_product_form("Update Product", values)


def delete_product():
    if db is None or not db.is_connected():
        messagebox.showwarning("Connection Required", "Connect to the database first.")
        return

    selected = data_table.selection()
    if not selected:
        messagebox.showwarning("Select Product", "Select a product from the table first.")
        return

    values = data_table.item(selected[0], "values")
    product_id = values[0]

    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Delete product ID {product_id}?"
    )

    if not confirm:
        return

    try:
        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM Product WHERE Product_ID = %s",
            (product_id,)
        )
        db.commit()
        cursor.close()
        messagebox.showinfo("Success", "Product deleted successfully.")
        refresh_products()

    except mysql.connector.Error as error:
        db.rollback()
        messagebox.showerror(
            "Delete Error",
            f"Could not delete this product.\n{error}"
        )


def open_product_form(form_title, product=None):
    form = tk.Toplevel(root)
    form.title(form_title)
    form.geometry("420x380")
    form.configure(bg="#eef2f7")
    form.transient(root)
    form.grab_set()

    fields = [
        ("Product Name", "name"),
        ("Product Category", "category"),
        ("Maximum Temperature", "temperature"),
        ("Unit", "unit")
    ]

    entries = {}

    for row, (label, key) in enumerate(fields):
        tk.Label(
            form,
            text=label + ":",
            bg="#eef2f7"
        ).grid(row=row, column=0, padx=15, pady=10, sticky="w")

        entry = ttk.Entry(form, width=25)
        entry.grid(row=row, column=1, padx=15, pady=10)
        entries[key] = entry

    tk.Label(
        form,
        text="Supplier:",
        bg="#eef2f7"
    ).grid(row=4, column=0, padx=15, pady=10, sticky="w")

    suppliers = get_supplier_options()
    supplier_names = [f"{name} (ID: {sid})" for sid, name in suppliers]

    supplier_box = ttk.Combobox(
        form,
        values=supplier_names,
        state="readonly",
        width=23
    )
    supplier_box.grid(row=4, column=1, padx=15, pady=10)

    if product:
        entries["name"].insert(0, product[1])
        entries["category"].insert(0, product[2] or "")
        entries["temperature"].insert(0, product[3] if product[3] is not None else "")
        entries["unit"].insert(0, product[4] or "")

        for index, (supplier_id, supplier_name) in enumerate(suppliers):
            if str(supplier_id) == str(product[5]):
                supplier_box.current(index)
                break
    elif supplier_names:
        supplier_box.current(0)

    def save_product():
        name = entries["name"].get().strip()
        category = entries["category"].get().strip()
        temperature = entries["temperature"].get().strip()
        unit = entries["unit"].get().strip()
        supplier_index = supplier_box.current()

        if not name:
            messagebox.showwarning("Validation", "Product name is required.")
            return

        if supplier_index < 0:
            messagebox.showwarning("Validation", "Please select a supplier.")
            return

        try:
            temperature_value = float(temperature) if temperature else None
            supplier_id = suppliers[supplier_index][0]
            cursor = db.cursor()

            if product:
                cursor.execute(
                    """
                    UPDATE Product
                    SET Product_Name=%s,
                        Product_Category=%s,
                        Max_Temperature=%s,
                        Unit=%s,
                        Supplier_ID=%s
                    WHERE Product_ID=%s
                    """,
                    (
                        name, category, temperature_value,
                        unit, supplier_id, product[0]
                    )
                )
            else:
                cursor.execute(
                    "SELECT COALESCE(MAX(Product_ID), 0) + 1 FROM Product"
                )
                new_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO Product
                    (Product_ID, Product_Name, Product_Category,
                     Max_Temperature, Unit, Supplier_ID)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        new_id, name, category,
                        temperature_value, unit, supplier_id
                    )
                )

            db.commit()
            cursor.close()
            messagebox.showinfo("Success", "Product saved successfully.")
            form.destroy()
            refresh_products()

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Maximum temperature must be a number."
            )
        except mysql.connector.Error as error:
            db.rollback()
            messagebox.showerror("Database Error", str(error))

    ttk.Button(
        form,
        text="Save Product",
        command=save_product
    ).grid(row=5, column=0, columnspan=2, pady=20)

def get_product_options():
    cursor = db.cursor()
    cursor.execute(
        "SELECT Product_ID, Product_Name FROM Product ORDER BY Product_ID"
    )
    products = cursor.fetchall()
    cursor.close()
    return products


def refresh_batches():
    load_data("batches")


def add_batch():
    if db is None or not db.is_connected():
        messagebox.showwarning(
            "Connection Required",
            "Connect to the database first."
        )
        return

    open_batch_form("Add Product Batch")


def update_batch():
    if db is None or not db.is_connected():
        messagebox.showwarning(
            "Connection Required",
            "Connect to the database first."
        )
        return

    selected = data_table.selection()
    if not selected:
        messagebox.showwarning(
            "Select Batch",
            "Select a batch from the Product Batches table first."
        )
        return

    values = data_table.item(selected[0], "values")
    if heading_label.cget("text") != "Product Batches":
        messagebox.showwarning(
            "Wrong Section",
            "Please open Product Batches and select a batch."
        )
        return

    open_batch_form("Update Product Batch", values)


def delete_batch():
    if db is None or not db.is_connected():
        messagebox.showwarning(
            "Connection Required",
            "Connect to the database first."
        )
        return

    if heading_label.cget("text") != "Product Batches":
        messagebox.showwarning(
            "Wrong Section",
            "Please open Product Batches first."
        )
        return

    selected = data_table.selection()
    if not selected:
        messagebox.showwarning(
            "Select Batch",
            "Select a batch from the table first."
        )
        return

    values = data_table.item(selected[0], "values")
    batch_id = values[0]

    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Delete batch ID {batch_id}?"
    )

    if not confirm:
        return

    try:
        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM Product_Batch WHERE Batch_ID = %s",
            (batch_id,)
        )
        db.commit()
        cursor.close()

        messagebox.showinfo(
            "Success",
            "Product batch deleted successfully."
        )
        refresh_batches()

    except mysql.connector.Error as error:
        db.rollback()
        messagebox.showerror(
            "Delete Error",
            f"Could not delete this batch.\n{error}"
        )


def open_batch_form(form_title, batch=None):
    form = tk.Toplevel(root)
    form.title(form_title)
    form.geometry("450x480")
    form.configure(bg="#eef2f7")
    form.transient(root)
    form.grab_set()

    fields = [
        ("Batch Number", "number"),
        ("Manufacturing Date (YYYY-MM-DD)", "manufacturing"),
        ("Expiry Date (YYYY-MM-DD)", "expiry"),
        ("Quantity", "quantity"),
        ("Batch Status", "status")
    ]

    entries = {}

    for row, (label, key) in enumerate(fields):
        tk.Label(
            form,
            text=label + ":",
            bg="#eef2f7"
        ).grid(row=row, column=0, padx=10, pady=10, sticky="w")

        entry = ttk.Entry(form, width=25)
        entry.grid(row=row, column=1, padx=10, pady=10)
        entries[key] = entry

    tk.Label(
        form,
        text="Product:",
        bg="#eef2f7"
    ).grid(row=5, column=0, padx=10, pady=10, sticky="w")

    products = get_product_options()
    product_names = [
        f"{name} (ID: {product_id})"
        for product_id, name in products
    ]

    product_box = ttk.Combobox(
        form,
        values=product_names,
        state="readonly",
        width=23
    )
    product_box.grid(row=5, column=1, padx=10, pady=10)

    if batch:
        entries["number"].insert(0, batch[1])
        entries["manufacturing"].insert(
            0, batch[2] if batch[2] is not None else ""
        )
        entries["expiry"].insert(
            0, batch[3] if batch[3] is not None else ""
        )
        entries["quantity"].insert(
            0, batch[4] if batch[4] is not None else ""
        )
        entries["status"].insert(
            0, batch[5] if batch[5] is not None else ""
        )

        for index, (product_id, product_name) in enumerate(products):
            if str(product_id) == str(batch[6]):
                product_box.current(index)
                break

    elif product_names:
        product_box.current(0)

    def save_batch():
        number = entries["number"].get().strip()
        manufacturing = entries["manufacturing"].get().strip() or None
        expiry = entries["expiry"].get().strip() or None
        quantity = entries["quantity"].get().strip()
        status = entries["status"].get().strip()
        product_index = product_box.current()

        if not number:
            messagebox.showwarning(
                "Validation",
                "Batch number is required."
            )
            return

        if not quantity:
            messagebox.showwarning(
                "Validation",
                "Quantity is required."
            )
            return

        if product_index < 0:
            messagebox.showwarning(
                "Validation",
                "Please select a product."
            )
            return

        try:
            quantity_value = int(quantity)

            if quantity_value < 0:
                messagebox.showwarning(
                    "Validation",
                    "Quantity cannot be negative."
                )
                return

            product_id = products[product_index][0]
            cursor = db.cursor()

            if batch:
                cursor.execute(
                    """
                    UPDATE Product_Batch
                    SET Batch_Number=%s,
                        Manufacturing_Date=%s,
                        Expiry_Date=%s,
                        Quantity=%s,
                        Batch_Status=%s,
                        Product_ID=%s
                    WHERE Batch_ID=%s
                    """,
                    (
                        number, manufacturing, expiry,
                        quantity_value, status, product_id, batch[0]
                    )
                )
            else:
                cursor.execute(
                    """
                    SELECT COALESCE(MAX(Batch_ID), 0) + 1
                    FROM Product_Batch
                    """
                )
                new_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO Product_Batch
                    (Batch_ID, Batch_Number, Manufacturing_Date,
                     Expiry_Date, Quantity, Batch_Status, Product_ID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        new_id, number, manufacturing, expiry,
                        quantity_value, status, product_id
                    )
                )

            db.commit()
            cursor.close()

            messagebox.showinfo(
                "Success",
                "Product batch saved successfully."
            )
            form.destroy()
            refresh_batches()

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Quantity must be a whole number."
            )
        except mysql.connector.Error as error:
            db.rollback()
            messagebox.showerror(
                "Database Error",
                str(error)
            )

    ttk.Button(
        form,
        text="Save Product Batch",
        command=save_batch
    ).grid(row=6, column=0, columnspan=2, pady=20)

def get_shipment_fk_options():
    try:
        cursor = db.cursor()

        cursor.execute("SELECT Vehicle_ID FROM Vehicle ORDER BY Vehicle_ID")
        vehicles = [str(row[0]) for row in cursor.fetchall()]

        cursor.execute("SELECT Driver_ID FROM Driver ORDER BY Driver_ID")
        drivers = [str(row[0]) for row in cursor.fetchall()]

        cursor.execute("SELECT Customer_ID FROM Customer ORDER BY Customer_ID")
        customers = [str(row[0]) for row in cursor.fetchall()]

        cursor.close()

        return vehicles, drivers, customers

    except mysql.connector.Error as error:
        messagebox.showerror("Database Error", str(error))
        return [], [], []
    
def refresh_shipments():
    load_data("shipments")
    
def add_shipment():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    vehicles, drivers, customers = get_shipment_fk_options()

    if not vehicles or not drivers or not customers:
        messagebox.showerror("Error", "Could not load Vehicle, Driver, or Customer IDs.")
        return

    form = tk.Toplevel(root)
    form.title("Add Shipment")
    form.geometry("400x500")

    fields = [
        "Origin",
        "Shipment Date (YYYY-MM-DD)",
        "Expected Delivery Date (YYYY-MM-DD)",
        "Actual Delivery Date (YYYY-MM-DD)",
        "Shipment Status"
    ]

    entries = {}

    for i, field in enumerate(fields):
        tk.Label(form, text=field).pack(pady=3)
        entry = tk.Entry(form, width=35)
        entry.pack(pady=3)
        entries[field] = entry

    tk.Label(form, text="Vehicle ID").pack(pady=3)
    vehicle_box = ttk.Combobox(form, values=vehicles, state="readonly")
    vehicle_box.pack(pady=3)

    tk.Label(form, text="Driver ID").pack(pady=3)
    driver_box = ttk.Combobox(form, values=drivers, state="readonly")
    driver_box.pack(pady=3)

    tk.Label(form, text="Customer ID").pack(pady=3)
    customer_box = ttk.Combobox(form, values=customers, state="readonly")
    customer_box.pack(pady=3)

    def save_shipment():
        origin = entries["Origin"].get().strip()
        shipment_date = entries["Shipment Date (YYYY-MM-DD)"].get().strip()
        expected_date = entries["Expected Delivery Date (YYYY-MM-DD)"].get().strip()
        actual_date = entries["Actual Delivery Date (YYYY-MM-DD)"].get().strip()
        shipment_status = entries["Shipment Status"].get().strip()

        if not all([origin, shipment_date, expected_date, shipment_status,
                    vehicle_box.get(), driver_box.get(), customer_box.get()]):
            messagebox.showwarning("Missing Details", "Fill all required fields.")
            return

        try:
            cursor = db.cursor()
            cursor.execute("SELECT COALESCE(MAX(Shipment_ID), 0) + 1 FROM Shipment")
            new_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO Shipment
                (Shipment_ID, Origin, Shipment_Date, Expected_Delivery_Date,
                 Actual_Delivery_Date, Shipment_Status, Vehicle_ID, Driver_ID, Customer_ID)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                new_id, origin, shipment_date, expected_date,
                actual_date if actual_date else None,
                shipment_status, int(vehicle_box.get()),
                int(driver_box.get()), int(customer_box.get())
            ))

            db.commit()
            cursor.close()

            messagebox.showinfo("Success", "Shipment added successfully!")
            form.destroy()
            refresh_shipments()

        except mysql.connector.Error as error:
            messagebox.showerror("Database Error", str(error))

    tk.Button(form, text="Save Shipment", command=save_shipment).pack(pady=15)

def update_shipment():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    if heading_label.cget("text") != "Shipments":
        messagebox.showwarning("Select Shipment", "Open the Shipments table first.")
        return

    selected = data_table.selection()

    if not selected:
        messagebox.showwarning("Select Shipment", "Select a shipment from the table.")
        return

    values = data_table.item(selected[0], "values")

    if len(values) < 9:
        messagebox.showerror("Error", "Shipment record does not contain all required columns.")
        return

    vehicles, drivers, customers = get_shipment_fk_options()

    form = tk.Toplevel(root)
    form.title("Update Shipment")
    form.geometry("400x500")

    fields = [
        "Origin",
        "Shipment Date (YYYY-MM-DD)",
        "Expected Delivery Date (YYYY-MM-DD)",
        "Actual Delivery Date (YYYY-MM-DD)",
        "Shipment Status"
    ]

    entries = {}
    initial_values = [values[1], values[2], values[3], values[4], values[5]]

    for i, field in enumerate(fields):
        tk.Label(form, text=field).pack(pady=3)
        entry = tk.Entry(form, width=35)
        entry.pack(pady=3)
        entry.insert(0, str(initial_values[i]) if initial_values[i] is not None else "")
        entries[field] = entry

    tk.Label(form, text="Vehicle ID").pack(pady=3)
    vehicle_box = ttk.Combobox(form, values=vehicles, state="readonly")
    vehicle_box.pack(pady=3)
    vehicle_box.set(str(values[6]))

    tk.Label(form, text="Driver ID").pack(pady=3)
    driver_box = ttk.Combobox(form, values=drivers, state="readonly")
    driver_box.pack(pady=3)
    driver_box.set(str(values[7]))

    tk.Label(form, text="Customer ID").pack(pady=3)
    customer_box = ttk.Combobox(form, values=customers, state="readonly")
    customer_box.pack(pady=3)
    customer_box.set(str(values[8]))

    def save_changes():
        origin = entries["Origin"].get().strip()
        shipment_date = entries["Shipment Date (YYYY-MM-DD)"].get().strip()
        expected_date = entries["Expected Delivery Date (YYYY-MM-DD)"].get().strip()
        actual_date = entries["Actual Delivery Date (YYYY-MM-DD)"].get().strip()
        shipment_status = entries["Shipment Status"].get().strip()

        if not all([origin, shipment_date, expected_date, shipment_status,
                    vehicle_box.get(), driver_box.get(), customer_box.get()]):
            messagebox.showwarning("Missing Details", "Fill all required fields.")
            return

        try:
            cursor = db.cursor()
            cursor.execute("""
                UPDATE Shipment
                SET Origin = %s,
                    Shipment_Date = %s,
                    Expected_Delivery_Date = %s,
                    Actual_Delivery_Date = %s,
                    Shipment_Status = %s,
                    Vehicle_ID = %s,
                    Driver_ID = %s,
                    Customer_ID = %s
                WHERE Shipment_ID = %s
            """, (
                origin, shipment_date, expected_date,
                actual_date if actual_date else None,
                shipment_status, int(vehicle_box.get()),
                int(driver_box.get()), int(customer_box.get()),
                int(values[0])
            ))

            db.commit()
            cursor.close()

            messagebox.showinfo("Success", "Shipment updated successfully!")
            form.destroy()
            refresh_shipments()

        except mysql.connector.Error as error:
            messagebox.showerror("Database Error", str(error))

    tk.Button(form, text="Save Changes", command=save_changes).pack(pady=15)

def delete_shipment():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    if heading_label.cget("text") != "Shipments":
        messagebox.showwarning("Select Shipment", "Open the Shipments table first.")
        return

    selected = data_table.selection()

    if not selected:
        messagebox.showwarning("Select Shipment", "Select a shipment from the table.")
        return

    values = data_table.item(selected[0], "values")
    shipment_id = values[0]

    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to delete Shipment ID {shipment_id}?"
    )

    if not confirm:
        return

    try:
        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM Shipment WHERE Shipment_ID = %s",
            (shipment_id,)
        )
        db.commit()
        cursor.close()

        messagebox.showinfo("Success", "Shipment deleted successfully!")
        refresh_shipments()

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Delete Error",
            "Could not delete this shipment. It may be referenced by another table.\n\n"
            + str(error)
        )

def get_temperature_shipment_options():
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT Shipment_ID FROM Shipment ORDER BY Shipment_ID"
        )
        shipments = [str(row[0]) for row in cursor.fetchall()]
        cursor.close()
        return shipments

    except mysql.connector.Error as error:
        messagebox.showerror("Database Error", str(error))
        return []
    
def refresh_temperature_logs():
    load_data("temperature")
    
def add_temperature_log():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    shipments = get_temperature_shipment_options()

    if not shipments:
        messagebox.showerror("Error", "No Shipment IDs available.")
        return

    form = tk.Toplevel(root)
    form.title("Add Temperature Log")
    form.geometry("400x300")

    tk.Label(form, text="Log Time (YYYY-MM-DD HH:MM:SS)").pack(pady=5)
    time_entry = tk.Entry(form, width=35)
    time_entry.pack(pady=5)

    tk.Label(form, text="Temperature").pack(pady=5)
    temperature_entry = tk.Entry(form, width=35)
    temperature_entry.pack(pady=5)

    tk.Label(form, text="Shipment ID").pack(pady=5)
    shipment_box = ttk.Combobox(form, values=shipments, state="readonly")
    shipment_box.pack(pady=5)

    def save_log():
        log_time = time_entry.get().strip()
        temperature = temperature_entry.get().strip()
        shipment_id = shipment_box.get()

        if not log_time or not temperature or not shipment_id:
            messagebox.showwarning("Missing Details", "Fill all fields.")
            return

        try:
            float(temperature)

            cursor = db.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(Temp_Log_ID), 0) + 1 FROM Temperature_Log"
            )
            new_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO Temperature_Log
                (Temp_Log_ID, Log_Time, Temperature, Shipment_ID)
                VALUES (%s, %s, %s, %s)
            """, (new_id, log_time, temperature, int(shipment_id)))

            db.commit()
            cursor.close()

            messagebox.showinfo("Success", "Temperature log added successfully!")
            form.destroy()
            refresh_temperature_logs()

        except ValueError:
            messagebox.showerror("Invalid Input", "Temperature must be a number.")

        except mysql.connector.Error as error:
            messagebox.showerror("Database Error", str(error))

    tk.Button(form, text="Save Temperature Log", command=save_log).pack(pady=15)
    
def update_temperature_log():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    if heading_label.cget("text") != "Temperature Logs":
        messagebox.showwarning("Select Record", "Open the Temperature Logs table first.")
        return

    selected = data_table.selection()

    if not selected:
        messagebox.showwarning("Select Record", "Select a temperature log first.")
        return

    values = data_table.item(selected[0], "values")

    if len(values) < 4:
        messagebox.showerror("Error", "Temperature log record is incomplete.")
        return

    shipments = get_temperature_shipment_options()

    form = tk.Toplevel(root)
    form.title("Update Temperature Log")
    form.geometry("400x300")

    tk.Label(form, text="Log Time (YYYY-MM-DD HH:MM:SS)").pack(pady=5)
    time_entry = tk.Entry(form, width=35)
    time_entry.pack(pady=5)
    time_entry.insert(0, str(values[1]))

    tk.Label(form, text="Temperature").pack(pady=5)
    temperature_entry = tk.Entry(form, width=35)
    temperature_entry.pack(pady=5)
    temperature_entry.insert(0, str(values[2]))

    tk.Label(form, text="Shipment ID").pack(pady=5)
    shipment_box = ttk.Combobox(form, values=shipments, state="readonly")
    shipment_box.pack(pady=5)
    shipment_box.set(str(values[3]))

    def save_changes():
        log_time = time_entry.get().strip()
        temperature = temperature_entry.get().strip()
        shipment_id = shipment_box.get()

        if not log_time or not temperature or not shipment_id:
            messagebox.showwarning("Missing Details", "Fill all fields.")
            return

        try:
            float(temperature)

            cursor = db.cursor()
            cursor.execute("""
                UPDATE Temperature_Log
                SET Log_Time = %s,
                    Temperature = %s,
                    Shipment_ID = %s
                WHERE Temp_Log_ID = %s
            """, (
                log_time,
                temperature,
                int(shipment_id),
                int(values[0])
            ))

            db.commit()
            cursor.close()

            messagebox.showinfo("Success", "Temperature log updated successfully!")
            form.destroy()
            refresh_temperature_logs()

        except ValueError:
            messagebox.showerror("Invalid Input", "Temperature must be a number.")

        except mysql.connector.Error as error:
            messagebox.showerror("Database Error", str(error))

    tk.Button(form, text="Save Changes", command=save_changes).pack(pady=15)

def delete_temperature_log():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    if heading_label.cget("text") != "Temperature Logs":
        messagebox.showwarning("Select Record", "Open the Temperature Logs table first.")
        return

    selected = data_table.selection()

    if not selected:
        messagebox.showwarning("Select Record", "Select a temperature log first.")
        return

    values = data_table.item(selected[0], "values")
    temp_log_id = values[0]

    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to delete Temperature Log ID {temp_log_id}?"
    )

    if not confirm:
        return

    try:
        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM Temperature_Log WHERE Temp_Log_ID = %s",
            (temp_log_id,)
        )
        db.commit()
        cursor.close()

        messagebox.showinfo("Success", "Temperature log deleted successfully!")
        refresh_temperature_logs()

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Delete Error",
            "Could not delete this temperature log.\n\n" + str(error)
        )

def get_temp_log_options():
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT Temp_Log_ID FROM Temperature_Log ORDER BY Temp_Log_ID"
        )
        logs = [str(row[0]) for row in cursor.fetchall()]
        cursor.close()
        return logs

    except mysql.connector.Error as error:
        messagebox.showerror("Database Error", str(error))
        return []


def refresh_temperature_violations():
    load_data("violations")

def add_temperature_violation():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    temp_logs = get_temp_log_options()

    if not temp_logs:
        messagebox.showerror("Error", "No Temperature Log IDs available.")
        return

    form = tk.Toplevel(root)
    form.title("Add Temperature Violation")
    form.geometry("450x400")

    tk.Label(form, text="Manufacturing Date (YYYY-MM-DD)").pack(pady=5)
    manufacturing_entry = tk.Entry(form, width=40)
    manufacturing_entry.pack(pady=5)

    tk.Label(form, text="Expiry Date (YYYY-MM-DD)").pack(pady=5)
    expiry_entry = tk.Entry(form, width=40)
    expiry_entry.pack(pady=5)

    tk.Label(form, text="Violation Description").pack(pady=5)
    description_entry = tk.Entry(form, width=40)
    description_entry.pack(pady=5)

    tk.Label(form, text="Violation Status").pack(pady=5)
    status_box = ttk.Combobox(
        form,
        values=["Open", "Resolved"],
        state="readonly",
        width=37
    )
    status_box.pack(pady=5)
    status_box.set("Open")

    tk.Label(form, text="Temperature Log ID").pack(pady=5)
    temp_log_box = ttk.Combobox(
        form,
        values=temp_logs,
        state="readonly",
        width=37
    )
    temp_log_box.pack(pady=5)

    def save_violation():
        manufacturing_date = manufacturing_entry.get().strip()
        expiry_date = expiry_entry.get().strip()
        description = description_entry.get().strip()
        status = status_box.get()
        temp_log_id = temp_log_box.get()

        if not all([
            manufacturing_date,
            expiry_date,
            description,
            status,
            temp_log_id
        ]):
            messagebox.showwarning("Missing Details", "Fill all fields.")
            return

        try:
            cursor = db.cursor()

            cursor.execute(
                "SELECT COALESCE(MAX(Violation_ID), 0) + 1 "
                "FROM Temperature_Violation"
            )
            new_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO Temperature_Violation
                (Violation_ID, Manufacturing_Date, Expiry_Date,
                 Violation_Description, Violation_Status, Temp_Log_ID)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                new_id,
                manufacturing_date,
                expiry_date,
                description,
                status,
                int(temp_log_id)
            ))

            db.commit()
            cursor.close()

            messagebox.showinfo(
                "Success",
                "Temperature violation added successfully!"
            )
            form.destroy()
            refresh_temperature_violations()

        except mysql.connector.Error as error:
            messagebox.showerror("Database Error", str(error))

    tk.Button(
        form,
        text="Save Temperature Violation",
        command=save_violation
    ).pack(pady=15)

def update_temperature_violation():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    if heading_label.cget("text") != "Temperature Violations":
        messagebox.showwarning(
            "Select Record",
            "Open the Temperature Violations table first."
        )
        return

    selected = data_table.selection()

    if not selected:
        messagebox.showwarning(
            "Select Record",
            "Select a temperature violation first."
        )
        return

    values = data_table.item(selected[0], "values")

    if len(values) < 6:
        messagebox.showerror("Error", "Violation record is incomplete.")
        return

    temp_logs = get_temp_log_options()

    form = tk.Toplevel(root)
    form.title("Update Temperature Violation")
    form.geometry("450x400")

    tk.Label(form, text="Manufacturing Date (YYYY-MM-DD)").pack(pady=5)
    manufacturing_entry = tk.Entry(form, width=40)
    manufacturing_entry.pack(pady=5)
    manufacturing_entry.insert(0, str(values[1]))

    tk.Label(form, text="Expiry Date (YYYY-MM-DD)").pack(pady=5)
    expiry_entry = tk.Entry(form, width=40)
    expiry_entry.pack(pady=5)
    expiry_entry.insert(0, str(values[2]))

    tk.Label(form, text="Violation Description").pack(pady=5)
    description_entry = tk.Entry(form, width=40)
    description_entry.pack(pady=5)
    description_entry.insert(0, str(values[3]))

    tk.Label(form, text="Violation Status").pack(pady=5)
    status_box = ttk.Combobox(
        form,
        values=["Open", "Resolved"],
        state="readonly",
        width=37
    )
    status_box.pack(pady=5)
    status_box.set(str(values[4]))

    tk.Label(form, text="Temperature Log ID").pack(pady=5)
    temp_log_box = ttk.Combobox(
        form,
        values=temp_logs,
        state="readonly",
        width=37
    )
    temp_log_box.pack(pady=5)
    temp_log_box.set(str(values[5]))

    def save_changes():
        manufacturing_date = manufacturing_entry.get().strip()
        expiry_date = expiry_entry.get().strip()
        description = description_entry.get().strip()
        status = status_box.get()
        temp_log_id = temp_log_box.get()

        if not all([
            manufacturing_date,
            expiry_date,
            description,
            status,
            temp_log_id
        ]):
            messagebox.showwarning("Missing Details", "Fill all fields.")
            return

        try:
            cursor = db.cursor()
            cursor.execute("""
                UPDATE Temperature_Violation
                SET Manufacturing_Date = %s,
                    Expiry_Date = %s,
                    Violation_Description = %s,
                    Violation_Status = %s,
                    Temp_Log_ID = %s
                WHERE Violation_ID = %s
            """, (
                manufacturing_date,
                expiry_date,
                description,
                status,
                int(temp_log_id),
                int(values[0])
            ))

            db.commit()
            cursor.close()

            messagebox.showinfo(
                "Success",
                "Temperature violation updated successfully!"
            )
            form.destroy()
            refresh_temperature_violations()

        except mysql.connector.Error as error:
            messagebox.showerror("Database Error", str(error))

    tk.Button(
        form,
        text="Save Changes",
        command=save_changes
    ).pack(pady=15)

def delete_temperature_violation():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    if heading_label.cget("text") != "Temperature Violations":
        messagebox.showwarning(
            "Select Record",
            "Open the Temperature Violations table first."
        )
        return

    selected = data_table.selection()

    if not selected:
        messagebox.showwarning(
            "Select Record",
            "Select a temperature violation first."
        )
        return

    values = data_table.item(selected[0], "values")
    violation_id = values[0]

    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to delete Violation ID {violation_id}?"
    )

    if not confirm:
        return

    try:
        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM Temperature_Violation WHERE Violation_ID = %s",
            (violation_id,)
        )
        db.commit()
        cursor.close()

        messagebox.showinfo(
            "Success",
            "Temperature violation deleted successfully!"
        )
        refresh_temperature_violations()

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Delete Error",
            "Could not delete this temperature violation.\n\n" + str(error)
        )

# Inventory CRUD Functions

def get_inventory_batch_options():
    cursor = db.cursor()
    cursor.execute(
        "SELECT Batch_ID FROM Product_Batch ORDER BY Batch_ID"
    )
    options = [str(row[0]) for row in cursor.fetchall()]
    cursor.close()
    return options


def get_inventory_storage_options():
    cursor = db.cursor()
    cursor.execute(
        "SELECT Storage_ID FROM Storage_Unit ORDER BY Storage_ID"
    )
    options = [str(row[0]) for row in cursor.fetchall()]
    cursor.close()
    return options

def refresh_inventory():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM Inventory ORDER BY Inventory_ID"
        )
        records = cursor.fetchall()
        cursor.close()

        for item in data_table.get_children():
            data_table.delete(item)

        for record in records:
            data_table.insert("", tk.END, values=record)

        heading_label.config(text="Inventory")

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Database Error",
            "Could not load Inventory records.\n\n" + str(error)
        )
        
def add_inventory():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    batch_options = get_inventory_batch_options()
    storage_options = get_inventory_storage_options()

    if not batch_options or not storage_options:
        messagebox.showerror(
            "Error",
            "No valid Batch IDs or Storage IDs are available."
        )
        return

    form = tk.Toplevel(root)
    form.title("Add Inventory")
    form.geometry("400x350")
    form.grab_set()

    tk.Label(form, text="Batch ID").pack(pady=5)
    batch_var = tk.StringVar(value=batch_options[0])
    ttk.Combobox(
        form, textvariable=batch_var,
        values=batch_options, state="readonly"
    ).pack(pady=5)

    tk.Label(form, text="Storage ID").pack(pady=5)
    storage_var = tk.StringVar(value=storage_options[0])
    ttk.Combobox(
        form, textvariable=storage_var,
        values=storage_options, state="readonly"
    ).pack(pady=5)

    tk.Label(form, text="Quantity").pack(pady=5)
    quantity_entry = ttk.Entry(form)
    quantity_entry.pack(pady=5)

    def save_inventory():
        try:
            quantity = int(quantity_entry.get())

            if quantity < 0:
                messagebox.showwarning(
                    "Invalid Quantity",
                    "Quantity cannot be negative."
                )
                return

            cursor = db.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(Inventory_ID), 0) + 1 FROM Inventory"
            )
            inventory_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO Inventory
                (Inventory_ID, Batch_ID, Storage_ID, Quantity, Last_Updated)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (
                    inventory_id,
                    int(batch_var.get()),
                    int(storage_var.get()),
                    quantity
                )
            )
            db.commit()
            cursor.close()

            messagebox.showinfo(
                "Success",
                "Inventory record added successfully!"
            )
            form.destroy()
            refresh_inventory()

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Please enter a valid whole-number quantity."
            )

        except mysql.connector.Error as error:
            messagebox.showerror(
                "Insert Error",
                "Could not add inventory.\n\n" + str(error)
            )

    ttk.Button(
        form,
        text="Save Inventory",
        command=save_inventory
    ).pack(pady=15)

def update_inventory():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    if heading_label.cget("text") != "Inventory":
        messagebox.showwarning(
            "Select Table",
            "Open the Inventory table first."
        )
        return

    selected = data_table.selection()

    if not selected:
        messagebox.showwarning(
            "Select Record",
            "Select an inventory record first."
        )
        return

    values = data_table.item(selected[0], "values")
    inventory_id = values[0]

    form = tk.Toplevel(root)
    form.title("Update Inventory")
    form.geometry("400x350")
    form.grab_set()

    batch_options = get_inventory_batch_options()
    storage_options = get_inventory_storage_options()

    tk.Label(form, text="Batch ID").pack(pady=5)
    batch_var = tk.StringVar(value=str(values[1]))
    ttk.Combobox(
        form, textvariable=batch_var,
        values=batch_options, state="readonly"
    ).pack(pady=5)

    tk.Label(form, text="Storage ID").pack(pady=5)
    storage_var = tk.StringVar(value=str(values[2]))
    ttk.Combobox(
        form, textvariable=storage_var,
        values=storage_options, state="readonly"
    ).pack(pady=5)

    tk.Label(form, text="Quantity").pack(pady=5)
    quantity_entry = ttk.Entry(form)
    quantity_entry.insert(0, str(values[3]))
    quantity_entry.pack(pady=5)

    def save_changes():
        try:
            quantity = int(quantity_entry.get())

            if quantity < 0:
                messagebox.showwarning(
                    "Invalid Quantity",
                    "Quantity cannot be negative."
                )
                return

            cursor = db.cursor()
            cursor.execute(
                """
                UPDATE Inventory
                SET Batch_ID = %s,
                    Storage_ID = %s,
                    Quantity = %s,
                    Last_Updated = NOW()
                WHERE Inventory_ID = %s
                """,
                (
                    int(batch_var.get()),
                    int(storage_var.get()),
                    quantity,
                    inventory_id
                )
            )
            db.commit()
            cursor.close()

            messagebox.showinfo(
                "Success",
                "Inventory record updated successfully!"
            )
            form.destroy()
            refresh_inventory()

        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Please enter a valid whole-number quantity."
            )

        except mysql.connector.Error as error:
            messagebox.showerror(
                "Update Error",
                "Could not update inventory.\n\n" + str(error)
            )

    ttk.Button(
        form,
        text="Save Changes",
        command=save_changes
    ).pack(pady=15)

def delete_inventory():
    if db is None or not db.is_connected():
        messagebox.showerror("Error", "Connect to the database first.")
        return

    if heading_label.cget("text") != "Inventory":
        messagebox.showwarning(
            "Select Table",
            "Open the Inventory table first."
        )
        return

    selected = data_table.selection()

    if not selected:
        messagebox.showwarning(
            "Select Record",
            "Select an inventory record first."
        )
        return

    values = data_table.item(selected[0], "values")
    inventory_id = values[0]

    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to delete Inventory ID {inventory_id}?"
    )

    if not confirm:
        return

    try:
        cursor = db.cursor()
        cursor.execute(
            "DELETE FROM Inventory WHERE Inventory_ID = %s",
            (inventory_id,)
        )
        db.commit()
        cursor.close()

        messagebox.showinfo(
            "Success",
            "Inventory record deleted successfully!"
        )
        refresh_inventory()

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Delete Error",
            "Could not delete inventory.\n\n" + str(error)
        )

# CRUD support for the remaining seven tables.
# Primary-key values are generated as MAX(primary_key) + 1 for single-key tables.
# Shipment_Batch uses its existing composite primary key (Shipment_ID, Batch_ID).
EXTRA_TABLES = {
    "suppliers": {
        "table": "Supplier", "heading": "Suppliers", "pk": ["Supplier_ID"],
        "fields": [
            ("Supplier_Name", "Supplier Name", "text", True, None),
            ("Contact_Number", "Contact Number", "text", False, None),
            ("Email", "Email", "text", False, None),
            ("Address", "Address", "text", False, None),
        ]
    },
    "warehouses": {
        "table": "Warehouse", "heading": "Warehouses", "pk": ["Warehouse_ID"],
        "fields": [
            ("Warehouse_Name", "Warehouse Name", "text", True, None),
            ("Location", "Location", "text", False, None),
            ("Capacity", "Capacity", "int", False, None),
        ]
    },
    "storage_units": {
        "table": "Storage_Unit", "heading": "Storage Units", "pk": ["Storage_ID"],
        "fields": [
            ("Storage_Name", "Storage Name", "text", True, None),
            ("Storage_Type", "Storage Type", "text", False, None),
            ("Capacity", "Capacity", "int", False, None),
            ("Min_Temperature", "Minimum Temperature", "float", False, None),
            ("Max_Temperature", "Maximum Temperature", "float", False, None),
            ("Status", "Status", "text", False, None),
            ("Warehouse_ID", "Warehouse", "fk", True,
             ("SELECT Warehouse_ID, Warehouse_Name FROM Warehouse ORDER BY Warehouse_ID", "Warehouse_ID", "Warehouse_Name")),
        ]
    },
    "vehicles": {
        "table": "Vehicle", "heading": "Vehicles", "pk": ["Vehicle_ID"],
        "fields": [
            ("Vehicle_Number", "Vehicle Number", "text", True, None),
            ("Vehicle_Type", "Vehicle Type", "text", False, None),
            ("Min_Temperature", "Minimum Temperature", "float", False, None),
            ("Max_Temperature", "Maximum Temperature", "float", False, None),
            ("Vehicle_Status", "Vehicle Status", "text", False, None),
        ]
    },
    "drivers": {
        "table": "Driver", "heading": "Drivers", "pk": ["Driver_ID"],
        "fields": [
            ("Driver_Name", "Driver Name", "text", True, None),
            ("Phone_Number", "Phone Number", "text", False, None),
            ("License_Number", "License Number", "text", False, None),
        ]
    },
    "customers": {
        "table": "Customer", "heading": "Customers", "pk": ["Customer_ID"],
        "fields": [
            ("Customer_Name", "Customer Name", "text", True, None),
            ("Customer_Type", "Customer Type", "text", False, None),
            ("Contact_Number", "Contact Number", "text", False, None),
            ("Email", "Email", "text", False, None),
            ("Address", "Address", "text", False, None),
        ]
    },
    "shipment_batches": {
        "table": "Shipment_Batch", "heading": "Shipment Batches",
        "pk": ["Shipment_ID", "Batch_ID"],
        "fields": [
            ("Shipment_ID", "Shipment", "fk", True,
             ("SELECT Shipment_ID, Origin FROM Shipment ORDER BY Shipment_ID", "Shipment_ID", "Origin")),
            ("Batch_ID", "Product Batch", "fk", True,
             ("SELECT Batch_ID, Batch_Number FROM Product_Batch ORDER BY Batch_ID", "Batch_ID", "Batch_Number")),
            ("Quantity", "Quantity", "int", False, None),
        ]
    },
}


def _extra_table_values(category):
    config = EXTRA_TABLES[category]
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM {config['table']}")
    records = cursor.fetchall()
    columns = [item[0] for item in cursor.description]
    cursor.close()
    return columns, records


def extra_table_crud(action):
    category = active_category.get()
    if category not in EXTRA_TABLES:
        messagebox.showwarning("Select a table", "First select one of the seven additional tables.")
        return
    if db is None or not db.is_connected():
        messagebox.showwarning("Connection Required", "Connect to MySQL first.")
        return

    config = EXTRA_TABLES[category]
    table = config["table"]
    selected_values = None
    if action in ("update", "delete"):
        if heading_label.cget("text") != config["heading"]:
            messagebox.showwarning("Wrong table", f"Open {config['heading']} and select a record first.")
            return
        selected = data_table.selection()
        if not selected:
            messagebox.showwarning("Select record", "Select a record from the table first.")
            return
        selected_values = data_table.item(selected[0], "values")

    if action == "delete":
        key_values = selected_values[:len(config["pk"])]
        key_text = ", ".join(f"{key}={value}" for key, value in zip(config["pk"], key_values))
        if not messagebox.askyesno("Confirm Delete", f"Delete this {table} record?\n{key_text}"):
            return
        try:
            cursor = db.cursor()
            where = " AND ".join(f"{key}=%s" for key in config["pk"])
            cursor.execute(f"DELETE FROM {table} WHERE {where}", tuple(key_values))
            db.commit()
            cursor.close()
            messagebox.showinfo("Success", f"{table} record deleted.")
            load_data(category)
        except mysql.connector.Error as error:
            db.rollback()
            messagebox.showerror("Delete Error", f"Could not delete this record. It may be referenced by another table.\n\n{error}")
        return

    form = tk.Toplevel(root)
    form.title(("Add " if action == "add" else "Update ") + table.replace("_", " "))
    form.geometry("560x620")
    form.configure(bg="#eef2f7")
    form.transient(root)
    form.grab_set()

    widgets = {}
    row = 0
    if action == "add" and len(config["pk"]) == 1:
        tk.Label(form, text=f"{config['pk'][0]}: Generated automatically", bg="#eef2f7", fg="#555").grid(row=row, column=0, columnspan=2, padx=12, pady=8, sticky="w")
        row += 1

    # Existing primary keys are not editable during updates.
    for field, label, kind, required, fk in config["fields"]:
        if action == "update" and field in config["pk"]:
            continue
        tk.Label(form, text=label + (" *" if required else ""), bg="#eef2f7").grid(row=row, column=0, padx=12, pady=7, sticky="w")
        if kind == "fk":
            query, id_col, display_col = fk
            cursor = db.cursor()
            cursor.execute(query)
            options = cursor.fetchall()
            cursor.close()
            choices = [f"{display} (ID: {ident})" for ident, display in options]
            widget = ttk.Combobox(form, values=choices, state="readonly", width=34)
            if action == "update":
                current_columns, _ = _extra_table_values(category)
                old_value = str(selected_values[current_columns.index(field)])
                for i, option in enumerate(options):
                    if str(option[0]) == old_value:
                        widget.current(i)
                        break
            elif choices:
                widget.current(0)
            widgets[field] = (widget, kind, options)
        else:
            widget = ttk.Entry(form, width=37)
            if action == "update":
                # Find this field's column in the selected Treeview row.
                all_columns, _ = _extra_table_values(category)
                old_value = selected_values[all_columns.index(field)]
                if old_value is not None:
                    widget.insert(0, str(old_value))
            widgets[field] = (widget, kind, None)
        widget.grid(row=row, column=1, padx=12, pady=7, sticky="ew")
        row += 1

    tk.Label(form, text="* Required fields", bg="#eef2f7", fg="#555").grid(row=row, column=0, columnspan=2, padx=12, pady=8, sticky="w")

    def save_record():
        values = {}
        try:
            for field, label, kind, required, fk in config["fields"]:
                if action == "update" and field in config["pk"]:
                    continue
                widget, widget_kind, options = widgets[field]
                raw = widget.get().strip()
                if required and not raw:
                    messagebox.showwarning("Validation", f"{label} is required.")
                    return
                if kind == "fk":
                    if not raw:
                        values[field] = None
                    else:
                        index = widget.current()
                        if index < 0:
                            messagebox.showwarning("Validation", f"Select a valid {label}.")
                            return
                        values[field] = options[index][0]
                elif raw == "":
                    values[field] = None
                elif kind == "int":
                    values[field] = int(raw)
                elif kind == "float":
                    values[field] = float(raw)
                else:
                    values[field] = raw

            cursor = db.cursor()
            if action == "add":
                if len(config["pk"]) == 1:
                    pk = config["pk"][0]
                    cursor.execute(f"SELECT COALESCE(MAX({pk}), 0) + 1 FROM {table}")
                    values[pk] = cursor.fetchone()[0]
                insert_columns = list(dict.fromkeys(config["pk"] + [field[0] for field in config["fields"]]))
                insert_values = [values.get(column) for column in insert_columns]
                placeholders = ", ".join(["%s"] * len(insert_columns))
                cursor.execute(
                    f"INSERT INTO {table} ({', '.join(insert_columns)}) VALUES ({placeholders})",
                    tuple(insert_values)
                )
            else:
                set_columns = [field[0] for field in config["fields"] if field[0] not in config["pk"]]
                set_clause = ", ".join(f"{column}=%s" for column in set_columns)
                where_clause = " AND ".join(f"{key}=%s" for key in config["pk"])
                all_columns, _ = _extra_table_values(category)
                old_keys = [selected_values[all_columns.index(key)] for key in config["pk"]]
                cursor.execute(
                    f"UPDATE {table} SET {set_clause} WHERE {where_clause}",
                    tuple(values.get(column) for column in set_columns) + tuple(old_keys)
                )
            db.commit()
            cursor.close()
            form.destroy()
            messagebox.showinfo("Success", f"{table} record {'added' if action == 'add' else 'updated'} successfully.")
            load_data(category)
        except ValueError:
            messagebox.showerror("Invalid Input", "Enter valid numbers in numeric fields.")
        except mysql.connector.Error as error:
            db.rollback()
            messagebox.showerror("Database Error", str(error))

    ttk.Button(form, text="Save Record", command=save_record).grid(row=row + 1, column=0, columnspan=2, pady=18)


def connect_database():
    global db

    try:
        db = mysql.connector.connect(
            host="localhost",
            user=username_entry.get(),
            password=password_entry.get(),
            database=DATABASE
        )

        if db.is_connected():
            messagebox.showinfo(
                "Success",
                "Connected to ColdChainLogistics database!"
            )
            status_label.config(
                text="Database Connected",
                foreground="green"
            )
            load_data("products")

    except mysql.connector.Error as error:
        db = None
        messagebox.showerror(
            "Database Connection Error",
            str(error)
        )
        status_label.config(
            text="Database Disconnected",
            foreground="red"
        )


active_category = tk.StringVar(value="products")

def load_data(category):
    active_category.set(category)
    if db is None or not db.is_connected():
        messagebox.showwarning(
            "Connection Required",
            "Please connect to the database first."
        )
        return

    queries = {
        "products": (
            "SELECT * FROM Product",
            "Products"
        ),
        "batches": (
            "SELECT * FROM Product_Batch",
            "Product Batches"
        ),
        "shipments": (
            "SELECT * FROM Shipment",
            "Shipments"
        ),
        "temperature": (
            "SELECT * FROM Temperature_Log",
            "Temperature Logs"
        ),
        "violations": (
            "SELECT * FROM Temperature_Violation",
            "Temperature Violations"
        ),
        "inventory": (
            "SELECT * FROM Inventory",
            "Inventory"
        ),
        "suppliers": ("SELECT * FROM Supplier", "Suppliers"),
        "warehouses": ("SELECT * FROM Warehouse", "Warehouses"),
        "storage_units": ("SELECT * FROM Storage_Unit", "Storage Units"),
        "vehicles": ("SELECT * FROM Vehicle", "Vehicles"),
        "drivers": ("SELECT * FROM Driver", "Drivers"),
        "customers": ("SELECT * FROM Customer", "Customers"),
        "shipment_batches": ("SELECT * FROM Shipment_Batch", "Shipment Batches")
    }

    try:
        query, heading = queries[category]

        cursor = db.cursor()
        cursor.execute(query)

        records = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        # Clear previous table
        for item in data_table.get_children():
            data_table.delete(item)

        data_table["columns"] = columns
        data_table["show"] = "headings"

        # Display column headings
        for column in columns:
            data_table.heading(column, text=column)
            data_table.column(
                column,
                width=130,
                minwidth=100,
                anchor="center"
            )

        # Display records
        for record in records:
            data_table.insert("", tk.END, values=record)

        heading_label.config(text=heading)

        cursor.close()

    except mysql.connector.Error as error:
        messagebox.showerror("Query Error", str(error))


# Application heading
title_label = tk.Label(
    main_frame,
    text="COLD CHAIN LOGISTICS MANAGEMENT SYSTEM",
    font=("Arial", 20, "bold"),
    bg="#17365d",
    fg="white",
    pady=20
)
title_label.pack(fill=tk.X)

# Database connection section
connection_frame = tk.LabelFrame(
    main_frame,
    text="Database Connection",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=15,
    pady=10
)
connection_frame.pack(fill=tk.X, padx=20, pady=15)

tk.Label(
    connection_frame,
    text="Username:",
    bg="#eef2f7"
).grid(row=0, column=0, padx=5, pady=5)

username_entry = ttk.Entry(connection_frame, width=20)
username_entry.insert(0, "coldchain_app")
username_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(
    connection_frame,
    text="Password:",
    bg="#eef2f7"
).grid(row=0, column=2, padx=5, pady=5)

password_entry = ttk.Entry(
    connection_frame,
    width=20,
    show="*"
)
password_entry.grid(row=0, column=3, padx=5, pady=5)

connect_button = ttk.Button(
    connection_frame,
    text="Connect to Database",
    command=connect_database
)
connect_button.grid(row=0, column=4, padx=15, pady=5)

status_label = tk.Label(
    connection_frame,
    text="Database Disconnected",
    fg="red",
    bg="#eef2f7",
    font=("Arial", 10, "bold")
)
status_label.grid(row=0, column=5, padx=10, pady=5)

# Navigation buttons
navigation_frame = tk.LabelFrame(
    main_frame,
    text="Manage Cold Chain Data",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=10,
    pady=10
)
navigation_frame.pack(fill=tk.X, padx=20, pady=5)

buttons = [
    ("Products", "products"),
    ("Product Batches", "batches"),
    ("Shipments", "shipments"),
    ("Temperature Logs", "temperature"),
    ("Temperature Violations", "violations"),
    ("Inventory", "inventory"),
    ("Suppliers", "suppliers"),
    ("Warehouses", "warehouses"),
    ("Storage Units", "storage_units"),
    ("Vehicles", "vehicles"),
    ("Drivers", "drivers"),
    ("Customers", "customers"),
    ("Shipment Batches", "shipment_batches")
]

for index, (label, category) in enumerate(buttons):
    ttk.Button(
        navigation_frame,
        text=label,
        command=lambda c=category: load_data(c)
    ).grid(
        row=index // 7,
        column=index % 7,
        padx=8,
        pady=10
    )

# Individual CRUD sections for the seven additional tables.
# Each section has its own buttons, matching the original six table sections.
def run_extra_crud(category, action):
    active_category.set(category)
    extra_table_crud(action)


def create_extra_crud_section(category, title, add_label, update_label, delete_label):
    section = tk.LabelFrame(
        main_frame,
        text=title,
        font=("Arial", 12, "bold"),
        bg="#eef2f7",
        padx=10,
        pady=10
    )
    section.pack(fill=tk.X, padx=20, pady=5)

    ttk.Button(
        section,
        text=add_label,
        command=lambda c=category: run_extra_crud(c, "add")
    ).pack(side=tk.LEFT, padx=10)

    ttk.Button(
        section,
        text=update_label,
        command=lambda c=category: run_extra_crud(c, "update")
    ).pack(side=tk.LEFT, padx=10)

    ttk.Button(
        section,
        text=delete_label,
        command=lambda c=category: run_extra_crud(c, "delete")
    ).pack(side=tk.LEFT, padx=10)


create_extra_crud_section(
    "suppliers", "Supplier Management (CRUD Operations)",
    "Add Supplier", "Update Selected Supplier", "Delete Selected Supplier"
)
create_extra_crud_section(
    "warehouses", "Warehouse Management (CRUD Operations)",
    "Add Warehouse", "Update Selected Warehouse", "Delete Selected Warehouse"
)
create_extra_crud_section(
    "storage_units", "Storage Unit Management (CRUD Operations)",
    "Add Storage Unit", "Update Selected Storage Unit", "Delete Selected Storage Unit"
)
create_extra_crud_section(
    "vehicles", "Vehicle Management (CRUD Operations)",
    "Add Vehicle", "Update Selected Vehicle", "Delete Selected Vehicle"
)
create_extra_crud_section(
    "drivers", "Driver Management (CRUD Operations)",
    "Add Driver", "Update Selected Driver", "Delete Selected Driver"
)
create_extra_crud_section(
    "customers", "Customer Management (CRUD Operations)",
    "Add Customer", "Update Selected Customer", "Delete Selected Customer"
)
create_extra_crud_section(
    "shipment_batches", "Shipment Batch Management (CRUD Operations)",
    "Add Shipment Batch", "Update Selected Shipment Batch", "Delete Selected Shipment Batch"
)

# Product CRUD operations
crud_frame = tk.LabelFrame(
    main_frame,
    text="Product Management (CRUD Operations)",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=5,
    pady=3
)
crud_frame.pack(fill=tk.X, padx=20, pady=5)

ttk.Button(
    crud_frame,
    text="Add Product",
    command=add_product
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    crud_frame,
    text="Update Selected Product",
    command=update_product
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    crud_frame,
    text="Delete Selected Product",
    command=delete_product
).pack(side=tk.LEFT, padx=10)

# Product Batch CRUD operations
batch_crud_frame = tk.LabelFrame(
    main_frame,
    text="Product Batch Management (CRUD Operations)",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=10,
    pady=10
)
batch_crud_frame.pack(fill=tk.X, padx=20, pady=5)

ttk.Button(
    batch_crud_frame,
    text="Add Batch",
    command=add_batch
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    batch_crud_frame,
    text="Update Selected Batch",
    command=update_batch
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    batch_crud_frame,
    text="Delete Selected Batch",
    command=delete_batch
).pack(side=tk.LEFT, padx=10)

# Shipment CRUD Operations
shipment_crud_frame = tk.LabelFrame(
    main_frame,
    text="Shipment Management (CRUD Operations)",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=10,
    pady=10
)
shipment_crud_frame.pack(fill=tk.X, padx=20, pady=5)

ttk.Button(
    shipment_crud_frame,
    text="Add Shipment",
    command=add_shipment
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    shipment_crud_frame,
    text="Update Selected Shipment",
    command=update_shipment
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    shipment_crud_frame,
    text="Delete Selected Shipment",
    command=delete_shipment
).pack(side=tk.LEFT, padx=10)

# Temperature Log CRUD Operations
temperature_crud_frame = tk.LabelFrame(
    main_frame,
    text="Temperature Log Management (CRUD Operations)",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=10,
    pady=10
)
temperature_crud_frame.pack(fill=tk.X, padx=20, pady=5)

ttk.Button(
    temperature_crud_frame,
    text="Add Temperature Log",
    command=add_temperature_log
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    temperature_crud_frame,
    text="Update Selected Temperature Log",
    command=update_temperature_log
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    temperature_crud_frame,
    text="Delete Selected Temperature Log",
    command=delete_temperature_log
).pack(side=tk.LEFT, padx=10)

# Inventory CRUD Operations
inventory_crud_frame = tk.LabelFrame(
    main_frame,
    text="Inventory Management (CRUD Operations)",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=10,
    pady=10
)
inventory_crud_frame.pack(fill=tk.X, padx=20, pady=5)

ttk.Button(
    inventory_crud_frame,
    text="Add Inventory",
    command=add_inventory
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    inventory_crud_frame,
    text="Update Selected Inventory",
    command=update_inventory
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    inventory_crud_frame,
    text="Delete Selected Inventory",
    command=delete_inventory
).pack(side=tk.LEFT, padx=10)

# Temperature Violation CRUD Operations
violation_crud_frame = tk.LabelFrame(
    main_frame,
    text="Temperature Violation Management (CRUD Operations)",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=10,
    pady=10
)
violation_crud_frame.pack(fill=tk.X, padx=20, pady=5)

ttk.Button(
    violation_crud_frame,
    text="Add Temperature Violation",
    command=add_temperature_violation
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    violation_crud_frame,
    text="Update Selected Violation",
    command=update_temperature_violation
).pack(side=tk.LEFT, padx=10)

ttk.Button(
    violation_crud_frame,
    text="Delete Selected Violation",
    command=delete_temperature_violation
).pack(side=tk.LEFT, padx=10)

# MongoDB Sensor Monitoring Section
create_sensor_monitoring_section(
    main_frame,
    lambda: db
)

# Data display section
display_frame = tk.LabelFrame(
    main_frame,
    text="Database Records",
    font=("Arial", 12, "bold"),
    bg="#eef2f7",
    padx=10,
    pady=10
)
display_frame.pack(
    fill=tk.BOTH,
    expand=True,
    padx=20,
    pady=5
)

heading_label = tk.Label(
    display_frame,
    text="Products",
    font=("Arial", 14, "bold"),
    bg="#eef2f7"
)
heading_label.pack(pady=5)

table_frame = tk.Frame(display_frame)
table_frame.pack(fill=tk.BOTH, expand=True)

vertical_scroll = ttk.Scrollbar(
    table_frame,
    orient=tk.VERTICAL
)
vertical_scroll.pack(side=tk.RIGHT, fill=tk.Y)

horizontal_scroll = ttk.Scrollbar(
    table_frame,
    orient=tk.HORIZONTAL
)
horizontal_scroll.pack(side=tk.BOTTOM, fill=tk.X)

data_table = ttk.Treeview(
    table_frame,
    yscrollcommand=vertical_scroll.set,
    xscrollcommand=horizontal_scroll.set
)

data_table.pack(fill=tk.BOTH, expand=True)

vertical_scroll.config(command=data_table.yview)
horizontal_scroll.config(command=data_table.xview)

# Footer
footer_label = tk.Label(
    main_frame,
    text="Cold Chain Logistics Management System | DBMS Mini Project",
    font=("Arial", 9),
    bg="#17365d",
    fg="white",
    pady=10
)
footer_label.pack(fill=tk.X)

# Start application
root.mainloop()
