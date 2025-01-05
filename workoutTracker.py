import sys
import sqlite3
from datetime import datetime

# Make sure we import QEasingCurve so we can use setEasingCurve(QEasingCurve.InOutQuad)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
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
    QPushButton,
    QFormLayout,
    QDialogButtonBox,
    QDialog,
    QToolButton,
    QMenu
)
from PySide6.QtGui import QFontDatabase

###############################################################################
# 1. DATABASE & UTILS
###############################################################################

DB_NAME = "futuristic_tracker_v6.db"

def initialize_db():
    """
    Creates the necessary tables in a brand-new DB.
    We'll store weigh_ins with (id, date, weight, height, bmi).
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # workouts
    c.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            workout_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL
        );
    """)

    # exercises
    c.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            FOREIGN KEY (workout_id) REFERENCES workouts(workout_id)
        );
    """)

    # sets (exercise_id + set_number)
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

    # weigh_ins: includes height + bmi
    c.execute("""
        CREATE TABLE IF NOT EXISTS weigh_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            weight FLOAT NOT NULL,
            height FLOAT NOT NULL,
            bmi FLOAT NOT NULL
        );
    """)

    # nutrition_log
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
# 3. PLAN DATA (Hard-coded, no CRUD)
###############################################################################
WORKOUT_PLAN = {
    "Day 1: Back & Biceps (Pull 1)": [
        "Neutral Grip Pull-Ups – 4 sets (8-12 reps)",
        "Pronated Pull-Ups – 3 sets (6-10 reps)",
        "Cable Rows (Wide-Grip) – 4 sets (10-12 reps)",
        "Lat Pullovers – 3 sets (12-15 reps)",
        "EZ Bar Curls – 4 sets (10-12 reps)",
        "Hammer Curls – 3 sets (10-12 reps)",
        "Incline Dumbbell Curls – 3 sets (12-15 reps)",
    ],
    "Day 2: Chest & Triceps (Push 1)": [
        "Incline Machine Press – 4 sets (8-12 reps)",
        "Flat Machine Bench Press – 4 sets (8-12 reps)",
        "Low to High Cable Flies – 3 sets (12-15 reps)",
        "Chest Dips – 3 sets (8-12 reps)",
        "Overhead Triceps Extension – 4 sets (10-12 reps)",
        "Cable Pushdowns – 4 sets (10-12 reps)",
        "Triceps Dips (Bodyweight or Weighted) – 3 sets (8-12 reps)",
    ],
    "Day 3: Legs (Legs 1)": [
        "Smith Machine Squats – 4 sets (8-12 reps)",
        "Hack Squat Machine – 4 sets (10-12 reps)",
        "Leg Press – 4 sets (10-15 reps)",
        "Leg Curls (Prone) – 3 sets (12-15 reps)",
        "Leg Extensions – 3 sets (12-15 reps)",
        "Seated Calf Raises – 4 sets (15-20 reps, slow eccentric)",
    ],
    "Day 4: Rest/Active Recovery": [
        "Light cardio (15-20 minutes)",
        "Dynamic stretching",
        "Foam rolling or yoga",
    ],
    "Day 5: Back, Biceps & Rear Delts (Pull 2)": [
        "Neutral Grip Pull-Ups – 4 sets (8-12 reps)",
        "One-Arm Dumbbell Rows – 3 sets (8-12 reps)",
        "Cable Rows (Close-Grip) – 4 sets (10-12 reps)",
        "Lat Pullovers – 3 sets (12-15 reps)",
        "Straight Bar Curls – 4 sets (10-12 reps)",
        "Reverse Grip Curls – 3 sets (12-15 reps)",
        "Rear Delt Flies (Machine) – 3 sets (12-15 reps)",
    ],
    "Day 6: Shoulders, Chest & Triceps (Push 2)": [
        "Machine Shoulder Press – 4 sets (8-12 reps)",
        "Dumbbell Lateral Flies – 3 sets (12-15 reps)",
        "Cable Side Lateral Flies (Single Arm) – 3 sets (12-15 reps)",
        "Rear Delt Flies (Machine) – 3 sets (12-15 reps)",
        "Chest Pullovers – 3 sets (10-12 reps)",
        "Overhead Dumbbell Triceps Extension – 3 sets (10-12 reps)",
        "Dumbbell Shrugs – 3 sets (15-20 reps for traps)",
    ],
    "Day 7: Rest/Active Recovery": [
        "Light stretching or mobility drills",
        "Gentle cardio (e.g., cycling or swimming)",
    ],
}

###############################################################################
# 4. PLAN TAB (Checklists + "Add to Workouts")
###############################################################################

class AddPlanExercisesDialog(QDialog):
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(10)

        self.day_combo = QComboBox()
        day_list = list(WORKOUT_PLAN.keys())
        self.day_combo.addItems(day_list)
        self.day_combo.currentIndexChanged.connect(self.on_day_changed)
        self.main_layout.addWidget(QLabel("Select a Day:"))
        self.main_layout.addWidget(self.day_combo)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.ex_container = QWidget()
        self.ex_layout = QVBoxLayout(self.ex_container)
        self.ex_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.ex_container)
        self.main_layout.addWidget(self.scroll_area)

        self.add_button = QPushButton("Add to Workouts")
        self.add_button.clicked.connect(self.on_add_to_workouts)
        self.main_layout.addWidget(self.add_button)

        self.setLayout(self.main_layout)
        self.populate_exercises(self.day_combo.currentText())

    def on_day_changed(self):
        day_key = self.day_combo.currentText()
        self.populate_exercises(day_key)

    def populate_exercises(self, day_key):
        for i in reversed(range(self.ex_layout.count())):
            item = self.ex_layout.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)

        ex_list = WORKOUT_PLAN.get(day_key, [])
        for ex_name in ex_list:
            checkbox = QCheckBox(ex_name)
            self.ex_layout.addWidget(checkbox)

    def on_add_to_workouts(self):
        checked_exercises = []
        for i in range(self.ex_layout.count()):
            item = self.ex_layout.itemAt(i)
            if not item:
                continue
            widget = item.widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                checked_exercises.append(widget.text())

        if not checked_exercises:
            QMessageBox.information(self,"No Selection","No exercises checked.")
            return

        dialog = AddPlanExercisesDialog(self)
        if dialog.exec() == QDialog.Accepted:
            date_str, reps_val, weight_val = dialog.get_data()
            for ex_name in checked_exercises:
                self.insert_exercise_to_db(date_str, ex_name, reps_val, weight_val)
            QMessageBox.information(self,"Success",
                f"Added {len(checked_exercises)} exercise(s) to your Workouts!")

    def insert_exercise_to_db(self, date_str, ex_name, reps, weight):
        conn = get_connection()
        c = conn.cursor()
        # get/create workout
        c.execute("SELECT workout_id FROM workouts WHERE date=?",(date_str,))
        row = c.fetchone()
        if row:
            w_id = row[0]
        else:
            c.execute("INSERT INTO workouts (date) VALUES (?)",(date_str,))
            w_id = c.lastrowid

        # get/create exercise
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

        # find max set_number
        c.execute("""
            SELECT COALESCE(MAX(set_number),0)
            FROM sets
            WHERE exercise_id=?
        """,(e_id,))
        max_sn = c.fetchone()[0]
        new_sn = max_sn+1

        # insert
        c.execute("""
            INSERT INTO sets (exercise_id, set_number, reps, weight)
            VALUES (?,?,?,?)
        """,(e_id, new_sn, reps, weight))
        conn.commit()
        conn.close()

###############################################################################
# 5. WORKOUT TAB: "Delete" Buttons (Bin icon) + Refresh
###############################################################################

class WorkoutTab(QWidget):
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

        # Refresh
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_sets)
        main_layout.addWidget(btn_refresh)

        # Table: columns => date, exercise, set#, reps, weight, delete
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Date","Exercise","Set #","Reps","Weight","Delete"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(QLabel("Recent Sets (Latest 10)"))
        main_layout.addWidget(self.table)

        self.setLayout(main_layout)
        self.load_sets()

    def load_sets(self):
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

            # Bin button to delete
            bin_button = QPushButton("🗑")  # or an icon if you prefer
            bin_button.setStyleSheet("QPushButton { font-size: 16px; }")
            bin_button.clicked.connect(lambda _, e_id=exercise_id, s_n=set_num: self.delete_set(e_id, s_n))
            self.table.setCellWidget(i, 5, bin_button)

    def add_set(self):
        date_str = self.date_input.text().strip() or today_str()
        ex_name = self.exercise_input.text().strip()
        reps_val = self.reps_input.value()
        weight_val = self.weight_input.value()

        if not ex_name:
            QMessageBox.warning(self, "Error", "Exercise cannot be empty.")
            return

        conn = get_connection()
        c = conn.cursor()
        # get/create workout
        c.execute("SELECT workout_id FROM workouts WHERE date=?",(date_str,))
        w_row = c.fetchone()
        if w_row:
            w_id = w_row[0]
        else:
            c.execute("INSERT INTO workouts (date) VALUES (?)",(date_str,))
            w_id = c.lastrowid

        # get/create exercise
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

        # find max set_number
        c.execute("""
            SELECT COALESCE(MAX(set_number),0)
            FROM sets
            WHERE exercise_id=?
        """,(e_id,))
        max_sn = c.fetchone()[0]
        new_sn = max_sn+1

        # insert
        c.execute("""
            INSERT INTO sets (exercise_id, set_number, reps, weight)
            VALUES (?,?,?,?)
        """,(e_id, new_sn, reps_val, weight_val))
        conn.commit()
        conn.close()

        self.exercise_input.clear()
        self.reps_input.setValue(10)
        self.weight_input.setValue(100.0)
        self.load_sets()

    def delete_set(self, e_id, s_n):
        ret = QMessageBox.question(
            self,"Confirm Delete",
            f"Delete set: exercise_id={e_id}, set_number={s_n}?",
            QMessageBox.Yes|QMessageBox.No,
            QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                DELETE FROM sets
                WHERE exercise_id=? AND set_number=?
            """,(e_id,s_n))
            conn.commit()
            conn.close()
            self.load_sets()

