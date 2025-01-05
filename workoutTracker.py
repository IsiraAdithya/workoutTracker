import sys
import sqlite3
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QToolButton,
    QMenu,
    QDialog,
    QFormLayout,
    QDialogButtonBox
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFontDatabase

###############################################################################
# 1. DATABASE & UTILS
###############################################################################

# Using a NEW DB name so we definitely don't conflict with old schemas:
DB_NAME = "futuristic_tracker_v2.db"

def initialize_db():
    """
    Creates the necessary tables in a fresh 'futuristic_tracker_v2.db'.
    We use (exercise_id, set_number) as a composite primary key in the 'sets' table.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Table: workouts
    c.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            workout_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL
        );
    """)

    # Table: exercises
    c.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            FOREIGN KEY (workout_id) REFERENCES workouts(workout_id)
        );
    """)

    # Table: sets (no separate 'set_id'; use set_number instead)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sets (
            exercise_id INTEGER NOT NULL,
            set_number INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            weight FLOAT NOT NULL,
            PRIMARY KEY (exercise_id, set_number),
            FOREIGN KEY (exercise_id) REFERENCES exercises(exercise_id)
        );
    """)

    # Table: weigh_ins
    c.execute("""
        CREATE TABLE IF NOT EXISTS weigh_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            weight FLOAT NOT NULL
        );
    """)

    # Table: nutrition_log
    c.execute("""
        CREATE TABLE IF NOT EXISTS nutrition_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            calories FLOAT NOT NULL,
            protein FLOAT NOT NULL,
            carbs FLOAT NOT NULL,
            fat FLOAT NOT NULL
        );
    """)

    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_NAME)

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

###############################################################################
# 2. STYLES
###############################################################################

FUTURISTIC_QSS = """
QMainWindow {
    background-color: #0D0F10;
}

QTabWidget::pane {
    border: 1px solid #0ff0fc;
}
QTabBar::tab {
    background: #1C1C1C;
    color: #e0e0e0;
    padding: 8px;
    margin: 2px;
}
QTabBar::tab:selected {
    background: #0ff0fc;
    color: #000;
}

QLabel {
    color: #e0e0e0;
    font-family: 'Exo 2';
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
    background-color: #1C1C1C;
    color: #e0e0e0;
    border: 1px solid #0ff0fc;
    border-radius: 4px;
    min-height: 28px;
    padding: 6px;
    font-size: 14px;
    font-family: 'Exo 2';
}

QPushButton {
    background-color: #0ff0fc;
    color: #000000;
    border: none;
    padding: 8px 16px;
    font-family: 'Exo 2';
    font-size: 14px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #0CC0C9;
    box-shadow: 0 0 12px #0ff0fc;
}

QTableWidget {
    background-color: #1C1C1C;
    color: #e0e0e0;
    gridline-color: #0ff0fc;
    border: none;
    font-family: 'Exo 2';
}
QHeaderView::section {
    background-color: #0ff0fc;
    color: #000;
    font-weight: bold;
}
"""

