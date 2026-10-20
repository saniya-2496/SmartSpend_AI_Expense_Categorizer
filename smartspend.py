"""
SmartSpend - Intelligent Expense Categorizer
Built using Python standard library only.

Features:
- Add expenses with automatic rule-based categorization
- Explain the rule used for a category prediction
- Store transactions and learned corrections locally in SQLite
- Dashboard totals and category-wise spending
- Search/filter transactions
- Correct a category and remember the description for future use
- Delete transactions
- Export transactions to CSV

Run: python smartspend.py
Requires: Python 3 with Tkinter available.
No external packages or datasets required.
"""

import csv
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from pathlib import Path

APP_NAME = "SmartSpend - Intelligent Expense Categorizer"
DB_PATH = Path(__file__).with_name("smartspend.db")

CATEGORIES = [
    "Food", "Transport", "Education", "Shopping", "Bills",
    "Health", "Entertainment", "Groceries", "Travel", "Other"
]

# Built-in knowledge base: category -> recognizable keywords.
# This is a hand-written rule set, not a downloaded dataset.
RULES = {
    "Food": [
        "restaurant", "cafe", "coffee", "pizza", "burger", "sandwich",
        "lunch", "dinner", "breakfast", "swiggy", "zomato", "tea", "snack"
    ],
    "Transport": [
        "uber", "ola", "taxi", "bus", "metro", "train", "auto",
        "rickshaw", "petrol", "fuel", "parking", "rapido", "toll"
    ],
    "Education": [
        "book", "notebook", "college", "course", "tuition", "exam",
        "stationery", "udemy", "coursera", "education", "class"
    ],
    "Shopping": [
        "amazon", "flipkart", "clothes", "shirt", "shoes", "dress",
        "mall", "shopping", "bag", "accessory"
    ],
    "Bills": [
        "electricity", "water bill", "internet", "wifi", "broadband",
        "mobile recharge", "recharge", "phone bill", "gas bill", "rent"
    ],
    "Health": [
        "doctor", "hospital", "medicine", "pharmacy", "medical",
        "clinic", "dentist", "test", "health"
    ],
    "Entertainment": [
        "movie", "cinema", "netflix", "spotify", "game", "concert",
        "subscription", "prime video", "youtube premium"
    ],
    "Groceries": [
        "grocery", "vegetables", "fruits", "milk", "bread", "rice",
        "atta", "supermarket", "market", "eggs", "household"
    ],
    "Travel": [
        "hotel", "flight", "airline", "booking", "trip", "vacation",
        "resort", "tourism", "hostel"
    ],
}

def normalize(text):
    """Normalize text for predictable rule matching."""
    return " ".join(text.lower().strip().split())

class ExpenseEngine:
    """Small explainable rule-based inference engine."""

    def __init__(self, connection):
        self.conn = connection

    def categorize(self, description):
        text = normalize(description)
        if not text:
            return "Other", "No description provided; defaulted to Other."

        # Learned exact-description corrections take priority.
        row = self.conn.execute(
            "SELECT category FROM learned_rules WHERE normalized_description = ?",
            (text,)
        ).fetchone()
        if row:
            return row[0], "Matched a category you corrected and saved previously."

        # Score categories by matching keywords; longer matches get priority.
        scores = {}
        matches = {}
        for category, keywords in RULES.items():
            found = [word for word in keywords if word in text]
            if found:
                scores[category] = sum(len(word) for word in found)
                matches[category] = found

        if not scores:
            return "Other", "No built-in keyword matched; defaulted to Other."

        best_score = max(scores.values())
        winners = [cat for cat, score in scores.items() if score == best_score]
        if len(winners) > 1:
            return "Other", "Several categories matched equally; please review the prediction."

        chosen = winners[0]
        matched = ", ".join(matches[chosen])
        return chosen, f"Matched keyword(s): {matched}."

    def remember_correction(self, description, category):
        text = normalize(description)
        if text:
            self.conn.execute(
                """INSERT INTO learned_rules(normalized_description, category)
                   VALUES (?, ?)
                   ON CONFLICT(normalized_description)
                   DO UPDATE SET category = excluded.category""",
                (text, category)
            )
            self.conn.commit()

class SmartSpendApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)

        self.conn = sqlite3.connect(DB_PATH)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()
        self.engine = ExpenseEngine(self.conn)

        self.description_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.category_var = tk.StringVar(value="Auto-detect")
        self.filter_var = tk.StringVar(value="All")
        self.search_var = tk.StringVar()
        self.prediction_var = tk.StringVar(value="Enter an expense to see the suggested category.")
        self.total_var = tk.StringVar(value="₹0.00")
        self.count_var = tk.StringVar(value="0")
        self.category_summary_var = tk.StringVar(value="No expenses yet.")
        self.build_ui()
        self.refresh_all()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                reason TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learned_rules (
                normalized_description TEXT PRIMARY KEY,
                category TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Metric.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Treeview", rowheight=27, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="SmartSpend", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Intelligent Expense Management", foreground="#526070").pack(side="left", padx=14, pady=(8, 0))
        ttk.Button(header, text="Export CSV", command=self.export_csv).pack(side="right")

        metrics = ttk.Frame(outer)
        metrics.pack(fill="x", pady=(0, 12))
        self.metric_card(metrics, "Total spending", self.total_var, 0)
        self.metric_card(metrics, "Transactions", self.count_var, 1)
        self.metric_card(metrics, "Top category", self.category_summary_var, 2)

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)

        form = ttk.LabelFrame(content, text="Add an expense", padding=12)
        form.pack(side="left", fill="y", padx=(0, 12))
        form.configure(width=300)
        form.pack_propagate(False)

        ttk.Label(form, text="Description").pack(anchor="w")
        desc_entry = ttk.Entry(form, textvariable=self.description_var, width=31)
        desc_entry.pack(fill="x", pady=(3, 10))
        desc_entry.bind("<KeyRelease>", self.preview_category)

        ttk.Label(form, text="Amount (₹)").pack(anchor="w")
        ttk.Entry(form, textvariable=self.amount_var).pack(fill="x", pady=(3, 10))

        ttk.Label(form, text="Date (YYYY-MM-DD)").pack(anchor="w")
        ttk.Entry(form, textvariable=self.date_var).pack(fill="x", pady=(3, 10))

        ttk.Label(form, text="Category").pack(anchor="w")
        category_choices = ["Auto-detect"] + CATEGORIES
        category_box = ttk.Combobox(
            form, textvariable=self.category_var, values=category_choices,
            state="readonly"
        )
        category_box.pack(fill="x", pady=(3, 10))
        category_box.bind("<<ComboboxSelected>>", self.preview_category)

        ttk.Label(form, text="AI explanation").pack(anchor="w")
        ttk.Label(
            form, textvariable=self.prediction_var, wraplength=255,
            foreground="#315a7d", justify="left"
        ).pack(fill="x", pady=(4, 12))

        ttk.Button(form, text="Add Expense", command=self.add_expense).pack(fill="x", pady=(0, 7))
        ttk.Button(form, text="Clear Form", command=self.clear_form).pack(fill="x")
        ttk.Separator(form).pack(fill="x", pady=14)
        ttk.Label(form, text="How the AI works", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(
            form,
            text="1. Match description to keyword rules.\n"
                 "2. Select the strongest category match.\n"
                 "3. Show the reason for the prediction.\n"
                 "4. Learn from your saved corrections.",
            wraplength=255, justify="left"
        ).pack(anchor="w", pady=(5, 0))

        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True)

        controls = ttk.Frame(right)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Label(controls, text="Search").pack(side="left")
        search_entry = ttk.Entry(controls, textvariable=self.search_var, width=22)
        search_entry.pack(side="left", padx=(5, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_transactions())
        ttk.Label(controls, text="Category").pack(side="left")
        filter_box = ttk.Combobox(
            controls, textvariable=self.filter_var,
            values=["All"] + CATEGORIES, state="readonly", width=16
        )
        filter_box.pack(side="left", padx=5)
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_transactions())

        columns = ("date", "description", "amount", "category", "reason")
        self.tree = ttk.Treeview(right, columns=columns, show="headings", selectmode="browse")
        headings = {
            "date": "Date", "description": "Description", "amount": "Amount (₹)",
            "category": "Category", "reason": "Categorization reason"
        }
        widths = {"date": 95, "description": 160, "amount": 90, "category": 110, "reason": 220}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.column("amount", anchor="e")
        yscroll = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        actions = ttk.Frame(right)
        actions.pack(fill="x", pady=(9, 0))
        ttk.Button(actions, text="Correct Selected Category", command=self.correct_selected).pack(side="left")
        ttk.Button(actions, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=7)
        ttk.Button(actions, text="Refresh", command=self.refresh_all).pack(side="right")

        ttk.Label(
            outer,
            text="Local-only storage • No external dataset • Rule-based AI (not machine learning)",
            foreground="#65717e"
        ).pack(anchor="w", pady=(10, 0))

    def metric_card(self, parent, label, variable, column):
        parent.columnconfigure(column, weight=1)
        card = ttk.LabelFrame(parent, text=label, padding=10)
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        ttk.Label(card, textvariable=variable, style="Metric.TLabel").pack(anchor="w")

    def preview_category(self, _event=None):
        description = self.description_var.get()
        category, reason = self.engine.categorize(description)
        chosen = self.category_var.get()
        if chosen != "Auto-detect":
            category = chosen
            reason = "Manual category selected by user."
        self.prediction_var.set(f"Suggested: {category}\n{reason}")

    def add_expense(self):
        description = self.description_var.get().strip()
        amount_text = self.amount_var.get().strip().replace(",", "")
        expense_date = self.date_var.get().strip()

        if not description:
            messagebox.showwarning("Missing description", "Please enter an expense description.")
            return
        try:
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid amount", "Enter an amount greater than zero.")
            return
        try:
            datetime.strptime(expense_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid date", "Use date format YYYY-MM-DD.")
            return

        predicted, reason = self.engine.categorize(description)
        selected = self.category_var.get()
        category = predicted if selected == "Auto-detect" else selected
        if selected != "Auto-detect":
            reason = "Category manually selected by user."
            # Explicit category selection is treated as feedback for this description.
            self.engine.remember_correction(description, category)

        self.conn.execute(
            """INSERT INTO expenses(expense_date, description, amount, category, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (expense_date, description, amount, category, reason)
        )
        self.conn.commit()
        self.clear_form()
        self.refresh_all()
        messagebox.showinfo("Expense added", f"Saved under: {category}")

    def clear_form(self):
        self.description_var.set("")
        self.amount_var.set("")
        self.date_var.set(date.today().isoformat())
        self.category_var.set("Auto-detect")
        self.prediction_var.set("Enter an expense to see the suggested category.")

    def refresh_all(self):
        self.refresh_metrics()
        self.refresh_transactions()

    def refresh_metrics(self):
        total, count = self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM expenses"
        ).fetchone()
        self.total_var.set(f"₹{total:,.2f}")
        self.count_var.set(str(count))
        rows = self.conn.execute(
            "SELECT category, SUM(amount) total FROM expenses GROUP BY category ORDER BY total DESC"
        ).fetchall()
        if rows:
            self.category_summary_var.set(rows[0][0])
        else:
            self.category_summary_var.set("—")

    def refresh_transactions(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        query = "SELECT id, expense_date, description, amount, category, reason FROM expenses WHERE 1=1"
        params = []
        category = self.filter_var.get()
        search = self.search_var.get().strip()
        if category != "All":
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (description LIKE ? OR category LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY expense_date DESC, id DESC"
        for row in self.conn.execute(query, params).fetchall():
            ident, exp_date, description, amount, category, reason = row
            self.tree.insert("", "end", iid=str(ident), values=(
                exp_date, description, f"{amount:,.2f}", category, reason
            ))

    def selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a transaction first.")
            return None
        return int(selected[0])

    def correct_selected(self):
        ident = self.selected_id()
        if ident is None:
            return
        row = self.conn.execute(
            "SELECT description, category FROM expenses WHERE id = ?", (ident,)
        ).fetchone()
        if not row:
            return
        description, current_category = row

        dialog = tk.Toplevel(self.root)
        dialog.title("Correct category")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"Expense: {description}", wraplength=330).pack(anchor="w", pady=(0, 10))
        ttk.Label(frame, text="Choose the correct category:").pack(anchor="w")
        chosen_var = tk.StringVar(value=current_category)
        ttk.Combobox(frame, textvariable=chosen_var, values=CATEGORIES, state="readonly").pack(fill="x", pady=8)
        ttk.Label(
            frame, text="The correction will be remembered for future matching descriptions.",
            wraplength=330
        ).pack(anchor="w", pady=(0, 10))

        def save():
            category = chosen_var.get()
            self.engine.remember_correction(description, category)
            self.conn.execute(
                "UPDATE expenses SET category = ?, reason = ? WHERE id = ?",
                (category, "Corrected by user; saved as a learning rule.", ident)
            )
            self.conn.commit()
            dialog.destroy()
            self.refresh_all()

        ttk.Button(frame, text="Save Correction", command=save).pack(anchor="e")

    def delete_selected(self):
        ident = self.selected_id()
        if ident is None:
            return
        if messagebox.askyesno("Confirm deletion", "Delete this expense? This cannot be undone."):
            self.conn.execute("DELETE FROM expenses WHERE id = ?", (ident,))
            self.conn.commit()
            self.refresh_all()

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Export expenses",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="smartspend_expenses.csv"
        )
        if not path:
            return
        rows = self.conn.execute(
            "SELECT expense_date, description, amount, category, reason FROM expenses ORDER BY expense_date DESC"
        ).fetchall()
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["Date", "Description", "Amount (INR)", "Category", "Reason"])
                writer.writerows(rows)
            messagebox.showinfo("Export complete", f"Exported {len(rows)} expenses to:\n{path}")
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))

    def on_close(self):
        self.conn.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    SmartSpendApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
