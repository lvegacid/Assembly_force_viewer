# -*- coding: utf-8 -*-
# Copilot: extend this GUI with a system selector and path manager
import sys
import os
import re
import json
import subprocess
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QFileDialog, QMessageBox, QInputDialog
)
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt


# =========================================================
# CONFIG
# =========================================================

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_SCRIPT_DIR, "systems_config.json")

DEFAULT_SYSTEMS = {
    "Next": r"Z:\Projects\PhysioII - NextMRI\Magnet\Forces\Estudio fuerzas montaje",
    "Preclinico": r"Z:\Projects\Preclinico\Estudio fuerzas montaje",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return dict(DEFAULT_SYSTEMS)


def save_config(systems):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(systems, f, indent=2, ensure_ascii=False)


# =========================================================
# VISOR CON ZOOM PERSISTENTE
# =========================================================

class ImageViewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.first_load = True

    def wheelEvent(self, event):
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 0.85
        self.scale(zoom_factor, zoom_factor)


# =========================================================
# MAIN VIEWER
# =========================================================

class StepViewer(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Visualizador Fuerzas Montaje")
        self.resize(1700, 1000)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.base_folder = None
        self.lids_available = False

        # =======================
        # SYSTEM SELECTOR
        # =======================

        self._systems = load_config()
        self._updating_system = False

        system_layout = QHBoxLayout()

        self.system_selector = QComboBox()
        self.system_selector.addItem("-- Select System --")
        for name in self._systems:
            self.system_selector.addItem(name)

        self.add_system_button = QPushButton("Add System")
        self.run_analysis_button = QPushButton("Run Force Assembly Analysis")

        system_layout.addWidget(QLabel("System:"))
        system_layout.addWidget(self.system_selector)
        system_layout.addWidget(self.add_system_button)
        system_layout.addWidget(self.run_analysis_button)
        system_layout.addStretch()

        self.layout.addLayout(system_layout)

        # =======================
        # SELECTOR CARPETA
        # =======================

        folder_layout = QHBoxLayout()

        self.folder_display = QLabel("No seleccionada")
        self.browse_button = QPushButton("Browse")

        folder_layout.addWidget(QLabel("Carpeta base:"))
        folder_layout.addWidget(self.folder_display)
        folder_layout.addWidget(self.browse_button)

        self.layout.addLayout(folder_layout)
        self.browse_button.clicked.connect(self.select_base_folder)

        # =======================
        # STEP + SELECTORES
        # =======================

        top_layout = QHBoxLayout()

        self.prev_button = QPushButton("⬅")
        self.next_button = QPushButton("➡")
        self.step_selector = QComboBox()

        self.plot_selector = QComboBox()
        self.plot_selector.addItems([
            "Fx", "Fy", "Fz", "NormF",
            "Tx", "Ty", "Tz", "NormT"
        ])

        # -------- LIDS SELECTOR (OCULTO POR DEFECTO) --------

        self.lids_selector = QComboBox()
        self.lids_selector.addItem("Lids-Visualization OFF")
        self.lids_selector.addItems([
            "Fx_Lids", "Fy_Lids", "Fz_Lids", "NormF_Lids",
            "Tx_Lids", "Ty_Lids", "Tz_Lids", "NormT_Lids"
        ])
        self.lids_selector.setVisible(False)

        top_layout.addWidget(self.prev_button)
        top_layout.addWidget(self.step_selector)
        top_layout.addWidget(self.next_button)
        top_layout.addWidget(self.plot_selector)
        top_layout.addWidget(self.lids_selector)

        self.layout.addLayout(top_layout)

        # =======================
        # WORST CASE
        # =======================

        worst_layout = QHBoxLayout()

        self.metric_type = QComboBox()
        self.metric_type.addItems(["SumPerRing", "PerCube", "Mounting_Ring"])

        self.metric_component = QComboBox()
        self.metric_component.addItems([
            "Fx", "Fy", "Fz", "normF",
            "Tx", "Ty", "Tz", "normT"
        ])

        self.worst_button = QPushButton("Find Worst Step")
        self.worst_result = QLabel("")

        worst_layout.addWidget(QLabel("Worst case:"))
        worst_layout.addWidget(self.metric_type)
        worst_layout.addWidget(self.metric_component)
        worst_layout.addWidget(self.worst_button)
        worst_layout.addWidget(self.worst_result)

        self.layout.addLayout(worst_layout)

        # =======================
        # RESET ZOOM
        # =======================

        self.reset_zoom_button = QPushButton("Reset Zoom")
        self.layout.addWidget(self.reset_zoom_button)
        
        self.reset_view_button = QPushButton("Reset View")
        self.layout.addWidget(self.reset_view_button)
        # =======================
        # IMAGEN
        # =======================

        self.viewer = ImageViewer()
        self.layout.addWidget(self.viewer)

        # =======================
        # TABLA
        # =======================

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        # Conexiones
        self.prev_button.clicked.connect(self.go_previous)
        self.next_button.clicked.connect(self.go_next)
        self.step_selector.currentIndexChanged.connect(self.update_view)
        self.plot_selector.currentIndexChanged.connect(self.update_view)
        self.lids_selector.currentIndexChanged.connect(self.update_view)
        self.worst_button.clicked.connect(self.compute_worst_case)
        self.reset_zoom_button.clicked.connect(self.reset_zoom)
        self.reset_view_button.clicked.connect(self.reset_view)
        self.system_selector.currentIndexChanged.connect(self.on_system_selected)
        self.add_system_button.clicked.connect(self.on_add_system)
        self.run_analysis_button.clicked.connect(self.on_run_analysis)
        


    # =========================================================
    def reset_view(self):

        if not self.base_folder:
            return

        # Ir al primer Step
        if self.step_selector.count() > 0:
            self.step_selector.setCurrentIndex(0)

        # Primer plot
        self.plot_selector.setCurrentIndex(0)

        # Desactivar Lids
        if self.lids_available:
            self.lids_selector.setCurrentIndex(0)

        # Limpiar worst case
        self.worst_result.setText("")

        # Reset zoom
        self.viewer.resetTransform()
        self.viewer.first_load = True

        # Forzar actualización
        self.update_view()

    def select_base_folder(self):

        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", "")

        if folder:
            self.base_folder = folder
            self.folder_display.setText(folder)
            self.load_steps()

    # =========================================================

    def load_steps(self):

        self.step_selector.clear()

        if not self.base_folder:
            return

        steps = [
            f for f in os.listdir(self.base_folder)
            if os.path.isdir(os.path.join(self.base_folder, f))
            and f.startswith("Step")
        ]

        def extract_num(name):
            match = re.search(r"Step(\d+)", name)
            return int(match.group(1)) if match else -1

        steps_sorted = sorted(steps, key=extract_num)
        self.step_selector.addItems(steps_sorted)

        # ===== Detectar Lids =====
        self.lids_available = False

        for step in steps_sorted:
            test_path = os.path.join(
                self.base_folder,
                step,
                f"{step}_TableForceTorqueSum_perLid.txt"
            )
            if os.path.exists(test_path):
                self.lids_available = True
                break

        self.lids_selector.setVisible(self.lids_available)

        if self.lids_available:
        
            new_metrics = ["PerLid", "PerLid+Y", "PerLid-Y", "PerLid+Z", "PerLid-Z"]
        
            for m in new_metrics:
                if m not in [self.metric_type.itemText(i) for i in range(self.metric_type.count())]:
                    self.metric_type.addItem(m)

        if steps_sorted:
            self.update_view()

    # =========================================================

    def go_previous(self):
        i = self.step_selector.currentIndex()
        if i > 0:
            self.step_selector.setCurrentIndex(i - 1)

    def go_next(self):
        i = self.step_selector.currentIndex()
        if i < self.step_selector.count() - 1:
            self.step_selector.setCurrentIndex(i + 1)

    # =========================================================

    def reset_zoom(self):
        self.viewer.resetTransform()
        self.viewer.first_load = True
        self.update_view()

    # =========================================================

    def update_view(self):

        if not self.base_folder:
            return

        step = self.step_selector.currentText()
        plot = self.plot_selector.currentText()
        lids_plot = self.lids_selector.currentText()

        step_path = os.path.join(self.base_folder, step)

        # =======================
        # CARGAR IMAGEN
        # =======================

        if self.lids_available and lids_plot != "Lids-Visualization OFF":
            image_path = os.path.join(step_path, f"{step}_{lids_plot}.png")
        else:
            image_path = os.path.join(step_path, f"{step}_{plot}.png")

        self.viewer.scene().clear()

        if os.path.exists(image_path):

            pixmap = QPixmap(image_path)
            item = QGraphicsPixmapItem(pixmap)
            self.viewer.scene().addItem(item)
            self.viewer.setSceneRect(item.boundingRect())

            if self.viewer.first_load:
                self.viewer.fitInView(item, Qt.KeepAspectRatio)
                self.viewer.first_load = False

        # =======================
        # TABLA NORMAL O LIDS
        # =======================

        if self.lids_available and lids_plot != "Lids-Visualization OFF":

            table_path = os.path.join(
                step_path,
                f"{step}_TableForceTorqueSum_perLid.txt"
            )

            if os.path.exists(table_path):

                df = pd.read_csv(table_path, sep="\t")

                df[["Ring","Lid"]] = df["Ring_Lid"].str.extract(r"Ring(\d+)_(.*)")
                df["Ring"] = df["Ring"].astype(int)

                component = lids_plot.replace("_Lids","")

                col_map = {
                    "Fx":"Fx_sum",
                    "Fy":"Fy_sum",
                    "Fz":"Fz_sum",
                    "NormF":"normF",
                    "Tx":"Tx_sum",
                    "Ty":"Ty_sum",
                    "Tz":"Tz_sum",
                    "NormT":"normT"
                }

                value_col = col_map[component]

                pivot = df.pivot(index="Ring", columns="Lid", values=value_col)

                self.table.setRowCount(len(pivot))
                self.table.setColumnCount(len(pivot.columns))
                self.table.setHorizontalHeaderLabels(pivot.columns.astype(str))

                for i, ring in enumerate(pivot.index):
                    for j, lid in enumerate(pivot.columns):
                        val = pivot.loc[ring, lid]
                        item = QTableWidgetItem(f"{val:.2f}")
                        self.table.setItem(i, j, item)

                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

                max_val = pivot.abs().values.max()

                for i in range(len(pivot.index)):
                    for j in range(len(pivot.columns)):
                        if abs(pivot.iloc[i,j]) == max_val:
                            self.table.item(i,j).setBackground(QColor(255,100,100))

        else:

            table_path = os.path.join(
                step_path,
                f"{step}_TableForceTorqueSum_perRing.txt"
            )

            if os.path.exists(table_path):

                df = pd.read_csv(table_path, sep="\t", decimal=",")

                df_display = df.copy()

                # Add final summary row with per-component totals
                sum_row = {}
                for col in df_display.columns:
                    if col == "Ring":
                        sum_row[col] = "Sum"
                    else:
                        numeric_col = pd.to_numeric(df_display[col], errors='coerce')
                        sum_row[col] = numeric_col.sum()

                df_display = pd.concat([df_display, pd.DataFrame([sum_row])], ignore_index=True)

                self.table.setRowCount(len(df_display))
                self.table.setColumnCount(len(df_display.columns))
                self.table.setHorizontalHeaderLabels(df_display.columns)

                for i in range(len(df_display)):
                    for j in range(len(df_display.columns)):
                        value = df_display.iloc[i, j]
                        if i == len(df_display) - 1 and j > 0:
                            item = QTableWidgetItem(f"{float(value):.6g}")
                        else:
                            item = QTableWidgetItem(str(value))
                        if i == len(df_display) - 1:
                            item.setBackground(QColor(230, 230, 230))
                        self.table.setItem(i, j, item)

                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

                for col in range(1, len(df.columns)):

                    col_values = pd.to_numeric(df.iloc[:, col], errors='coerce')
                    max_val = col_values.abs().max()

                    for row in range(len(df)):
                        value = pd.to_numeric(df.iloc[row, col], errors='coerce')
                        if abs(value) == max_val:
                            self.table.item(row, col).setBackground(QColor(255, 100, 100))

    # =========================================================

    def compute_worst_case(self):

        worst_file = os.path.join(self.base_folder, "WorstCases_Global.txt")

        if not os.path.exists(worst_file):
            self.worst_result.setText("No existe WorstCases_Global.txt")
            return

        df = pd.read_csv(worst_file, sep="\t")

        metric = self.metric_type.currentText()
        component = self.metric_component.currentText()

        row = df[df["Component"] == component]

        if row.empty:
            return

        if component.lower() == "normf":
            plot_name = "NormF"
        elif component.lower() == "normt":
            plot_name = "NormT"
        else:
            plot_name = component            

        # ===============================
        # PER LID (GLOBAL + SUBDIVISIONES)
        # ===============================
        
        if metric.startswith("PerLid"):
        
            if metric == "PerLid":
                step_col = "PerLid_Step"
                value_col = "PerLid_Value"
            else:
                suffix = metric.replace("PerLid", "")
                step_col = f"PerLid{suffix}_Step"
                value_col = f"PerLid{suffix}_Value"
        
            step = row[step_col].values[0]
            value = row[value_col].values[0]
        
            self.worst_result.setText(
                f"Worst {metric} → {step} | {component} = {value:.2f}"
            )
        
            self.step_selector.setCurrentText(step)
            self.lids_selector.setCurrentText(f"{plot_name}_Lids")
        
            return

        elif metric == "SumPerRing":

            step = row["SumPerRing_Step"].values[0]
            value = row["SumPerRing_Value"].values[0]

            self.worst_result.setText(
                f"Worst SumPerRing → {step} | {component} = {value:.2f}"
            )

        elif metric == "PerCube":

            step = row["PerCube_Step"].values[0]
            value = row["PerCube_Value"].values[0]

            self.worst_result.setText(
                f"Worst PerCube → {step} | {component} = {value:.2f}"
            )

        elif metric == "Mounting_Ring":

            step = row["MountingRing_Step"].values[0]
            value = row["MountingRing_Value"].values[0]

            self.worst_result.setText(
                f"Worst Mounting Ring → {step} | {component} = {value:.2f}"
            )

        self.step_selector.setCurrentText(step)
        self.plot_selector.setCurrentText(plot_name)


    # =========================================================
    # SYSTEM MANAGEMENT
    # =========================================================

    def on_system_selected(self, index):
        """Called when the system dropdown changes."""
        if self._updating_system:
            return
        if index < 0 or self.system_selector.count() == 0:
            return

        name = self.system_selector.currentText()
        if not name or name == "-- Select System --":
            return

        path = self._systems.get(name, "")

        if not os.path.isdir(path):
            msg = QMessageBox(self)
            msg.setWindowTitle("Path not found")
            msg.setText(
                f"Path not found:\n{path}\n\nWould you like to browse for a new folder?"
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            ret = msg.exec_()

            if ret == QMessageBox.Yes:
                new_path = QFileDialog.getExistingDirectory(
                    self, f"Select folder for '{name}'", ""
                )
                if new_path:
                    self._systems[name] = new_path
                    save_config(self._systems)
                    path = new_path
                else:
                    return
            else:
                return

        self.base_folder = path
        self.folder_display.setText(path)

        # Check that Step* subfolders exist
        steps = [
            f for f in os.listdir(path)
            if os.path.isdir(os.path.join(path, f)) and f.startswith("Step")
        ]

        if not steps:
            QMessageBox.information(
                self,
                "Analysis not found",
                "Required analysis folders not found. Press 'Run Force Assembly Analysis'."
            )
            return

        self.load_steps()

    def on_add_system(self):
        """Prompt for a new system name and folder, then persist it."""
        name, ok = QInputDialog.getText(self, "Add System", "System name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        path = QFileDialog.getExistingDirectory(
            self, f"Select folder for '{name}'", ""
        )
        if not path:
            return

        self._updating_system = True
        self._systems[name] = path
        save_config(self._systems)

        already_present = any(
            self.system_selector.itemText(i) == name
            for i in range(self.system_selector.count())
        )
        if not already_present:
            self.system_selector.addItem(name)

        self._updating_system = False

        QMessageBox.information(
            self,
            "System added",
            f"System '{name}' saved.\nPath: {path}"
        )

    def on_run_analysis(self):
        """Run Force_extractor_assembly.py in the selected system folder."""
        if not self.base_folder:
            QMessageBox.warning(self, "No system", "Please select a system first.")
            return

        script_path = os.path.join(_SCRIPT_DIR, "Force_extractor_assembly.py")
        if not os.path.exists(script_path):
            QMessageBox.critical(
                self,
                "Script not found",
                f"Could not find:\n{script_path}"
            )
            return

        reply = QMessageBox.question(
            self,
            "Run analysis",
            f"Run Force Assembly Analysis for:\n{self.base_folder}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        lids_reply = QMessageBox.question(
            self,
            "Include Lids",
            "Include Lids?",
            QMessageBox.Yes | QMessageBox.No
        )
        include_lids = (lids_reply == QMessageBox.Yes)

        try:
            cmd = [
                sys.executable, script_path,
                "--base_folder", self.base_folder,
                "--magnet_info", self.system_selector.currentText(),
            ]
            if include_lids:
                cmd.append("--include_lids")

            result = subprocess.run(
                cmd,
                cwd=self.base_folder,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                QMessageBox.information(self, "Done", "Analysis done.")
                # Reload steps after successful analysis
                self.on_system_selected(self.system_selector.currentIndex())
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Analysis failed (exit code {result.returncode}).\n\n"
                    + result.stderr[-2000:]
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# =========================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = StepViewer()
    viewer.show()
    sys.exit(app.exec_())