###############################################################################
# 3. PLAN (FIXED, NO CRUD) & CHECKLIST
###############################################################################
WORKOUT_PLAN = {
    "Day 1: Back & Biceps (Pull 1)": [
        "Neutral Grip Pull-Ups",
        "Pronated Pull-Ups",
        "Cable Rows (Wide-Grip)",
        "Lat Pullovers",
        "EZ Bar Curls",
        "Hammer Curls",
        "Incline Dumbbell Curls",
    ],
    "Day 2: Chest & Triceps (Push 1)": [
        "Incline Machine Press",
        "Flat Machine Bench Press",
        "Low to High Cable Flies",
        "Chest Dips",
        "Overhead Triceps Extension",
        "Cable Pushdowns",
        "Triceps Dips (Bodyweight or Weighted)",
    ],
    "Day 3: Legs (Legs 1)": [
        "Smith Machine Squats",
        "Hack Squat Machine",
        "Leg Press",
        "Leg Curls (Prone)",
        "Leg Extensions",
        "Seated Calf Raises",
    ],
    "Day 4: Rest/Active Recovery": [
        "Light cardio (15-20 minutes)",
        "Dynamic stretching",
        "Foam rolling or yoga",
    ],
    "Day 5: Back, Biceps & Rear Delts (Pull 2)": [
        "Neutral Grip Pull-Ups",
        "One-Arm Dumbbell Rows",
        "Cable Rows (Close-Grip)",
        "Lat Pullovers",
        "Straight Bar Curls",
        "Reverse Grip Curls",
        "Rear Delt Flies (Machine)",
    ],
    "Day 6: Shoulders, Chest & Triceps (Push 2)": [
        "Machine Shoulder Press",
        "Dumbbell Lateral Flies",
        "Cable Side Lateral Flies (Single Arm)",
        "Rear Delt Flies (Machine)",
        "Chest Pullovers",
        "Overhead Dumbbell Triceps Extension",
        "Dumbbell Shrugs",
    ],
    "Day 7: Rest/Active Recovery": [
        "Light stretching or mobility drills",
        "Gentle cardio (e.g., cycling or swimming)",
    ],
}

class AddPlanExercisesDialog(QDialog):
    """
    Prompt for date, reps, weight for all selected exercises.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Selected Exercises to Workouts")
        self.resize(300, 200)

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Date (YYYY-MM-DD), blank=Today")

        self.reps_input = QSpinBox()
        self.reps_input.setRange(1, 999)
        self.reps_input.setValue(10)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0, 9999)
        self.weight_input.setValue(100.0)
        self.weight_input.setSingleStep(5.0)

        form = QFormLayout()
        form.addRow("Date:", self.date_input)
        form.addRow("Reps:", self.reps_input)
        form.addRow("Weight:", self.weight_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def get_data(self):
        date_str = self.date_input.text().strip() or today_str()
        reps_val = self.reps_input.value()
        weight_val = self.weight_input.value()
        return date_str, reps_val, weight_val

class PlanTab(QWidget):
    """
    Shows day combo -> checkboxes for each exercise -> "Add to Workouts" button.
    If the same day & exercise are added again, increment set_number automatically.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(10)

        # Day combo
        self.day_combo = QComboBox()
        day_list = list(WORKOUT_PLAN.keys())
        self.day_combo.addItems(day_list)
        self.day_combo.currentIndexChanged.connect(self.on_day_changed)

        self.main_layout.addWidget(QLabel("Select a Day:"))
        self.main_layout.addWidget(self.day_combo)

        # Scroll area for multiple exercises
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.ex_container = QWidget()
        self.ex_layout = QVBoxLayout(self.ex_container)
        self.ex_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.ex_container)
        self.main_layout.addWidget(self.scroll_area)

        # Button to add selected
        self.add_button = QPushButton("Add to Workouts")
        self.add_button.clicked.connect(self.on_add_to_workouts)
        self.main_layout.addWidget(self.add_button)

        self.setLayout(self.main_layout)
        self.populate_exercises(self.day_combo.currentText())

    def on_day_changed(self):
        selected_day = self.day_combo.currentText()
        self.populate_exercises(selected_day)

    def populate_exercises(self, day_key):
        # Clear old
        for i in reversed(range(self.ex_layout.count())):
            w_item = self.ex_layout.itemAt(i)
            w = w_item.widget()
            if w:
                w.setParent(None)

        ex_list = WORKOUT_PLAN.get(day_key, [])
        for ex_name in ex_list:
            checkbox = QCheckBox(ex_name)
            self.ex_layout.addWidget(checkbox)

        self.ex_layout.addStretch()

    def on_add_to_workouts(self):
        """
        1) Gather checked exercises
        2) Ask date, reps, weight
        3) Insert each set (auto-increment set_number).
        """
        checked_exercises = []
        for i in range(self.ex_layout.count()):
            item = self.ex_layout.itemAt(i)
            if not item:
                continue
            widget = item.widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                checked_exercises.append(widget.text())

        if not checked_exercises:
            QMessageBox.information(self, "No Selection", "No exercises checked.")
            return

        dialog = AddPlanExercisesDialog(self)
        if dialog.exec() == QDialog.Accepted:
            date_str, reps_val, weight_val = dialog.get_data()
            for ex_name in checked_exercises:
                self.insert_exercise_to_db(date_str, ex_name, reps_val, weight_val)

            QMessageBox.information(self, "Success",
                f"Added {len(checked_exercises)} exercise(s) to your Workouts!")

    def insert_exercise_to_db(self, date_str, ex_name, reps, weight):
        conn = get_connection()
        c = conn.cursor()
        # 1) find or create workout
        c.execute("SELECT workout_id FROM workouts WHERE date=?", (date_str,))
        row = c.fetchone()
        if row:
            workout_id = row[0]
        else:
            c.execute("INSERT INTO workouts (date) VALUES (?)", (date_str,))
            workout_id = c.lastrowid

        # 2) find or create exercise
        c.execute("""
            SELECT exercise_id FROM exercises
            WHERE workout_id=? AND exercise_name=?
        """,(workout_id, ex_name))
        e_row = c.fetchone()
        if e_row:
            exercise_id = e_row[0]
        else:
            c.execute("""
                INSERT INTO exercises (workout_id, exercise_name)
                VALUES (?,?)
            """,(workout_id, ex_name))
            exercise_id = c.lastrowid

        # 3) find max set_number so far for that exercise
        c.execute("""
            SELECT COALESCE(MAX(set_number),0)
            FROM sets
            WHERE exercise_id=?
        """, (exercise_id,))
        max_set_num = c.fetchone()[0]
        new_set_number = max_set_num + 1

        # 4) insert set
        c.execute("""
            INSERT INTO sets (exercise_id, set_number, reps, weight)
            VALUES (?,?,?,?)
        """,(exercise_id, new_set_number, reps, weight))
        conn.commit()
        conn.close()