###############################################################################
# 6. WEIGH-IN TAB: now with a bin button for each row
###############################################################################

class WeighInTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout()

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Date (YYYY-MM-DD), blank=Today")

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0, 1000)
        self.weight_input.setSingleStep(0.5)
        self.weight_input.setValue(70.0)

        self.height_input = QDoubleSpinBox()
        self.height_input.setRange(100, 250)
        self.height_input.setValue(170.0)

        btn_log = QPushButton("Log Weight & BMI")
        btn_log.clicked.connect(self.log_weight_and_bmi)

        main_layout.addWidget(QLabel("Log Weigh-In"))
        main_layout.addWidget(QLabel("Date:"))
        main_layout.addWidget(self.date_input)
        main_layout.addWidget(QLabel("Weight (kg):"))
        main_layout.addWidget(self.weight_input)
        main_layout.addWidget(QLabel("Height (cm):"))
        main_layout.addWidget(self.height_input)
        main_layout.addWidget(btn_log)

        # Table: date, weight, height, bmi, delete
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date","Weight","Height","BMI","Delete"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        main_layout.addWidget(QLabel("Weigh-In History (Latest 10)"))
        main_layout.addWidget(self.table)
        self.setLayout(main_layout)
        self.load_weigh_ins()

    def load_weigh_ins(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, date, weight, height, bmi
            FROM weigh_ins
            ORDER BY date DESC
            LIMIT 10;
        """)
        rows = c.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            w_id, date_val, w_kg, h_val, b_val = row
            self.table.setItem(i, 0, QTableWidgetItem(date_val))
            self.table.setItem(i, 1, QTableWidgetItem(str(w_kg)))
            self.table.setItem(i, 2, QTableWidgetItem(str(h_val)))
            self.table.setItem(i, 3, QTableWidgetItem(str(b_val)))

            # Bin button to delete
            bin_button = QPushButton("🗑")
            bin_button.setStyleSheet("QPushButton { font-size: 16px; }")
            bin_button.clicked.connect(lambda _, w_id_=w_id: self.delete_weigh_in(w_id_))
            self.table.setCellWidget(i, 4, bin_button)

    def log_weight_and_bmi(self):
        date_str = self.date_input.text().strip() or today_str()
        w_kg = self.weight_input.value()
        h_cm = self.height_input.value()
        if h_cm>0:
            h_m = h_cm/100.0
            bmi = round(w_kg/(h_m**2),2)
        else:
            bmi=0

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO weigh_ins (date, weight, height, bmi)
            VALUES (?,?,?,?)
        """,(date_str,w_kg,h_cm,bmi))
        conn.commit()
        conn.close()

        self.date_input.clear()
        self.load_weigh_ins()

    def delete_weigh_in(self, w_id):
        ret = QMessageBox.question(
            self,"Confirm Delete",
            f"Delete weigh-in #{w_id}?",
            QMessageBox.Yes|QMessageBox.No,
            QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM weigh_ins WHERE id=?",(w_id,))
            conn.commit()
            conn.close()
            self.load_weigh_ins()

###############################################################################
# 7. NUTRITION TAB
###############################################################################

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
        layout.addWidget(QLabel("Date:"))
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
            INSERT INTO nutrition_log (date, calories, protein, carbs, fat)
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
# 8. MAIN WINDOW
###############################################################################

class FuturisticFitnessTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Futuristic Fitness Tracker (v6)")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet(FUTURISTIC_QSS)

        self.setWindowOpacity(0.0)
        self.fade_in_animation()

        self.tabs = QTabWidget()

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
# 9. APPLICATION ENTRY
###############################################################################

def main():
    # Create a brand-new DB with the weigh_ins table that has (id, date, weight, height, bmi)
    initialize_db()

    app = QApplication(sys.argv)
    window = FuturisticFitnessTracker()
    window.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