###############################################################################
# 4. WORKOUT TAB WITH CRUD (NO set_id; 'set_number' auto increments)
###############################################################################

class EditSetDialog(QDialog):
    """
    Edits a set: (exercise_id, set_number).
    We allow changing date, exercise_name, reps, weight => new row for that combo.
    """
    def __init__(self, exercise_id, set_number, parent=None):
        super().__init__(parent)
        self.exercise_id = exercise_id
        self.set_number = set_number

        self.setWindowTitle(f"Edit Set (exercise_id={exercise_id}, set_num={set_number})")
        self.resize(300,200)

        self.date_input = QLineEdit()
        self.exercise_input = QLineEdit()
        self.reps_input = QSpinBox()
        self.reps_input.setRange(1,999)
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0,9999)
        self.weight_input.setSingleStep(5.0)

        self.load_set_data()

        form = QFormLayout()
        form.addRow("Date:", self.date_input)
        form.addRow("Exercise:", self.exercise_input)
        form.addRow("Reps:", self.reps_input)
        form.addRow("Weight:", self.weight_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def load_set_data(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT w.date, e.exercise_name, s.reps, s.weight
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.exercise_id
            JOIN workouts w ON e.workout_id = w.workout_id
            WHERE s.exercise_id=? AND s.set_number=?
        """,(self.exercise_id,self.set_number))
        row = c.fetchone()
        conn.close()

        if row:
            date_val, ex_name, reps_val, weight_val = row
            self.date_input.setText(date_val)
            self.exercise_input.setText(ex_name)
            self.reps_input.setValue(reps_val)
            self.weight_input.setValue(weight_val)

    def get_data(self):
        d = self.date_input.text().strip()
        e = self.exercise_input.text().strip()
        r = self.reps_input.value()
        w = self.weight_input.value()
        return d, e, r, w

class WorkoutTab(QWidget):
    """
    Displays the last 10 sets => date, exercise, set#, reps, weight,
    plus an actions menu for Edit/Delete.
    Also 'Add Set' + 'Refresh' button.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # Add Set
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Date (YYYY-MM-DD), blank=Today")

        self.exercise_input = QLineEdit()
        self.exercise_input.setPlaceholderText("Exercise Name")

        self.reps_input = QSpinBox()
        self.reps_input.setRange(1,999)
        self.reps_input.setValue(10)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0,9999)
        self.weight_input.setSingleStep(5.0)
        self.weight_input.setValue(100.0)

        btn_add = QPushButton("Add Set")
        btn_add.clicked.connect(self.add_set)

        main_layout.addWidget(QLabel("Add a Single Set"))
        main_layout.addWidget(self.date_input)
        main_layout.addWidget(self.exercise_input)
        main_layout.addWidget(QLabel("Reps:"))
        main_layout.addWidget(self.reps_input)
        main_layout.addWidget(QLabel("Weight:"))
        main_layout.addWidget(self.weight_input)
        main_layout.addWidget(btn_add)

        # Refresh button
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_sets)
        main_layout.addWidget(btn_refresh)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)  # date, exercise, set#, reps, weight, actions
        self.table.setHorizontalHeaderLabels([
            "Date","Exercise","Set #","Reps","Weight","Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        main_layout.addWidget(QLabel("Recent Sets (Latest 10)"))
        main_layout.addWidget(self.table)
        self.setLayout(main_layout)

        self.load_sets()

    def load_sets(self):
        """
        SELECT last 10 sets => we get (date, exercise_name, set_number, reps, weight, exercise_id).
        """
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT w.date, e.exercise_name, s.set_number, s.reps, s.weight, s.exercise_id
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.exercise_id
            JOIN workouts w ON e.workout_id = w.workout_id
            ORDER BY w.date DESC, s.exercise_id DESC, s.set_number DESC
            LIMIT 10;
        """)
        rows = c.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            date_val, ex_name, set_num, reps_val, weight_val, exercise_id = row
            self.table.setItem(i, 0, QTableWidgetItem(date_val))
            self.table.setItem(i, 1, QTableWidgetItem(ex_name))
            self.table.setItem(i, 2, QTableWidgetItem(str(set_num)))
            self.table.setItem(i, 3, QTableWidgetItem(str(reps_val)))
            self.table.setItem(i, 4, QTableWidgetItem(str(weight_val)))

            # 3-dot menu
            tool_btn = QToolButton()
            tool_btn.setText("⋮")
            menu = QMenu()
            action_edit = menu.addAction("Edit")
            action_delete = menu.addAction("Delete")

            action_edit.triggered.connect(lambda checked, e_id=exercise_id, s_n=set_num: self.edit_set(e_id, s_n))
            action_delete.triggered.connect(lambda checked, e_id=exercise_id, s_n=set_num: self.delete_set(e_id, s_n))

            tool_btn.setMenu(menu)
            tool_btn.setPopupMode(QToolButton.InstantPopup)

            self.table.setCellWidget(i, 5, tool_btn)

    def add_set(self):
        """
        Insert a new set => auto-increment set_number for that exercise.
        """
        date_str = self.date_input.text().strip() or today_str()
        ex_name = self.exercise_input.text().strip()
        reps_val = self.reps_input.value()
        weight_val = self.weight_input.value()

        if not ex_name:
            QMessageBox.warning(self,"Error","Exercise cannot be empty.")
            return

        conn = get_connection()
        c = conn.cursor()

        # 1) get/create workout
        c.execute("SELECT workout_id FROM workouts WHERE date=?",(date_str,))
        row = c.fetchone()
        if row:
            w_id = row[0]
        else:
            c.execute("INSERT INTO workouts (date) VALUES (?)",(date_str,))
            w_id = c.lastrowid

        # 2) get/create exercise
        c.execute("""
            SELECT exercise_id FROM exercises
            WHERE workout_id=? AND exercise_name=?
        """,(w_id, ex_name))
        e_row = c.fetchone()
        if e_row:
            e_id = e_row[0]
        else:
            c.execute("""
                INSERT INTO exercises (workout_id, exercise_name)
                VALUES (?,?)
            """,(w_id, ex_name))
            e_id = c.lastrowid

        # 3) find max set_number
        c.execute("""
            SELECT COALESCE(MAX(set_number),0)
            FROM sets
            WHERE exercise_id=?
        """,(e_id,))
        max_sn = c.fetchone()[0]
        new_sn = max_sn+1

        # 4) insert row
        c.execute("""
            INSERT INTO sets (exercise_id, set_number, reps, weight)
            VALUES (?,?,?,?)
        """,(e_id, new_sn, reps_val, weight_val))
        conn.commit()
        conn.close()

        # Clear fields
        self.exercise_input.clear()
        self.reps_input.setValue(10)
        self.weight_input.setValue(100.0)

        # Refresh
        self.load_sets()

    def edit_set(self, exercise_id, set_number):
        dialog = EditSetDialog(exercise_id, set_number, self)
        if dialog.exec() == QDialog.Accepted:
            new_date, new_ex, new_reps, new_weight = dialog.get_data()
            if not new_ex:
                QMessageBox.warning(self,"Error","Exercise name cannot be empty.")
                return
            self.update_set(exercise_id, set_number, new_date, new_ex, new_reps, new_weight)
            self.load_sets()

    def update_set(self, old_e_id, old_sn, new_date, new_ex, new_reps, new_weight):
        """
        1) get/create workout for new_date
        2) get/create exercise row for new_ex
        3) find new set_number for that exercise
        4) remove old row
        5) insert new row
        """
        conn = get_connection()
        c = conn.cursor()

        # new or existing workout
        c.execute("SELECT workout_id FROM workouts WHERE date=?",(new_date,))
        w_row = c.fetchone()
        if w_row:
            w_id = w_row[0]
        else:
            c.execute("INSERT INTO workouts (date) VALUES (?)",(new_date,))
            w_id = c.lastrowid

        # new or existing exercise
        c.execute("""
            SELECT exercise_id FROM exercises
            WHERE workout_id=? AND exercise_name=?
        """,(w_id, new_ex))
        ex_row = c.fetchone()
        if ex_row:
            new_eid = ex_row[0]
        else:
            c.execute("""
                INSERT INTO exercises (workout_id, exercise_name)
                VALUES (?,?)
            """,(w_id, new_ex))
            new_eid = c.lastrowid

        # find next set_number
        c.execute("""
            SELECT COALESCE(MAX(set_number),0)
            FROM sets
            WHERE exercise_id=?
        """,(new_eid,))
        max_sn = c.fetchone()[0]
        new_sn = max_sn+1

        # remove old row
        c.execute("""
            DELETE FROM sets
            WHERE exercise_id=? AND set_number=?
        """,(old_e_id, old_sn))

        # insert new row
        c.execute("""
            INSERT INTO sets (exercise_id, set_number, reps, weight)
            VALUES (?,?,?,?)
        """,(new_eid, new_sn, new_reps, new_weight))

        conn.commit()
        conn.close()

    def delete_set(self, e_id, s_num):
        ret = QMessageBox.question(
            self,"Confirm Delete",
            f"Delete set: exercise_id={e_id}, set_number={s_num}?",
            QMessageBox.Yes|QMessageBox.No,
            QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                DELETE FROM sets
                WHERE exercise_id=? AND set_number=?
            """,(e_id,s_num))
            conn.commit()
            conn.close()
            self.load_sets()

###############################################################################
# 5. WEIGH-INS & NUTRITION (same as before)
###############################################################################

class WeighInTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Date (YYYY-MM-DD), blank=Today")
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0,1000)
        self.weight_input.setValue(180.0)
        self.weight_input.setSingleStep(0.5)

        btn_log = QPushButton("Log Weight")
        btn_log.clicked.connect(self.log_weight)

        layout.addWidget(QLabel("Log Weigh-In"))
        layout.addWidget(self.date_input)
        layout.addWidget(self.weight_input)
        layout.addWidget(btn_log)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Date","Weight"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(QLabel("Weigh-In History (Latest 10)"))
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.load_weigh_ins()

    def load_weigh_ins(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT date, weight FROM weigh_ins ORDER BY date DESC LIMIT 10;")
        rows = c.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(row[0]))
            self.table.setItem(i,1,QTableWidgetItem(str(row[1])))

    def log_weight(self):
        date_str = self.date_input.text().strip() or today_str()
        w_val = self.weight_input.value()
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO weigh_ins (date,weight) VALUES (?,?)",(date_str,w_val))
        conn.commit()
        conn.close()

        self.date_input.clear()
        self.weight_input.setValue(180.0)
        self.load_weigh_ins()

class NutritionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Date (YYYY-MM-DD), blank=Today")

        self.calories_input = QSpinBox()
        self.calories_input.setRange(0,100000)
        self.calories_input.setValue(2000)

        self.protein_input = QSpinBox()
        self.protein_input.setRange(0,1000)
        self.protein_input.setValue(150)

        self.carbs_input = QSpinBox()
        self.carbs_input.setRange(0,1000)
        self.carbs_input.setValue(200)

        self.fat_input = QSpinBox()
        self.fat_input.setRange(0,500)
        self.fat_input.setValue(70)

        btn_log_nutrition = QPushButton("Log Daily Nutrition")
        btn_log_nutrition.clicked.connect(self.log_nutrition)

        layout.addWidget(QLabel("Log Daily Nutrition"))
        layout.addWidget(self.date_input)
        layout.addWidget(QLabel("Calories:"))
        layout.addWidget(self.calories_input)
        layout.addWidget(QLabel("Protein (g):"))
        layout.addWidget(self.protein_input)
        layout.addWidget(QLabel("Carbs (g):"))
        layout.addWidget(self.carbs_input)
        layout.addWidget(QLabel("Fat (g):"))
        layout.addWidget(self.fat_input)
        layout.addWidget(btn_log_nutrition)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date","Calories","Protein","Carbs","Fat"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(QLabel("Recent Nutrition Logs (Latest 10)"))
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.load_nutrition()

    def load_nutrition(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT date, calories, protein, carbs, fat
            FROM nutrition_log
            ORDER BY date DESC
            LIMIT 10;
        """)
        rows = c.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,val in enumerate(row):
                self.table.setItem(i,j,QTableWidgetItem(str(val)))

    def log_nutrition(self):
        date_str = self.date_input.text().strip() or today_str()
        cals = self.calories_input.value()
        prot = self.protein_input.value()
        carbs = self.carbs_input.value()
        fat = self.fat_input.value()

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO nutrition_log (date,calories,protein,carbs,fat)
            VALUES (?,?,?,?,?)
        """,(date_str,cals,prot,carbs,fat))
        conn.commit()
        conn.close()

        self.date_input.clear()
        self.calories_input.setValue(2000)
        self.protein_input.setValue(150)
        self.carbs_input.setValue(200)
        self.fat_input.setValue(70)
        self.load_nutrition()

###############################################################################
# 6. MAIN WINDOW
###############################################################################
from PySide6.QtCore import QPropertyAnimation

class FuturisticFitnessTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Futuristic Fitness Tracker (v2)")
        self.setGeometry(100,100,1000,700)
        self.setStyleSheet(FUTURISTIC_QSS)

        self.setWindowOpacity(0.0)
        self.fade_in_animation()

        self.tabs = QTabWidget()

        # TABS
        self.plan_tab = PlanTab()
        self.workout_tab = WorkoutTab()
        self.weigh_in_tab = WeighInTab()
        self.nutrition_tab = NutritionTab()

        self.tabs.addTab(self.plan_tab, "Plan")
        self.tabs.addTab(self.workout_tab, "Workouts")
        self.tabs.addTab(self.weigh_in_tab, "Weigh-Ins")
        self.tabs.addTab(self.nutrition_tab, "Nutrition")

        self.setCentralWidget(self.tabs)

    def fade_in_animation(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(800)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

###############################################################################
# 7. APP ENTRY
###############################################################################

def main():
    # We create a brand-new DB "futuristic_tracker_v2.db" with the correct schema.
    initialize_db()

    app = QApplication(sys.argv)
    window = FuturisticFitnessTracker()
    window.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
