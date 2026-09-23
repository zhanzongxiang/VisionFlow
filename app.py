from __future__ import annotations

import json
import os
import copy
import importlib.util
import math
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unicodedata
import uuid
from pathlib import Path
from typing import Any, NamedTuple

from PySide6.QtCore import QObject, QPoint, QPointF, QRect, QRectF, QSize, QSettings, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QBrush, QColor, QCloseEvent, QCursor, QFont, QFontDatabase, QIcon, QImage, QKeySequence, QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap, QPolygonF, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QListView,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QSplitter,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QTextEdit,
    QToolBar,
    QTabWidget,
    QComboBox,
    QCheckBox,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "识动 VisionFlow"
APP_VERSION = "0.1.0-beta.1"
SCRIPT_VERSION = 4
APP_STYLESHEET = """
QMainWindow, QDialog {
    background: #0e1116;
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 9pt;
}
QToolBar {
    background: #15181d;
    border: none;
    border-bottom: 1px solid #292e36;
    padding: 7px 14px;
    spacing: 4px;
}
QToolBar::separator {
    background: #303640;
    width: 1px;
    margin: 7px 7px;
}
QToolBar QToolButton {
    color: #cbd2dc;
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 7px 9px;
}
QToolBar QToolButton:hover {
    color: #ffffff;
    background: #242a32;
}
QToolBar QToolButton:pressed {
    background: #2d343e;
}
QPushButton {
    color: #d8dee8;
    background: #20252c;
    border: 1px solid #343b45;
    border-radius: 4px;
    padding: 6px 11px;
}
QPushButton:hover {
    color: #ffffff;
    background: #292f38;
    border-color: #4a5360;
}
QPushButton:pressed {
    background: #171b20;
}
QPushButton:disabled {
    color: #5e6671;
    background: #171a1f;
    border-color: #252a31;
}
QMenu {
    background: #1b1f25;
    color: #dce2ea;
    border: 1px solid #343b45;
    padding: 5px;
}
QMenu::item {
    padding: 7px 26px 7px 12px;
    border-radius: 3px;
}
QMenu::item:selected {
    background: #315fa8;
    color: #ffffff;
}
QToolTip {
    color: #f1f4f8;
    background: #22272f;
    border: 1px solid #414955;
    padding: 5px 7px;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #111419;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #3a414b;
    border-radius: 4px;
    min-height: 24px;
    min-width: 24px;
}
QScrollBar::handle:hover {
    background: #505966;
}
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
    border: none;
}
QToolBar QPushButton {
    color: #dce2ea;
    background: #20252c;
    border: 1px solid #343b45;
    border-radius: 4px;
    padding: 6px 11px;
    min-height: 18px;
}
QToolBar QPushButton:hover {
    background: #292f38;
    border-color: #4a5360;
}
QToolBar QPushButton:pressed {
    background: #171b20;
}
QToolBar QPushButton:disabled {
    color: #5e6671;
    background: #171a1f;
    border-color: #252a31;
}
QToolBar #runButton {
    color: #ffffff;
    background: #356fd3;
    border-color: #5b91ed;
    font-weight: 600;
}
QToolBar #runButton:hover {
    background: #427fe2;
    border-color: #79a6f2;
}
QToolBar #stopButton {
    color: #f08a96;
    background: #241b20;
    border-color: #6d3741;
    font-weight: 600;
}
QToolBar #stopButton:hover {
    color: #ffabb4;
    background: #352027;
    border-color: #a94b5a;
}
QToolBar #recordMacroButton {
    color: #e7bd76;
    background: #29231a;
    border-color: #68512b;
    font-weight: 600;
}
QToolBar #recordMacroButton:hover {
    background: #393022;
    border-color: #9b7132;
}
QToolBar #recordMacroButton:checked {
    color: #ffffff;
    background: #b66a2d;
    border-color: #e5a15f;
}
QSplitter {
    background: #0e1116;
}
QSplitter::handle {
    background: #292e36;
}
QGraphicsView#flowCanvas {
    background: #111419;
    border: 1px solid #2c323a;
    border-radius: 5px;
}
QLabel#sectionTitle {
    color: #f0f3f7;
    font-size: 16px;
    font-weight: 700;
    padding: 0 0 2px 1px;
}
QLabel#fixedModeLabel {
    color: #78d5aa;
    background: #15271f;
    border: 1px solid #315c47;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: 600;
}
QLabel {
    color: #9da7b3;
}
QListWidget {
    background: #13161b;
    alternate-background-color: #171b21;
    color: #cfd6df;
    border: 1px solid #2b3038;
    border-radius: 4px;
    padding: 4px;
    outline: none;
}
QListWidget::item {
    color: #c5ccd6;
    padding: 9px 10px;
    border-radius: 3px;
    margin: 2px 1px;
}
QListWidget::item:hover {
    background: #20252c;
}
QListWidget::item:selected {
    color: #ffffff;
    background: #253a5a;
    border: 1px solid #477dce;
}
QListWidget:disabled, QTableWidget:disabled, QTextEdit:disabled {
    color: #5e6671;
    background: #12151a;
    border-color: #252a31;
}
QGroupBox {
    background: #161a20;
    color: #e6ebf1;
    border: 1px solid #2c323a;
    border-radius: 5px;
    margin-top: 12px;
    padding: 17px 13px 13px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    color: #dce2ea;
    padding: 0 7px;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #101318;
    color: #e6ebf1;
    border: 1px solid #343b45;
    border-radius: 4px;
    padding: 6px 8px;
    selection-background-color: #356fd3;
    selection-color: #ffffff;
}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #4a5360;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #5b91ed;
}
QComboBox::drop-down {
    width: 26px;
    border: none;
}
QComboBox QAbstractItemView {
    background: #1b1f25;
    color: #e1e6ed;
    border: 1px solid #3a424d;
    selection-background-color: #315fa8;
    selection-color: #ffffff;
}
QTableWidget {
    background: #111419;
    alternate-background-color: #171b21;
    color: #cdd4dd;
    border: 1px solid #2c323a;
    border-radius: 4px;
    selection-background-color: #315fa8;
    selection-color: #ffffff;
    gridline-color: #252a31;
}
QTableWidget::item {
    padding: 5px 7px;
}
QTableWidget QHeaderView::section {
    background: #1c2026;
    color: #aeb7c2;
    border: none;
    border-bottom: 1px solid #343b45;
    padding: 6px 7px;
    font-weight: 600;
}
QTableWidget:disabled {
    color: #5e6671;
}
QCheckBox {
    color: #bac2cc;
    spacing: 7px;
}
#capturePositionButton, #recordDragButton, #probeWindowButton {
    color: #8fb7fa;
    background: #182236;
    border: 1px solid #365583;
    border-radius: 4px;
    padding: 6px 10px;
    font-weight: 600;
}
#capturePositionButton:hover, #recordDragButton:hover, #probeWindowButton:hover {
    color: #c4d9ff;
    background: #20304c;
    border-color: #527fc2;
}
QPushButton#taskAddButton,
QPushButton#taskSyncButton {
    color: #dce2ea;
    background: #20252c;
    border: 1px solid #343b45;
    border-radius: 4px;
    font-weight: 600;
}
QPushButton#taskAddButton:hover,
QPushButton#taskSyncButton:hover {
    background: #292f38;
    border-color: #4a5360;
}
QPushButton#taskDeleteButton,
QPushButton#taskClearStepsButton,
QPushButton#taskStopButton,
QPushButton#taskStopAllButton {
    color: #e9828f;
    background: #1f1a1e;
    border: 1px solid #58313a;
    border-radius: 4px;
    font-weight: 600;
}
QPushButton#taskDeleteButton:hover,
QPushButton#taskClearStepsButton:hover,
QPushButton#taskStopButton:hover,
QPushButton#taskStopAllButton:hover {
    color: #ffabb4;
    background: #332027;
    border-color: #914351;
}
QPushButton#taskRunButton {
    color: #ffffff;
    background: #356fd3;
    border: 1px solid #5b91ed;
    border-radius: 4px;
    font-weight: 600;
}
QPushButton#taskRunButton:hover {
    background: #427fe2;
    border-color: #79a6f2;
}
QPushButton#taskRunAllButton {
    color: #8edbb4;
    background: #18241f;
    border: 1px solid #335d49;
    border-radius: 4px;
    font-weight: 600;
}
QPushButton#taskRunAllButton:hover {
    color: #b3efcf;
    background: #203229;
    border-color: #4b8468;
}
QPushButton#taskWindowRefreshButton {
    color: #aeb7c2;
    background: #20252c;
    border: 1px solid #343b45;
    border-radius: 4px;
    padding: 5px;
}
QPushButton#taskWindowRefreshButton:hover {
    color: #ffffff;
    background: #292f38;
    border-color: #4a5360;
}
QPushButton#taskAddButton:disabled,
QPushButton#taskSyncButton:disabled,
QPushButton#taskDeleteButton:disabled,
QPushButton#taskClearStepsButton:disabled,
QPushButton#taskStopButton:disabled,
QPushButton#taskStopAllButton:disabled,
QPushButton#taskRunButton:disabled,
QPushButton#taskRunAllButton:disabled,
QPushButton#taskWindowRefreshButton:disabled {
    color: #5e6671;
    background: #171a1f;
    border-color: #252a31;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QStatusBar {
    background: #12151a;
    color: #7f8995;
    border-top: 1px solid #292e36;
}
QScrollArea {
    background: #13161b;
    border: 1px solid #2b3038;
}
#windowTasksPage {
    background: #0e1116;
}
#windowTasksPage QLabel#taskPageTitle {
    color: #f2f5f8;
    font-size: 17px;
    font-weight: 700;
    padding: 0;
}
#windowTasksPage QLabel#taskCountLabel {
    color: #8f99a6;
    background: #1a1e24;
    border: 1px solid #303640;
    border-radius: 4px;
    padding: 3px 8px;
}
#windowTasksPage QWidget#taskSidebar {
    background: #15181d;
    border: 1px solid #292e36;
    border-radius: 5px;
}
#windowTasksPage QLabel#taskListCaption,
#windowTasksPage QLabel#taskStepsCaption {
    color: #b8c0ca;
    font-size: 9pt;
    font-weight: 600;
    padding: 0;
}
#windowTasksPage QGroupBox {
    margin-top: 10px;
    padding: 16px 14px 13px;
    font-size: 9.5pt;
}
#windowTasksPage QGroupBox::title {
    padding: 0 7px;
}
#windowTasksPage QLabel {
    font-size: 9pt;
}
#windowTasksPage QLineEdit,
#windowTasksPage QComboBox,
#windowTasksPage QSpinBox,
#windowTasksPage QDoubleSpinBox {
    min-height: 27px;
    padding: 3px 8px;
    font-size: 9pt;
}
#windowTasksPage QCheckBox {
    font-size: 9pt;
    min-height: 25px;
}
#windowTasksPage QListWidget {
    background: transparent;
    alternate-background-color: #1a1e24;
    border: none;
    border-radius: 0;
    padding: 0;
    font-size: 9pt;
}
#windowTasksPage QListWidget::item {
    padding: 9px 10px;
    margin: 2px 0;
}
#windowTasksPage QPushButton {
    min-height: 28px;
    font-size: 9pt;
}
#windowTasksPage QLabel#taskStatusLabel {
    color: #aeb7c2;
    background: #1c2026;
    border: 1px solid #3a424d;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: 600;
}
#windowTasksPage QLabel#taskStatusLabel[state="running"] {
    color: #a8c7ff;
    background: #182236;
    border-color: #426aa6;
}
#windowTasksPage QLabel#taskStatusLabel[state="success"] {
    color: #8edbb4;
    background: #18271f;
    border-color: #38664f;
}
#windowTasksPage QLabel#taskStatusLabel[state="error"] {
    color: #f09aa4;
    background: #2b1c21;
    border-color: #70404a;
}
#windowTasksPage QSplitter::handle {
    background: #0e1116;
}
QTabWidget::pane {
    border: 1px solid #292e36;
    border-left: none;
    border-right: none;
    border-bottom: none;
    background: #0e1116;
}
QTabBar {
    background: #15181d;
}
QTabBar::tab {
    background: #15181d;
    color: #8f99a6;
    padding: 8px 18px;
    border: none;
    border-right: 1px solid #292e36;
}
QTabBar::tab:selected {
    background: #0e1116;
    color: #f0f3f7;
    font-weight: 600;
    border-top: 2px solid #5b91ed;
}
QTabBar::tab:hover {
    color: #dce2ea;
    background: #20252c;
}

/* Visual refresh: calm workbench hierarchy and clearer state semantics. */
QWidget {
    font-family: "Noto Sans SC", "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 9pt;
}
QMainWindow, QDialog {
    background: #101419;
}
QToolBar#mainToolbar {
    background: #171d23;
    border-bottom: 1px solid #2b353f;
    padding: 8px 16px;
    spacing: 6px;
    min-height: 42px;
}
QToolBar#mainToolbar QToolButton {
    color: #c6d0d9;
    border-radius: 6px;
    padding: 7px 10px;
}
QToolBar#mainToolbar QToolButton:hover {
    color: #f4f8fa;
    background: #27313a;
}
QToolBar#mainToolbar QPushButton {
    min-height: 27px;
    padding: 5px 12px;
    border-radius: 6px;
    background: #202930;
    border-color: #394650;
}
QToolBar#mainToolbar #runButton,
QPushButton#taskRunButton {
    color: #f4fffb;
    background: #2b9977;
    border-color: #51c39b;
    font-weight: 700;
}
QToolBar#mainToolbar #runButton:hover,
QPushButton#taskRunButton:hover {
    background: #36ad87;
    border-color: #71d5b3;
}
QToolBar#mainToolbar #stopButton,
QPushButton#taskStopButton,
QPushButton#taskStopAllButton,
QPushButton#taskDeleteButton,
QPushButton#taskClearStepsButton {
    color: #f1a4aa;
    background: #291e23;
    border-color: #69404a;
}
QToolBar#mainToolbar #stopButton:hover,
QPushButton#taskStopButton:hover,
QPushButton#taskStopAllButton:hover,
QPushButton#taskDeleteButton:hover,
QPushButton#taskClearStepsButton:hover {
    color: #ffd1d4;
    background: #39242b;
    border-color: #a85b68;
}
QToolBar#mainToolbar #recordMacroButton {
    color: #f0c98e;
    background: #2a241d;
    border-color: #745a32;
}
QToolBar#mainToolbar #recordMacroButton:checked {
    color: #fff8ec;
    background: #a96b35;
    border-color: #e3a565;
}
QPushButton#taskRunAllButton {
    color: #a9ead0;
    background: #1c322b;
    border-color: #39755f;
    font-weight: 700;
}
QPushButton#taskRunAllButton:hover {
    color: #d1f8e9;
    background: #25463a;
    border-color: #56a886;
}
QPushButton#taskAddButton,
QPushButton#taskSyncButton,
QPushButton#taskWindowRefreshButton {
    border-radius: 6px;
    background: #202930;
    border-color: #394650;
}
QPushButton#taskAddButton:hover,
QPushButton#taskSyncButton:hover,
QPushButton#taskWindowRefreshButton:hover {
    background: #2a353e;
    border-color: #53636f;
}
QPushButton#addButton,
QPushButton#deleteButton,
QPushButton#moveButton {
    border-radius: 6px;
}
QPushButton#capturePositionButton,
QPushButton#recordDragButton,
QPushButton#probeWindowButton {
    color: #9bdcc6;
    background: #19332c;
    border-color: #397b64;
    border-radius: 6px;
}
QPushButton#capturePositionButton:hover,
QPushButton#recordDragButton:hover,
QPushButton#probeWindowButton:hover {
    color: #d5f8eb;
    background: #25483c;
    border-color: #5ab694;
}
QSplitter {
    background: transparent;
}
QSplitter::handle {
    background: #101419;
}
QSplitter::handle:hover {
    background: #35434d;
}
#editorLeftPanel,
#editorRightPanel,
#windowTasksPage QWidget#taskSidebar {
    background: #151b21;
    border: 1px solid #29343e;
    border-radius: 10px;
}
#editorLeftPanel QLabel#sectionTitle,
#windowTasksPage QLabel#taskPageTitle {
    color: #f2f6f8;
    font-size: 19px;
    font-weight: 700;
    letter-spacing: 0.3px;
}
#editorHint,
#editorEmptyState,
#windowTasksPage QLabel#taskPageSubtitle,
#windowTasksPage QLabel#taskListHint {
    color: #82909b;
    font-size: 8pt;
}
#editorEmptyState {
    background: #151d23;
    border: 1px dashed #35434d;
    border-radius: 8px;
    min-height: 84px;
    padding: 16px;
    color: #71808b;
}
#windowTasksPage QLabel#taskListHint {
    padding-bottom: 2px;
}
#windowTasksPage QLabel#taskPageTitle {
    font-size: 21px;
}
#windowTasksPage QLabel#taskCountLabel {
    color: #a9dcca;
    background: #1a3029;
    border: 1px solid #366d59;
    border-radius: 12px;
    padding: 4px 11px;
    font-weight: 700;
}
QGroupBox#nodePropertiesPanel,
QGroupBox#logPanel,
#windowTasksPage QGroupBox {
    background: #1a2128;
    border: 1px solid #2b3741;
    border-radius: 9px;
    margin-top: 14px;
    padding: 18px 14px 14px;
}
QGroupBox#nodePropertiesPanel::title,
QGroupBox#logPanel::title,
#windowTasksPage QGroupBox::title {
    color: #d8e2e7;
    padding: 0 8px;
    font-weight: 700;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    min-height: 28px;
    background: #11171c;
    border: 1px solid #35424c;
    border-radius: 6px;
    padding: 5px 9px;
}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #53636f;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #58b999;
    background: #131c20;
}
QLabel {
    color: #9eabb5;
}
QCheckBox {
    color: #c1ccd3;
}
QListWidget {
    background: #11171c;
    border: 1px solid #2d3943;
    border-radius: 7px;
    padding: 5px;
}
QListWidget::item {
    color: #c7d1d8;
    padding: 10px 11px;
    border-radius: 6px;
    margin: 2px 0;
}
QListWidget::item:hover {
    background: #202b33;
}
QListWidget::item:selected {
    color: #f4fffb;
    background: #21463b;
    border: 1px solid #3e9f80;
}
QGraphicsView#flowCanvas {
    background: #0d1318;
    border: 1px solid #2d3a44;
    border-radius: 8px;
}
QScrollArea {
    background: transparent;
    border: none;
}
QTextEdit#logView {
    background: #10161b;
    color: #aebbc3;
    border: 1px solid #2d3943;
    border-radius: 7px;
    padding: 9px;
    selection-background-color: #2b7560;
}
QStatusBar {
    background: #151b21;
    color: #83909b;
    border-top: 1px solid #29343e;
    padding-left: 8px;
}
QTabWidget::pane {
    border: none;
    background: #101419;
}
QTabBar {
    background: #171d23;
}
QTabBar::tab {
    background: #171d23;
    color: #84919c;
    padding: 10px 22px;
    border: none;
    border-right: 1px solid #29343e;
}
QTabBar::tab:selected {
    background: #101419;
    color: #eef7f4;
    border-top: 2px solid #4fba97;
    font-weight: 700;
}
QTabBar::tab:hover {
    color: #d8e7e3;
    background: #202b33;
}

/* Immersive workspace shell. */
QMainWindow, QDialog {
    background: #0d1216;
}
QToolBar#mainToolbar {
    min-height: 40px;
    padding: 6px 12px;
    spacing: 5px;
    background: #151c21;
    border: none;
    border-bottom: 1px solid #2b3740;
}
QToolBar#mainToolbar QLabel#appBrand {
    color: #edf5f8;
    font-size: 10pt;
    font-weight: 700;
    padding: 0 4px 0 2px;
}
QToolBar#mainToolbar QLabel#workspaceContext {
    color: #80919c;
    padding: 0 8px;
}
QToolBar#mainToolbar QLabel#backendStatusBadge {
    color: #8de1c4;
    background: #132a23;
    border: 1px solid #315446;
    border-radius: 11px;
    padding: 3px 9px;
    margin-right: 4px;
}
QToolBar#mainToolbar QToolButton,
QToolBar#mainToolbar QPushButton {
    min-height: 28px;
    color: #c6d2d9;
    background: #182026;
    border: 1px solid #33414a;
    border-radius: 5px;
    padding: 4px 9px;
}
QToolBar#mainToolbar QToolButton:hover,
QToolBar#mainToolbar QPushButton:hover {
    color: #f2f8fa;
    background: #222d34;
    border-color: #4b5c67;
}
QToolBar#mainToolbar #runButton {
    color: #071317;
    background: #55d3f5;
    border-color: #70dcf7;
}
QToolBar#mainToolbar #runButton:hover {
    background: #75def7;
    border-color: #8ce5f9;
}
QWidget#appShell {
    background: #0d1216;
}
QWidget#navigationRail {
    background: #12181d;
    border-right: 1px solid #2b3740;
}
QWidget#navigationRail QLabel#navBrandMark {
    min-width: 30px;
    min-height: 30px;
    max-width: 30px;
    max-height: 30px;
    color: #071317;
    background: #55d3f5;
    border-radius: 6px;
    font-weight: 800;
}
QWidget#navigationRail QPushButton {
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    padding: 0;
    color: #82939d;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
}
QWidget#navigationRail QPushButton:hover {
    color: #d7e4e9;
    background: #1b252c;
    border-color: #2c3942;
}
QWidget#navigationRail QPushButton:checked {
    color: #75ddf8;
    background: #1d2930;
    border-color: #354852;
}
QStackedWidget#workspaceStack {
    background: #0d1216;
    border: none;
}
QWidget#pageHeader,
QWidget#flowHeader {
    min-height: 48px;
    max-height: 48px;
    background: #10171b;
    border-bottom: 1px solid #2b3740;
}
QLabel#pageTitle {
    color: #edf4f7;
    font-size: 11pt;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #788a94;
    font-size: 8pt;
}
QLabel#pageCountBadge {
    color: #8fe1c4;
    background: #132a23;
    border: 1px solid #315446;
    border-radius: 11px;
    padding: 3px 9px;
}
#windowTasksPage {
    background: #0d1216;
}
#windowTasksPage QWidget#taskSidebar {
    background: #10161a;
    border: none;
    border-right: 1px solid #2b3740;
    border-radius: 0;
}
#windowTasksPage QWidget#taskDetailPanel {
    background: #131a1f;
}
#windowTasksPage QListWidget#taskList {
    background: #10161a;
    border: none;
    border-radius: 0;
    padding: 0;
}
#windowTasksPage QListWidget#taskList::item {
    min-height: 46px;
    padding: 8px 11px;
    margin: 1px 0;
    color: #becbd2;
    background: transparent;
    border: none;
    border-bottom: 1px solid #202a31;
    border-radius: 0;
}
#windowTasksPage QListWidget#taskList::item:hover {
    background: #151f25;
}
#windowTasksPage QListWidget#taskList::item:selected {
    color: #edf6f8;
    background: #172635;
    border: none;
    border-left: 3px solid #4c9dff;
}
QGroupBox#targetPanel,
QGroupBox#operationsPanel,
QGroupBox#nodePropertiesPanel {
    color: #dce7eb;
    background: #131a1f;
    border: none;
    border-bottom: 1px solid #2b3740;
    border-radius: 0;
    margin-top: 16px;
    padding: 17px 13px 13px;
}
QGroupBox#targetPanel::title,
QGroupBox#operationsPanel::title,
QGroupBox#nodePropertiesPanel::title {
    color: #e5eef2;
    padding: 0 4px;
    font-weight: 700;
}
QGroupBox#nodePropertiesPanel {
    margin-top: 0;
    padding: 4px 0 0;
    border-bottom: none;
}
QWidget#editorPage,
QWidget#flowWorkspace {
    background: #0d1317;
}
QWidget#editorRightPanel {
    background: #151d22;
    border-left: 1px solid #35434c;
    border-radius: 0;
}
QWidget#editorRightPanel QLabel#inspectorTitle {
    color: #edf4f7;
    font-size: 11pt;
    font-weight: 700;
}
#editorEmptyState {
    color: #758690;
    background: #151d22;
    border: none;
    border-radius: 0;
    padding: 18px;
}
QGraphicsView#flowCanvas {
    background: #0d1317;
    border: none;
    border-radius: 0;
}
QWidget#runHistoryPage,
QWidget#templateLibraryPage,
QWidget#settingsPage {
    background: #0d1216;
}
QListWidget#runSessionList {
    background: #11181c;
    border: none;
    border-right: 1px solid #2b3740;
    border-radius: 0;
    padding: 8px;
}
QListWidget#runSessionList::item {
    min-height: 42px;
    padding: 7px 9px;
    margin: 2px 0;
    border-radius: 5px;
}
QListWidget#runSessionList::item:selected {
    color: #e8f1f4;
    background: #1b2b36;
    border: none;
}
QTextEdit#logView {
    color: #aebdc4;
    background: #0f1519;
    border: none;
    border-radius: 0;
    padding: 10px 12px;
    font-family: "Cascadia Mono", "Consolas", "Microsoft YaHei UI", monospace;
}
QWidget#logDetailPanel,
QWidget#templateDetailPanel {
    background: #131a1f;
    border-left: 1px solid #2b3740;
}
QListWidget#templateList {
    background: #10161a;
    border: none;
    border-radius: 0;
    padding: 12px;
}
QListWidget#templateList::item {
    color: #c8d4da;
    background: #151d22;
    border: 1px solid #2e3b43;
    border-radius: 6px;
    padding: 8px;
    margin: 4px;
}
QListWidget#templateList::item:hover {
    background: #1b252b;
    border-color: #44545e;
}
QListWidget#templateList::item:selected {
    color: #eff8fa;
    background: #172635;
    border: 1px solid #4c9dff;
}
QLabel#templatePreview {
    color: #778994;
    background: #0a0f12;
    border: 1px solid #35434c;
    border-radius: 5px;
}
QWidget#settingsNav {
    background: #11181c;
    border-right: 1px solid #2b3740;
}
QWidget#settingsNav QPushButton {
    min-height: 36px;
    color: #91a2ac;
    background: transparent;
    border: none;
    border-radius: 5px;
    text-align: left;
    padding: 0 11px;
}
QWidget#settingsNav QPushButton:checked {
    color: #75ddf8;
    background: #1b2931;
}
QWidget#settingsContent {
    background: #0d1216;
}
QWidget#settingsContent QLabel#settingsSectionTitle {
    color: #dfe9ed;
    font-size: 10pt;
    font-weight: 700;
}
QLabel#dependencyReady {
    color: #8de1c4;
}
QLabel#dependencyMissing {
    color: #f09aa4;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    color: #e3ecef;
    background: #11181d;
    border: 1px solid #34424b;
    border-radius: 5px;
    padding: 5px 8px;
    selection-background-color: #367cc5;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #55d3f5;
    background: #131c21;
}
QPushButton {
    border-radius: 5px;
}
QPushButton#taskRunButton,
QPushButton#taskRunAllButton,
QPushButton#templateRefreshButton {
    color: #071317;
    background: #55d3f5;
    border-color: #70dcf7;
}
QPushButton#taskRunButton:hover,
QPushButton#taskRunAllButton:hover,
QPushButton#templateRefreshButton:hover {
    background: #75def7;
    border-color: #8ce5f9;
}
QStatusBar {
    min-height: 29px;
    color: #8fa0aa;
    background: #141b20;
    border-top: 1px solid #2b3740;
    padding: 0 8px;
}
QStatusBar QLabel#statusPrimary {
    color: #bac8cf;
}
QStatusBar QLabel#statusMetrics {
    color: #82949e;
    padding: 0 6px;
}
QWidget#appShell[density="compact"] QListWidget#taskList::item {
    min-height: 38px;
    padding-top: 5px;
    padding-bottom: 5px;
}
"""
STEP_TYPES = [
    ("click", "单击坐标"),
    ("double_click", "双击坐标"),
    ("move", "移动鼠标"),
    ("drag", "按住拖拽"),
    ("macro", "宏动作"),
    ("press", "按下按键"),
    ("type", "输入文字"),
    ("wait", "等待时间"),
    ("wait_image", "等待图片"),
    ("click_image", "查找图片并点击"),
    ("window_wait_image", "窗口内等待图片"),
    ("window_click_image", "窗口内识别并点击"),
    ("ocr", "OCR文字识别"),
    ("window_ocr", "窗口内OCR文字识别"),
    ("find_window", "查找窗口"),
    ("screenshot", "截取屏幕"),
]
TYPE_LABELS = dict(STEP_TYPES)


def default_step(step_type: str = "wait") -> dict[str, Any]:
    step: dict[str, Any] = {"type": step_type, "enabled": True, "label": ""}
    if step_type in {"click", "double_click", "move"}:
        step.update({"x": 0, "y": 0})
    elif step_type == "drag":
        step.update({"start_x": 0, "start_y": 0, "end_x": 0, "end_y": 0, "duration": 0.8})
    elif step_type == "macro":
        step.update({"name": "未命名动作", "events": [], "mode": "once", "repeat": 1, "interval": 0.2})
    elif step_type == "press":
        step["key"] = "ENTER"
    elif step_type == "type":
        step["text"] = ""
    elif step_type == "wait":
        step["seconds"] = 1.0
    elif step_type in {"wait_image", "click_image", "window_wait_image", "window_click_image"}:
        step.update({"image": "", "confidence": 0.85, "timeout": 10.0, "offset_x": 0, "offset_y": 0})
    elif step_type in {"ocr", "window_ocr"}:
        step.update({"target_text": "", "confidence": 0.6, "timeout": 10.0})
    elif step_type == "find_window":
        step.update({
            "title_contains": "",
            "process_name": "",
            "window_timeout": 10.0,
            # Window automation always uses the non-activating message path.
            # Keep the fields for JSON compatibility, but do not expose a
            # foreground/background choice in the UI.
            "background_input": True,
            "activate_window": False,
        })
    elif step_type == "screenshot":
        step["path"] = "screenshot.png"
    return step


def default_window_task(index: int = 1) -> dict[str, Any]:
    return {
        "name": f"窗口任务 {index}",
        "title_contains": "",
        "process_name": "",
        "window_timeout": 10.0,
        "background_input": True,
        "activate_window": False,
        "run_mode": "once",
        "repeat": 2,
        "interval": 0.5,
        "steps": [default_step("wait")],
        "flow": None,
    }


class AutomationError(RuntimeError):
    pass


def new_flow_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def flow_from_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a straight-line flow from legacy/task step data."""
    origin_x = 32
    gap_x = 198
    nodes: list[dict[str, Any]] = [
        {"id": "start", "type": "start", "x": origin_x, "y": 180},
    ]
    edges: list[dict[str, Any]] = []
    previous = "start"
    for index, step in enumerate(steps):
        node_id = f"step_{index + 1}"
        nodes.append({"id": node_id, "type": "action", "step": copy.deepcopy(step), "x": origin_x + gap_x * (index + 1), "y": 180})
        edges.append({"from": previous, "to": node_id, "port": "next"})
        previous = node_id
    nodes.append({"id": "end", "type": "end", "x": origin_x + gap_x * (len(steps) + 1), "y": 180})
    edges.append({"from": previous, "to": "end", "port": "next"})
    return {"nodes": nodes, "edges": edges}


def steps_from_flow(flow: dict[str, Any]) -> list[dict[str, Any]]:
    """Return action steps in execution order for linear-compatible tasks."""
    nodes = flow.get("nodes", []) if isinstance(flow, dict) else []
    edges = flow.get("edges", []) if isinstance(flow, dict) else []
    by_id = {str(node.get("id")): node for node in nodes if isinstance(node, dict)}
    outgoing: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        if isinstance(edge, dict):
            outgoing.setdefault(str(edge.get("from")), []).append(edge)
    current = "start"
    result: list[dict[str, Any]] = []
    visited: set[str] = set()
    while current not in visited:
        visited.add(current)
        options = outgoing.get(current, [])
        if not options:
            break
        edge = options[0]
        current = str(edge.get("to", ""))
        node = by_id.get(current, {})
        if node.get("type") == "action" and isinstance(node.get("step"), dict):
            result.append(copy.deepcopy(node["step"]))
    return result


def _safe_float(value: Any, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    """Convert imported numeric fields without leaking TypeError/ValueError to the UI."""
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        number = float(default)
    if not math.isfinite(number):
        number = float(default)
    if minimum is not None:
        number = max(float(minimum), number)
    if maximum is not None:
        number = min(float(maximum), number)
    return number


def _safe_int(value: Any, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    """Convert imported integer fields with deterministic bounds."""
    try:
        number = int(float(value))
    except (OverflowError, TypeError, ValueError):
        number = int(default)
    if minimum is not None:
        number = max(int(minimum), number)
    if maximum is not None:
        number = min(int(maximum), number)
    return number


def match_template(cv2_module, frame, template) -> tuple[float, tuple[int, int]]:
    """Return similarity and top-left location, including uniform templates."""
    if float(cv2_module.meanStdDev(template)[1].max()) < 1.0:
        result = cv2_module.matchTemplate(frame, template, cv2_module.TM_SQDIFF)
        minimum, _maximum, location, _other = cv2_module.minMaxLoc(result)
        rms_error = math.sqrt(max(0.0, float(minimum)) / template.size)
        return max(0.0, 1.0 - rms_error / 255.0), location
    result = cv2_module.matchTemplate(frame, template, cv2_module.TM_CCOEFF_NORMED)
    _minimum, maximum, _other, location = cv2_module.minMaxLoc(result)
    return float(maximum), location


class TemplateMatch(NamedTuple):
    score: float
    location: tuple[int, int]
    size: tuple[int, int]
    scale: float


TEMPLATE_MATCH_SCALES = (1.0, 0.975, 1.025, 0.95, 1.05, 0.925, 1.075, 0.9, 1.1)


def find_template_match(
    cv2_module,
    frame,
    template,
    scales: tuple[float, ...] = TEMPLATE_MATCH_SCALES,
) -> TemplateMatch:
    """Find the best template match while tolerating small render-scale changes."""
    frame_height, frame_width = frame.shape[:2]
    template_height, template_width = template.shape[:2]
    best = TemplateMatch(-1.0, (0, 0), (template_width, template_height), 1.0)
    tested_sizes: set[tuple[int, int]] = set()
    for scale in scales:
        width = max(1, int(round(template_width * float(scale))))
        height = max(1, int(round(template_height * float(scale))))
        size = (width, height)
        if size in tested_sizes or width > frame_width or height > frame_height:
            continue
        tested_sizes.add(size)
        if size == (template_width, template_height):
            candidate = template
        else:
            interpolation = cv2_module.INTER_AREA if scale < 1.0 else cv2_module.INTER_CUBIC
            candidate = cv2_module.resize(template, size, interpolation=interpolation)
        score, location = match_template(cv2_module, frame, candidate)
        if score > best.score:
            best = TemplateMatch(float(score), location, size, float(scale))
    return best


def fit_frame_to_size(cv2_module, frame, target_width: int, target_height: int):
    """Fit a framebuffer into a target client area without changing its aspect ratio."""
    source_height, source_width = frame.shape[:2]
    if source_width <= 0 or source_height <= 0 or target_width <= 0 or target_height <= 0:
        raise ValueError("截图尺寸无效")
    scale = min(target_width / source_width, target_height / source_height)
    width = max(1, min(target_width, int(round(source_width * scale))))
    height = max(1, min(target_height, int(round(source_height * scale))))
    if (width, height) == (source_width, source_height):
        resized = frame.copy()
    else:
        interpolation = cv2_module.INTER_AREA if scale < 1.0 else cv2_module.INTER_CUBIC
        resized = cv2_module.resize(frame, (width, height), interpolation=interpolation)
    left = (target_width - width) // 2
    right = target_width - width - left
    top = (target_height - height) // 2
    bottom = target_height - height - top
    fitted = cv2_module.copyMakeBorder(
        resized, top, bottom, left, right, cv2_module.BORDER_CONSTANT, value=(0, 0, 0)
    )
    return fitted, (left, top, width, height)


def validate_flow(flow: dict[str, Any]) -> list[str]:
    """Return user-facing errors for an executable task flow."""
    if not isinstance(flow, dict):
        return ["任务没有流程图数据"]
    raw_nodes = flow.get("nodes", [])
    raw_edges = flow.get("edges", [])
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        return ["流程图节点或连线格式无效"]

    nodes = {
        str(node.get("id")): node
        for node in raw_nodes
        if isinstance(node, dict) and node.get("id")
    }
    errors: list[str] = []
    if "start" not in nodes or nodes["start"].get("type") != "start":
        errors.append("缺少开始节点")
    if "end" not in nodes or nodes["end"].get("type") != "end":
        errors.append("缺少结束节点")
    if errors:
        return errors

    outgoing: dict[str, list[dict[str, Any]]] = {}
    incoming: dict[str, list[dict[str, Any]]] = {}
    for edge in raw_edges:
        if not isinstance(edge, dict):
            continue
        source = str(edge.get("from", ""))
        target = str(edge.get("to", ""))
        if source not in nodes or target not in nodes:
            errors.append("存在指向已删除节点的连线")
            continue
        outgoing.setdefault(source, []).append(edge)
        incoming.setdefault(target, []).append(edge)

    for node_id, node in nodes.items():
        node_type = str(node.get("type", "action"))
        choices = outgoing.get(node_id, [])
        ports = [str(edge.get("port", "next")) for edge in choices]
        if node_type not in {"start", "end", "action", "condition"}:
            errors.append(f"节点“{node_id}”类型不受支持")
            continue
        if node_type == "condition":
            operator = str(node.get("operator", "and")).lower()
            if operator not in {"and", "or", "not"}:
                errors.append(f"判断节点“{node_id}”的匹配方式无效")
            conditions = node.get("conditions", [])
            has_image = any(
                isinstance(condition, dict) and str(condition.get("image", "")).strip()
                for condition in conditions
            ) if isinstance(conditions, list) else False
            if not has_image:
                errors.append(f"判断节点“{node_id}”至少需要一张模板图片")
        if node_type == "end":
            if choices:
                errors.append("结束节点不能再连接后续节点")
            continue
        if node_type == "start" and incoming.get(node_id):
            errors.append("开始节点不能有输入连线")
        required_ports = ("true", "false") if node_type == "condition" else ("next",)
        for port in required_ports:
            count = ports.count(port)
            label = {"true": "是", "false": "否", "next": "下一步"}[port]
            if count == 0:
                errors.append(f"节点“{node_id}”缺少“{label}”连线")
            elif count > 1:
                errors.append(f"节点“{node_id}”的“{label}”出口存在多条连线")

    reachable: set[str] = set()
    queue = ["start"]
    while queue:
        node_id = queue.pop(0)
        if node_id in reachable:
            continue
        reachable.add(node_id)
        queue.extend(
            str(edge.get("to", ""))
            for edge in outgoing.get(node_id, [])
            if str(edge.get("to", "")) not in reachable
        )
    unreachable = [
        node_id for node_id, node in nodes.items()
        if node_id not in reachable and node.get("type") not in {"start", "end"}
    ]
    if unreachable:
        errors.append(f"有 {len(unreachable)} 个节点未连接到开始节点")
    if "end" not in reachable:
        errors.append("开始节点无法到达结束节点")
    return errors


class FlowNodeItem(QGraphicsObject):
    """A compact draggable node with one input and up to two output ports."""

    moved = Signal()
    move_finished = Signal()
    selected = Signal(object)
    port_clicked = Signal(object, str)
    port_pressed = Signal(object, str, object)
    port_dragged = Signal(object, object)
    port_released = Signal(object, object)

    def __init__(self, node: dict[str, Any], parent=None):
        super().__init__(parent)
        self.node = node
        self.width = 148.0
        self.height = 64.0
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setPos(float(node.get("x", 0)), float(node.get("y", 0)))
        self._drag_start = QPointF()
        self._port_dragging: str | None = None

    def boundingRect(self) -> QRectF:
        # Ports and antialiased borders extend outside the node body. Keeping
        # them inside the dirty region prevents trails while dragging.
        return QRectF(-8, -8, self.width + 16, self.height + 16)

    def body_rect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def _title(self) -> str:
        kind = self.node.get("type")
        if kind == "start":
            return "开始"
        if kind == "end":
            return "结束"
        if kind == "condition":
            custom_label = str(self.node.get("label", "")).strip()
            if custom_label:
                return custom_label
            raw_operator = str(self.node.get("operator", "and")).lower()
            legacy_not = raw_operator == "not"
            operator = "AND" if raw_operator in {"and", "not"} else "OR"
            suffix = " · 非" if bool(self.node.get("negate", False)) or legacy_not else ""
            return f"判断 · {operator}{suffix}"
        step = self.node.get("step", {})
        custom_label = str(step.get("label", "")).strip()
        if custom_label:
            return custom_label
        return TYPE_LABELS.get(str(step.get("type", "action")), "操作")

    def _subtitle(self) -> str:
        if self.node.get("type") == "start":
            return "任务入口"
        if self.node.get("type") == "end":
            return "流程完成"
        if self.node.get("type") == "condition":
            conditions = self.node.get("conditions", [])
            return f"{len(conditions)} 个图片条件"
        step = self.node.get("step", {})
        step_type = step.get("type")
        if step_type in {"click", "double_click", "move"}:
            return f"({step.get('x', 0)}, {step.get('y', 0)})"
        if step_type == "type":
            return str(step.get("text", ""))[:22] or "输入文字"
        if step_type == "press":
            return str(step.get("key", "ENTER"))
        if step_type == "wait":
            return f"{float(step.get('seconds', 1)):.2f} 秒"
        if step_type == "macro":
            return str(step.get("name", "未命名动作"))[:22]
        return "双击打开属性"

    def paint(self, painter: QPainter, option, widget=None) -> None:
        selected = self.isSelected()
        kind = self.node.get("type")
        if kind == "condition":
            painter.setBrush(QColor("#2a2418") if not selected else QColor("#342d1d"))
            painter.setPen(QPen(QColor("#7b6130") if not selected else QColor("#e0ad4e"), 2 if selected else 1))
            painter.drawRoundedRect(self.body_rect(), 6, 6)
            painter.setPen(QColor("#f2e3bd"))
            painter.drawText(QRectF(12, 10, self.width - 34, 22), Qt.AlignLeft | Qt.AlignVCenter, self._title())
            painter.setPen(QColor("#b8a77e"))
            painter.drawText(QRectF(12, 35, self.width - 34, 20), Qt.AlignLeft | Qt.AlignVCenter, self._subtitle())
            painter.setPen(QColor("#64d69e"))
            painter.drawText(QRectF(self.width - 28, 7, 22, 18), Qt.AlignCenter, "是")
            painter.setPen(QColor("#f18a94"))
            painter.drawText(QRectF(self.width - 28, self.height - 25, 22, 18), Qt.AlignCenter, "否")
        else:
            colors = {"start": ("#142923", "#2e7d66"), "end": ("#271a1e", "#6b4650")}
            fill, outline = colors.get(kind, ("#182128", "#394852"))
            painter.setBrush(QColor(fill) if not selected else QColor("#182942"))
            painter.setPen(QPen(QColor("#4c9dff") if selected else QColor(outline), 2 if selected else 1))
            painter.drawRoundedRect(self.body_rect(), 6, 6)
            painter.setPen(QColor("#edf1f6"))
            painter.drawText(QRectF(12, 9, self.width - 24, 23), Qt.AlignLeft | Qt.AlignVCenter, self._title())
            painter.setPen(QColor("#8799a3"))
            painter.drawText(QRectF(12, 35, self.width - 24, 19), Qt.AlignLeft | Qt.AlignVCenter, self._subtitle())
        if kind not in {"start"}:
            self._draw_port(painter, QPointF(0, self.height / 2), "in")
        if kind not in {"end", "condition"}:
            self._draw_port(painter, QPointF(self.width, self.height / 2), "next")
        if kind == "condition":
            self._draw_port(painter, QPointF(self.width, 18), "true")
            self._draw_port(painter, QPointF(self.width, self.height - 18), "false")

    @staticmethod
    def _draw_port(painter: QPainter, point: QPointF, name: str) -> None:
        color = {"true": "#3ab27c", "false": "#d45c6b"}.get(name, "#6f7d8e")
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(point, 4.0, 4.0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.node["x"] = round(self.pos().x(), 1)
            self.node["y"] = round(self.pos().y(), 1)
            self.moved.emit()
        return super().itemChange(change, value)

    def _port_at(self, local: QPointF) -> str | None:
        """Return an output port when the pointer is in its hit area."""
        if local.x() < self.width - 20 or self.node.get("type") == "end":
            return None
        if self.node.get("type") == "condition":
            if abs(local.y() - 18) <= 16:
                return "true"
            if abs(local.y() - (self.height - 18)) <= 16:
                return "false"
            return None
        return "next" if abs(local.y() - self.height / 2) <= 20 else None

    def mousePressEvent(self, event) -> None:
        self._drag_start = self.pos()
        if event.button() == Qt.LeftButton:
            local_pos = event.pos()
            port = self._port_at(local_pos)
            if port is not None:
                self._port_dragging = port
                self.setSelected(True)
                self.selected.emit(self)
                self.port_pressed.emit(self, port, self.mapToScene(local_pos))
                event.accept()
                return
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.selected.emit(self)

    def mouseMoveEvent(self, event) -> None:
        if self._port_dragging is not None:
            self.port_dragged.emit(self, self.mapToScene(event.pos()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._port_dragging is not None and event.button() == Qt.LeftButton:
            self.port_released.emit(self, self.mapToScene(event.pos()))
            self._port_dragging = None
            event.accept()
            return
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and self.pos() != self._drag_start:
            self.move_finished.emit()

    def mouseDoubleClickEvent(self, event) -> None:
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.LeftButton:
            self.selected.emit(self)


class FlowEdgeItem(QGraphicsPathItem):
    def __init__(self, source: FlowNodeItem, target: FlowNodeItem, edge: dict[str, Any], parent=None):
        super().__init__(parent)
        self.source = source
        self.target = target
        self.edge = edge
        self.port = str(edge.get("port", "next"))
        self.color = QColor({"true": "#4fc58c", "false": "#e26d78"}.get(self.port, "#617681"))
        self.setPen(QPen(self.color, 2))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setToolTip("选中连线后可点击“删除”")
        self.setZValue(-1)
        self._end = QPointF()
        self._control_end = QPointF()
        self.update_path()

    def update_path(self) -> None:
        start = self.source.pos() + self._port_point(self.source, self.port)
        end = self.target.pos() + QPointF(0, self.target.height / 2)
        path = QPainterPath(start)
        distance = max(50.0, abs(end.x() - start.x()) * 0.45)
        path.cubicTo(start + QPointF(distance, 0), end - QPointF(distance, 0), end)
        self.setPath(path)
        self._end = end
        self._control_end = end - QPointF(distance, 0)

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(self.path())

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self.color, 3 if self.isSelected() else 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())
        dx = self._end.x() - self._control_end.x()
        dy = self._end.y() - self._control_end.y()
        angle = math.atan2(dy, dx)
        size = 8.0
        left = self._end - QPointF(math.cos(angle - 0.48) * size, math.sin(angle - 0.48) * size)
        right = self._end - QPointF(math.cos(angle + 0.48) * size, math.sin(angle + 0.48) * size)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.color)
        painter.drawPolygon(QPolygonF([self._end, left, right]))

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-9, -9, 9, 9)

    @staticmethod
    def _port_point(node: FlowNodeItem, port: str) -> QPointF:
        if port == "true":
            return QPointF(node.width, 18)
        if port == "false":
            return QPointF(node.width, node.height - 18)
        return QPointF(node.width, node.height / 2)


class FlowCanvas(QGraphicsView):
    node_selected = Signal(object)
    flow_changed = Signal()
    save_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setObjectName("flowCanvas")
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setCacheMode(QGraphicsView.CacheNone)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setBackgroundBrush(QColor("#0d1317"))
        self.setMinimumHeight(400)
        self.setToolTip("右键添加节点；从节点右侧端口拖到目标节点左侧端口即可连线；Ctrl+滚轮缩放")
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.node_items: dict[str, FlowNodeItem] = {}
        self.edge_items: list[FlowEdgeItem] = []
        self.flow: dict[str, Any] = {"nodes": [], "edges": []}
        self.pending_source: tuple[str, str] | None = None
        self.connection_preview: QGraphicsPathItem | None = None
        self._property_callback = None
        self._rebuilding = False
        self.scene.selectionChanged.connect(self._selection_changed)

    def set_property_callback(self, callback):
        self._property_callback = callback

    def set_flow(self, flow: dict[str, Any] | None, *, fit: bool = True):
        self._rebuilding = True
        self.flow = copy.deepcopy(flow or {"nodes": [], "edges": []})
        self.pending_source = None
        self.connection_preview = None
        try:
            self.scene.clear()
            self.node_items.clear()
            self.edge_items.clear()
            for node in self.flow.get("nodes", []):
                if not isinstance(node, dict):
                    continue
                item = FlowNodeItem(node)
                self.node_items[str(node.get("id"))] = item
                self.scene.addItem(item)
                item.selected.connect(self._node_selected)
                item.moved.connect(self._update_edges)
                item.move_finished.connect(self._node_move_finished)
                item.port_pressed.connect(self._node_port_pressed)
                item.port_dragged.connect(self._node_port_dragged)
                item.port_released.connect(self._node_port_released)
            self._rebuild_edges()
            self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-120, -120, 120, 120))
            if fit and self.isVisible():
                self.fit_flow()
        finally:
            self._rebuilding = False

    def fit_flow(self) -> None:
        rect = self.scene.itemsBoundingRect()
        if rect.isValid() and not rect.isEmpty():
            target = rect.adjusted(-42, -42, 42, 42)
            viewport_size = self.viewport().size()
            self.resetTransform()
            if target.width() > viewport_size.width() or target.height() > viewport_size.height():
                self.fitInView(target, Qt.KeepAspectRatio)
            else:
                self.centerOn(rect.center())

    def _rebuild_edges(self):
        for edge in self.edge_items:
            self.scene.removeItem(edge)
        self.edge_items.clear()
        for edge in self.flow.get("edges", []):
            source = self.node_items.get(str(edge.get("from")))
            target = self.node_items.get(str(edge.get("to")))
            if source and target:
                item = FlowEdgeItem(source, target, edge)
                self.edge_items.append(item)
                self.scene.addItem(item)

    def _update_edges(self):
        if getattr(self, "_rebuilding", False):
            return
        for edge in self.edge_items:
            edge.update_path()
        self.viewport().update()

    def _node_move_finished(self) -> None:
        bounds = self.scene.itemsBoundingRect().adjusted(-120, -120, 120, 120)
        self.scene.setSceneRect(self.scene.sceneRect().united(bounds))
        self.flow_changed.emit()

    def _node_port_pressed(self, item: FlowNodeItem, port: str, scene_pos: QPointF) -> None:
        if item.node.get("type") == "end":
            return
        self._begin_connection(item, port)
        self._update_connection_preview(scene_pos)

    def _node_port_dragged(self, item: FlowNodeItem, scene_pos: QPointF) -> None:
        if self.pending_source is None:
            return
        if str(item.node.get("id")) == self.pending_source[0]:
            self._update_connection_preview(scene_pos)

    def _node_port_released(self, item: FlowNodeItem, scene_pos: QPointF) -> None:
        if self.pending_source is None:
            return
        source_id, port = self.pending_source
        target = self._target_at(scene_pos)
        if target is not None and str(target.node.get("id")) != source_id:
            self.connect_nodes(source_id, str(target.node.get("id")), port)
        self._clear_pending_connection()

    def _node_selected(self, item: FlowNodeItem):
        self.node_selected.emit(item.node)
        if self._property_callback:
            self._property_callback(item.node)

    def _selection_changed(self) -> None:
        if self._rebuilding:
            return
        selected_nodes = [item for item in self.scene.selectedItems() if isinstance(item, FlowNodeItem)]
        if selected_nodes:
            self.node_selected.emit(selected_nodes[0].node)
        else:
            self.node_selected.emit(None)

    def add_action_node(
        self,
        step: dict[str, Any] | None = None,
        position: QPointF | None = None,
        *,
        connect_before_end: bool = True,
    ):
        node_id = new_flow_id("step")
        position = position or QPointF(260, 140 + len(self.node_items) * 25)
        node = {
            "id": node_id,
            "type": "action",
            "step": copy.deepcopy(step or default_step("wait")),
            "x": round(position.x(), 1),
            "y": round(position.y(), 1),
        }
        self._add_node(node, connect_before_end)
        self.node_items[node_id].setSelected(True)
        self._node_selected(self.node_items[node_id])
        self.flow_changed.emit()

    def add_condition_node(
        self,
        position: QPointF | None = None,
        *,
        connect_before_end: bool = True,
    ):
        node_id = new_flow_id("condition")
        position = position or QPointF(260, 140 + len(self.node_items) * 25)
        node = {
            "id": node_id,
            "type": "condition",
            "label": "",
            "operator": "and",
            "negate": False,
            "conditions": [{"type": "image_exists", "image": "", "confidence": 0.85, "timeout": 5.0}],
            "x": round(position.x(), 1),
            "y": round(position.y(), 1),
        }
        self._add_node(node, connect_before_end)
        self.node_items[node_id].setSelected(True)
        self._node_selected(self.node_items[node_id])
        self.flow_changed.emit()

    def _add_node(self, node: dict[str, Any], connect_before_end: bool) -> None:
        if connect_before_end:
            self._insert_before_end(node)
        else:
            self.flow.setdefault("nodes", []).append(node)
        self.set_flow(self.flow, fit=False)

    def _insert_before_end(self, node: dict[str, Any]) -> None:
        nodes = self.flow.setdefault("nodes", [])
        nodes.append(node)
        end_id = next((str(item.get("id")) for item in nodes if item.get("type") == "end"), None)
        incoming_end = [edge for edge in self.flow.setdefault("edges", []) if str(edge.get("to")) == end_id]
        if end_id and len(incoming_end) == 1:
            edge = incoming_end[0]
            edge["to"] = node["id"]
            ports = ("true", "false") if node.get("type") == "condition" else ("next",)
            for port in ports:
                self.flow["edges"].append({"from": node["id"], "to": end_id, "port": port})

    def delete_selected(self):
        selected = self.scene.selectedItems()
        selected_edges = [item.edge for item in selected if isinstance(item, FlowEdgeItem)]
        ids = {item.node.get("id") for item in selected if isinstance(item, FlowNodeItem) and item.node.get("id") not in {"start", "end"}}
        if not ids and not selected_edges:
            return
        self.flow["nodes"] = [node for node in self.flow.get("nodes", []) if node.get("id") not in ids]
        self.flow["edges"] = [
            edge for edge in self.flow.get("edges", [])
            if edge not in selected_edges and edge.get("from") not in ids and edge.get("to") not in ids
        ]
        self.set_flow(self.flow)
        self.node_selected.emit(None)
        self.flow_changed.emit()

    def connect_nodes(self, source_id: str, target_id: str, port: str = "next") -> bool:
        source = self.node_items.get(str(source_id))
        target = self.node_items.get(str(target_id))
        if source is None or target is None or source is target:
            return False
        if source.node.get("type") == "end" or target.node.get("type") == "start":
            return False
        allowed = {"true", "false"} if source.node.get("type") == "condition" else {"next"}
        if port not in allowed:
            return False
        edges = self.flow.setdefault("edges", [])
        edges[:] = [
            edge for edge in edges
            if not (str(edge.get("from")) == str(source_id) and str(edge.get("port", "next")) == port)
        ]
        edges.append({"from": str(source_id), "to": str(target_id), "port": port})
        self._rebuild_edges()
        self.flow_changed.emit()
        return True

    def auto_layout(self) -> None:
        selected_ids = [
            str(item.node.get("id"))
            for item in self.scene.selectedItems()
            if isinstance(item, FlowNodeItem)
        ]
        nodes = {
            str(node.get("id")): node
            for node in self.flow.get("nodes", [])
            if isinstance(node, dict) and node.get("id")
        }
        if not nodes:
            return
        outgoing: dict[str, list[str]] = {}
        for edge in self.flow.get("edges", []):
            source = str(edge.get("from", ""))
            target = str(edge.get("to", ""))
            if source in nodes and target in nodes:
                outgoing.setdefault(source, []).append(target)
        levels: dict[str, int] = {"start": 0} if "start" in nodes else {}
        queue = ["start"] if "start" in nodes else []
        while queue:
            source = queue.pop(0)
            for target in outgoing.get(source, []):
                if target in levels:
                    continue
                levels[target] = levels[source] + 1
                queue.append(target)
        fallback_level = max(levels.values(), default=-1) + 1
        for node_id in nodes:
            if node_id not in levels:
                levels[node_id] = fallback_level
        columns: dict[int, list[dict[str, Any]]] = {}
        for node_id, level in levels.items():
            columns.setdefault(level, []).append(nodes[node_id])
        for level, column_nodes in columns.items():
            for row, node in enumerate(column_nodes):
                node["x"] = 32 + level * 198
                node["y"] = 90 + row * 135
        self.set_flow(self.flow)
        for node_id in selected_ids:
            item = self.node_items.get(node_id)
            if item is not None:
                item.setSelected(True)
        self.flow_changed.emit()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802 - Qt API name
        painter.fillRect(rect, QColor("#0d1317"))
        grid = 24
        left = math.floor(rect.left() / grid) * grid
        top = math.floor(rect.top() / grid) * grid
        painter.setPen(QPen(QColor("#1e292f"), 1))
        x = left
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += grid
        y = top
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += grid

    def contextMenuEvent(self, event) -> None:  # noqa: N802 - Qt API name
        scene_pos = self.mapToScene(event.pos())
        clicked_item = self.itemAt(event.pos())
        node_item = clicked_item if isinstance(clicked_item, FlowNodeItem) else None
        edge_item = clicked_item if isinstance(clicked_item, FlowEdgeItem) else None

        menu = QMenu(self)
        edit_action = menu.addAction("编辑节点属性") if node_item is not None else None
        if edit_action is not None:
            menu.addSeparator()
        add_action = menu.addAction("添加操作节点")
        add_condition = menu.addAction("添加判断节点")
        delete_action = None
        if edge_item is not None:
            menu.addSeparator()
            delete_action = menu.addAction("删除连线")
        elif node_item is not None and node_item.node.get("id") not in {"start", "end"}:
            menu.addSeparator()
            delete_action = menu.addAction("删除节点")
        menu.addSeparator()
        layout_action = menu.addAction("自动排列")
        save_action = menu.addAction("导出 JSON")

        chosen = menu.exec(event.globalPos())
        if chosen is None:
            return
        if chosen is edit_action and node_item is not None:
            self.scene.clearSelection()
            node_item.setSelected(True)
            self._node_selected(node_item)
        elif chosen is add_action:
            self.add_action_node(default_step("wait"), scene_pos - QPointF(74, 32), connect_before_end=False)
        elif chosen is add_condition:
            self.add_condition_node(scene_pos - QPointF(74, 32), connect_before_end=False)
        elif chosen is delete_action and (node_item is not None or edge_item is not None):
            self.scene.clearSelection()
            target = node_item if node_item is not None else edge_item
            target.setSelected(True)
            self.delete_selected()
        elif chosen is layout_action:
            self.auto_layout()
        elif chosen is save_action:
            self.save_requested.emit()
        event.accept()

    @staticmethod
    def _port_for_node(item: FlowNodeItem, local: QPointF) -> str | None:
        if item.node.get("type") == "end" or local.x() < item.width - 18:
            return None
        if item.node.get("type") == "condition":
            if abs(local.y() - 18) <= 15:
                return "true"
            if abs(local.y() - (item.height - 18)) <= 15:
                return "false"
            return None
        return "next" if abs(local.y() - item.height / 2) <= 18 else None

    def _source_at(self, scene_pos: QPointF) -> tuple[FlowNodeItem, str] | None:
        for item in self.scene.items(scene_pos):
            if isinstance(item, FlowNodeItem):
                port = self._port_for_node(item, item.mapFromScene(scene_pos))
                if port is not None:
                    return item, port
        return None

    def _target_at(self, scene_pos: QPointF) -> FlowNodeItem | None:
        for item in self.scene.items(scene_pos):
            if not isinstance(item, FlowNodeItem) or item.node.get("type") == "start":
                continue
            local = item.mapFromScene(scene_pos)
            if local.x() <= 18 and abs(local.y() - item.height / 2) <= 22:
                return item
        return None

    def _begin_connection(self, item: FlowNodeItem, port: str) -> None:
        self.pending_source = (str(item.node.get("id")), port)
        self.connection_preview = QGraphicsPathItem()
        self.connection_preview.setPen(QPen(QColor("#55d3f5"), 2, Qt.DashLine))
        self.connection_preview.setZValue(-0.5)
        self.connection_preview.setAcceptedMouseButtons(Qt.NoButton)
        self.scene.addItem(self.connection_preview)
        self._update_connection_preview(item.pos() + FlowEdgeItem._port_point(item, port))
        self.viewport().setCursor(Qt.CrossCursor)

    def _update_connection_preview(self, end: QPointF) -> None:
        if self.pending_source is None or self.connection_preview is None:
            return
        source = self.node_items.get(self.pending_source[0])
        if source is None:
            return
        start = source.pos() + FlowEdgeItem._port_point(source, self.pending_source[1])
        distance = max(50.0, abs(end.x() - start.x()) * 0.45)
        path = QPainterPath(start)
        path.cubicTo(start + QPointF(distance, 0), end - QPointF(distance, 0), end)
        self.connection_preview.setPath(path)
        valid_target = self._target_at(end)
        color = "#3ab27c" if valid_target is not None and str(valid_target.node.get("id")) != self.pending_source[0] else "#55d3f5"
        self.connection_preview.setPen(QPen(QColor(color), 2, Qt.DashLine))

    def _clear_pending_connection(self) -> None:
        if self.connection_preview is not None and self.connection_preview.scene() is self.scene:
            self.scene.removeItem(self.connection_preview)
        self.connection_preview = None
        self.pending_source = None
        self.viewport().unsetCursor()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            source = self._source_at(scene_pos)
            if source is not None:
                self._begin_connection(*source)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        scene_pos = self.mapToScene(event.position().toPoint())
        if self.pending_source is not None:
            self._update_connection_preview(scene_pos)
            event.accept()
            return
        self.viewport().setCursor(Qt.CrossCursor if self._source_at(scene_pos) is not None else Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self.pending_source and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            source_id, port = self.pending_source
            target = self._target_at(scene_pos)
            if target is not None and str(target.node.get("id")) != source_id:
                self.connect_nodes(source_id, str(target.node.get("id")), port)
            self._clear_pending_connection()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if event.key() == Qt.Key_Escape and self.pending_source is not None:
            self._clear_pending_connection()
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event) -> None:
        if self.pending_source is not None:
            self._clear_pending_connection()
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            current_scale = max(abs(self.transform().m11()), 0.000001)
            if delta > 0:
                if current_scale >= 3.0:
                    event.accept()
                    return
                target_scale = min(3.0, current_scale * 1.15)
            elif delta < 0:
                if current_scale <= 0.2:
                    event.accept()
                    return
                target_scale = max(0.2, current_scale * 0.87)
            else:
                event.accept()
                return
            factor = target_scale / current_scale
            self.scale(factor, factor)
            self.viewport().update()
            event.accept()
            return

        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()
        horizontal = bool(event.modifiers() & Qt.ShiftModifier) or abs(angle_delta.x()) > abs(angle_delta.y())
        if horizontal:
            amount = pixel_delta.x() if not pixel_delta.isNull() else angle_delta.x() or angle_delta.y()
            bar = self.horizontalScrollBar()
        else:
            amount = pixel_delta.y() if not pixel_delta.isNull() else angle_delta.y()
            bar = self.verticalScrollBar()
        bar.setValue(bar.value() - int(amount / 2))
        self.viewport().update()
        event.accept()


class ScreenSelectLabel(QLabel):
    """Display a screenshot and let the user select a rectangular template."""

    selection_changed = Signal(bool)

    def __init__(self, pixmap: QPixmap, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        self.setCursor(Qt.CrossCursor)
        self.start_point: QPoint | None = None
        self.end_point: QPoint | None = None

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if event.button() == Qt.RightButton:
            dialog = self.window()
            if isinstance(dialog, QDialog):
                dialog.reject()
            return
        if event.button() == Qt.LeftButton:
            self.start_point = event.position().toPoint()
            self.end_point = self.start_point
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if self.start_point is not None:
            self.end_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if event.button() == Qt.LeftButton and self.start_point is not None:
            self.end_point = event.position().toPoint()
            self.update()
            self.selection_changed.emit(self.selected_rect() is not None)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API name
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap())
        painter.fillRect(self.rect(), QColor(0, 0, 0, 125))
        if self.start_point is None or self.end_point is None:
            return
        rect = QRect(self.start_point, self.end_point).normalized()
        # Restore the selected area above the dim layer, like a lightweight
        # WeChat screenshot overlay.
        painter.drawPixmap(rect, self.pixmap(), rect)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#20d6a1"), 2, Qt.SolidLine))
        painter.drawRect(rect)
        painter.setPen(QPen(Qt.white, 1, Qt.SolidLine))
        painter.drawText(rect.adjusted(7, 5, -7, -7), Qt.AlignLeft | Qt.AlignTop, f"{rect.width()} × {rect.height()}")

    def selected_rect(self) -> QRect | None:
        if self.start_point is None or self.end_point is None:
            return None
        rect = QRect(self.start_point, self.end_point).normalized()
        return rect if rect.width() >= 2 and rect.height() >= 2 else None


class TemplateCaptureDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("截取模板区域")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setCursor(Qt.CrossCursor)
        self.frame = None
        self.screen_offset = (0, 0)
        self.capture_scale = (1.0, 1.0)
        self.toolbar = None
        self.save_button = None
        try:
            import mss
            import numpy as np

            with mss.mss() as sct:
                monitor = self._monitor_for_cursor(sct)
                self.screen_offset = (monitor["left"], monitor["top"])
                shot = np.array(sct.grab(monitor))
            self.frame = shot[:, :, :3]
            # Channel reversal creates a strided view; QImage requires a
            # C-contiguous buffer, so make an explicit RGB copy first.
            rgb = np.ascontiguousarray(self.frame[:, :, ::-1])
            image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
            screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
            if screen is not None:
                geometry = screen.geometry()
                display_size = geometry.size()
                if display_size.width() > 0 and display_size.height() > 0 and image.size() != display_size:
                    self.capture_scale = (
                        image.width() / display_size.width(),
                        image.height() / display_size.height(),
                    )
                    image = image.scaled(display_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                self.setGeometry(geometry)
            else:
                display_size = image.size()
            self.selector = ScreenSelectLabel(QPixmap.fromImage(image))
            if screen is None:
                self.resize(display_size)
            self._build_overlay_controls()
        except Exception as exc:  # noqa: BLE001 - show capture failures in the dialog
            self.selector = None
            self.capture_error = str(exc)
            self.setWindowFlags(Qt.Dialog)
            self.resize(620, 180)
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel(f"无法截取屏幕: {self.capture_error}"))
            buttons = QDialogButtonBox(QDialogButtonBox.Close)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

    @staticmethod
    def _monitor_for_cursor(sct):
        """Choose the mss monitor under the cursor, with a primary fallback."""
        monitors = list(sct.monitors[1:])
        if not monitors:
            raise RuntimeError("没有可用的显示器")
        cursor = QCursor.pos()
        screen = QApplication.screenAt(cursor) or QApplication.primaryScreen()
        if screen is not None:
            # Qt reports the active screen in the coordinate system used by
            # the UI (which may be logical pixels under Windows scaling),
            # while mss reports capture rectangles in device pixels. Matching
            # centers avoids assuming those coordinate systems are identical.
            center = screen.geometry().center()
            return min(
                monitors,
                key=lambda item: (item["left"] + item["width"] / 2 - center.x()) ** 2
                + (item["top"] + item["height"] / 2 - center.y()) ** 2,
            )
        for monitor in monitors:
            if (
                monitor["left"] <= cursor.x() < monitor["left"] + monitor["width"]
                and monitor["top"] <= cursor.y() < monitor["top"] + monitor["height"]
            ):
                return monitor
        return monitors[0]

    def _build_overlay_controls(self) -> None:
        self.toolbar = QWidget(self)
        self.toolbar.setObjectName("captureOverlayToolbar")
        self.toolbar.setStyleSheet(
            "#captureOverlayToolbar { background: rgba(26, 35, 42, 235); border-radius: 8px; }"
            "QLabel { color: #ffffff; padding: 0 8px; }"
            "QPushButton { color: #ffffff; background: #2f424d; border: 1px solid #60727b; "
            "border-radius: 5px; padding: 6px 14px; min-width: 58px; }"
            "QPushButton:hover { background: #405761; }"
            "QPushButton#captureSaveButton { background: #119b8c; border-color: #119b8c; }"
            "QPushButton#captureSaveButton:hover { background: #0d8578; }"
        )
        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(7)
        hint = QLabel("拖动框选区域")
        self.save_button = QPushButton("保存")
        self.save_button.setObjectName("captureSaveButton")
        self.save_button.setEnabled(False)
        cancel_button = QPushButton("取消")
        layout.addWidget(hint)
        layout.addStretch(1)
        layout.addWidget(self.save_button)
        layout.addWidget(cancel_button)
        self.selector.setParent(self)
        self.selector.show()
        self.selector.selection_changed.connect(self.save_button.setEnabled)
        self.save_button.clicked.connect(self._accept_selection)
        cancel_button.clicked.connect(self.reject)
        self.toolbar.adjustSize()
        self._position_overlay_toolbar()
        self.toolbar.raise_()

    def _position_overlay_toolbar(self) -> None:
        if self.toolbar is None:
            return
        self.toolbar.adjustSize()
        margin = 18
        self.toolbar.move(max(margin, self.width() - self.toolbar.width() - margin), max(margin, self.height() - self.toolbar.height() - margin))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._position_overlay_toolbar()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def _accept_selection(self) -> None:
        if self.selector is None or self.frame is None:
            QMessageBox.warning(self, "无法截取", "当前环境无法获取屏幕截图。")
            return
        if self.selector.selected_rect() is None:
            QMessageBox.information(self, "未选择区域", "请先拖动鼠标框选一个区域。")
            return
        self.accept()

    def selected_image(self):
        if self.selector is None or self.frame is None:
            return None
        rect = self.selector.selected_rect()
        if rect is None:
            return None
        scale_x, scale_y = self.capture_scale
        left = max(0, min(self.frame.shape[1] - 1, int(round(rect.left() * scale_x))))
        top = max(0, min(self.frame.shape[0] - 1, int(round(rect.top() * scale_y))))
        right = max(left + 1, min(self.frame.shape[1], int(round((rect.right() + 1) * scale_x))))
        bottom = max(top + 1, min(self.frame.shape[0], int(round((rect.bottom() + 1) * scale_y))))
        return self.frame[top:bottom, left:right].copy()


class ScriptWorker(QObject):
    step_started = Signal(int)
    log = Signal(str)
    completed = Signal(bool, str)

    def __init__(
        self,
        steps: list[dict[str, Any]],
        base_dir: Path,
        output_dir: Path | None = None,
        flow: dict[str, Any] | None = None,
        initial_step: dict[str, Any] | None = None,
        run_mode: str = "once",
        repeat: int = 1,
        interval: float = 0.5,
    ):
        super().__init__()
        self.steps = steps
        # Resolve once at the worker boundary.  A draft created by an older
        # version can contain a relative script path, while the worker runs in
        # a thread whose current directory is not guaranteed to be the script
        # directory (especially when launched from a shortcut or a packaged
        # executable).
        self.base_dir = Path(base_dir).expanduser().resolve(strict=False)
        self.output_dir = (
            Path(output_dir).expanduser().resolve(strict=False)
            if output_dir is not None
            else None
        )
        self.flow = flow
        self.initial_step = initial_step
        self.run_mode = run_mode if run_mode in {"once", "repeat", "loop"} else "once"
        self.repeat = max(1, int(repeat))
        self.interval = max(0.0, float(interval))
        self.stop_event = threading.Event()
        self.last_window: dict[str, Any] | None = None
        # Window actions are always dispatched through the background input
        # path. The setting remains on the worker for compatibility with
        # existing step data, but it is never user-selectable.
        self.background_input = True
        self.current_context = ""
        self._emulator_capture_backend: dict[str, Any] | None = None
        self._emulator_capture_checked = False
        self._emulator_capture_retry_at = 0.0
        self._emulator_capture_logged = False
        self._emulator_capture_error = ""
        self._last_capture_backend = ""
        self._last_capture_detail = ""
        self._ocr_engine = None

    @staticmethod
    def _step_label(step: dict[str, Any] | None) -> str:
        if not isinstance(step, dict):
            return "未知步骤"
        step_type = str(step.get("type", "unknown"))
        label = TYPE_LABELS.get(step_type, step_type)
        custom_label = str(step.get("label", "")).strip()
        if custom_label:
            label = f"{custom_label} · {label}"
        if step_type in {"click", "double_click", "move"}:
            return f"{label} ({step.get('x', 0)}, {step.get('y', 0)})"
        if step_type == "drag":
            return (
                f"{label} ({step.get('start_x', 0)}, {step.get('start_y', 0)})"
                f" -> ({step.get('end_x', 0)}, {step.get('end_y', 0)})"
            )
        if step_type in {"wait_image", "click_image", "window_wait_image", "window_click_image"}:
            return f"{label} [{step.get('image', '') or '未设置图片'}]"
        if step_type in {"ocr", "window_ocr"}:
            return f"{label} [{step.get('target_text', '') or '任意文字'}]"
        if step_type == "find_window":
            criteria = step.get("title_contains") or step.get("process_name") or "未设置窗口条件"
            return f"{label} [{criteria}]"
        if step_type == "macro":
            return f"{label} [{step.get('name', '未命名动作')}]"
        return label

    def _log_step_failure(self, context: str, step: dict[str, Any] | None, error: Exception) -> None:
        detail = self._step_label(step)
        self.log.emit(f"步骤执行失败 | {context} | {detail} | {error}")

    @Slot()
    def run(self) -> None:
        try:
            if self.initial_step is not None:
                self._check_stopped()
                self.current_context = "初始步骤"
                self.log.emit(f"开始执行 | {self.current_context} | {self._step_label(self.initial_step)}")
                try:
                    self.execute_step(self.initial_step)
                except Exception as exc:
                    self._log_step_failure(self.current_context, self.initial_step, exc)
                    raise
                self.log.emit(f"步骤执行成功 | {self.current_context} | {self._step_label(self.initial_step)}")
            rounds = None if self.run_mode == "loop" else (self.repeat if self.run_mode == "repeat" else 1)
            current_round = 0
            while rounds is None or current_round < rounds:
                self._check_stopped()
                current_round += 1
                total = str(rounds) if rounds is not None else "持续循环"
                round_name = f"第 {current_round} 轮 / {total}"
                self.current_context = round_name
                self.log.emit(f"========== {round_name} 开始 ==========")
                try:
                    if self.flow is not None:
                        self._run_flow(self.flow)
                    else:
                        self._run_linear_steps()
                except Exception:
                    status = "已停止" if self.stop_event.is_set() else "失败"
                    self.log.emit(f"========== 第 {current_round} 轮结束：{status} ==========")
                    raise
                self.log.emit(f"========== 第 {current_round} 轮结束：成功 ==========")
                if rounds is None or current_round < rounds:
                    if self.interval > 0:
                        self.log.emit(f"等待下一轮 | {self.interval:.2f} 秒")
                    self._sleep(self.interval)
            if self.run_mode == "repeat":
                message = f"任务重复执行完成，共 {current_round} 轮"
            else:
                message = "流程执行完成" if self.flow is not None else "脚本执行完成"
            self.completed.emit(True, message)
        except Exception as exc:  # noqa: BLE001 - worker must report any runtime failure
            self.log.emit(f"脚本执行失败 | {self.current_context or '未定位步骤'} | {exc}")
            self.completed.emit(False, str(exc))

    def _run_linear_steps(self) -> None:
        for index, step in enumerate(self.steps):
            if not step.get("enabled", True):
                self.log.emit(f"跳过步骤 {index + 1}: {self._step_label(step)}")
                continue
            self._check_stopped()
            self.step_started.emit(index)
            self.current_context = f"步骤 {index + 1}"
            self.log.emit(f"开始执行 | {self.current_context} | {self._step_label(step)}")
            try:
                self.execute_step(step)
            except Exception as exc:
                self._log_step_failure(self.current_context, step, exc)
                raise
            self.log.emit(f"步骤执行成功 | {self.current_context} | {self._step_label(step)}")

    def _run_flow(self, flow: dict[str, Any]) -> None:
        nodes = {
            str(node.get("id")): node
            for node in flow.get("nodes", [])
            if isinstance(node, dict) and node.get("id")
        }
        outgoing: dict[str, list[dict[str, Any]]] = {}
        for edge in flow.get("edges", []):
            if isinstance(edge, dict):
                outgoing.setdefault(str(edge.get("from")), []).append(edge)
        current = "start"
        visited_count: dict[str, int] = {}
        while current:
            self._check_stopped()
            node = nodes.get(current)
            if node is None:
                raise AutomationError(f"流程节点不存在: {current}")
            node_type = node.get("type")
            if node_type == "end":
                return
            if node_type == "action":
                step = node.get("step")
                if isinstance(step, dict) and step.get("enabled", True):
                    node_label = str(step.get("label", "")).strip() or current
                    self.current_context = f"流程节点 {node_label}"
                    self.log.emit(f"开始执行 | {self.current_context} | {self._step_label(step)}")
                    try:
                        self.execute_step(step)
                    except Exception as exc:
                        self._log_step_failure(self.current_context, step, exc)
                        raise
                    self.log.emit(f"步骤执行成功 | {self.current_context} | {self._step_label(step)}")
                next_port = "next"
            elif node_type == "condition":
                node_label = str(node.get("label", "")).strip() or current
                self.current_context = f"判断节点 {node_label}"
                self.log.emit(f"开始判断 | {self.current_context}")
                try:
                    result = self._evaluate_condition(node)
                except Exception as exc:
                    self.log.emit(f"判断执行失败 | {self.current_context} | {exc}")
                    raise
                self.log.emit(f"判断节点结果: {'是' if result else '否'}")
                next_port = "true" if result else "false"
            else:
                next_port = "next"
            visited_count[current] = visited_count.get(current, 0) + 1
            if visited_count[current] > 10000:
                raise AutomationError("流程循环次数超过 10000 次，请检查连线")
            choices = outgoing.get(current, [])
            matching = [edge for edge in choices if str(edge.get("port", "next")) == next_port]
            if not matching:
                label = {"true": "是", "false": "否", "next": "下一步"}.get(next_port, next_port)
                raise AutomationError(f"节点“{current}”缺少“{label}”连线")
            if len(matching) > 1:
                raise AutomationError(f"节点“{current}”的出口存在多条连线")
            current = str(matching[0].get("to", ""))

    def _evaluate_condition(self, node: dict[str, Any]) -> bool:
        operator = str(node.get("operator", "and")).lower()
        legacy_not = operator == "not"
        if legacy_not:
            operator = "and"
        conditions = node.get("conditions", [])
        if not isinstance(conditions, list):
            conditions = []
        results = [self._condition_image_exists(item) for item in conditions if isinstance(item, dict)]
        if not results:
            return False
        result = any(results) if operator == "or" else all(results)
        return not result if bool(node.get("negate", False)) or legacy_not else result

    @staticmethod
    def _permanent_capture_error(error: AutomationError) -> bool:
        detail = str(error)
        return "目标窗口已关闭" in detail or "请先执行查找窗口" in detail

    def _condition_image_exists(self, condition: dict[str, Any]) -> bool:
        image_path = self._resolve_input_path(str(condition.get("image", "")))
        if not image_path.exists():
            self.log.emit(f"判断图片不存在: {image_path}")
            return False
        try:
            cv2, template = self._read_color_image(image_path)
        except AutomationError as exc:
            self.log.emit(f"判断图片读取失败 | {image_path} | {exc}")
            return False
        confidence = _safe_float(condition.get("confidence", 0.85), 0.85, 0.1, 0.99)
        timeout = _safe_float(condition.get("timeout", 1.0), 1.0, 0.0)
        started = time.monotonic()
        best_match = TemplateMatch(-1.0, (0, 0), (template.shape[1], template.shape[0]), 1.0)
        capture_failures = 0
        last_capture_error = ""
        while time.monotonic() - started <= timeout:
            self._check_stopped()
            try:
                if self.last_window is not None:
                    cv2_module, frame, _origin = self._capture_window()
                else:
                    cv2_module, frame, _origin = self._capture()
                current = find_template_match(cv2_module, frame, template)
                if current.score > best_match.score:
                    best_match = current
                if current.score >= confidence:
                    return True
            except AutomationError as exc:
                if self.stop_event.is_set():
                    raise
                if self._permanent_capture_error(exc):
                    self.log.emit(f"判断图片识别异常 | {image_path.name} | {exc}")
                    return False
                capture_failures += 1
                last_capture_error = str(exc)
            self._sleep(0.15)
        detail = (
            f"最高匹配度 {max(best_match.score, 0.0):.3f} | "
            f"最佳缩放 {best_match.scale * 100:.1f}% | 截图失败 {capture_failures} 次"
        )
        if last_capture_error:
            detail += f" | 最后错误 {last_capture_error}"
        self.log.emit(
            f"判断图片未识别 | {image_path.name} | {detail} | "
            f"要求 {confidence:.2f} | 超时 {timeout:.2f} 秒"
        )
        return False

    def stop(self) -> None:
        self.stop_event.set()

    def _check_stopped(self) -> None:
        if self.stop_event.is_set():
            raise AutomationError("用户已停止脚本")

    def _sleep(self, seconds: float) -> None:
        end = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end:
            self._check_stopped()
            time.sleep(min(0.05, end - time.monotonic()))

    def execute_step(self, step: dict[str, Any]) -> None:
        step_type = step.get("type")
        if step_type in {"click", "double_click", "move"}:
            self._mouse_action(step_type, int(step.get("x", 0)), int(step.get("y", 0)))
        elif step_type == "drag":
            self._drag(
                int(step.get("start_x", 0)),
                int(step.get("start_y", 0)),
                int(step.get("end_x", 0)),
                int(step.get("end_y", 0)),
                float(step.get("duration", 0.8)),
            )
        elif step_type == "macro":
            self._run_macro(step)
        elif step_type == "press":
            self._press_key(str(step.get("key", "ENTER")))
        elif step_type == "type":
            self._type_text(str(step.get("text", "")))
        elif step_type == "wait":
            self._sleep(float(step.get("seconds", 1)))
        elif step_type in {"wait_image", "click_image"}:
            point = self._wait_for_image(step)
            if step_type == "click_image":
                offset = (int(step.get("offset_x", 0)), int(step.get("offset_y", 0)))
                click_point = (point[0] + offset[0], point[1] + offset[1])
                self.log.emit(
                    f"图片点击坐标 | 识别坐标 ({point[0]}, {point[1]}) | "
                    f"偏移 ({offset[0]}, {offset[1]}) | 最终坐标 ({click_point[0]}, {click_point[1]})"
                )
                self._mouse_action("click", click_point[0], click_point[1])
        elif step_type in {"window_wait_image", "window_click_image"}:
            point = self._wait_for_window_image(step)
            if step_type == "window_click_image":
                offset = (int(step.get("offset_x", 0)), int(step.get("offset_y", 0)))
                click_point = (point[0] + offset[0], point[1] + offset[1])
                self.log.emit(
                    f"窗口图片点击坐标 | 识别坐标 ({point[0]}, {point[1]}) | "
                    f"偏移 ({offset[0]}, {offset[1]}) | 最终坐标 ({click_point[0]}, {click_point[1]})"
                )
                self._mouse_action("click", click_point[0], click_point[1])
        elif step_type == "ocr":
            self._wait_for_ocr(step, window=False)
        elif step_type == "window_ocr":
            self._wait_for_ocr(step, window=True)
        elif step_type == "find_window":
            self._find_window(step)
        elif step_type == "screenshot":
            self._take_screenshot(str(step.get("path", "screenshot.png")))
        else:
            raise AutomationError(f"不支持的步骤类型: {step_type}")

    def _mouse_action(self, action: str, x: int, y: int) -> None:
        self.log.emit(f"执行鼠标动作 | {action} | 坐标 ({x}, {y})")
        if self.background_input and self.last_window is not None:
            self._post_background_mouse_action(action, x, y)
            return
        try:
            from pynput.mouse import Button, Controller
        except ImportError as exc:
            raise AutomationError("缺少 pynput，请先安装 requirements.txt") from exc
        mouse = Controller()
        mouse.position = (x, y)
        self._sleep(0.08)
        if action == "click":
            mouse.click(Button.left)
        elif action == "double_click":
            mouse.click(Button.left, 2)

    def _drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float) -> None:
        if self.background_input and self.last_window is not None:
            self._post_background_drag(start_x, start_y, end_x, end_y, duration)
            return
        try:
            from pynput.mouse import Button, Controller
        except ImportError as exc:
            raise AutomationError("缺少 pynput，请先安装 requirements.txt") from exc
        mouse = Controller()
        duration = max(0.05, duration)
        samples = max(2, int(duration / 0.02))
        mouse.position = (start_x, start_y)
        mouse.press(Button.left)
        try:
            for index in range(1, samples + 1):
                self._check_stopped()
                progress = index / samples
                x = round(start_x + (end_x - start_x) * progress)
                y = round(start_y + (end_y - start_y) * progress)
                mouse.position = (x, y)
                self._sleep(duration / samples)
        finally:
            mouse.release(Button.left)

    def _run_macro(self, step: dict[str, Any]) -> None:
        if self.background_input and self.last_window is not None:
            self._run_macro_background(step)
            return
        try:
            from pynput.keyboard import Controller as KeyboardController
            from pynput.mouse import Button, Controller as MouseController
        except ImportError as exc:
            raise AutomationError("缺少 pynput，请先安装 requirements.txt") from exc

        events = step.get("events", [])
        if not isinstance(events, list) or not events:
            raise AutomationError("宏动作没有可执行的事件")
        mode = step.get("mode", "once")
        if mode == "loop":
            rounds = None
        elif mode == "repeat":
            rounds = max(1, int(step.get("repeat", 1)))
        else:
            rounds = 1

        mouse = MouseController()
        keyboard = KeyboardController()
        pressed_mouse: set[Any] = set()
        pressed_keys: set[Any] = set()
        current_round = 0
        try:
            while rounds is None or current_round < rounds:
                current_round += 1
                self.log.emit(f"执行宏动作 {step.get('name', '未命名动作')} ({current_round}{' / ' + str(rounds) if rounds else ''})")
                for event in events:
                    self._sleep(float(event.get("dt", 0)))
                    self._check_stopped()
                    event_type = event.get("type")
                    if event_type == "mouse_move":
                        mouse.position = (int(event.get("x", 0)), int(event.get("y", 0)))
                    elif event_type in {"mouse_down", "mouse_up"}:
                        mouse.position = (int(event.get("x", 0)), int(event.get("y", 0)))
                        button = self._mouse_button(event.get("button", "left"), Button)
                        if event_type == "mouse_down":
                            mouse.press(button)
                            pressed_mouse.add(button)
                        else:
                            mouse.release(button)
                            pressed_mouse.discard(button)
                    elif event_type == "mouse_scroll":
                        mouse.position = (int(event.get("x", 0)), int(event.get("y", 0)))
                        mouse.scroll(int(event.get("dx", 0)), int(event.get("dy", 0)))
                    elif event_type in {"key_down", "key_up"}:
                        key = self._macro_key(event)
                        if event_type == "key_down":
                            keyboard.press(key)
                            pressed_keys.add(key)
                        else:
                            keyboard.release(key)
                            pressed_keys.discard(key)
                    else:
                        raise AutomationError(f"宏动作包含不支持的事件: {event_type}")
                if rounds is not None and current_round < rounds:
                    self._sleep(float(step.get("interval", 0.2)))
        finally:
            for button in list(pressed_mouse):
                mouse.release(button)
            for key in list(pressed_keys):
                keyboard.release(key)

    @staticmethod
    def _mouse_button(name: str, button_enum):
        return getattr(button_enum, str(name).lower(), button_enum.left)

    @staticmethod
    def _macro_key(event: dict[str, Any]):
        from pynput.keyboard import Key, KeyCode

        kind = event.get("key_kind", "special")
        value = event.get("key")
        if kind == "char" and value:
            return KeyCode.from_char(str(value))
        if kind == "vk" and value is not None:
            return KeyCode.from_vk(int(value))
        key = getattr(Key, str(value).lower(), None)
        if key is None:
            raise AutomationError(f"无法识别宏按键: {value}")
        return key

    def _press_key(self, key_name: str) -> None:
        if self.background_input and self.last_window is not None:
            self._post_background_key(key_name)
            return
        try:
            from pynput.keyboard import Controller, Key
        except ImportError as exc:
            raise AutomationError("缺少 pynput，请先安装 requirements.txt") from exc
        keyboard = Controller()
        normalized = key_name.strip()
        key = getattr(Key, normalized.lower(), None)
        if key is None and len(normalized) == 1:
            key = normalized
        if key is None:
            raise AutomationError(f"无法识别按键: {key_name}")
        keyboard.press(key)
        keyboard.release(key)

    def _type_text(self, value: str) -> None:
        if self.background_input and self.last_window is not None:
            self._post_background_text(value)
            return
        try:
            from pynput.keyboard import Controller
        except ImportError as exc:
            raise AutomationError("缺少 pynput，请先安装 requirements.txt") from exc
        keyboard = Controller()
        # Type one character at a time so a stop request can interrupt a long
        # text action instead of waiting for pynput's bulk type call to end.
        for character in value:
            self._check_stopped()
            keyboard.type(character)

    @staticmethod
    def _background_user32():
        if os.name != "nt":
            raise AutomationError("后台窗口消息输入仅支持 Windows")
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.EnumChildWindows.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.LPARAM]
        user32.EnumChildWindows.restype = wintypes.BOOL
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.restype = ctypes.c_int
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
        user32.GetWindowRect.restype = wintypes.BOOL
        user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
        user32.GetClientRect.restype = wintypes.BOOL
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.c_void_p]
        user32.ClientToScreen.restype = wintypes.BOOL
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW.restype = wintypes.BOOL
        user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.SendMessageW.restype = ctypes.c_ssize_t
        user32.SendMessageTimeoutW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
            wintypes.UINT,
            wintypes.UINT,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        user32.SendMessageTimeoutW.restype = ctypes.c_ssize_t
        user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
        user32.VkKeyScanW.restype = wintypes.SHORT
        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.IsIconic.restype = wintypes.BOOL
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.BringWindowToTop.argtypes = [wintypes.HWND]
        user32.BringWindowToTop.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        return ctypes, user32

    def _background_hwnd(self):
        if not self.last_window:
            raise AutomationError("尚未找到目标窗口")
        hwnd = int(self.last_window.get("hwnd", 0))
        ctypes, user32 = self._background_user32()
        if not hwnd or not user32.IsWindow(hwnd):
            raise AutomationError("目标窗口已关闭，请重新执行查找窗口步骤")
        return ctypes, user32, hwnd

    @staticmethod
    def _window_name(user32, hwnd: int) -> tuple[str, str]:
        import ctypes

        class_name_buffer = ctypes.create_unicode_buffer(256)
        title_length = max(0, int(user32.GetWindowTextLengthW(hwnd)))
        title_buffer = ctypes.create_unicode_buffer(title_length + 1)
        user32.GetClassNameW(hwnd, class_name_buffer, len(class_name_buffer))
        user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
        return class_name_buffer.value, title_buffer.value

    def _resolve_background_input_handle(self, window: dict[str, Any]) -> int:
        """Pick the renderer child window used by emulator-style Win32 hosts."""
        ctypes, user32 = self._background_user32()
        root = int(window.get("hwnd", 0))
        if not root or not user32.IsWindow(root):
            return root

        root_class, root_title = self._window_name(user32, root)
        emulator_hint = " ".join(
            str(window.get(key, "")) for key in ("title", "process_name")
        ).casefold()
        emulator_hint = f"{emulator_hint} {root_class} {root_title}".casefold()
        nox_hint = "nox" in emulator_hint or "夜神" in emulator_hint
        root_minimized = bool(window.get("minimized", False)) or bool(user32.IsIconic(root))

        class Rect(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        root_client = Rect()
        root_area = 0
        if user32.GetClientRect(root, ctypes.byref(root_client)):
            root_area = max(0, int(root_client.right - root_client.left)) * max(0, int(root_client.bottom - root_client.top))
        candidates: list[tuple[int, int, str, str, int, int]] = []
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_ssize_t)

        def callback(child_hwnd, _param):
            child = int(child_hwnd)
            if not user32.IsWindow(child):
                return True
            # Minimized emulator renderers are valid input/capture targets but
            # Windows marks their child HWNDs as invisible.
            if not root_minimized and not user32.IsWindowVisible(child):
                return True
            rect = Rect()
            client = Rect()
            if not user32.GetWindowRect(child, ctypes.byref(rect)):
                return True
            if not user32.GetClientRect(child, ctypes.byref(client)):
                return True
            width = max(0, int(client.right - client.left))
            height = max(0, int(client.bottom - client.top))
            if width < 80 or height < 80:
                return True
            class_name, title = self._window_name(user32, child)
            label = f"{class_name} {title}".casefold()
            known = any(token in label for token in (
                "mumuplayer", "nemuplayer", "mumunxdevice", "therender",
                "hd-player", "_ctl.w", "nox", "ldplayer",
            ))
            nox_renderer = nox_hint and (label.strip() == "sub" or " sub" in f" {label}")
            if nox_renderer:
                known = True
            area = width * height
            score = ((2 * 10**12) if nox_renderer else (10**12 if known else 0)) + area
            candidates.append((score, area, class_name, title, child, width * height))
            return True

        callback_instance = callback_type(callback)
        user32.EnumChildWindows(root, callback_instance, 0)
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
            selected = candidates[0]
            # Do not redirect ordinary Win32 windows to a small unrelated child.
            if selected[0] >= 10**12 or (root_area and selected[1] >= int(root_area * 0.9)):
                window["input_hwnd"] = int(selected[4])
                window["input_class"] = selected[2]
                window["input_title"] = selected[3]
                chain: list[int] = []
                current = int(selected[4])
                seen: set[int] = set()
                while current and current not in seen and current != root:
                    seen.add(current)
                    chain.append(current)
                    current = int(user32.GetParent(current) or 0)
                chain.reverse()
                # OAS forwards Nox button-down messages through the complete
                # child tree. Other emulator families receive input on the
                # selected renderer only.
                window["input_chain"] = ([root] + chain) if nox_hint and chain else [int(selected[4])]
                return int(selected[4])
        window["input_hwnd"] = root
        window["input_class"] = ""
        window["input_title"] = str(window.get("title", ""))
        window["input_chain"] = [root]
        return root

    def _background_input_handles(self) -> list[int]:
        """Return valid input targets from the root toward the renderer."""
        ctypes, user32, root = self._background_hwnd()
        window = self.last_window or {}
        raw_chain = window.get("input_chain", [])
        if not isinstance(raw_chain, list):
            raw_chain = []
        chain: list[int] = []
        for value in raw_chain:
            try:
                hwnd = int(value)
            except (TypeError, ValueError):
                continue
            if hwnd and user32.IsWindow(hwnd) and hwnd not in chain:
                chain.append(hwnd)
        if not chain:
            chain = [self._background_input_hwnd() or root]
        return chain

    def _background_input_hwnd(self) -> int:
        ctypes, user32, root = self._background_hwnd()
        window = self.last_window or {}
        target = int(window.get("input_hwnd", 0))
        if not target or not user32.IsWindow(target):
            target = self._resolve_background_input_handle(window)
        chain = window.get("input_chain")
        if not isinstance(chain, list) or not chain:
            window["input_chain"] = [target or root]
        return target or root

    def _activate_window(self, window: dict[str, Any]) -> None:
        """Restore and focus a target window before sending foreground input."""
        ctypes, user32 = self._background_user32()
        hwnd = int(window.get("hwnd", 0))
        if not hwnd or not user32.IsWindow(hwnd):
            raise AutomationError("目标窗口已关闭，无法激活")
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            self._sleep(0.08)
        user32.BringWindowToTop(hwnd)
        if not user32.SetForegroundWindow(hwnd):
            error = ctypes.get_last_error()
            raise AutomationError(f"无法激活目标窗口，错误码 {error}")
        self._sleep(0.08)

    @staticmethod
    def _pack_point(x: int, y: int) -> int:
        return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)

    def _background_client_point(self, x: int, y: int) -> tuple[int, int]:
        """Convert screen coordinates into the selected renderer's client space."""
        window = self.last_window or {}
        ctypes, user32, root = self._background_hwnd()
        target = self._background_input_hwnd()
        backend = self._emulator_capture_backend or {}
        main_hwnd = int(backend.get("main_hwnd", 0) or 0)
        main_minimized = bool(main_hwnd and user32.IsWindow(main_hwnd) and user32.IsIconic(main_hwnd))
        window["minimized"] = bool(
            user32.IsIconic(root)
            or main_minimized
            or (target != root and not user32.IsWindowVisible(target))
        )

        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        root_point = Point()
        root_ok = bool(user32.ClientToScreen(root, ctypes.byref(root_point)))
        if bool(window.get("minimized", False)):
            root_x = int(window.get("normal_x", window.get("x", 0)))
            root_y = int(window.get("normal_y", window.get("y", 0)))
            root_origin = (
                root_x + int(window.get("client_offset_x", 0)),
                root_y + int(window.get("client_offset_y", 0)),
            )
        elif root_ok:
            root_origin = (int(root_point.x), int(root_point.y))
        else:
            root_x = int(window.get("x", 0))
            root_y = int(window.get("y", 0))
            root_origin = (
                root_x + int(window.get("client_offset_x", 0)),
                root_y + int(window.get("client_offset_y", 0)),
            )
        point_x = int(x) - root_origin[0]
        point_y = int(y) - root_origin[1]

        if target == root:
            return point_x, point_y

        target_point = Point()
        if root_ok and user32.ClientToScreen(target, ctypes.byref(target_point)):
            # Keep the normal-window origin used by PrintWindow, but transfer
            # the child offset from the current window tree. This also works
            # while the parent is minimized because both points share the same
            # minimized coordinate space.
            point_x -= int(target_point.x - root_point.x)
            point_y -= int(target_point.y - root_point.y)

        class Rect(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        target_client = Rect()
        target_width = target_height = 0
        if user32.GetClientRect(target, ctypes.byref(target_client)):
            target_width = max(0, int(target_client.right - target_client.left))
            target_height = max(0, int(target_client.bottom - target_client.top))
        capture_width = int(window.get("capture_width", window.get("client_width", 0)))
        capture_height = int(window.get("capture_height", window.get("client_height", 0)))
        if target_width > 0 and capture_width > 0 and target_width != capture_width:
            point_x = round(point_x * target_width / capture_width)
        if target_height > 0 and capture_height > 0 and target_height != capture_height:
            point_y = round(point_y * target_height / capture_height)
        return int(point_x), int(point_y)

    def _post_background_message(self, message: int, wparam: int, lparam: int, hwnd: int | None = None) -> None:
        ctypes, user32, root = self._background_hwnd()
        target = int(hwnd or root)
        if not user32.PostMessageW(target, message, wparam, lparam):
            error = ctypes.get_last_error()
            raise AutomationError(f"无法发送后台窗口消息，错误码 {error}")

    def _send_background_message(self, message: int, wparam: int, lparam: int, hwnd: int | None = None) -> None:
        ctypes, user32, root = self._background_hwnd()
        target = int(hwnd or self._background_input_hwnd() or root)
        # Synchronous messages are important for emulator renderer children:
        # they often do not consume a queued PostMessage click reliably.
        result = ctypes.c_size_t()
        # A hung renderer must not block the worker forever.  OAS uses
        # synchronous delivery, while the timeout keeps stop/retry usable.
        sent = user32.SendMessageTimeoutW(
            target,
            message,
            wparam,
            lparam,
            0x0002,  # SMTO_ABORTIFHUNG
            800,
            ctypes.byref(result),
        )
        if not sent:
            error = ctypes.get_last_error()
            raise AutomationError(
                f"后台窗口消息发送超时或失败 | HWND {target} | 消息 0x{message:04X} | 错误码 {error}"
            )

    def _release_background_inputs(
        self, releases: list[tuple[int, int, int, int]], *, synchronous: bool = False
    ) -> None:
        """Release every posted down, without letting one failed window block the rest."""
        original_error = sys.exc_info()[1]
        release_error = None
        for message, wparam, lparam, hwnd in reversed(releases):
            try:
                if synchronous:
                    self._send_background_message(message, wparam, lparam, hwnd)
                else:
                    self._post_background_message(message, wparam, lparam, hwnd)
            except Exception as exc:
                self.log.emit(f"后台输入释放失败 | HWND {hwnd} | {exc}")
                if release_error is None:
                    release_error = exc
        if release_error is not None and original_error is None:
            raise release_error

    def _post_background_mouse_move(self, x: int, y: int, buttons: int = 0) -> None:
        client_x, client_y = self._background_client_point(x, y)
        self._post_background_message(
            0x0200,
            buttons,
            self._pack_point(client_x, client_y),
            self._background_input_hwnd(),
        )

    @staticmethod
    def _background_mouse_messages(button: str) -> tuple[int, int, int]:
        values = {
            "left": (0x0201, 0x0202, 0x0001),
            "right": (0x0204, 0x0205, 0x0002),
            "middle": (0x0207, 0x0208, 0x0010),
            "xbutton1": (0x020B, 0x020C, 0x0020),
            "xbutton2": (0x020B, 0x020C, 0x0040),
        }
        return values.get(str(button).lower(), values["left"])

    @staticmethod
    def _background_mouse_wparams(button: str, mask: int) -> tuple[int, int]:
        xbutton = {"xbutton1": 1, "xbutton2": 2}.get(str(button).lower(), 0)
        button_id = xbutton << 16
        return button_id | mask, button_id

    def _post_background_mouse_action(self, action: str, x: int, y: int) -> None:
        down_message, up_message, button_mask = self._background_mouse_messages("left")
        ctypes, user32, root = self._background_hwnd()
        targets = self._background_input_handles()
        target = targets[-1]
        client_point = self._pack_point(*self._background_client_point(x, y))
        # OASX/OAS activate the root window but deliver mouse messages to the
        # renderer child (MuMuPlayer/NemuPlayer/TheRender, etc.).
        self._send_background_message(0x0006, 1, 0, root)  # WM_ACTIVATE / WA_ACTIVE
        self._send_background_message(0x0006, 1, 0, target)  # renderer focus
        self._post_background_mouse_move(x, y)
        self._send_background_message(0x0084, 0, client_point, target)  # WM_NCHITTEST
        if action == "move":
            return
        self._send_background_message(0x0020, target, self._pack_point(1, 0x0201), target)  # WM_SETCURSOR
        for click_index in range(2 if action == "double_click" else 1):
            if click_index:
                self._sleep(0.05)
            held: list[tuple[int, int, int, int]] = []
            try:
                for destination in targets:
                    self._send_background_message(down_message, button_mask, client_point, destination)
                    held.append((up_message, 0, client_point, destination))
                self._sleep(0.04)
            finally:
                self._release_background_inputs(held, synchronous=True)
        self.log.emit(
            f"后台点击消息已发送 | HWND {target} | 客户区坐标 ({client_point & 0xFFFF}, {(client_point >> 16) & 0xFFFF})"
        )

    def _post_background_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float,
    ) -> None:
        down_message, up_message, button_mask = self._background_mouse_messages("left")
        ctypes, user32, root = self._background_hwnd()
        targets = self._background_input_handles()
        target = targets[-1]
        duration = max(0.05, float(duration))
        samples = max(2, int(duration / 0.02))
        # Keep the parent active, but send the actual mouse stream to the
        # renderer child.  Sending the button-down to the root window leaves
        # emulator drag operations in a pressed-but-untracked state.
        self._send_background_message(0x0006, 1, 0, root)  # WM_ACTIVATE / WA_ACTIVE
        self._send_background_message(0x0006, 1, 0, target)  # renderer focus
        self._post_background_mouse_move(start_x, start_y)
        start_point = self._pack_point(*self._background_client_point(start_x, start_y))
        self._send_background_message(0x0084, 0, start_point, target)  # WM_NCHITTEST
        self._send_background_message(0x0020, target, self._pack_point(1, 0x0201), target)  # WM_SETCURSOR
        held: list[tuple[int, int, int, int]] = []
        try:
            for destination in targets:
                self._send_background_message(down_message, button_mask, start_point, destination)
                held.append((up_message, 0, start_point, destination))
            for index in range(1, samples + 1):
                self._check_stopped()
                progress = index / samples
                x = round(start_x + (end_x - start_x) * progress)
                y = round(start_y + (end_y - start_y) * progress)
                self._post_background_mouse_move(x, y, button_mask)
                point = self._pack_point(*self._background_client_point(x, y))
                held = [(message, wparam, point, hwnd) for message, wparam, _, hwnd in held]
                self._sleep(duration / samples)
        finally:
            self._release_background_inputs(held, synchronous=True)
        self.log.emit(
            f"后台拖拽消息已发送 | HWND {target} | 起点 ({start_x}, {start_y}) | "
            f"终点 ({end_x}, {end_y})"
        )

    @staticmethod
    def _background_key_code(value: Any, kind: str = "special") -> int:
        if kind == "vk":
            return int(value)
        if kind == "char":
            text = str(value or "")
            if not text:
                raise AutomationError("空字符无法转换为按键")
            ctypes, user32 = ScriptWorker._background_user32()
            code = int(user32.VkKeyScanW(text[0]))
            if code < 0:
                raise AutomationError(f"无法转换按键字符: {text[0]}")
            return code & 0xFF
        names = {
            "backspace": 0x08,
            "tab": 0x09,
            "enter": 0x0D,
            "shift": 0x10,
            "shift_l": 0xA0,
            "shift_r": 0xA1,
            "ctrl": 0x11,
            "ctrl_l": 0xA2,
            "ctrl_r": 0xA3,
            "alt": 0x12,
            "alt_l": 0xA4,
            "alt_r": 0xA5,
            "pause": 0x13,
            "caps_lock": 0x14,
            "esc": 0x1B,
            "space": 0x20,
            "page_up": 0x21,
            "page_down": 0x22,
            "end": 0x23,
            "home": 0x24,
            "left": 0x25,
            "up": 0x26,
            "right": 0x27,
            "down": 0x28,
            "insert": 0x2D,
            "delete": 0x2E,
            "num_lock": 0x90,
            "scroll_lock": 0x91,
            "print_screen": 0x2C,
        }
        normalized = str(value or "").strip().lower()
        if normalized in names:
            return names[normalized]
        if len(normalized) == 1 and ("a" <= normalized <= "z" or "0" <= normalized <= "9"):
            return ord(normalized.upper())
        if normalized.startswith("f") and normalized[1:].isdigit():
            function_number = int(normalized[1:])
            if 1 <= function_number <= 24:
                return 0x6F + function_number
        raise AutomationError(f"无法转换后台按键: {value}")

    def _post_background_key_event(self, value: Any, kind: str, pressed: bool, hwnd: int | None = None) -> None:
        code = self._background_key_code(value, kind)
        self._post_background_message(
            0x0100 if pressed else 0x0101,
            code,
            1 if pressed else 0xC0000001,
            hwnd or self._background_input_hwnd(),
        )

    def _post_background_key(self, key_name: str) -> None:
        key = key_name.strip()
        target = self._background_input_hwnd()
        code = self._background_key_code(key, "special")
        held: list[tuple[int, int, int, int]] = []
        try:
            self._post_background_key_event(key, "special", True, target)
            held.append((0x0101, code, 0xC0000001, target))
            self._sleep(0.04)
        finally:
            self._release_background_inputs(held)

    def _post_background_text(self, value: str) -> None:
        for character in value:
            self._check_stopped()
            self._post_background_message(0x0102, ord(character), 1, self._background_input_hwnd())

    def _post_background_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        target = self._background_input_hwnd()
        # WM_MOUSEWHEEL / WM_MOUSEHWHEEL lParam is a screen point, unlike mouse button messages.
        point = self._pack_point(x, y)
        if dy:
            wheel_delta = max(-120 * 120, min(120 * 120, int(dy) * 120))
            self._post_background_message(0x020A, (wheel_delta & 0xFFFF) << 16, point, target)
        if dx:
            wheel_delta = max(-120 * 120, min(120 * 120, int(dx) * 120))
            self._post_background_message(0x020E, (wheel_delta & 0xFFFF) << 16, point, target)

    def _run_macro_background(self, step: dict[str, Any]) -> None:
        events = step.get("events", [])
        if not isinstance(events, list) or not events:
            raise AutomationError("宏动作没有可执行的事件")
        mode = step.get("mode", "once")
        if mode == "loop":
            rounds = None
        elif mode == "repeat":
            rounds = max(1, int(step.get("repeat", 1)))
        else:
            rounds = 1
        current_round = 0
        pressed_mouse: dict[tuple[str, int], tuple[int, int, int, int]] = {}
        pressed_keys: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        try:
            while rounds is None or current_round < rounds:
                current_round += 1
                _, _, root = self._background_hwnd()
                target = self._background_input_hwnd()
                self._send_background_message(0x0006, 1, 0, root)  # WM_ACTIVATE
                self._send_background_message(0x0006, 1, 0, target)  # renderer focus
                self.log.emit(
                    f"执行后台宏动作 {step.get('name', '未命名动作')} "
                    f"({current_round}{' / ' + str(rounds) if rounds else ''})"
                )
                for event in events:
                    self._sleep(float(event.get("dt", 0)))
                    self._check_stopped()
                    event_type = event.get("type")
                    if event_type == "mouse_move":
                        x, y = int(event.get("x", 0)), int(event.get("y", 0))
                        buttons = 0
                        for button, _destination in pressed_mouse:
                            buttons |= self._background_mouse_messages(button)[2]
                        self._post_background_mouse_move(x, y, buttons)
                        point = self._pack_point(*self._background_client_point(x, y))
                        for identity, (message, wparam, _old_point, destination) in pressed_mouse.items():
                            pressed_mouse[identity] = (message, wparam, point, destination)
                    elif event_type in {"mouse_down", "mouse_up"}:
                        button = str(event.get("button", "left")).lower()
                        down_message, up_message, button_mask = self._background_mouse_messages(button)
                        down_wparam, up_wparam = self._background_mouse_wparams(button, button_mask)
                        point = self._pack_point(*self._background_client_point(int(event.get("x", 0)), int(event.get("y", 0))))
                        if event_type == "mouse_down":
                            for destination in self._background_input_handles():
                                self._post_background_message(down_message, down_wparam, point, destination)
                                pressed_mouse[(button, destination)] = (up_message, up_wparam, point, destination)
                        else:
                            held = [identity for identity in pressed_mouse if identity[0] == button]
                            if not held:
                                held = [(button, self._background_input_hwnd())]
                            for identity in reversed(held):
                                destination = identity[1]
                                self._post_background_message(up_message, up_wparam, point, destination)
                                pressed_mouse.pop(identity, None)
                    elif event_type == "mouse_scroll":
                        self._post_background_scroll(
                            int(event.get("x", 0)),
                            int(event.get("y", 0)),
                            int(event.get("dx", 0)),
                            int(event.get("dy", 0)),
                        )
                    elif event_type in {"key_down", "key_up"}:
                        value = event.get("key", "")
                        kind = str(event.get("key_kind", "special"))
                        code = self._background_key_code(value, kind)
                        if event_type == "key_down":
                            destination = self._background_input_hwnd()
                            self._post_background_key_event(value, kind, True, destination)
                            pressed_keys[(code, destination)] = (0x0101, code, 0xC0000001, destination)
                        else:
                            held = [identity for identity in pressed_keys if identity[0] == code]
                            if not held:
                                held = [(code, self._background_input_hwnd())]
                            for identity in reversed(held):
                                self._post_background_key_event(value, kind, False, identity[1])
                                pressed_keys.pop(identity, None)
                    else:
                        raise AutomationError(f"后台宏不支持的事件: {event_type}")
                if rounds is not None and current_round < rounds:
                    self._sleep(float(step.get("interval", 0.2)))
        finally:
            self._release_background_inputs([*pressed_mouse.values(), *pressed_keys.values()])

    def _capture(self):
        try:
            import cv2
            import mss
            import numpy as np
        except ImportError as exc:
            raise AutomationError(f"图像依赖加载失败: {exc}") from exc
        with mss.mss() as sct:
            # monitor 0 is the complete virtual desktop, including secondary
            # displays and negative origins on Windows.
            monitor = sct.monitors[0]
            shot = np.array(sct.grab(monitor))
        frame = shot[:, :, :3]
        self._last_capture_backend = "桌面截图"
        self._last_capture_detail = f"{frame.shape[1]}x{frame.shape[0]}"
        return cv2, frame, (monitor["left"], monitor["top"])

    def _resolve_input_path(self, value: str) -> Path:
        # Keep path resolution in one place so task-relative assets continue to
        # work for both the source tree and packaged applications.  An empty
        # value is intentionally mapped to the base directory; _read_color_image
        # will turn it into a useful validation error instead of feeding a
        # directory/empty buffer to OpenCV.
        raw_text = str(value or "").strip()
        if os.sep != "\\":
            raw_text = raw_text.replace("\\", os.sep)
        path = Path(raw_text).expanduser()
        if path.is_absolute():
            return path.resolve(strict=False)
        roots: list[Path] = []
        if self.output_dir is not None:
            roots.append(self.output_dir)
        roots.extend([self.base_dir, Path.cwd().resolve()])
        if getattr(sys, "frozen", False):
            roots.append(Path(sys.executable).resolve(strict=False).parent)
        else:
            roots.append(Path(__file__).resolve(strict=False).parent)
        candidates: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            candidate = (root / path).resolve(strict=False)
            key = os.path.normcase(str(candidate))
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
            if candidate.exists():
                return candidate
        return candidates[0] if candidates else (self.base_dir / path).resolve(strict=False)

    @staticmethod
    def _read_color_image(path: Path):
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise AutomationError(f"OpenCV/NumPy 加载失败: {exc}") from exc
        path = Path(path)
        if not str(path).strip():
            raise AutomationError("未设置模板图片路径")
        try:
            if not path.exists():
                raise AutomationError(f"模板图片不存在: {path}")
            if not path.is_file():
                raise AutomationError(f"模板图片路径不是文件: {path}")
            size = path.stat().st_size
            if size <= 0:
                raise AutomationError(f"模板图片为空（0 字节）: {path}")
            data = path.read_bytes()
        except AutomationError:
            raise
        except (OSError, ValueError) as exc:
            raise AutomationError(f"无法读取模板图片: {path}（{exc}）") from exc
        if not data:
            raise AutomationError(f"模板图片为空（0 字节）: {path}")
        encoded = np.frombuffer(data, dtype=np.uint8)
        try:
            image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        except cv2.error as exc:
            raise AutomationError(
                f"模板图片解析失败: {path}（文件大小 {len(data)} 字节，可能已损坏或格式不受支持）"
            ) from exc
        if image is None:
            raise AutomationError(
                f"模板图片解析失败: {path}（文件大小 {len(data)} 字节，可能已损坏或格式不受支持）"
            )
        return cv2, image

    @staticmethod
    def _decode_json_output(data: bytes) -> dict[str, Any]:
        for encoding in ("utf-8-sig", "utf-16", "gb18030"):
            try:
                value = json.loads(data.decode(encoding))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                return value
        return {}

    def _resolve_emulator_capture_backend(self) -> dict[str, Any] | None:
        """Resolve an ADB framebuffer for the selected emulator instance."""
        if self._emulator_capture_backend is not None:
            return self._emulator_capture_backend
        now = time.monotonic()
        if self._emulator_capture_checked and now < self._emulator_capture_retry_at:
            return None
        self._emulator_capture_checked = True
        window = self.last_window or {}
        hint = " ".join(
            str(window.get(key, ""))
            for key in ("title", "process_name", "input_class", "input_title")
        ).casefold()
        if not any(token in hint for token in ("mumu", "nemu", "夜神", "nox", "雷电", "ldplayer", "dnplayer")):
            self._emulator_capture_error = "当前窗口未识别为支持 ADB 回退的模拟器"
            self._emulator_capture_retry_at = now + 30.0
            return None

        candidates: list[Path] = []
        roots: list[Path] = []
        process_path = str(window.get("process_path", ""))
        if process_path:
            roots.extend(Path(process_path).parents)
        for environment_name in ("ProgramFiles", "ProgramFiles(x86)"):
            value = os.environ.get(environment_name)
            if value:
                roots.append(Path(value))
        roots.extend(Path(drive + "\\") for drive in ("C:", "D:", "E:", "F:"))

        manager_names = ("MuMuManager.exe", "MuMuManagerGlobal.exe")
        for root in roots:
            for relative in (
                Path("nx_main"), Path("MuMuPlayer") / "nx_main",
                Path("Netease") / "MuMuPlayer-12.0" / "shell",
            ):
                folder = root / relative
                for name in manager_names:
                    manager = folder / name
                    if manager.is_file() and manager not in candidates:
                        candidates.append(manager)
        # The common MuMu install can be on a non-system drive. A bounded
        # direct probe avoids recursively scanning entire disks.
        for drive in ("C:", "D:", "E:", "F:"):
            for relative in (
                Path("MuMuPlayer") / "nx_main" / "MuMuManager.exe",
                Path("Program Files") / "Netease" / "MuMuPlayer-12.0" / "shell" / "MuMuManager.exe",
            ):
                manager = Path(drive + "\\") / relative
                if manager.is_file() and manager not in candidates:
                    candidates.append(manager)

        root_hwnd = int(window.get("hwnd", 0))
        root_pid = 0
        if root_hwnd:
            try:
                import ctypes
                from ctypes import wintypes

                user32 = ctypes.WinDLL("user32", use_last_error=True)
                user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
                user32.GetWindowThreadProcessId.restype = wintypes.DWORD
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(root_hwnd, ctypes.byref(pid))
                root_pid = int(pid.value)
            except (OSError, ValueError):
                root_pid = 0
        for manager in candidates:
            try:
                result = subprocess.run(
                    [str(manager), "info", "--vmindex", "all"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=4,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            instances = self._decode_json_output(result.stdout)
            for instance in instances.values():
                if not isinstance(instance, dict) or not instance.get("is_android_started"):
                    continue
                def parse_hwnd(value: Any) -> int:
                    text = str(value or "").strip()
                    try:
                        return int(text, 16) if text else 0
                    except ValueError:
                        return 0

                main_hwnd = parse_hwnd(instance.get("main_wnd"))
                render_hwnd = parse_hwnd(instance.get("render_wnd"))
                try:
                    instance_pid = int(instance.get("pid", 0) or 0)
                except (TypeError, ValueError):
                    instance_pid = 0
                handle_matches = root_hwnd in {main_hwnd, render_hwnd}
                process_matches = bool(root_pid and instance_pid and root_pid == instance_pid)
                if root_hwnd and not handle_matches and not process_matches:
                    continue
                host = str(instance.get("adb_host_ip", "127.0.0.1"))
                port = int(instance.get("adb_port", 0) or 0)
                if not port:
                    continue
                adb_candidates = [
                    manager.parent / "adb.exe",
                    manager.parent.parent / "nx_device" / str(instance.get("android_version", "")) / "shell" / "adb.exe",
                ]
                adb = next((path for path in adb_candidates if path.is_file()), None)
                if adb is None:
                    continue
                self._emulator_capture_backend = {
                    "kind": "adb",
                    "adb": adb,
                    "serial": f"{host}:{port}",
                    "vmindex": str(instance.get("index", "")),
                    "name": str(instance.get("name", "")),
                    "main_hwnd": main_hwnd,
                    "render_hwnd": render_hwnd,
                    "pid": instance_pid,
                }
                # MuMu exposes several sibling top-level windows. Regardless
                # of which one the user selected, messages must go to the
                # renderer HWND reported for the same VM process.
                if render_hwnd:
                    try:
                        _, input_user32 = self._background_user32()
                        if input_user32.IsWindow(render_hwnd):
                            input_class, input_title = self._window_name(input_user32, render_hwnd)
                            window["input_hwnd"] = render_hwnd
                            window["input_class"] = input_class
                            window["input_title"] = input_title
                            window["input_chain"] = [render_hwnd]
                    except (AutomationError, OSError, ValueError):
                        pass
                self._emulator_capture_error = ""
                self._emulator_capture_retry_at = 0.0
                return self._emulator_capture_backend
        self._emulator_capture_error = "未找到与目标窗口对应的模拟器 ADB 实例"
        self._emulator_capture_retry_at = time.monotonic() + 3.0
        return None

    def _capture_emulator_frame(self, width: int, height: int):
        backend = self._resolve_emulator_capture_backend()
        if not backend:
            return None
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise AutomationError(f"图像依赖加载失败: {exc}") from exc
        adb = str(backend["adb"])
        serial = str(backend["serial"])
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        def run_adb(arguments: list[str], timeout: float = 8):
            return subprocess.run(
                [adb, *arguments],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                creationflags=creationflags,
                check=False,
            )

        def output_text(result) -> str:
            data = (result.stdout or b"") + (result.stderr or b"")
            return data.decode("utf-8", errors="replace").strip()

        def ensure_connected() -> bool:
            try:
                state = run_adb(["-s", serial, "get-state"], timeout=4)
                if state.returncode == 0 and state.stdout.decode("utf-8", errors="replace").strip() == "device":
                    backend["adb_ready"] = True
                    return True
                connection = run_adb(["connect", serial], timeout=6)
                detail = output_text(connection)
                state = run_adb(["-s", serial, "get-state"], timeout=4)
            except (OSError, subprocess.SubprocessError) as exc:
                backend["adb_ready"] = False
                self._emulator_capture_error = f"ADB 自动连接失败 | {serial} | {exc}"
                return False
            if state.returncode == 0 and state.stdout.decode("utf-8", errors="replace").strip() == "device":
                backend["adb_ready"] = True
                if not backend.get("adb_connection_logged"):
                    backend["adb_connection_logged"] = True
                    self.log.emit(f"ADB 已自动连接 | {serial}")
                return True
            backend["adb_ready"] = False
            state_detail = output_text(state)
            self._emulator_capture_error = (
                f"ADB 设备未连接 | {serial} | "
                f"{state_detail or detail or '模拟器未开放 ADB 连接'}"
            )
            return False

        if not backend.get("adb_ready") and not ensure_connected():
            return None

        result = None
        payload = b""
        for attempt in range(2):
            try:
                result = run_adb(["-s", serial, "exec-out", "screencap", "-p"])
            except (OSError, subprocess.SubprocessError) as exc:
                backend["adb_ready"] = False
                self._emulator_capture_error = f"ADB 截图命令失败: {exc}"
                return None
            payload = result.stdout or b""
            if result.returncode == 0 and payload:
                break
            detail = output_text(result)
            backend["adb_ready"] = False
            if attempt == 0 and ensure_connected():
                self.log.emit(f"ADB 截图连接已恢复，正在重试 | {serial}")
                continue
            self._emulator_capture_error = (
                f"ADB 截图失败 | {serial} | "
                f"{detail or f'返回空数据（退出码 {result.returncode}，{len(payload)} 字节）'}"
            )
            return None

        # Never feed an empty buffer to OpenCV. The connection checks above
        # also turn MuMu's transient device-not-found response into one retry.
        if not payload:
            self._emulator_capture_error = f"ADB 截图返回空数据 | {serial}"
            return None
        try:
            frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        except cv2.error as exc:
            self._emulator_capture_error = f"ADB 截图解析失败（{len(payload)} 字节）: {exc}"
            return None
        if frame is None:
            self._emulator_capture_error = f"ADB 截图解析失败（{len(payload)} 字节，返回内容不是有效图片）"
            return None
        source_height, source_width = frame.shape[:2]
        content = (0, 0, source_width, source_height)
        if width > 0 and height > 0 and (source_width != width or source_height != height):
            frame, content = fit_frame_to_size(cv2, frame, width, height)
        if not self._emulator_capture_logged:
            self._emulator_capture_logged = True
            left, top, content_width, content_height = content
            self.log.emit(
                f"模拟器截图已切换到 ADB | {backend.get('name') or backend['serial']} | "
                f"原始 {source_width}x{source_height} | 匹配尺寸 {frame.shape[1]}x{frame.shape[0]} | "
                f"内容区域 ({left}, {top}, {content_width}x{content_height})"
            )
        return frame

    def _capture_window(self):
        """Capture the target window client area through PrintWindow.

        The returned origin is expressed in screen coordinates so existing
        background input and foreground mouse actions can consume it directly.
        """
        if os.name != "nt":
            raise AutomationError("窗口内截图仅支持 Windows")
        try:
            import ctypes
            from ctypes import wintypes

            import cv2
            import numpy as np
        except ImportError as exc:
            raise AutomationError(f"图像依赖加载失败: {exc}") from exc
        if not self.last_window:
            raise AutomationError("请先执行查找窗口步骤")

        class Rect(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class BitmapInfoHeader(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        class BitmapInfo(ctypes.Structure):
            _fields_ = [
                ("bmiHeader", BitmapInfoHeader),
                ("bmiColors", wintypes.DWORD * 3),
            ]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        hwnd_type = wintypes.HWND
        handle_type = ctypes.c_void_p
        user32.IsWindow.argtypes = [hwnd_type]
        user32.IsWindow.restype = wintypes.BOOL
        user32.GetClientRect.argtypes = [hwnd_type, ctypes.POINTER(Rect)]
        user32.GetClientRect.restype = wintypes.BOOL
        user32.ClientToScreen.argtypes = [hwnd_type, ctypes.c_void_p]
        user32.ClientToScreen.restype = wintypes.BOOL
        user32.GetWindowLongW.argtypes = [hwnd_type, ctypes.c_int]
        user32.GetWindowLongW.restype = wintypes.LONG
        user32.AdjustWindowRectEx.argtypes = [
            ctypes.POINTER(Rect),
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        user32.AdjustWindowRectEx.restype = wintypes.BOOL
        user32.PrintWindow.argtypes = [hwnd_type, handle_type, wintypes.UINT]
        user32.PrintWindow.restype = wintypes.BOOL
        user32.GetDC.argtypes = [hwnd_type]
        user32.GetDC.restype = handle_type
        user32.ReleaseDC.argtypes = [hwnd_type, handle_type]
        user32.ReleaseDC.restype = ctypes.c_int
        gdi32.CreateCompatibleDC.argtypes = [handle_type]
        gdi32.CreateCompatibleDC.restype = handle_type
        gdi32.CreateCompatibleBitmap.argtypes = [handle_type, ctypes.c_int, ctypes.c_int]
        gdi32.CreateCompatibleBitmap.restype = handle_type
        gdi32.SelectObject.argtypes = [handle_type, handle_type]
        gdi32.SelectObject.restype = handle_type
        gdi32.DeleteObject.argtypes = [handle_type]
        gdi32.DeleteObject.restype = wintypes.BOOL
        gdi32.DeleteDC.argtypes = [handle_type]
        gdi32.DeleteDC.restype = wintypes.BOOL
        gdi32.GetDIBits.argtypes = [
            handle_type,
            handle_type,
            wintypes.UINT,
            wintypes.UINT,
            handle_type,
            ctypes.POINTER(BitmapInfo),
            wintypes.UINT,
        ]
        gdi32.GetDIBits.restype = ctypes.c_int

        root_hwnd = hwnd_type(int(self.last_window.get("hwnd", 0)))
        if not root_hwnd or not user32.IsWindow(root_hwnd):
            raise AutomationError("目标窗口已关闭，请重新查找窗口")
        window = self.last_window
        backend = self._resolve_emulator_capture_backend() if self.background_input else None
        root_minimized = bool(user32.IsIconic(root_hwnd))
        # Background input and recognition must use the same renderer child.
        # Capturing the top-level frame while clicking a child shifts the
        # match point by the emulator toolbar/child offset.
        hwnd = root_hwnd
        if self.background_input:
            try:
                candidate = int(self._background_input_hwnd())
            except AutomationError:
                candidate = int(root_hwnd)
            if candidate and user32.IsWindow(hwnd_type(candidate)):
                hwnd = hwnd_type(candidate)
        main_minimized = False
        if backend:
            main_hwnd = int(backend.get("main_hwnd", 0) or 0)
            if main_hwnd and user32.IsWindow(hwnd_type(main_hwnd)):
                main_minimized = bool(user32.IsIconic(hwnd_type(main_hwnd)))
        renderer_hidden = self.background_input and not bool(user32.IsWindowVisible(hwnd))
        # A sibling render HWND is not itself iconic when MuMu minimizes its
        # main window; it simply becomes hidden and PrintWindow returns black.
        window["minimized"] = bool(root_minimized or main_minimized or renderer_hidden)
        client = Rect()
        has_client_rect = bool(user32.GetClientRect(hwnd, ctypes.byref(client)))
        width = int(client.right - client.left)
        height = int(client.bottom - client.top)
        client_offset_x = int(window.get("client_offset_x", 0))
        client_offset_y = int(window.get("client_offset_y", 0))
        if (not has_client_rect or width <= 0 or height <= 0) and bool(window.get("minimized", False)):
            # A minimized window can report a 0x0 client rect. Derive the
            # normal client size from its style so PrintWindow still gets a
            # correctly sized buffer without restoring the window.
            if int(hwnd.value or 0) == int(root_hwnd.value or 0):
                style = int(user32.GetWindowLongW(hwnd, -16)) & 0xFFFFFFFF
                ex_style = int(user32.GetWindowLongW(hwnd, -20)) & 0xFFFFFFFF
                adjusted = Rect()
                if user32.AdjustWindowRectEx(ctypes.byref(adjusted), style, False, ex_style):
                    client_offset_x = max(0, int(-adjusted.left))
                    client_offset_y = max(0, int(-adjusted.top))
                    normal_width = int(window.get("normal_width", 0))
                    normal_height = int(window.get("normal_height", 0))
                    width = normal_width - int(adjusted.right - adjusted.left)
                    height = normal_height - int(adjusted.bottom - adjusted.top)
                    window["client_width"] = max(0, width)
                    window["client_height"] = max(0, height)
                    window["client_offset_x"] = client_offset_x
                    window["client_offset_y"] = client_offset_y
            else:
                # Renderer children generally retain their normal dimensions
                # while the parent is minimized. Use the last known frame if
                # Windows reports a transient 0x0 client rect.
                width = int(window.get("capture_width", 0))
                height = int(window.get("capture_height", 0))
                if width <= 0 or height <= 0:
                    child_rect = Rect()
                    if user32.GetWindowRect(hwnd, ctypes.byref(child_rect)):
                        width = max(0, int(child_rect.right - child_rect.left))
                        height = max(0, int(child_rect.bottom - child_rect.top))
                if width <= 0 or height <= 0:
                    width = int(window.get("client_width", 0))
                    height = int(window.get("client_height", 0))
        if width <= 0 or height <= 0:
            raise AutomationError("目标窗口客户区没有有效尺寸")
        window["capture_width"] = int(width)
        window["capture_height"] = int(height)
        capture_hwnd = int(hwnd.value or 0)
        if int(window.get("capture_log_hwnd", 0)) != capture_hwnd:
            window["capture_log_hwnd"] = capture_hwnd
            capture_kind = "渲染子窗口" if capture_hwnd != int(root_hwnd.value or 0) else "顶层窗口"
            self.log.emit(
                f"后台截图目标 | {capture_kind} HWND {capture_hwnd} | 尺寸 {width}x{height}"
            )

        screen_dc = user32.GetDC(0)
        if not screen_dc:
            raise AutomationError("无法创建屏幕设备上下文")
        memory_dc = None
        bitmap = None
        old_bitmap = None
        try:
            memory_dc = gdi32.CreateCompatibleDC(screen_dc)
            bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
            if not memory_dc or not bitmap:
                raise AutomationError("无法创建窗口截图缓冲区")
            old_bitmap = gdi32.SelectObject(memory_dc, bitmap)
            if not old_bitmap:
                raise AutomationError("无法初始化窗口截图缓冲区")
            # PW_CLIENTONLY renders only the client area; flag 2 asks DWM to
            # render the full content when the window is minimized.
            captured = bool(user32.PrintWindow(hwnd, memory_dc, 0x00000003))
            if not captured:
                captured = bool(user32.PrintWindow(hwnd, memory_dc, 0x00000001))
            if not captured and not bool(window.get("minimized", False)) and backend is None:
                error = ctypes.get_last_error()
                raise AutomationError(f"目标窗口不支持后台截图，错误码 {error}")
            if captured:
                info = BitmapInfo()
                info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
                info.bmiHeader.biWidth = width
                info.bmiHeader.biHeight = -height
                info.bmiHeader.biPlanes = 1
                info.bmiHeader.biBitCount = 32
                info.bmiHeader.biCompression = 0  # BI_RGB
                buffer = (ctypes.c_ubyte * (width * height * 4))()
                copied = gdi32.GetDIBits(
                    memory_dc,
                    bitmap,
                    0,
                    height,
                    ctypes.cast(buffer, handle_type),
                    ctypes.byref(info),
                    0,
                )
                if copied == height:
                    frame = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))[:, :, :3].copy()
                elif bool(window.get("minimized", False)) or backend is not None:
                    frame = np.zeros((height, width, 3), dtype=np.uint8)
                else:
                    raise AutomationError("无法读取窗口截图像素")
            else:
                # The framebuffer will be replaced by the emulator backend
                # immediately after releasing the GDI resources.
                frame = np.zeros((height, width, 3), dtype=np.uint8)
        finally:
            if old_bitmap and memory_dc:
                gdi32.SelectObject(memory_dc, old_bitmap)
            if bitmap:
                gdi32.DeleteObject(bitmap)
            if memory_dc:
                gdi32.DeleteDC(memory_dc)
            user32.ReleaseDC(0, screen_dc)

        capture_backend = "PrintWindow"
        # Prefer the emulator framebuffer whenever it is available. This keeps
        # visible and minimized matching on one stable pixel source and avoids
        # stale frames returned by hardware-accelerated renderer windows.
        if backend is not None:
            emulator_frame = self._capture_emulator_frame(width, height)
            if emulator_frame is not None:
                frame = emulator_frame
                capture_backend = "ADB"
        frame_std = float(frame.std())
        self._last_capture_backend = capture_backend
        self._last_capture_detail = f"{frame.shape[1]}x{frame.shape[0]} | 画面标准差 {frame_std:.1f}"
        if frame_std < 0.5 and self.background_input:
            detail = self._emulator_capture_error or "Win32 截图为空"
            scope = "最小化窗口" if bool(window.get("minimized", False)) else "窗口"
            raise AutomationError(f"{scope}截图内容为空，且未能取得有效 ADB 画面；{detail}")

        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        if capture_hwnd != int(root_hwnd.value or 0):
            child_origin = Point()
            root_origin_point = Point()
            child_ok = bool(user32.ClientToScreen(hwnd, ctypes.byref(child_origin)))
            root_ok = bool(user32.ClientToScreen(root_hwnd, ctypes.byref(root_origin_point)))
            if bool(window.get("minimized", False)) and child_ok and root_ok:
                normal_origin = (
                    int(window.get("normal_x", window.get("x", 0))) + client_offset_x,
                    int(window.get("normal_y", window.get("y", 0))) + client_offset_y,
                )
                origin = (
                    normal_origin[0] + int(child_origin.x - root_origin_point.x),
                    normal_origin[1] + int(child_origin.y - root_origin_point.y),
                )
            elif child_ok:
                origin = (int(child_origin.x), int(child_origin.y))
            elif root_ok:
                origin = (int(root_origin_point.x), int(root_origin_point.y))
            else:
                origin = (
                    int(window.get("normal_x", window.get("x", 0))) + client_offset_x,
                    int(window.get("normal_y", window.get("y", 0))) + client_offset_y,
                )
        elif bool(window.get("minimized", False)):
            origin = (
                int(window.get("normal_x", window.get("x", 0))) + client_offset_x,
                int(window.get("normal_y", window.get("y", 0))) + client_offset_y,
            )
        else:
            root_origin = Point()
            if user32.ClientToScreen(root_hwnd, ctypes.byref(root_origin)):
                origin = (int(root_origin.x), int(root_origin.y))
            else:
                origin = (
                    int(window.get("x", 0)) + client_offset_x,
                    int(window.get("y", 0)) + client_offset_y,
                )
        return cv2, frame, origin

    @staticmethod
    def _enumerate_windows(include_hidden: bool = False) -> list[dict[str, Any]]:
        """Enumerate visible top-level Windows windows and their screen rectangles."""
        if os.name != "nt":
            raise AutomationError("查找窗口功能仅支持 Windows")
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hwnd_type = wintypes.HWND

        class Rect(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class Point(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class WindowPlacement(ctypes.Structure):
            _fields_ = [
                ("length", wintypes.UINT),
                ("flags", wintypes.DWORD),
                ("showCmd", wintypes.UINT),
                ("ptMinPosition", Point),
                ("ptMaxPosition", Point),
                ("rcNormalPosition", Rect),
            ]

        user32.IsWindowVisible.argtypes = [hwnd_type]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.GetWindowTextLengthW.argtypes = [hwnd_type]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [hwnd_type, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowRect.argtypes = [hwnd_type, ctypes.POINTER(Rect)]
        user32.GetWindowRect.restype = wintypes.BOOL
        user32.GetClientRect.argtypes = [hwnd_type, ctypes.POINTER(Rect)]
        user32.GetClientRect.restype = wintypes.BOOL
        user32.GetWindowPlacement.argtypes = [hwnd_type, ctypes.POINTER(WindowPlacement)]
        user32.GetWindowPlacement.restype = wintypes.BOOL
        user32.ClientToScreen.argtypes = [hwnd_type, ctypes.POINTER(Point)]
        user32.ClientToScreen.restype = wintypes.BOOL
        user32.GetWindowThreadProcessId.argtypes = [hwnd_type, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        process_query_limited_information = 0x1000

        def process_info(hwnd: Any) -> tuple[str, str]:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            handle = kernel32.OpenProcess(process_query_limited_information, False, pid.value)
            if not handle:
                return "", ""
            try:
                buffer = ctypes.create_unicode_buffer(260)
                size = wintypes.DWORD(len(buffer))
                if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                    return Path(buffer.value).name, buffer.value
            finally:
                kernel32.CloseHandle(handle)
            return "", ""

        windows: list[dict[str, Any]] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, hwnd_type, wintypes.LPARAM)
        def callback(hwnd, _lparam):
            is_visible = bool(user32.IsWindowVisible(hwnd))
            if not is_visible and not include_hidden:
                return True
            title_length = user32.GetWindowTextLengthW(hwnd)
            if title_length <= 0:
                return True
            title_buffer = ctypes.create_unicode_buffer(title_length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
            title = title_buffer.value.strip()
            if not title:
                return True
            outer = Rect()
            if not user32.GetWindowRect(hwnd, ctypes.byref(outer)):
                return True
            width = int(outer.right - outer.left)
            height = int(outer.bottom - outer.top)
            if width <= 0 or height <= 0:
                return True
            client = Rect()
            client_width = client_height = 0
            if user32.GetClientRect(hwnd, ctypes.byref(client)):
                client_width = max(0, int(client.right - client.left))
                client_height = max(0, int(client.bottom - client.top))
            client_origin = Point()
            client_offset_x = client_offset_y = 0
            if user32.ClientToScreen(hwnd, ctypes.byref(client_origin)):
                client_offset_x = int(client_origin.x - outer.left)
                client_offset_y = int(client_origin.y - outer.top)
            placement = WindowPlacement()
            placement.length = ctypes.sizeof(WindowPlacement)
            is_minimized = False
            normal = outer
            if user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
                is_minimized = int(placement.showCmd) == 2
                normal = placement.rcNormalPosition
            executable_name, executable_path = process_info(hwnd)
            windows.append({
                "hwnd": int(hwnd),
                "title": title,
                "process_name": executable_name,
                "process_path": executable_path,
                "x": int(outer.left),
                "y": int(outer.top),
                "width": width,
                "height": height,
                "client_width": client_width,
                "client_height": client_height,
                "client_offset_x": client_offset_x,
                "client_offset_y": client_offset_y,
                "normal_x": int(normal.left),
                "normal_y": int(normal.top),
                "normal_width": max(0, int(normal.right - normal.left)),
                "normal_height": max(0, int(normal.bottom - normal.top)),
                "minimized": is_minimized,
                "visible": is_visible,
            })
            return True

        if not user32.EnumWindows(callback, 0):
            error = ctypes.get_last_error()
            if error:
                raise AutomationError(f"无法枚举桌面窗口，错误码 {error}")
        return windows

    @staticmethod
    def _window_matches(window: dict[str, Any], title_contains: str, process_name: str) -> bool:
        title_query = title_contains.strip().casefold()
        process_query = process_name.strip().casefold()
        if title_query and title_query not in str(window.get("title", "")).casefold():
            return False
        if process_query and process_query not in str(window.get("process_name", "")).casefold():
            return False
        return bool(title_query or process_query)

    def _find_window(self, step: dict[str, Any]) -> dict[str, Any]:
        title_contains = str(step.get("title_contains", ""))
        process_name = str(step.get("process_name", ""))
        if not title_contains.strip() and not process_name.strip():
            raise AutomationError("查找窗口至少需要填写标题关键词或进程名")
        timeout = max(0.1, float(step.get("window_timeout", 10)))
        # The application is intentionally background-only. Older scripts may
        # still contain background_input=false, so force the runtime behavior
        # here as the final compatibility guard.
        self.background_input = True
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            self._check_stopped()
            # A minimized emulator can hide its renderer sibling without
            # marking that HWND iconic. Runtime lookup therefore includes
            # titled hidden windows; UI dropdowns keep the default visible-only list.
            windows = self._enumerate_windows(include_hidden=True)
            for window in windows:
                if self._window_matches(window, title_contains, process_name):
                    self.last_window = window
                    self._emulator_capture_backend = None
                    self._emulator_capture_checked = False
                    self._emulator_capture_retry_at = 0.0
                    self._emulator_capture_logged = False
                    self._emulator_capture_error = ""
                    if self.background_input:
                        self._resolve_background_input_handle(window)
                        # This also maps sibling MuMu windows to the renderer
                        # HWND belonging to the same VM process.
                        self._resolve_emulator_capture_backend()
                        input_hwnd = self._background_input_hwnd()
                        input_class = str(window.get("input_class", ""))
                        input_title = str(window.get("input_title", ""))
                        if input_hwnd and input_hwnd != int(window.get("hwnd", 0)):
                            self.log.emit(
                                f"后台输入目标已选择 | 根 HWND {int(window.get('hwnd', 0))} | "
                                f"渲染 HWND {input_hwnd} | {input_class or input_title or '子窗口'}"
                            )
                        else:
                            self.log.emit("后台输入使用顶层窗口，未发现可用渲染子窗口")
                    if self.background_input:
                        self.log.emit("已启用后台窗口消息输入；将优先向渲染子窗口发送同步点击消息")
                    if window.get("minimized"):
                        geometry = (
                            f"还原=({window['normal_x']}, {window['normal_y']}, "
                            f"{window['normal_width']}x{window['normal_height']}) "
                            f"当前外框=({window['x']}, {window['y']}, "
                            f"{window['width']}x{window['height']})"
                        )
                    else:
                        geometry = f"外框=({window['x']}, {window['y']}, {window['width']}x{window['height']})"
                    self.log.emit(
                        "找到窗口: "
                        f"{window['title']} [{window.get('process_name') or '未知进程'}] "
                        f"{geometry} "
                        f"客户区={window['client_width']}x{window['client_height']}"
                    )
                    return window
            self._sleep(0.25)
        criteria = title_contains.strip() or process_name.strip()
        self.log.emit(f"窗口未识别 | 匹配条件: {criteria} | 超时 {timeout:.2f} 秒")
        raise AutomationError(f"查找窗口超时: {criteria}")

    def _wait_for_image(self, step: dict[str, Any]) -> tuple[int, int]:
        image_path = self._resolve_input_path(str(step.get("image", "")))
        cv2, template = self._read_color_image(image_path)
        timeout = max(0.1, float(step.get("timeout", 10)))
        confidence = min(0.99, max(0.1, float(step.get("confidence", 0.85))))
        started = time.monotonic()
        self.log.emit(
            f"开始识别图片 | {image_path} | 模板 {template.shape[1]}x{template.shape[0]} | "
            f"置信度 {confidence:.2f} | 缩放容差 90%-110% | 超时 {timeout:.2f} 秒"
        )
        best_match = TemplateMatch(-1.0, (0, 0), (template.shape[1], template.shape[0]), 1.0)
        best_frame = None
        last_frame = None
        capture_failures = 0
        last_capture_error = ""
        last_report = started
        while time.monotonic() - started < timeout:
            self._check_stopped()
            try:
                cv2_module, screen, screen_offset = self._capture()
                last_frame = screen
                current = find_template_match(cv2_module, screen, template)
            except AutomationError as exc:
                capture_failures += 1
                last_capture_error = str(exc)
                if capture_failures == 1 or time.monotonic() - last_report >= 1.0:
                    self.log.emit(
                        f"图片截图暂不可用 | {image_path.name} | 已重试 {capture_failures} 次 | {exc}"
                    )
                    last_report = time.monotonic()
                self._sleep(0.25)
                continue
            if current.score > best_match.score:
                best_match = current
                best_frame = screen.copy()
            if time.monotonic() - last_report >= 1.0:
                self.log.emit(
                    f"图片识别中 | {image_path.name} | 当前 {current.score:.3f} | "
                    f"最高 {max(best_match.score, 0.0):.3f} | 最佳缩放 {best_match.scale * 100:.1f}% | "
                    f"{self._last_capture_backend} {screen.shape[1]}x{screen.shape[0]}"
                )
                last_report = time.monotonic()
            if current.score >= confidence:
                width, height = current.size
                point = (
                    screen_offset[0] + current.location[0] + width // 2,
                    screen_offset[1] + current.location[1] + height // 2,
                )
                self.log.emit(
                    f"找到图片 | {image_path.name} | 匹配度 {current.score:.3f} | "
                    f"缩放 {current.scale * 100:.1f}% | 识别坐标 {point}"
                )
                return point
            self._sleep(0.25)
        diagnostic = self._save_recognition_failure_frame(
            cv2, best_frame if best_frame is not None else last_frame, image_path, "屏幕"
        )
        error_detail = f" | 最后截图错误 {last_capture_error}" if last_capture_error else ""
        diagnostic_detail = f" | 失败截图 {diagnostic}" if diagnostic else ""
        capture_detail = f" | 截图 {self._last_capture_detail}" if self._last_capture_detail else ""
        self.log.emit(
            f"图片未识别 | {image_path} | 最高匹配度 {max(best_match.score, 0.0):.3f} | "
            f"最佳缩放 {best_match.scale * 100:.1f}% | 截图失败 {capture_failures} 次 | "
            f"要求 {confidence:.2f} | 超时 {timeout:.2f} 秒{capture_detail}{error_detail}{diagnostic_detail}"
        )
        raise AutomationError(f"等待图片超时: {image_path.name}")

    def _wait_for_window_image(self, step: dict[str, Any]) -> tuple[int, int]:
        image_path = self._resolve_input_path(str(step.get("image", "")))
        cv2, template = self._read_color_image(image_path)
        timeout = max(0.1, float(step.get("timeout", 10)))
        confidence = min(0.99, max(0.1, float(step.get("confidence", 0.85))))
        started = time.monotonic()
        self.log.emit(
            f"开始识别窗口内图片 | {image_path} | 模板 {template.shape[1]}x{template.shape[0]} | "
            f"置信度 {confidence:.2f} | 缩放容差 90%-110% | 超时 {timeout:.2f} 秒"
        )
        best_match = TemplateMatch(-1.0, (0, 0), (template.shape[1], template.shape[0]), 1.0)
        best_frame = None
        last_frame = None
        capture_failures = 0
        last_capture_error = ""
        last_report = started
        while time.monotonic() - started < timeout:
            self._check_stopped()
            try:
                cv2_module, frame, origin = self._capture_window()
                last_frame = frame
                current = find_template_match(cv2_module, frame, template)
            except AutomationError as exc:
                if self._permanent_capture_error(exc):
                    raise
                capture_failures += 1
                last_capture_error = str(exc)
                if capture_failures == 1 or time.monotonic() - last_report >= 1.0:
                    self.log.emit(
                        f"窗口截图暂不可用 | {image_path.name} | 已重试 {capture_failures} 次 | {exc}"
                    )
                    last_report = time.monotonic()
                self._sleep(0.25)
                continue
            if current.score > best_match.score:
                best_match = current
                best_frame = frame.copy()
            if time.monotonic() - last_report >= 1.0:
                self.log.emit(
                    f"窗口内图片识别中 | {image_path.name} | 当前 {current.score:.3f} | "
                    f"最高 {max(best_match.score, 0.0):.3f} | 最佳缩放 {best_match.scale * 100:.1f}% | "
                    f"{self._last_capture_backend} {frame.shape[1]}x{frame.shape[0]}"
                )
                last_report = time.monotonic()
            if current.score >= confidence:
                width, height = current.size
                point = (
                    origin[0] + current.location[0] + width // 2,
                    origin[1] + current.location[1] + height // 2,
                )
                self.log.emit(
                    f"找到窗口内图片 | {image_path.name} | 匹配度 {current.score:.3f} | "
                    f"缩放 {current.scale * 100:.1f}% | 识别坐标 {point}"
                )
                return point
            self._sleep(0.25)
        diagnostic = self._save_recognition_failure_frame(
            cv2, best_frame if best_frame is not None else last_frame, image_path, "窗口"
        )
        error_detail = f" | 最后截图错误 {last_capture_error}" if last_capture_error else ""
        diagnostic_detail = f" | 失败截图 {diagnostic}" if diagnostic else ""
        capture_detail = f" | 截图 {self._last_capture_detail}" if self._last_capture_detail else ""
        self.log.emit(
            f"窗口内图片未识别 | {image_path} | 最高匹配度 {max(best_match.score, 0.0):.3f} | "
            f"最佳缩放 {best_match.scale * 100:.1f}% | 截图失败 {capture_failures} 次 | "
            f"后端 {self._last_capture_backend or '未知'} | 要求 {confidence:.2f} | "
            f"超时 {timeout:.2f} 秒{capture_detail}{error_detail}{diagnostic_detail}"
        )
        raise AutomationError(f"窗口内图片超时: {image_path.name}")

    def _save_recognition_failure_frame(
        self, cv2_module, frame, image_path: Path, scope: str
    ) -> Path | None:
        if frame is None:
            return None
        safe_stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", image_path.stem).strip(" ._") or "template"
        destination = (self.output_dir or self.base_dir) / "识别调试" / f"最近失败_{scope}_{safe_stem}.png"
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            encoded, data = cv2_module.imencode(".png", frame)
            if not encoded:
                return None
            destination.write_bytes(data.tobytes())
            return destination
        except (OSError, ValueError):
            return None

    def _get_ocr_engine(self):
        """Create the bundled RapidOCR engine lazily for the worker thread."""
        if self._ocr_engine is not None:
            return self._ocr_engine
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise AutomationError("缺少 OCR 依赖，请先安装 requirements.txt") from exc
        try:
            self._ocr_engine = RapidOCR()
        except Exception as exc:  # noqa: BLE001 - model/runtime errors vary by machine
            raise AutomationError(f"OCR 引擎初始化失败: {exc}") from exc
        return self._ocr_engine

    def _run_ocr(self, frame) -> list[dict[str, Any]]:
        """Run OCR and normalize RapidOCR's result format for matching/logging."""
        try:
            raw_result = self._get_ocr_engine()(frame)
        except AutomationError:
            raise
        except Exception as exc:  # noqa: BLE001 - ONNX runtime errors vary by machine
            raise AutomationError(f"OCR 识别失败: {exc}") from exc
        raw_items = raw_result[0] if isinstance(raw_result, tuple) else raw_result
        parsed: list[dict[str, Any]] = []
        for item in raw_items or []:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            text = str(item[1] or "").strip()
            if not text:
                continue
            try:
                score = float(item[2])
            except (TypeError, ValueError):
                continue
            points: list[tuple[float, float]] = []
            try:
                for point in item[0]:
                    if len(point) >= 2:
                        points.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                points = []
            if not points:
                continue
            parsed.append({"text": text, "score": score, "points": points})
        return parsed

    @staticmethod
    def _ocr_match(results: list[dict[str, Any]], target: str, confidence: float) -> dict[str, Any] | None:
        target_compact = re.sub(r"\s+", "", target.casefold())
        for result in results:
            if float(result.get("score", 0.0)) < confidence:
                continue
            text = str(result.get("text", ""))
            text_compact = re.sub(r"\s+", "", text.casefold())
            if target_compact and target_compact not in text_compact:
                continue
            points = result.get("points", [])
            if not points:
                continue
            left = min(point[0] for point in points)
            right = max(point[0] for point in points)
            top = min(point[1] for point in points)
            bottom = max(point[1] for point in points)
            result["center"] = (int(round((left + right) / 2)), int(round((top + bottom) / 2)))
            return result
        return None

    def _wait_for_ocr(self, step: dict[str, Any], window: bool = False) -> tuple[int, int]:
        target = str(step.get("target_text", "")).strip()
        timeout = max(0.1, float(step.get("timeout", 10)))
        confidence = min(0.99, max(0.1, float(step.get("confidence", 0.6))))
        scope = "窗口内" if window else "屏幕"
        started = time.monotonic()
        last_report = started
        last_texts: list[str] = []
        self.log.emit(
            f"开始{scope}OCR | 目标文字 {target or '任意文字'} | "
            f"置信度 {confidence:.2f} | 超时 {timeout:.2f} 秒"
        )
        while time.monotonic() - started < timeout:
            self._check_stopped()
            if window:
                _cv2, frame, origin = self._capture_window()
            else:
                _cv2, frame, origin = self._capture()
            results = self._run_ocr(frame)
            last_texts = [str(result["text"]) for result in results[:8]]
            match = self._ocr_match(results, target, confidence)
            if match is not None:
                center = match["center"]
                point = (int(origin[0] + center[0]), int(origin[1] + center[1]))
                self.log.emit(
                    f"找到{scope}文字 | {match['text']} | 置信度 {float(match['score']):.3f} | "
                    f"识别坐标 {point}"
                )
                return point
            if time.monotonic() - last_report >= 1.0:
                preview = " | ".join(last_texts) if last_texts else "未检测到文字"
                self.log.emit(f"{scope}OCR识别中 | 当前文字 {preview[:240]}")
                last_report = time.monotonic()
            self._sleep(0.25)
        preview = " | ".join(last_texts) if last_texts else "未检测到文字"
        self.log.emit(
            f"{scope}OCR未识别 | 目标文字 {target or '任意文字'} | "
            f"最后结果 {preview[:240]} | 超时 {timeout:.2f} 秒"
        )
        raise AutomationError(f"{scope}OCR文字超时: {target or '任意文字'}")

    def _take_screenshot(self, output_path: str) -> None:
        try:
            import mss
            import cv2
            import numpy as np
        except ImportError as exc:
            raise AutomationError(f"截图依赖加载失败: {exc}") from exc
        destination = Path(str(output_path or "screenshot.png")).expanduser()
        if destination.name in {"", ".", ".."}:
            destination = Path("screenshot.png")
        if not destination.is_absolute():
            destination = (self.output_dir or self.base_dir) / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        with mss.mss() as sct:
            # Capture the complete virtual desktop so screenshots match the
            # coordinate system used by screen image matching and OCR.
            shot = sct.grab(sct.monitors[0])
            # OpenCV file writers can reject Chinese paths on some Windows
            # builds. Encode to PNG in memory, then let pathlib write bytes.
            frame = np.asarray(shot)[:, :, :3]
            encoded, data = cv2.imencode(".png", frame)
            if not encoded:
                raise AutomationError("无法编码屏幕截图")
            destination.write_bytes(data.tobytes())
        self.log.emit(f"已保存截图: {destination}")


_UI_FONT_FAMILY: str | None = None


def configure_ui_font(application: QApplication | None = None) -> str:
    """Register a dependable Chinese UI font before creating application widgets."""
    global _UI_FONT_FAMILY
    application = application or QApplication.instance()
    if application is None:
        return ""
    if _UI_FONT_FAMILY:
        application.setFont(QFont(_UI_FONT_FAMILY, 9))
        return _UI_FONT_FAMILY

    bundled_root = Path(str(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)))
    candidates = [
        bundled_root / "fonts" / "NotoSansSC-VF.ttf",
        bundled_root / "assets" / "fonts" / "NotoSansSC-VF.ttf",
        bundled_root / "NotoSansSC-VF.ttf",
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/Deng.ttf"),
    ]
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).casefold()
        if key in seen or not candidate.is_file():
            continue
        seen.add(key)
        font_id = QFontDatabase.addApplicationFont(str(candidate))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            _UI_FONT_FAMILY = str(families[0])
            application.setFont(QFont(_UI_FONT_FAMILY, 9))
            return _UI_FONT_FAMILY

    fallback = "Microsoft YaHei UI"
    application.setFont(QFont(fallback, 9))
    return fallback


class MainWindow(QMainWindow):
    mouse_position_captured = Signal(int, int)
    drag_recorded = Signal(int, int, int, int, float)
    macro_recorded = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        configure_ui_font(QApplication.instance())
        self.setWindowTitle(APP_NAME)
        self.resize(1120, 720)
        self.current_file: Path | None = None
        self.is_dirty = False
        self._draft_settings = QSettings("AutomationTool", "AutomationTool")
        self._last_accepted_draft: tuple[str, str] = ("", "")
        self._discarded_changes = False
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(350)
        self._autosave_timer.timeout.connect(self._write_autosave)
        self.steps: list[dict[str, Any]] = []
        self.window_tasks: list[dict[str, Any]] = []
        self.active_task_index = -1
        self.window_task_runs: dict[int, dict[str, Any]] = {}
        self.window_task_status: dict[int, str] = {}
        self._window_worker_meta: dict[int, tuple[int, str]] = {}
        self._updating_task_form = False
        self.worker: ScriptWorker | None = None
        self.worker_thread: QThread | None = None
        self.position_listener = None
        self.drag_listener = None
        self.macro_mouse_listener = None
        self.macro_keyboard_listener = None
        self.macro_events: list[dict[str, Any]] = []
        self.macro_last_event_time: float | None = None
        self.macro_last_move: tuple[int, int] | None = None
        self.macro_lock = threading.Lock()
        self._updating_form = False
        self._build_ui()
        if not self._restore_autosave():
            self._new_script()

    def _apply_button_icon(self, button: QPushButton, standard_pixmap: QStyle.StandardPixmap) -> None:
        button.setIcon(QApplication.style().standardIcon(standard_pixmap))
        button.setIconSize(button.iconSize())

    def _configure_toolbar_button(self, button: QPushButton, object_name: str, tooltip: str) -> None:
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setCursor(Qt.PointingHandCursor)

    def _build_ui(self) -> None:
        self.setStatusBar(QStatusBar())
        toolbar = QToolBar("工具栏")
        self.main_toolbar = toolbar
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QPixmap(16, 16).size())
        self.addToolBar(toolbar)
        self.app_brand_label = QLabel("自动化流程")
        self.app_brand_label.setObjectName("appBrand")
        self.workspace_context_label = QLabel("任务库 · 本地草稿自动保存")
        self.workspace_context_label.setObjectName("workspaceContext")
        toolbar.addWidget(self.app_brand_label)
        toolbar.addWidget(self.workspace_context_label)
        toolbar_spacer = QWidget()
        toolbar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(toolbar_spacer)
        self.backend_status_label = QLabel("● 后台服务就绪")
        self.backend_status_label.setObjectName("backendStatusBadge")
        toolbar.addWidget(self.backend_status_label)
        self.action_new = QAction("新建", self)
        self.action_open = QAction("打开", self)
        self.action_save = QAction("导出 JSON", self)
        self.action_new.setShortcut(QKeySequence("Ctrl+N"))
        self.action_open.setShortcut(QKeySequence("Ctrl+O"))
        self.action_save.setShortcut(QKeySequence("Ctrl+S"))
        self.action_new.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.action_open.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.action_save.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton))
        for action in (self.action_new, self.action_open, self.action_save):
            toolbar.addAction(action)
        self._editor_toolbar_separators: list[QAction] = []
        self._editor_toolbar_actions: list[QAction] = []
        self._editor_toolbar_separators.append(toolbar.addSeparator())
        self.add_button = QPushButton("添加操作")
        self.delete_button = QPushButton("删除选中")
        self.up_button = QPushButton("自动排列")
        self._configure_toolbar_button(self.add_button, "addButton", "添加一个操作节点到流程图")
        self._configure_toolbar_button(self.delete_button, "deleteButton", "删除选中的节点或连线")
        self._configure_toolbar_button(self.up_button, "moveButton", "按流程拓扑重新排列节点")
        self._apply_button_icon(self.add_button, QStyle.SP_FileDialogNewFolder)
        self._apply_button_icon(self.delete_button, QStyle.SP_TrashIcon)
        self._apply_button_icon(self.up_button, QStyle.SP_ArrowRight)
        self.record_macro_button = QPushButton("录制动作")
        self.record_macro_button.setObjectName("recordMacroButton")
        self.record_macro_button.setCheckable(True)
        self._configure_toolbar_button(self.record_macro_button, "recordMacroButton", "录制一整组鼠标和键盘操作；再次点击停止")
        self._apply_button_icon(self.record_macro_button, QStyle.SP_DialogApplyButton)
        self.run_button = QPushButton("运行")
        self.stop_button = QPushButton("停止")
        self._configure_toolbar_button(self.run_button, "runButton", "运行当前脚本")
        self._configure_toolbar_button(self.stop_button, "stopButton", "停止当前脚本")
        self._apply_button_icon(self.run_button, QStyle.SP_MediaPlay)
        self._apply_button_icon(self.stop_button, QStyle.SP_MediaStop)
        self.stop_button.setEnabled(False)
        self._editor_toolbar_actions.append(toolbar.addWidget(self.run_button))
        self._editor_toolbar_actions.append(toolbar.addWidget(self.stop_button))

        self.step_list = QListWidget()
        self.step_list.setMinimumWidth(285)
        self.step_list.setVisible(False)
        self.step_list.setAlternatingRowColors(True)
        self.step_list.currentRowChanged.connect(self._on_step_selected)

        left_panel = QWidget()
        left_panel.setObjectName("flowWorkspace")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        flow_header = QWidget()
        flow_header.setObjectName("flowHeader")
        task_switch_row = QHBoxLayout(flow_header)
        task_switch_row.setContentsMargins(12, 7, 12, 7)
        task_switch_row.setSpacing(8)
        flow_crumb = QLabel("任务库  ›")
        flow_crumb.setObjectName("pageSubtitle")
        task_switch_row.addWidget(flow_crumb)
        self.editor_task_box = QComboBox()
        self.editor_task_box.setMinimumWidth(220)
        self.editor_task_box.setToolTip("选择要直接编辑操作步骤的窗口任务")
        self.editor_target_button = QPushButton("任务设置")
        self.editor_target_button.setToolTip("打开当前任务的目标窗口设置")
        self._apply_button_icon(self.editor_target_button, QStyle.SP_FileDialogDetailedView)
        self.add_action_node_button = QPushButton("操作")
        self.add_action_node_button.setToolTip("添加一个鼠标、键盘、图片识别或宏操作节点")
        self._apply_button_icon(self.add_action_node_button, QStyle.SP_FileDialogNewFolder)
        self.add_condition_button = QPushButton("判断")
        self.add_condition_button.setToolTip("添加一个带与/或/非出口的图片判断节点")
        self._apply_button_icon(self.add_condition_button, QStyle.SP_MessageBoxQuestion)
        for button, accessible_name in (
            (self.add_action_node_button, "添加操作节点"),
            (self.add_condition_button, "添加判断节点"),
            (self.delete_button, "删除选中节点或连线"),
            (self.up_button, "自动排列流程"),
            (self.record_macro_button, "录制宏动作"),
            (self.editor_target_button, "任务设置"),
        ):
            button.setText("")
            button.setAccessibleName(accessible_name)
            button.setFixedSize(32, 32)
        self.add_button.setParent(flow_header)
        self.add_button.hide()
        task_switch_row.addWidget(self.editor_task_box)
        task_switch_row.addStretch(1)
        task_switch_row.addWidget(self.add_action_node_button)
        task_switch_row.addWidget(self.add_condition_button)
        task_switch_row.addWidget(self.delete_button)
        task_switch_row.addWidget(self.up_button)
        task_switch_row.addWidget(self.record_macro_button)
        task_switch_row.addWidget(self.editor_target_button)
        left_layout.addWidget(flow_header)
        self.flow_canvas = FlowCanvas()
        self.flow_canvas.node_selected.connect(self._on_flow_node_selected)
        self.flow_canvas.flow_changed.connect(self._flow_changed)
        self.flow_canvas.save_requested.connect(self._save_script)
        left_layout.addWidget(self.flow_canvas, 1)
        left_layout.addWidget(self.step_list, 1)

        self.properties = QGroupBox("")
        self.properties.setObjectName("nodePropertiesPanel")
        # The inspector is narrower than the flow canvas by design.  Let its
        # contents shrink to the viewport and wrap long form rows instead of
        # making the user pan sideways through node properties.
        self.properties.setMinimumSize(0, 0)
        self.properties.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.properties_scroll = QScrollArea()
        self.properties_scroll.setObjectName("nodePropertiesScroll")
        self.properties_scroll.setWidgetResizable(True)
        self.properties_scroll.setFrameShape(QScrollArea.NoFrame)
        self.properties_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.properties_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.properties_scroll.setAlignment(Qt.AlignTop)
        self.properties_scroll.setWidget(self.properties)
        self.form = QFormLayout(self.properties)
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.form.setFormAlignment(Qt.AlignTop)
        self.node_name_edit = QLineEdit()
        self.node_name_edit.setPlaceholderText("可选，例如：点击登录按钮")
        self.enabled_box = QCheckBox("启用此步骤")
        self.type_box = QComboBox()
        for key, label in STEP_TYPES:
            if key == "find_window":
                continue
            self.type_box.addItem(label, key)
        self.form.addRow("步骤名称", self.node_name_edit)
        self.form.addRow(self.enabled_box)
        self.form.addRow("步骤类型", self.type_box)

        self.coordinate_widget = QWidget()
        coordinate_layout = QGridLayout(self.coordinate_widget)
        coordinate_layout.setContentsMargins(0, 0, 0, 0)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-10000, 10000)
        coordinate_layout.addWidget(QLabel("X"), 0, 0)
        coordinate_layout.addWidget(self.x_spin, 0, 1)
        coordinate_layout.addWidget(QLabel("Y"), 1, 0)
        coordinate_layout.addWidget(self.y_spin, 1, 1)
        self.capture_position_button = QPushButton("读取当前坐标")
        self.capture_position_button.setObjectName("capturePositionButton")
        self.capture_position_button.setToolTip("点击后，下一次鼠标左键点击会填入 X、Y；快捷键 F8")
        self.capture_position_button.setMinimumWidth(140)
        self.capture_position_button.setCursor(Qt.PointingHandCursor)
        self._apply_button_icon(self.capture_position_button, QStyle.SP_DialogApplyButton)
        coordinate_layout.addWidget(self.capture_position_button, 2, 0, 1, 2)
        self.form.addRow("坐标", self.coordinate_widget)

        self.drag_widget = QWidget()
        drag_layout = QGridLayout(self.drag_widget)
        drag_layout.setContentsMargins(0, 0, 0, 0)
        self.drag_start_x_spin = QSpinBox()
        self.drag_start_x_spin.setRange(-10000, 10000)
        self.drag_start_y_spin = QSpinBox()
        self.drag_start_y_spin.setRange(-10000, 10000)
        self.drag_end_x_spin = QSpinBox()
        self.drag_end_x_spin.setRange(-10000, 10000)
        self.drag_end_y_spin = QSpinBox()
        self.drag_end_y_spin.setRange(-10000, 10000)
        drag_layout.addWidget(QLabel("起点 X"), 0, 0)
        drag_layout.addWidget(self.drag_start_x_spin, 0, 1)
        drag_layout.addWidget(QLabel("起点 Y"), 0, 2)
        drag_layout.addWidget(self.drag_start_y_spin, 0, 3)
        drag_layout.addWidget(QLabel("终点 X"), 1, 0)
        drag_layout.addWidget(self.drag_end_x_spin, 1, 1)
        drag_layout.addWidget(QLabel("终点 Y"), 1, 2)
        drag_layout.addWidget(self.drag_end_y_spin, 1, 3)
        self.drag_duration_spin = QDoubleSpinBox()
        self.drag_duration_spin.setRange(0.05, 86400)
        self.drag_duration_spin.setDecimals(2)
        self.drag_duration_spin.setSingleStep(0.05)
        self.drag_duration_spin.setSuffix(" 秒")
        drag_layout.addWidget(QLabel("持续时间"), 2, 0)
        drag_layout.addWidget(self.drag_duration_spin, 2, 1, 1, 3)
        self.record_drag_button = QPushButton("录制下一次拖拽")
        self.record_drag_button.setObjectName("recordDragButton")
        self.record_drag_button.setToolTip("点击后，在屏幕上按住左键拖动并松开")
        self.record_drag_button.setCursor(Qt.PointingHandCursor)
        self._apply_button_icon(self.record_drag_button, QStyle.SP_DialogApplyButton)
        drag_layout.addWidget(self.record_drag_button, 3, 0, 1, 4)
        self.form.addRow("拖拽参数", self.drag_widget)

        self.macro_widget = QWidget()
        macro_layout = QGridLayout(self.macro_widget)
        macro_layout.setContentsMargins(0, 0, 0, 0)
        self.macro_name_edit = QLineEdit()
        self.macro_name_edit.setPlaceholderText("例如：整理窗口")
        macro_layout.addWidget(QLabel("动作名称"), 0, 0)
        macro_layout.addWidget(self.macro_name_edit, 0, 1, 1, 3)
        self.macro_event_count_label = QLabel("0 个事件")
        macro_layout.addWidget(QLabel("录制内容"), 1, 0)
        macro_layout.addWidget(self.macro_event_count_label, 1, 1, 1, 3)
        self.macro_event_table = QTableWidget(0, 4)
        self.macro_event_table.setHorizontalHeaderLabels(["序号", "操作", "参数", "间隔（秒）"])
        self.macro_event_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.macro_event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.macro_event_table.setAlternatingRowColors(True)
        self.macro_event_table.setShowGrid(False)
        self.macro_event_table.setWordWrap(False)
        self.macro_event_table.setMinimumHeight(180)
        self.macro_event_table.setMaximumHeight(300)
        self.macro_event_table.verticalHeader().setVisible(False)
        event_header = self.macro_event_table.horizontalHeader()
        event_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        event_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        event_header.setSectionResizeMode(2, QHeaderView.Stretch)
        event_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        macro_layout.addWidget(self.macro_event_table, 2, 0, 1, 4)
        self.macro_mode_box = QComboBox()
        self.macro_mode_box.addItem("单次执行", "once")
        self.macro_mode_box.addItem("重复指定次数", "repeat")
        self.macro_mode_box.addItem("持续循环", "loop")
        macro_layout.addWidget(QLabel("执行模式"), 3, 0)
        macro_layout.addWidget(self.macro_mode_box, 3, 1, 1, 3)
        self.macro_repeat_spin = QSpinBox()
        self.macro_repeat_spin.setRange(1, 999999)
        self.macro_repeat_spin.setValue(2)
        self.macro_repeat_label = QLabel("重复次数")
        macro_layout.addWidget(self.macro_repeat_label, 4, 0)
        macro_layout.addWidget(self.macro_repeat_spin, 4, 1)
        self.macro_interval_spin = QDoubleSpinBox()
        self.macro_interval_spin.setRange(0, 86400)
        self.macro_interval_spin.setDecimals(2)
        self.macro_interval_spin.setSingleStep(0.1)
        self.macro_interval_spin.setSuffix(" 秒")
        self.macro_interval_spin.setValue(0.2)
        self.macro_interval_label = QLabel("重复间隔")
        macro_layout.addWidget(self.macro_interval_label, 4, 2)
        macro_layout.addWidget(self.macro_interval_spin, 4, 3)
        self.form.addRow("宏动作", self.macro_widget)

        self.window_widget = QWidget()
        window_layout = QGridLayout(self.window_widget)
        window_layout.setContentsMargins(0, 0, 0, 0)
        self.window_choice_box = QComboBox()
        self.window_choice_box.addItem("选择当前已打开的窗口…", None)
        self.window_choice_box.setToolTip("从当前可见窗口中选择目标；下拉数据仅用于填充匹配条件")
        self.window_refresh_button = QPushButton("刷新列表")
        self.window_refresh_button.setObjectName("probeWindowButton")
        self.window_refresh_button.setToolTip("重新枚举当前桌面的可见顶层窗口")
        self.window_title_edit = QLineEdit()
        self.window_title_edit.setPlaceholderText("例如：游戏名称（标题包含匹配）")
        self.window_process_edit = QLineEdit()
        self.window_process_edit.setPlaceholderText("可选，例如：game.exe")
        self.window_timeout_spin = QDoubleSpinBox()
        self.window_timeout_spin.setRange(0.1, 86400)
        self.window_timeout_spin.setDecimals(1)
        self.window_timeout_spin.setSingleStep(0.5)
        self.window_timeout_spin.setSuffix(" 秒")
        self.window_timeout_spin.setValue(10.0)
        self.window_probe_button = QPushButton("立即查找")
        self.window_probe_button.setObjectName("probeWindowButton")
        self.window_probe_button.setToolTip("现在扫描一次可见的顶层窗口并读取大小")
        self.window_result_label = QLabel("尚未查找")
        self.window_result_label.setWordWrap(True)
        self.window_background_check = QCheckBox("允许后台窗口消息输入（实验）")
        self.window_background_check.setToolTip(
            "目标窗口最小化时尝试发送窗口消息；普通 Win32 控件可能支持，游戏引擎通常不支持"
        )
        self.window_activate_check = QCheckBox("运行时激活窗口（前台模式）")
        self.window_background_check.setChecked(True)
        self.window_activate_check.setChecked(False)
        self.window_background_check.hide()
        self.window_activate_check.hide()
        self.window_activate_check.setToolTip("命中目标后恢复最小化窗口并将其置前，前台模拟输入会发送到该窗口")
        self.window_mode_label = QLabel("后台执行（固定）")
        self.window_mode_label.setObjectName("fixedModeLabel")
        self.window_mode_label.setToolTip("窗口任务始终使用后台消息输入，不会激活或抢占当前窗口")
        window_layout.addWidget(QLabel("已打开窗口"), 0, 0)
        window_layout.addWidget(self.window_choice_box, 0, 1, 1, 2)
        window_layout.addWidget(self.window_refresh_button, 0, 3)
        window_layout.addWidget(QLabel("标题关键词"), 1, 0)
        window_layout.addWidget(self.window_title_edit, 1, 1, 1, 3)
        window_layout.addWidget(QLabel("进程名"), 2, 0)
        window_layout.addWidget(self.window_process_edit, 2, 1, 1, 3)
        window_layout.addWidget(QLabel("识别超时"), 3, 0)
        window_layout.addWidget(self.window_timeout_spin, 3, 1)
        window_layout.addWidget(self.window_probe_button, 3, 2, 1, 2)
        window_layout.addWidget(self.window_mode_label, 4, 0, 1, 4)
        window_layout.addWidget(QLabel("最近结果"), 6, 0)
        window_layout.addWidget(self.window_result_label, 6, 1, 1, 3)
        self.form.addRow("窗口识别", self.window_widget)

        self.condition_widget = QWidget()
        condition_layout = QGridLayout(self.condition_widget)
        condition_layout.setContentsMargins(0, 0, 0, 0)
        self.condition_operator_box = QComboBox()
        self.condition_operator_box.addItem("全部满足（与）", "and")
        self.condition_operator_box.addItem("任一满足（或）", "or")
        self.condition_operator_box.setToolTip("先按与/或汇总多张图片，再用下面的非开关反转结果")
        self.condition_negate_box = QCheckBox("反向结果（非）")
        self.condition_negate_box.setToolTip("将判断结果反转：满足变为不满足，不满足变为满足")
        self.condition_image_edit = QLineEdit()
        self.condition_image_edit.setPlaceholderText("模板图片路径；多张图片用 ; 分隔")
        self.condition_image_edit.setToolTip("先选择与/或，再决定是否反向结果。多张图片用英文分号 ; 分隔")
        self.condition_image_button = QPushButton("选择")
        self.condition_confidence_spin = QDoubleSpinBox()
        self.condition_confidence_spin.setRange(0.1, 0.99)
        self.condition_confidence_spin.setSingleStep(0.01)
        self.condition_confidence_spin.setDecimals(2)
        self.condition_confidence_spin.setValue(0.85)
        self.condition_timeout_spin = QDoubleSpinBox()
        self.condition_timeout_spin.setRange(0.1, 86400)
        self.condition_timeout_spin.setDecimals(1)
        self.condition_timeout_spin.setSuffix(" 秒")
        self.condition_timeout_spin.setValue(1.0)
        self.condition_hint_label = QLabel("与：全部图片存在；或：任意图片存在；非：反转最终结果")
        self.condition_hint_label.setWordWrap(True)
        self.condition_hint_label.setStyleSheet("color: #7f8b9a; font-size: 8pt;")
        condition_layout.addWidget(QLabel("匹配方式"), 0, 0)
        condition_layout.addWidget(self.condition_operator_box, 0, 1, 1, 3)
        condition_layout.addWidget(self.condition_negate_box, 1, 1, 1, 3)
        condition_layout.addWidget(QLabel("模板图片"), 2, 0)
        condition_layout.addWidget(self.condition_image_edit, 2, 1)
        condition_layout.addWidget(self.condition_image_button, 2, 2)
        condition_layout.addWidget(QLabel("置信度"), 3, 0)
        condition_layout.addWidget(self.condition_confidence_spin, 3, 1)
        condition_layout.addWidget(QLabel("检查超时"), 3, 2)
        condition_layout.addWidget(self.condition_timeout_spin, 3, 3)
        condition_layout.addWidget(self.condition_hint_label, 4, 0, 1, 4)
        self.form.addRow("判断属性", self.condition_widget)

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("例如 ENTER、TAB、a")
        self.key_row = self._make_field_row(self.key_edit)
        self.form.addRow("按键", self.key_row)
        self.text_edit = QTextEdit()
        self.text_edit.setFixedHeight(90)
        self.text_row = self._make_field_row(self.text_edit)
        self.form.addRow("输入内容", self.text_row)
        self.seconds_spin = QDoubleSpinBox()
        self.seconds_spin.setRange(0, 86400)
        self.seconds_spin.setDecimals(2)
        self.seconds_spin.setSingleStep(0.1)
        self.seconds_spin.setSuffix(" 秒")
        self.seconds_row = self._make_field_row(self.seconds_spin)
        self.form.addRow("等待时间", self.seconds_row)

        self.ocr_target_edit = QLineEdit()
        self.ocr_target_edit.setPlaceholderText("要识别的文字；留空表示识别到任意文字即可")
        self.ocr_target_edit.setToolTip("支持中文、英文和数字；匹配时忽略大小写和空白字符")
        self.ocr_widget = self._make_field_row(self.ocr_target_edit)
        self.form.addRow("目标文字", self.ocr_widget)

        self.image_edit = QLineEdit()
        self.image_button = QPushButton("选择")
        self.capture_button = QPushButton("截取模板")
        self.image_row = QWidget()
        image_layout = QHBoxLayout(self.image_row)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.addWidget(self.image_edit)
        image_layout.addWidget(self.image_button)
        image_layout.addWidget(self.capture_button)
        self.form.addRow("模板图片", self.image_row)
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 0.99)
        self.confidence_spin.setSingleStep(0.01)
        self.confidence_spin.setDecimals(2)
        self.confidence_row = self._make_field_row(self.confidence_spin)
        self.form.addRow("匹配置信度", self.confidence_row)
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.1, 86400)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_row = self._make_field_row(self.timeout_spin)
        self.form.addRow("识别超时", self.timeout_row)
        self.image_offset_widget = QWidget()
        image_offset_layout = QGridLayout(self.image_offset_widget)
        image_offset_layout.setContentsMargins(0, 0, 0, 0)
        image_offset_layout.setHorizontalSpacing(8)
        self.image_offset_x_spin = QSpinBox()
        self.image_offset_x_spin.setRange(-10000, 10000)
        self.image_offset_x_spin.setSuffix(" px")
        self.image_offset_y_spin = QSpinBox()
        self.image_offset_y_spin.setRange(-10000, 10000)
        self.image_offset_y_spin.setSuffix(" px")
        image_offset_layout.addWidget(QLabel("X"), 0, 0)
        image_offset_layout.addWidget(self.image_offset_x_spin, 0, 1)
        image_offset_layout.addWidget(QLabel("Y"), 0, 2)
        image_offset_layout.addWidget(self.image_offset_y_spin, 0, 3)
        self.form.addRow("点击偏移", self.image_offset_widget)
        self.path_edit = QLineEdit()
        self.path_row = self._make_field_row(self.path_edit)
        self.form.addRow("截图路径", self.path_row)

        inspector_inputs = (
            self.node_name_edit,
            self.type_box,
            self.x_spin,
            self.y_spin,
            self.capture_position_button,
            self.drag_start_x_spin,
            self.drag_start_y_spin,
            self.drag_end_x_spin,
            self.drag_end_y_spin,
            self.drag_duration_spin,
            self.record_drag_button,
            self.macro_name_edit,
            self.macro_mode_box,
            self.macro_repeat_spin,
            self.macro_interval_spin,
            self.window_choice_box,
            self.window_refresh_button,
            self.window_title_edit,
            self.window_process_edit,
            self.window_timeout_spin,
            self.window_probe_button,
            self.condition_operator_box,
            self.condition_image_edit,
            self.condition_image_button,
            self.condition_confidence_spin,
            self.condition_timeout_spin,
            self.key_edit,
            self.text_edit,
            self.seconds_spin,
            self.ocr_target_edit,
            self.image_edit,
            self.image_button,
            self.capture_button,
            self.confidence_spin,
            self.timeout_spin,
            self.image_offset_x_spin,
            self.image_offset_y_spin,
            self.path_edit,
        )
        for widget in inspector_inputs:
            widget.setMinimumWidth(0)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        for row_widget in (
            self.coordinate_widget,
            self.drag_widget,
            self.macro_widget,
            self.window_widget,
            self.condition_widget,
            self.ocr_widget,
            self.image_row,
            self.image_offset_widget,
            self.path_row,
        ):
            row_widget.setMinimumWidth(0)
            row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.macro_event_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(5000)
        self.log_view.setPlaceholderText("运行日志会显示在这里")

        right = QWidget()
        right.setObjectName("editorRightPanel")
        self.editor_inspector_panel = right
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(13, 13, 13, 13)
        right_layout.setSpacing(8)
        inspector_header = QHBoxLayout()
        inspector_header.setContentsMargins(0, 0, 0, 2)
        inspector_title = QLabel("节点属性")
        inspector_title.setObjectName("inspectorTitle")
        self.inspector_close_button = QPushButton("")
        self.inspector_close_button.setAccessibleName("关闭节点属性")
        self.inspector_close_button.setToolTip("收起节点属性")
        self.inspector_close_button.setFixedSize(32, 32)
        self._apply_button_icon(self.inspector_close_button, QStyle.SP_TitleBarCloseButton)
        inspector_header.addWidget(inspector_title)
        inspector_header.addStretch(1)
        inspector_header.addWidget(self.inspector_close_button)
        right_layout.addLayout(inspector_header)
        self.editor_empty_state = QLabel("选择一个节点\n右侧将显示可编辑属性")
        self.editor_empty_state.setObjectName("editorEmptyState")
        self.editor_empty_state.setAlignment(Qt.AlignCenter)
        self.editor_empty_state.setWordWrap(True)
        right_layout.addWidget(self.editor_empty_state)
        right_layout.addWidget(self.properties_scroll, 1)
        splitter = QSplitter(Qt.Horizontal)
        self.editor_splitter = splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right)
        splitter.setSizes([820, 300])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setCollapsible(1, True)
        splitter.setHandleWidth(1)
        self.editor_page = QWidget()
        self.editor_page.setObjectName("editorPage")
        editor_page_layout = QVBoxLayout(self.editor_page)
        editor_page_layout.setContentsMargins(0, 0, 0, 0)
        editor_page_layout.setSpacing(0)
        editor_page_layout.addWidget(splitter)

        self.window_tasks_page = self._build_window_tasks_page()
        self.window_tasks_page.setObjectName("windowTasksPage")
        self.run_history_page = self._build_run_history_page()
        self.template_library_page = self._build_template_library_page()
        self.settings_page = self._build_settings_page()

        self.main_tabs = QStackedWidget()
        self.main_tabs.setObjectName("workspaceStack")
        for page in (
            self.window_tasks_page,
            self.editor_page,
            self.run_history_page,
            self.template_library_page,
            self.settings_page,
        ):
            self.main_tabs.addWidget(page)

        shell = QWidget()
        self.app_shell = shell
        shell.setObjectName("appShell")
        shell.setProperty(
            "density",
            "compact" if bool(self._draft_settings.value("ui/compact_density", False, type=bool)) else "comfortable",
        )
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        navigation = QWidget()
        navigation.setObjectName("navigationRail")
        navigation.setFixedWidth(58)
        navigation_layout = QVBoxLayout(navigation)
        navigation_layout.setContentsMargins(10, 10, 10, 10)
        navigation_layout.setSpacing(6)
        nav_brand = QLabel("A")
        nav_brand.setObjectName("navBrandMark")
        nav_brand.setAlignment(Qt.AlignCenter)
        navigation_layout.addWidget(nav_brand, 0, Qt.AlignHCenter)
        navigation_layout.addSpacing(6)

        self.nav_tasks_button = self._create_navigation_button("任务库", QStyle.SP_FileDialogListView)
        self.nav_flow_button = self._create_navigation_button("流程设计", QStyle.SP_FileDialogDetailedView)
        self.nav_logs_button = self._create_navigation_button("执行记录", QStyle.SP_MessageBoxInformation)
        self.nav_templates_button = self._create_navigation_button("模板库", QStyle.SP_FileIcon)
        self.nav_settings_button = self._create_navigation_button("设置", QStyle.SP_ComputerIcon)
        for button in (
            self.nav_tasks_button,
            self.nav_flow_button,
            self.nav_logs_button,
            self.nav_templates_button,
        ):
            navigation_layout.addWidget(button, 0, Qt.AlignHCenter)
        navigation_layout.addStretch(1)
        navigation_layout.addWidget(self.nav_settings_button, 0, Qt.AlignHCenter)
        shell_layout.addWidget(navigation)
        shell_layout.addWidget(self.main_tabs, 1)
        self.setCentralWidget(shell)
        self.setMinimumSize(920, 620)

        self.status_primary_label = QLabel("就绪")
        self.status_primary_label.setObjectName("statusPrimary")
        self.status_metrics_label = QLabel("日志 0  ·  错误 0")
        self.status_metrics_label.setObjectName("statusMetrics")
        self.statusBar().addWidget(self.status_primary_label, 1)
        self.statusBar().addPermanentWidget(self.status_metrics_label)
        self._log_message_count = 0
        self._log_error_count = 0

        self._editor_toolbar_controls = (
            self.run_button,
            self.stop_button,
        )
        self.main_tabs.currentChanged.connect(self._on_main_tab_changed)
        self.nav_tasks_button.clicked.connect(lambda: self._show_workspace_page(self.window_tasks_page))
        self.nav_flow_button.clicked.connect(lambda: self._show_workspace_page(self.editor_page))
        self.nav_logs_button.clicked.connect(lambda: self._show_workspace_page(self.run_history_page))
        self.nav_templates_button.clicked.connect(lambda: self._show_workspace_page(self.template_library_page))
        self.nav_settings_button.clicked.connect(lambda: self._show_workspace_page(self.settings_page))
        self.inspector_close_button.clicked.connect(self._collapse_inspector)
        self.editor_task_box.currentIndexChanged.connect(self._editor_task_changed)
        self.editor_target_button.clicked.connect(self._show_active_task_settings)
        self.nav_tasks_button.setChecked(True)
        self._on_main_tab_changed(self.main_tabs.currentIndex())

        self.action_new.triggered.connect(self._new_script)
        self.action_open.triggered.connect(self._open_script)
        self.action_save.triggered.connect(self._save_script)
        self.add_button.clicked.connect(self._add_step)
        self.add_action_node_button.clicked.connect(self._add_step)
        self.add_condition_button.clicked.connect(self._add_condition_node)
        self.delete_button.clicked.connect(self._delete_step)
        self.up_button.clicked.connect(self._auto_layout_flow)
        self.run_button.clicked.connect(self._run_script)
        self.stop_button.clicked.connect(self._stop_script)
        self.type_box.currentIndexChanged.connect(self._form_changed)
        self.node_name_edit.textChanged.connect(self._form_changed)
        self.node_name_edit.textChanged.connect(self._condition_form_changed)
        self.enabled_box.stateChanged.connect(self._form_changed)
        self.x_spin.valueChanged.connect(self._form_changed)
        self.y_spin.valueChanged.connect(self._form_changed)
        self.drag_start_x_spin.valueChanged.connect(self._form_changed)
        self.drag_start_y_spin.valueChanged.connect(self._form_changed)
        self.drag_end_x_spin.valueChanged.connect(self._form_changed)
        self.drag_end_y_spin.valueChanged.connect(self._form_changed)
        self.drag_duration_spin.valueChanged.connect(self._form_changed)
        self.macro_name_edit.textChanged.connect(self._form_changed)
        self.macro_mode_box.currentIndexChanged.connect(self._form_changed)
        self.macro_repeat_spin.valueChanged.connect(self._form_changed)
        self.macro_interval_spin.valueChanged.connect(self._form_changed)
        self.window_title_edit.textChanged.connect(self._form_changed)
        self.window_process_edit.textChanged.connect(self._form_changed)
        self.window_timeout_spin.valueChanged.connect(self._form_changed)
        self.window_background_check.stateChanged.connect(self._form_changed)
        self.window_background_check.stateChanged.connect(self._update_window_mode_controls)
        self.window_activate_check.stateChanged.connect(self._form_changed)
        self.window_choice_box.currentIndexChanged.connect(self._window_choice_changed)
        self.window_refresh_button.clicked.connect(self._refresh_window_choices)
        self.window_probe_button.clicked.connect(self._probe_window)
        self.key_edit.textChanged.connect(self._form_changed)
        self.text_edit.textChanged.connect(self._form_changed)
        self.seconds_spin.valueChanged.connect(self._form_changed)
        self.ocr_target_edit.textChanged.connect(self._form_changed)
        self.image_edit.textChanged.connect(self._form_changed)
        self.confidence_spin.valueChanged.connect(self._form_changed)
        self.timeout_spin.valueChanged.connect(self._form_changed)
        self.image_offset_x_spin.valueChanged.connect(self._form_changed)
        self.image_offset_y_spin.valueChanged.connect(self._form_changed)
        self.path_edit.textChanged.connect(self._form_changed)
        self.condition_operator_box.currentIndexChanged.connect(self._condition_form_changed)
        self.condition_negate_box.stateChanged.connect(self._condition_form_changed)
        self.condition_image_edit.textChanged.connect(self._condition_form_changed)
        self.condition_confidence_spin.valueChanged.connect(self._condition_form_changed)
        self.condition_timeout_spin.valueChanged.connect(self._condition_form_changed)
        self.condition_image_button.clicked.connect(self._choose_condition_image)
        self.image_button.clicked.connect(self._choose_image)
        self.capture_button.clicked.connect(self._capture_template)
        self.capture_position_button.clicked.connect(self._capture_mouse_position)
        self.mouse_position_captured.connect(self._finish_mouse_capture)
        self.record_drag_button.clicked.connect(self._record_drag)
        self.drag_recorded.connect(self._finish_drag_recording)
        self.record_macro_button.clicked.connect(self._toggle_macro_recording)
        self.macro_recorded.connect(self._finish_macro_recording)
        self.position_shortcut = QShortcut(QKeySequence("F8"), self)
        self.position_shortcut.setContext(Qt.ApplicationShortcut)
        self.position_shortcut.activated.connect(self._capture_mouse_position)
        self.macro_shortcut = QShortcut(QKeySequence("F9"), self)
        self.macro_shortcut.setContext(Qt.ApplicationShortcut)
        self.macro_shortcut.activated.connect(self._toggle_macro_recording)

    def _create_navigation_button(
        self,
        label: str,
        standard_pixmap: QStyle.StandardPixmap,
    ) -> QPushButton:
        button = QPushButton("")
        button.setAccessibleName(label)
        button.setToolTip(label)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setCursor(Qt.PointingHandCursor)
        self._apply_button_icon(button, standard_pixmap)
        return button

    def _show_workspace_page(self, page: QWidget) -> None:
        if self.main_tabs.currentWidget() is page:
            return
        self.main_tabs.setCurrentWidget(page)

    def _collapse_inspector(self) -> None:
        self.editor_inspector_panel.hide()
        self.editor_splitter.setSizes([1, 0])

    def _expand_inspector(self) -> None:
        if self.editor_inspector_panel.isVisible():
            return
        self.editor_inspector_panel.show()
        width = max(600, self.editor_splitter.width())
        self.editor_splitter.setSizes([max(320, width - 300), 300])

    def _update_workspace_context(self) -> None:
        if not hasattr(self, "main_tabs") or not hasattr(self, "workspace_context_label"):
            return
        page = self.main_tabs.currentWidget()
        if page is self.window_tasks_page:
            context = f"任务库 · {len(self.window_tasks)} 个本地任务"
        elif page is self.editor_page:
            task = self._active_task()
            task_name = str(task.get("name", "未命名任务")) if task is not None else "未选择任务"
            context = f"{task_name} · 更改自动保存"
        elif page is self.run_history_page:
            context = "执行记录 · 当前会话"
        elif page is self.template_library_page:
            count = self.template_list.count() if hasattr(self, "template_list") else 0
            context = f"模板库 · {count} 个素材"
        else:
            context = "本地设置"
        self.workspace_context_label.setText(context)

    def _on_main_tab_changed(self, index: int) -> None:
        """Keep the toolbar focused on the active page."""
        page = self.main_tabs.widget(index)
        editor_visible = page is self.editor_page
        for control in getattr(self, "_editor_toolbar_controls", ()):
            control.setVisible(editor_visible)
        for action in getattr(self, "_editor_toolbar_actions", ()):
            action.setVisible(editor_visible)
        for separator in getattr(self, "_editor_toolbar_separators", ()):
            separator.setVisible(editor_visible)
        page_state = {
            self.window_tasks_page: (self.nav_tasks_button, f"任务库 · {len(self.window_tasks)} 个本地任务"),
            self.editor_page: (self.nav_flow_button, "流程设计 · 更改自动保存"),
            self.run_history_page: (self.nav_logs_button, "执行记录 · 当前会话"),
            self.template_library_page: (self.nav_templates_button, "模板库 · 任务资源"),
            self.settings_page: (self.nav_settings_button, "本地设置"),
        }
        button, context = page_state.get(page, (None, APP_NAME))
        if button is not None:
            button.setChecked(True)
        self.workspace_context_label.setText(context)
        self._update_workspace_context()
        if editor_visible and hasattr(self, "flow_canvas"):
            self._refresh_editor_task_box()
            QTimer.singleShot(0, self.flow_canvas.fit_flow)
        elif page is self.template_library_page:
            self._refresh_template_library()

    def _build_window_tasks_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("pageHeader")
        page_title = QLabel("任务库")
        page_title.setObjectName("pageTitle")
        page_subtitle = QLabel("集中管理目标窗口、执行模式和流程")
        page_subtitle.setObjectName("pageSubtitle")
        self.task_count_label = QLabel("0 个任务")
        self.task_count_label.setObjectName("pageCountBadge")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 5, 14, 5)
        header_layout.setSpacing(9)
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(0)
        title_column.addWidget(page_title)
        title_column.addWidget(page_subtitle)
        header_layout.addLayout(title_column)
        header_layout.addWidget(self.task_count_label)
        header_layout.addStretch(1)
        page_layout.addWidget(header)

        self.task_list = QListWidget()
        self.task_list.setObjectName("taskList")
        self.task_list.setMinimumWidth(340)
        self.task_list.setMinimumHeight(170)
        self.task_list.setAlternatingRowColors(True)
        self.task_list.currentRowChanged.connect(self._on_window_task_selected)
        self.task_add_button = QPushButton("新增任务")
        self.task_delete_button = QPushButton("")
        self.task_delete_button.setAccessibleName("删除任务")
        self.task_delete_button.setFixedWidth(36)
        self.task_run_button = QPushButton("运行任务")
        self.task_stop_button = QPushButton("")
        self.task_stop_button.setAccessibleName("停止任务")
        self.task_stop_button.setFixedWidth(38)
        self.task_run_all_button = QPushButton("运行全部")
        self.task_stop_all_button = QPushButton("")
        self.task_stop_all_button.setAccessibleName("停止全部任务")
        self.task_stop_all_button.setFixedWidth(38)
        for button, object_name, tooltip in (
            (self.task_add_button, "taskAddButton", "新增一个独立窗口任务"),
            (self.task_delete_button, "taskDeleteButton", "删除当前窗口任务"),
            (self.task_run_button, "taskRunButton", "在独立线程中运行当前任务"),
            (self.task_stop_button, "taskStopButton", "停止当前任务"),
            (self.task_run_all_button, "taskRunAllButton", "为每个任务启动独立线程"),
            (self.task_stop_all_button, "taskStopAllButton", "停止所有窗口任务"),
        ):
            self._configure_toolbar_button(button, object_name, tooltip)
        for button, icon in (
            (self.task_add_button, QStyle.SP_FileDialogNewFolder),
            (self.task_delete_button, QStyle.SP_TrashIcon),
            (self.task_run_button, QStyle.SP_MediaPlay),
            (self.task_stop_button, QStyle.SP_MediaStop),
            (self.task_run_all_button, QStyle.SP_MediaPlay),
            (self.task_stop_all_button, QStyle.SP_MediaStop),
        ):
            self._apply_button_icon(button, icon)
        self.task_stop_button.setEnabled(False)
        self.task_stop_all_button.setEnabled(False)
        header_layout.addWidget(self.task_add_button)
        header_layout.addWidget(self.task_run_all_button)
        header_layout.addWidget(self.task_stop_all_button)
        task_run_row = QHBoxLayout()
        task_run_row.setContentsMargins(0, 0, 0, 0)
        task_run_row.setSpacing(6)
        task_run_row.addWidget(self.task_run_button, 1)
        task_run_row.addWidget(self.task_stop_button)
        task_run_row.addWidget(self.task_delete_button)
        task_list_panel = QWidget()
        task_list_panel.setObjectName("taskSidebar")
        task_list_layout = QVBoxLayout(task_list_panel)
        task_list_layout.setContentsMargins(14, 12, 14, 12)
        task_list_layout.setSpacing(8)
        task_list_caption = QLabel("任务列表")
        task_list_caption.setObjectName("taskListCaption")
        task_list_hint = QLabel("双击或点击“编辑流程”进入流程设计")
        task_list_hint.setObjectName("taskListHint")
        task_list_layout.addWidget(task_list_caption)
        task_list_layout.addWidget(task_list_hint)
        task_list_layout.addWidget(self.task_list, 1)
        task_list_layout.addLayout(task_run_row)

        target_group = QGroupBox("任务配置")
        target_group.setObjectName("targetPanel")
        target_layout = QGridLayout(target_group)
        target_layout.setContentsMargins(14, 17, 14, 13)
        target_layout.setHorizontalSpacing(10)
        target_layout.setVerticalSpacing(9)
        target_layout.setColumnStretch(1, 2)
        target_layout.setColumnStretch(3, 1)
        self.task_name_edit = QLineEdit()
        self.task_name_edit.setPlaceholderText("例如：处理窗口 A")
        self.task_window_choice_box = QComboBox()
        self.task_window_choice_box.addItem("选择当前已打开的窗口…", None)
        self.task_window_refresh_button = QPushButton("")
        self.task_window_refresh_button.setAccessibleName("刷新窗口列表")
        self.task_window_refresh_button.setFixedWidth(36)
        self._configure_toolbar_button(
            self.task_window_refresh_button,
            "taskWindowRefreshButton",
            "重新枚举当前桌面上已打开的窗口",
        )
        self._apply_button_icon(self.task_window_refresh_button, QStyle.SP_BrowserReload)
        self.task_title_edit = QLineEdit()
        self.task_title_edit.setPlaceholderText("标题关键词（包含匹配）")
        self.task_process_edit = QLineEdit()
        self.task_process_edit.setPlaceholderText("进程名，可选，例如 game.exe")
        self.task_timeout_spin = QDoubleSpinBox()
        self.task_timeout_spin.setRange(0.1, 86400.0)
        self.task_timeout_spin.setDecimals(1)
        self.task_timeout_spin.setSingleStep(0.5)
        self.task_timeout_spin.setSuffix(" 秒")
        self.task_timeout_spin.setValue(10.0)
        self.task_background_check = QCheckBox("允许后台窗口消息输入（实验）")
        self.task_activate_check = QCheckBox("运行时激活窗口（前台模式）")
        self.task_background_check.setChecked(True)
        self.task_activate_check.setChecked(False)
        self.task_background_check.hide()
        self.task_activate_check.hide()
        self.task_mode_label = QLabel("后台模式")
        self.task_mode_label.setObjectName("fixedModeLabel")
        self.task_mode_label.setToolTip("窗口任务始终使用后台消息输入，不会激活或抢占当前窗口")
        self.task_run_mode_box = QComboBox()
        self.task_run_mode_box.addItem("执行一次", "once")
        self.task_run_mode_box.addItem("重复指定次数", "repeat")
        self.task_run_mode_box.addItem("持续循环", "loop")
        self.task_repeat_label = QLabel("重复次数")
        self.task_repeat_spin = QSpinBox()
        self.task_repeat_spin.setRange(1, 999999)
        self.task_repeat_spin.setValue(2)
        self.task_interval_label = QLabel("轮次间隔")
        self.task_interval_spin = QDoubleSpinBox()
        self.task_interval_spin.setRange(0, 86400)
        self.task_interval_spin.setDecimals(2)
        self.task_interval_spin.setSingleStep(0.1)
        self.task_interval_spin.setSuffix(" 秒")
        self.task_interval_spin.setValue(0.5)
        self.task_status_label = QLabel("未运行")
        self.task_status_label.setObjectName("taskStatusLabel")
        self.task_status_label.setWordWrap(True)
        target_layout.addWidget(QLabel("任务名称"), 0, 0)
        target_layout.addWidget(self.task_name_edit, 0, 1)
        target_layout.addWidget(QLabel("状态"), 0, 2)
        target_layout.addWidget(self.task_status_label, 0, 3)
        target_layout.addWidget(QLabel("目标窗口"), 1, 0)
        target_layout.addWidget(self.task_window_choice_box, 1, 1, 1, 2)
        target_layout.addWidget(self.task_window_refresh_button, 1, 3)
        target_layout.addWidget(QLabel("标题关键词"), 2, 0)
        target_layout.addWidget(self.task_title_edit, 2, 1)
        target_layout.addWidget(QLabel("进程名"), 2, 2)
        target_layout.addWidget(self.task_process_edit, 2, 3)
        target_layout.addWidget(QLabel("执行模式"), 3, 0)
        target_layout.addWidget(self.task_run_mode_box, 3, 1)
        target_layout.addWidget(self.task_repeat_label, 3, 2)
        target_layout.addWidget(self.task_repeat_spin, 3, 3)
        target_layout.addWidget(QLabel("查找超时"), 4, 0)
        target_layout.addWidget(self.task_timeout_spin, 4, 1)
        target_layout.addWidget(self.task_interval_label, 4, 2)
        target_layout.addWidget(self.task_interval_spin, 4, 3)
        target_layout.addWidget(self.task_mode_label, 5, 0, 1, 4, Qt.AlignLeft)

        operations_group = QGroupBox("任务流程")
        operations_group.setObjectName("operationsPanel")
        operations_layout = QVBoxLayout(operations_group)
        operations_layout.setContentsMargins(14, 17, 14, 13)
        operations_layout.setSpacing(8)
        self.task_steps_preview = QListWidget()
        self.task_steps_preview.setObjectName("taskStepsPreview")
        self.task_steps_preview.setAlternatingRowColors(True)
        self.task_steps_preview.setMinimumHeight(110)
        self.task_steps_preview.setMaximumHeight(250)
        self.task_steps_preview.setToolTip("双击步骤可直接进入当前任务的步骤编辑器")
        operations_layout.addWidget(self.task_steps_preview)
        operation_buttons = QHBoxLayout()
        self.task_edit_steps_button = QPushButton("编辑流程")
        self.task_clear_steps_button = QPushButton("")
        self.task_clear_steps_button.setAccessibleName("清空流程")
        self.task_clear_steps_button.setFixedWidth(36)
        self._configure_toolbar_button(self.task_edit_steps_button, "taskSyncButton", "打开当前任务专属的流程图编辑器")
        self._configure_toolbar_button(self.task_clear_steps_button, "taskClearStepsButton", "清空当前任务的流程图并保留开始/结束节点")
        self._apply_button_icon(self.task_edit_steps_button, QStyle.SP_FileDialogDetailedView)
        self._apply_button_icon(self.task_clear_steps_button, QStyle.SP_TrashIcon)
        operation_buttons.addWidget(self.task_edit_steps_button)
        operation_buttons.addWidget(self.task_clear_steps_button)
        operation_buttons.addStretch(1)
        operations_layout.addLayout(operation_buttons)

        right_panel = QWidget()
        right_panel.setObjectName("taskDetailPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(13, 4, 13, 13)
        right_layout.setSpacing(0)
        right_layout.addWidget(target_group)
        right_layout.addWidget(operations_group, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(task_list_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(1)
        splitter.setSizes([620, 380])
        page_layout.addWidget(splitter, 1)

        self.task_add_button.clicked.connect(self._add_window_task)
        self.task_delete_button.clicked.connect(self._delete_window_task)
        self.task_run_button.clicked.connect(self._run_selected_window_task)
        self.task_stop_button.clicked.connect(self._stop_selected_window_task)
        self.task_run_all_button.clicked.connect(self._run_all_window_tasks)
        self.task_stop_all_button.clicked.connect(self._stop_all_window_tasks)
        self.task_name_edit.textChanged.connect(self._window_task_form_changed)
        self.task_title_edit.textChanged.connect(self._window_task_form_changed)
        self.task_process_edit.textChanged.connect(self._window_task_form_changed)
        self.task_timeout_spin.valueChanged.connect(self._window_task_form_changed)
        self.task_background_check.stateChanged.connect(self._window_task_form_changed)
        self.task_background_check.stateChanged.connect(self._update_task_mode_controls)
        self.task_activate_check.stateChanged.connect(self._window_task_form_changed)
        self.task_run_mode_box.currentIndexChanged.connect(self._window_task_form_changed)
        self.task_run_mode_box.currentIndexChanged.connect(self._update_task_mode_controls)
        self.task_repeat_spin.valueChanged.connect(self._window_task_form_changed)
        self.task_interval_spin.valueChanged.connect(self._window_task_form_changed)
        self.task_window_choice_box.currentIndexChanged.connect(self._task_window_choice_changed)
        self.task_window_refresh_button.clicked.connect(self._refresh_task_window_choices)
        self.task_edit_steps_button.clicked.connect(self._edit_selected_task_steps)
        self.task_clear_steps_button.clicked.connect(self._clear_window_task_steps)
        self.task_steps_preview.itemDoubleClicked.connect(lambda _item: self._edit_selected_task_steps())
        return page

    @staticmethod
    def _build_page_header(title: str, subtitle: str) -> tuple[QWidget, QHBoxLayout]:
        header = QWidget()
        header.setObjectName("pageHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 5, 14, 5)
        layout.setSpacing(9)
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(0)
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("pageSubtitle")
        title_column.addWidget(title_label)
        title_column.addWidget(subtitle_label)
        layout.addLayout(title_column)
        layout.addStretch(1)
        return header, layout

    def _build_run_history_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("runHistoryPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        header, header_layout = self._build_page_header(
            "执行记录",
            "按当前会话查看步骤日志、识别结果和错误",
        )
        self.log_export_button = QPushButton("导出日志")
        self.log_clear_button = QPushButton("清空")
        self._apply_button_icon(self.log_export_button, QStyle.SP_DialogSaveButton)
        self._apply_button_icon(self.log_clear_button, QStyle.SP_TrashIcon)
        header_layout.addWidget(self.log_export_button)
        header_layout.addWidget(self.log_clear_button)
        page_layout.addWidget(header)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setHandleWidth(1)
        self.run_session_list = QListWidget()
        self.run_session_list.setObjectName("runSessionList")
        self.run_session_list.setMinimumWidth(190)
        self.run_session_list.setMaximumWidth(250)
        self.log_session_item = QListWidgetItem("当前会话\n尚未运行")
        self.log_session_item.setSizeHint(QSize(0, 58))
        self.run_session_list.addItem(self.log_session_item)
        self.run_session_list.setCurrentRow(0)
        body_splitter.addWidget(self.run_session_list)

        console = QWidget()
        console_layout = QVBoxLayout(console)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.setSpacing(0)
        console_bar = QWidget()
        console_bar.setObjectName("flowHeader")
        console_bar_layout = QHBoxLayout(console_bar)
        console_bar_layout.setContentsMargins(12, 7, 12, 7)
        console_bar_layout.addWidget(QLabel("运行日志"))
        console_bar_layout.addSpacing(12)
        diagnostic_label = QLabel("识别诊断会直接写入对应步骤日志")
        diagnostic_label.setObjectName("pageSubtitle")
        console_bar_layout.addWidget(diagnostic_label)
        console_bar_layout.addStretch(1)
        console_layout.addWidget(console_bar)
        console_layout.addWidget(self.log_view, 1)
        body_splitter.addWidget(console)

        detail = QWidget()
        detail.setObjectName("logDetailPanel")
        detail.setMinimumWidth(235)
        detail.setMaximumWidth(310)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(15, 15, 15, 15)
        detail_layout.setSpacing(10)
        detail_title = QLabel("当前会话")
        detail_title.setObjectName("pageTitle")
        detail_layout.addWidget(detail_title)
        self.log_summary_label = QLabel("尚无执行日志")
        self.log_summary_label.setWordWrap(True)
        self.log_summary_label.setObjectName("pageSubtitle")
        detail_layout.addWidget(self.log_summary_label)
        self.log_round_label = QLabel("轮次  —")
        self.log_round_label.setObjectName("fixedModeLabel")
        detail_layout.addWidget(self.log_round_label, 0, Qt.AlignLeft)
        detail_layout.addSpacing(8)
        diagnostic_hint = QLabel("错误和未识别信息会保留完整步骤名称、匹配度与截图路径。")
        diagnostic_hint.setWordWrap(True)
        detail_layout.addWidget(diagnostic_hint)
        detail_layout.addStretch(1)
        body_splitter.addWidget(detail)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setStretchFactor(2, 0)
        body_splitter.setSizes([220, 650, 270])
        page_layout.addWidget(body_splitter, 1)

        self.log_clear_button.clicked.connect(self._clear_log_preview)
        self.log_export_button.clicked.connect(self._export_log_text)
        return page

    def _build_template_library_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("templateLibraryPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        header, header_layout = self._build_page_header(
            "模板库",
            "集中查看任务流程引用的图片模板和判断素材",
        )
        self.template_open_folder_button = QPushButton("打开目录")
        self.template_refresh_button = QPushButton("刷新素材")
        self.template_refresh_button.setObjectName("templateRefreshButton")
        self._apply_button_icon(self.template_open_folder_button, QStyle.SP_DirOpenIcon)
        self._apply_button_icon(self.template_refresh_button, QStyle.SP_BrowserReload)
        header_layout.addWidget(self.template_open_folder_button)
        header_layout.addWidget(self.template_refresh_button)
        page_layout.addWidget(header)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setHandleWidth(1)
        self.template_list = QListWidget()
        self.template_list.setObjectName("templateList")
        self.template_list.setViewMode(QListView.IconMode)
        self.template_list.setResizeMode(QListView.Adjust)
        self.template_list.setMovement(QListView.Static)
        self.template_list.setIconSize(QSize(150, 88))
        self.template_list.setGridSize(QSize(190, 142))
        self.template_list.setWordWrap(True)
        self.template_list.setSpacing(4)
        body_splitter.addWidget(self.template_list)

        detail = QWidget()
        detail.setObjectName("templateDetailPanel")
        detail.setMinimumWidth(260)
        detail.setMaximumWidth(340)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(15, 15, 15, 15)
        detail_layout.setSpacing(9)
        self.template_title_label = QLabel("未选择模板")
        self.template_title_label.setObjectName("pageTitle")
        self.template_task_label = QLabel("从左侧选择一个素材")
        self.template_task_label.setObjectName("pageSubtitle")
        self.template_preview_label = QLabel("暂无预览")
        self.template_preview_label.setObjectName("templatePreview")
        self.template_preview_label.setAlignment(Qt.AlignCenter)
        self.template_preview_label.setMinimumHeight(190)
        self.template_preview_label.setWordWrap(True)
        self.template_path_label = QLabel("—")
        self.template_path_label.setWordWrap(True)
        self.template_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.template_usage_label = QLabel("引用次数 0")
        self.template_usage_label.setObjectName("templateUsageLabel")
        self.template_reference_title = QLabel("引用节点")
        self.template_reference_title.setObjectName("settingsSectionTitle")
        self.template_reference_list = QListWidget()
        self.template_reference_list.setObjectName("templateReferenceList")
        self.template_reference_list.setAlternatingRowColors(True)
        self.template_reference_list.setWordWrap(False)
        self.template_reference_list.setTextElideMode(Qt.ElideRight)
        self.template_reference_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.template_reference_list.setMinimumHeight(38)
        self.template_reference_list.setMaximumHeight(190)
        self.template_reference_list.setToolTip("双击引用可直接定位到对应流程节点")
        self.template_locate_button = QPushButton("定位到流程")
        self.template_delete_button = QPushButton("删除图片")
        self._configure_toolbar_button(
            self.template_locate_button,
            "templateLocateButton",
            "打开流程设计并选中引用该图片的节点",
        )
        self._configure_toolbar_button(
            self.template_delete_button,
            "templateDeleteButton",
            "删除未被流程节点引用的图片素材",
        )
        self._apply_button_icon(self.template_locate_button, QStyle.SP_FileDialogDetailedView)
        self._apply_button_icon(self.template_delete_button, QStyle.SP_TrashIcon)
        template_actions = QHBoxLayout()
        template_actions.setContentsMargins(0, 3, 0, 0)
        template_actions.setSpacing(6)
        template_actions.addWidget(self.template_locate_button, 1)
        template_actions.addWidget(self.template_delete_button, 1)
        detail_layout.addWidget(self.template_title_label)
        detail_layout.addWidget(self.template_task_label)
        detail_layout.addWidget(self.template_preview_label)
        detail_layout.addWidget(QLabel("文件位置"))
        detail_layout.addWidget(self.template_path_label)
        detail_layout.addWidget(self.template_usage_label)
        detail_layout.addWidget(self.template_reference_title)
        detail_layout.addWidget(self.template_reference_list)
        detail_layout.addLayout(template_actions)
        detail_layout.addStretch(1)
        body_splitter.addWidget(detail)
        body_splitter.setStretchFactor(0, 1)
        body_splitter.setStretchFactor(1, 0)
        body_splitter.setSizes([780, 300])
        page_layout.addWidget(body_splitter, 1)

        self.template_list.currentItemChanged.connect(self._on_template_selected)
        self.template_reference_list.itemDoubleClicked.connect(self._locate_template_reference_item)
        self.template_refresh_button.clicked.connect(self._refresh_template_library)
        self.template_open_folder_button.clicked.connect(self._open_template_directory)
        self.template_locate_button.clicked.connect(self._locate_selected_template)
        self.template_delete_button.clicked.connect(self._delete_selected_template)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        header, _header_layout = self._build_page_header(
            "设置",
            "识别、后台输入、本地存储和运行诊断",
        )
        page_layout.addWidget(header)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        settings_nav = QWidget()
        settings_nav.setObjectName("settingsNav")
        settings_nav.setFixedWidth(190)
        settings_nav_layout = QVBoxLayout(settings_nav)
        settings_nav_layout.setContentsMargins(10, 12, 10, 12)
        settings_nav_layout.setSpacing(4)
        self.settings_recognition_button = QPushButton("识别与 OCR")
        self.settings_input_button = QPushButton("后台输入")
        self.settings_storage_button = QPushButton("存储与草稿")
        self.settings_diagnostics_button = QPushButton("诊断")
        for button in (
            self.settings_recognition_button,
            self.settings_input_button,
            self.settings_storage_button,
            self.settings_diagnostics_button,
        ):
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.PointingHandCursor)
            settings_nav_layout.addWidget(button)
        self.settings_recognition_button.setChecked(True)
        settings_nav_layout.addStretch(1)
        body_layout.addWidget(settings_nav)

        self.settings_stack = QStackedWidget()
        self.settings_stack.setObjectName("settingsContent")
        recognition_page = QWidget()
        recognition_layout = QVBoxLayout(recognition_page)
        recognition_layout.setContentsMargins(24, 20, 24, 20)
        recognition_layout.setSpacing(12)
        recognition_title = QLabel("图片识别")
        recognition_title.setObjectName("settingsSectionTitle")
        recognition_layout.addWidget(recognition_title)
        recognition_layout.addWidget(QLabel("新建图片步骤默认使用的匹配置信度"))
        self.default_confidence_spin = QDoubleSpinBox()
        self.default_confidence_spin.setRange(0.10, 0.99)
        self.default_confidence_spin.setSingleStep(0.01)
        self.default_confidence_spin.setDecimals(2)
        self.default_confidence_spin.setValue(float(self._draft_settings.value("ui/default_confidence", 0.85)))
        self.default_confidence_spin.setMaximumWidth(320)
        recognition_layout.addWidget(self.default_confidence_spin)
        scale_title = QLabel("多尺度匹配")
        scale_title.setObjectName("settingsSectionTitle")
        recognition_layout.addWidget(scale_title)
        recognition_layout.addWidget(QLabel("图片步骤会自动尝试 90% - 110% 的模板尺寸，以适配窗口缩放和 DPI 差异。"))
        ocr_title = QLabel("OCR")
        ocr_title.setObjectName("settingsSectionTitle")
        recognition_layout.addWidget(ocr_title)
        recognition_layout.addWidget(QLabel("窗口内 OCR 使用本地 RapidOCR 中英文模型，截图不会上传。"))
        recognition_layout.addStretch(1)

        input_page = QWidget()
        input_layout = QVBoxLayout(input_page)
        input_layout.setContentsMargins(24, 20, 24, 20)
        input_layout.setSpacing(12)
        input_title = QLabel("后台输入")
        input_title.setObjectName("settingsSectionTitle")
        input_layout.addWidget(input_title)
        fixed_mode = QLabel("● 后台窗口消息模式已启用")
        fixed_mode.setObjectName("dependencyReady")
        input_layout.addWidget(fixed_mode)
        input_layout.addWidget(QLabel("窗口任务不会主动抢占鼠标焦点；兼容性取决于目标程序是否接受 Win32 后台消息。"))
        input_layout.addWidget(QLabel("最小化窗口会优先使用后台截图，失败时日志会记录截图方式和具体原因。"))
        input_layout.addStretch(1)

        storage_page = QWidget()
        storage_layout = QVBoxLayout(storage_page)
        storage_layout.setContentsMargins(24, 20, 24, 20)
        storage_layout.setSpacing(12)
        storage_title = QLabel("本地草稿")
        storage_title.setObjectName("settingsSectionTitle")
        storage_layout.addWidget(storage_title)
        self.autosave_check = QCheckBox("编辑后自动保存本地草稿")
        self.autosave_check.setChecked(bool(self._draft_settings.value("ui/autosave_enabled", True, type=bool)))
        storage_layout.addWidget(self.autosave_check)
        self.compact_density_check = QCheckBox("使用紧凑任务列表")
        self.compact_density_check.setChecked(bool(self._draft_settings.value("ui/compact_density", False, type=bool)))
        storage_layout.addWidget(self.compact_density_check)
        storage_path = QLabel(str(self._base_dir()))
        storage_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        storage_path.setWordWrap(True)
        storage_layout.addWidget(QLabel("任务素材默认保存在任务同名目录中"))
        storage_layout.addWidget(storage_path)
        storage_layout.addStretch(1)

        diagnostics_page = QWidget()
        diagnostics_layout = QVBoxLayout(diagnostics_page)
        diagnostics_layout.setContentsMargins(24, 20, 24, 20)
        diagnostics_layout.setSpacing(11)
        diagnostics_title = QLabel("依赖状态")
        diagnostics_title.setObjectName("settingsSectionTitle")
        diagnostics_layout.addWidget(diagnostics_title)
        self.dependency_labels: dict[str, QLabel] = {}
        for module_name, display_name in (
            ("cv2", "OpenCV 图像识别"),
            ("numpy", "NumPy 图像数据"),
            ("rapidocr_onnxruntime", "RapidOCR 文字识别"),
            ("pynput", "键鼠录制"),
        ):
            available = importlib.util.find_spec(module_name) is not None
            label = QLabel(f"{'●' if available else '○'}  {display_name}  {'已就绪' if available else '未安装'}")
            label.setObjectName("dependencyReady" if available else "dependencyMissing")
            diagnostics_layout.addWidget(label)
            self.dependency_labels[module_name] = label
        diagnostics_layout.addStretch(1)

        for settings_page in (recognition_page, input_page, storage_page, diagnostics_page):
            self.settings_stack.addWidget(settings_page)
        body_layout.addWidget(self.settings_stack, 1)
        page_layout.addWidget(body, 1)

        self.settings_recognition_button.clicked.connect(lambda: self.settings_stack.setCurrentIndex(0))
        self.settings_input_button.clicked.connect(lambda: self.settings_stack.setCurrentIndex(1))
        self.settings_storage_button.clicked.connect(lambda: self.settings_stack.setCurrentIndex(2))
        self.settings_diagnostics_button.clicked.connect(lambda: self.settings_stack.setCurrentIndex(3))
        self.default_confidence_spin.valueChanged.connect(self._save_default_confidence)
        self.autosave_check.toggled.connect(self._save_autosave_setting)
        self.compact_density_check.toggled.connect(self._save_density_setting)
        return page

    def _save_default_confidence(self, value: float) -> None:
        self._draft_settings.setValue("ui/default_confidence", float(value))

    def _save_autosave_setting(self, enabled: bool) -> None:
        self._draft_settings.setValue("ui/autosave_enabled", bool(enabled))
        if enabled and self.is_dirty:
            self._schedule_autosave()
        elif not enabled:
            self._autosave_timer.stop()

    def _save_density_setting(self, compact: bool) -> None:
        self._draft_settings.setValue("ui/compact_density", bool(compact))
        if not hasattr(self, "app_shell"):
            return
        self.app_shell.setProperty("density", "compact" if compact else "comfortable")
        self.app_shell.style().unpolish(self.app_shell)
        self.app_shell.style().polish(self.app_shell)
        if hasattr(self, "task_list"):
            self.task_list.style().unpolish(self.task_list)
            self.task_list.style().polish(self.task_list)

    def _export_log_text(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出运行日志",
            str(self._base_dir() / f"automation-log-{time.strftime('%Y%m%d-%H%M%S')}.txt"),
            "文本文件 (*.txt)",
        )
        if not filename:
            return
        try:
            Path(filename).write_text(self.log_view.toPlainText(), encoding="utf-8")
            self.statusBar().showMessage(f"日志已导出：{filename}", 4000)
        except OSError as exc:
            QMessageBox.critical(self, "导出日志失败", str(exc))

    def _resolve_template_library_path(self, raw_path: Any, task_name: str) -> Path:
        """Resolve a task image exactly like the worker does at runtime.

        Relative paths are task-local first.  Older drafts may contain a
        relative ``current_file`` and scripts exported from a packaged build
        may be opened from a different working directory, so try every stable
        project root before reporting a missing asset.
        """
        raw_text = str(raw_path or "").strip()
        if os.sep != "\\":
            # Keep exported Windows paths usable in development/test runs on
            # other platforms as well.
            raw_text = raw_text.replace("\\", os.sep)
        requested = Path(raw_text).expanduser()
        if requested.is_absolute():
            return requested.absolute()
        base_dir = self._base_dir()
        roots: list[Path] = [base_dir / self._safe_folder_name(task_name)]
        roots.extend(
            [
                base_dir,
                self._application_dir(),
                Path.cwd().resolve(),
            ]
        )
        candidates: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            # Keep the user's path spelling for display (notably Windows
            # short-name segments) while using _template_path_key for stable
            # de-duplication.
            candidate = (root / requested).absolute()
            key = self._template_path_key(candidate)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
            if candidate.is_file():
                return candidate
        # Keep a deterministic absolute path for the detail pane and for a
        # useful "file not found" message when no candidate exists.
        return candidates[0] if candidates else (base_dir / requested).absolute()

    @staticmethod
    def _load_template_pixmap(path: Path) -> QPixmap:
        """Decode an image from bytes so non-ASCII Windows paths are safe."""
        try:
            data = Path(path).read_bytes()
        except (OSError, ValueError):
            return QPixmap()
        if not data:
            return QPixmap()
        image = QImage()
        if not image.loadFromData(data):
            return QPixmap()
        return QPixmap.fromImage(image)

    @staticmethod
    def _template_path_key(path: Path) -> str:
        try:
            resolved = path.resolve(strict=False)
        except OSError:
            resolved = path.absolute()
        return os.path.normcase(unicodedata.normalize("NFC", str(resolved)))

    def _template_reference_entries(self) -> list[dict[str, Any]]:
        """Return real image assets and every flow node that references them."""
        entries: dict[str, dict[str, Any]] = {}
        base_dir = self._base_dir()
        supported = {".png", ".jpg", ".jpeg", ".bmp"}

        def add_reference(
            *,
            task_index: int,
            task_name: str,
            raw_path: Any,
            node: dict[str, Any] | None,
            source: str,
            step_type: str,
            condition_index: int | None = None,
            step_index: int | None = None,
        ) -> None:
            raw = str(raw_path or "").strip()
            if not raw:
                return
            path = self._resolve_template_library_path(raw, task_name)
            key = self._template_path_key(path)
            entry = entries.setdefault(
                key,
                {"path": path, "tasks": set(), "usages": []},
            )
            # An existing file is a better display path than a stale missing
            # candidate when multiple tasks spell the same absolute path.
            if not Path(entry["path"]).is_file() and path.is_file():
                entry["path"] = path
            entry["tasks"].add(task_name)
            node_id = str(node.get("id", "")) if isinstance(node, dict) else ""
            if source == "condition":
                fallback_label = "判断节点"
            else:
                fallback_label = TYPE_LABELS.get(step_type, step_type or "操作节点")
            node_label = ""
            if isinstance(node, dict):
                node_label = str(node.get("label", "")).strip()
                if not node_label and isinstance(node.get("step"), dict):
                    node_label = str(node["step"].get("label", "")).strip()
            usage = {
                "task_index": task_index,
                "task_name": task_name,
                "node_id": node_id,
                "node_label": node_label or fallback_label,
                "node_type": source,
                "step_type": step_type,
                "condition_index": condition_index,
                "step_index": step_index,
                "raw_path": raw,
                "path": str(path),
            }
            entry["usages"].append(usage)

        for task_index, task in enumerate(self.window_tasks):
            task_name = str(task.get("name") or f"窗口任务 {task_index + 1}")
            flow = task.get("flow")
            nodes = flow.get("nodes", []) if isinstance(flow, dict) else []
            if not isinstance(nodes, list):
                nodes = []
            legacy_steps = task.get("steps", [])
            if not isinstance(legacy_steps, list):
                legacy_steps = []
            has_flow_nodes = isinstance(nodes, list) and any(
                isinstance(node, dict) and node.get("type") in {"action", "condition"}
                for node in nodes
            )
            flow_has_image = any(
                isinstance(node, dict)
                and (
                    (
                        node.get("type") == "action"
                        and isinstance(node.get("step"), dict)
                        and str(node["step"].get("image", "")).strip()
                    )
                    or (
                        node.get("type") == "condition"
                        and isinstance(node.get("conditions"), list)
                        and any(
                            isinstance(condition, dict)
                            and str(condition.get("image", "")).strip()
                            for condition in node.get("conditions", [])
                        )
                    )
                )
                for node in nodes
            )
            legacy_steps_have_image = any(
                isinstance(step, dict) and str(step.get("image", "")).strip()
                for step in legacy_steps
            )
            if has_flow_nodes and (flow_has_image or not legacy_steps_have_image):
                # The flow is canonical.  task["steps"] is a compatibility
                # projection and must not be scanned a second time.
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    node_type = str(node.get("type", ""))
                    if node_type == "action" and isinstance(node.get("step"), dict):
                        step = node["step"]
                        add_reference(
                            task_index=task_index,
                            task_name=task_name,
                            raw_path=step.get("image"),
                            node=node,
                            source="action",
                            step_type=str(step.get("type", "")),
                        )
                    elif node_type == "condition":
                        conditions = node.get("conditions", [])
                        if not isinstance(conditions, list):
                            continue
                        for condition_index, condition in enumerate(conditions):
                            if not isinstance(condition, dict):
                                continue
                            add_reference(
                                task_index=task_index,
                                task_name=task_name,
                                raw_path=condition.get("image"),
                                node=node,
                                source="condition",
                                step_type=str(condition.get("type", "image_exists")),
                                condition_index=condition_index,
                            )
            else:
                # Legacy scripts may not have a flow yet.
                for step_index, step in enumerate(legacy_steps):
                    if not isinstance(step, dict):
                        continue
                    add_reference(
                        task_index=task_index,
                        task_name=task_name,
                        raw_path=step.get("image"),
                        node=None,
                        source="action",
                        step_type=str(step.get("type", "")),
                        step_index=step_index,
                    )

            task_dir = base_dir / self._safe_folder_name(task_name)
            if task_dir.is_dir():
                try:
                    task_assets = task_dir.iterdir()
                except OSError:
                    task_assets = ()
                for path in task_assets:
                    if not path.is_file() or path.suffix.lower() not in supported:
                        continue
                    key = self._template_path_key(path)
                    entry = entries.setdefault(
                        key,
                        {"path": path, "tasks": set(), "usages": []},
                    )
                    entry["tasks"].add(task_name)

        for entry in entries.values():
            entry["references"] = len(entry["usages"])
        return sorted(
            entries.values(),
            key=lambda item: (
                not Path(item["path"]).is_file(),
                Path(item["path"]).name.casefold(),
                self._template_path_key(Path(item["path"])),
            ),
        )

    def _refresh_template_library(self) -> None:
        if not hasattr(self, "template_list"):
            return
        selected_path = None
        selected = self.template_list.currentItem()
        if selected is not None and isinstance(selected.data(Qt.UserRole), dict):
            selected_path = self._template_path_key(Path(str(selected.data(Qt.UserRole).get("path", ""))))
        self.template_list.blockSignals(True)
        self.template_list.clear()
        restore_row = -1
        for row, entry in enumerate(self._template_reference_entries()):
            path = Path(entry["path"])
            item_tooltip = str(path)
            if path.is_file():
                pixmap = self._load_template_pixmap(path)
                if pixmap.isNull():
                    icon = QApplication.style().standardIcon(QStyle.SP_FileIcon)
                    item_tooltip = f"文件存在但无法解码：{path}"
                else:
                    icon = QIcon(pixmap.scaled(150, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                icon = QApplication.style().standardIcon(QStyle.SP_MessageBoxWarning)
                item_tooltip = f"文件不存在：{path}"
            # Keep the collection scannable.  Usage statistics belong in the
            # detail pane, where the user can also inspect each source node.
            display_name = path.name or "未命名图片"
            item = QListWidgetItem(icon, display_name)
            item.setSizeHint(QSize(184, 134))
            item.setToolTip(item_tooltip)
            item.setData(Qt.UserRole, {
                "path": str(path),
                "tasks": sorted(str(name) for name in entry["tasks"]),
                "references": int(entry.get("references", 0)),
                "usages": copy.deepcopy(entry.get("usages", [])),
            })
            self.template_list.addItem(item)
            if selected_path == self._template_path_key(path):
                restore_row = row
        self.template_list.blockSignals(False)
        if self.template_list.count():
            self.template_list.setCurrentRow(restore_row if restore_row >= 0 else 0)
        else:
            self._on_template_selected(None, None)
        self._update_workspace_context()

    def _refresh_template_library_if_ready(self) -> None:
        """Keep the asset browser in sync while editing a flow."""
        if hasattr(self, "template_list"):
            self._refresh_template_library()

    def _on_template_selected(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        data = current.data(Qt.UserRole) if current is not None else None
        if not isinstance(data, dict):
            self.template_title_label.setText("暂无模板")
            self.template_task_label.setText("在流程节点中截取或选择模板后会显示在这里")
            self.template_preview_label.setPixmap(QPixmap())
            self.template_preview_label.setText("暂无预览")
            self.template_path_label.setText("—")
            self.template_usage_label.setText("引用次数 0")
            self.template_reference_list.clear()
            self.template_reference_title.setVisible(False)
            self.template_reference_list.setVisible(False)
            self.template_locate_button.setEnabled(False)
            self.template_delete_button.setEnabled(False)
            return
        path = Path(str(data.get("path", "")))
        self.template_title_label.setText(path.name or "未命名模板")
        tasks = data.get("tasks", [])
        self.template_task_label.setText(
            f"所属任务：{'、'.join(tasks) if tasks else '未归属任务'}"
        )
        self.template_path_label.setText(str(path))
        usages = data.get("usages", [])
        if not isinstance(usages, list):
            usages = []
        reference_count = len(usages)
        self.template_usage_label.setText(f"引用次数 {reference_count}")
        self.template_reference_title.setVisible(reference_count > 0)
        self.template_reference_list.setVisible(reference_count > 0)
        self.template_reference_list.clear()
        for usage in usages:
            if not isinstance(usage, dict):
                continue
            task_name = str(usage.get("task_name", "未命名任务"))
            node_label = str(usage.get("node_label", "流程节点"))
            source = "判断" if usage.get("node_type") == "condition" else "操作"
            condition_index = usage.get("condition_index")
            suffix = f" · 条件 {int(condition_index) + 1}" if isinstance(condition_index, int) else ""
            reference_item = QListWidgetItem(f"{task_name} · {source} · {node_label}{suffix}")
            reference_item.setData(Qt.UserRole, usage)
            reference_item.setToolTip(str(usage.get("raw_path", "")))
            self.template_reference_list.addItem(reference_item)
        if reference_count:
            row_height = max(28, self.template_reference_list.sizeHintForRow(0))
            visible_rows = min(reference_count, 5)
            self.template_reference_list.setFixedHeight(row_height * visible_rows + 8)
        self.template_locate_button.setEnabled(reference_count > 0)
        # Keep the delete action available for referenced files so the user
        # gets an explicit safety explanation instead of a mysterious disabled
        # control.  _delete_selected_template blocks the destructive case.
        self.template_delete_button.setEnabled(path.is_file())
        self.template_delete_button.setToolTip(
            "该图片仍被节点引用，点击查看引用并阻止删除"
            if reference_count
            else "删除未被流程节点引用的图片素材"
        )
        pixmap = self._load_template_pixmap(path) if path.is_file() else QPixmap()
        if pixmap.isNull():
            self.template_preview_label.setPixmap(QPixmap())
            self.template_preview_label.setText(
                "文件不存在" if not path.is_file() else "文件存在但无法读取"
            )
        else:
            self.template_preview_label.setText("")
            self.template_preview_label.setPixmap(
                pixmap.scaled(290, 190, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def _locate_template_reference_item(self, item: QListWidgetItem) -> None:
        usage = item.data(Qt.UserRole) if item is not None else None
        if isinstance(usage, dict):
            self._locate_template_usage(usage)

    def _locate_selected_template(self) -> None:
        item = self.template_list.currentItem() if hasattr(self, "template_list") else None
        data = item.data(Qt.UserRole) if item is not None else None
        usages = data.get("usages", []) if isinstance(data, dict) else []
        if isinstance(usages, list) and usages and isinstance(usages[0], dict):
            self._locate_template_usage(usages[0])

    def _locate_template_usage(self, usage: dict[str, Any]) -> None:
        try:
            task_index = int(usage.get("task_index", -1))
        except (TypeError, ValueError):
            task_index = -1
        if not 0 <= task_index < len(self.window_tasks):
            QMessageBox.information(self, "无法定位", "引用的窗口任务已经不存在。")
            return
        self.task_list.setCurrentRow(task_index)
        self._bind_task_steps(task_index)
        self.main_tabs.setCurrentWidget(self.editor_page)
        node_id = str(usage.get("node_id", "")).strip()
        step_index = usage.get("step_index")

        def select_node() -> None:
            item = self.flow_canvas.node_items.get(node_id) if node_id else None
            if item is None and isinstance(step_index, int):
                action_items = [
                    candidate for candidate in self.flow_canvas.node_items.values()
                    if candidate.node.get("type") == "action"
                ]
                item = action_items[step_index] if 0 <= step_index < len(action_items) else None
            if item is None:
                QMessageBox.information(self, "无法定位", "流程中已经找不到该引用节点。")
                return
            self.flow_canvas.scene.clearSelection()
            item.setSelected(True)
            self.flow_canvas.centerOn(item)
            self._on_flow_node_selected(item)
            self._expand_inspector()

        QTimer.singleShot(0, select_node)

    def _delete_selected_template(self) -> None:
        item = self.template_list.currentItem() if hasattr(self, "template_list") else None
        data = item.data(Qt.UserRole) if item is not None else None
        if not isinstance(data, dict):
            return
        path = Path(str(data.get("path", "")))
        usages = data.get("usages", [])
        if isinstance(usages, list) and usages:
            preview = []
            for usage in usages[:6]:
                if isinstance(usage, dict):
                    preview.append(
                        f"{usage.get('task_name', '任务')} / {usage.get('node_label', '流程节点')}"
                    )
            more = "" if len(usages) <= 6 else f" 等 {len(usages)} 个节点"
            self._append_log(f"模板删除已阻止 | {path} | 仍被 {len(usages)} 个节点引用")
            QMessageBox.warning(
                self,
                "图片仍在使用",
                "该图片仍被流程节点引用，已阻止删除以避免破坏任务。\n"
                + "\n".join(preview)
                + more
                + "\n\n请先点击“定位到流程”移除引用，再删除素材。",
            )
            return
        if not path.is_file():
            QMessageBox.information(self, "素材不存在", f"找不到图片文件：\n{path}")
            self._refresh_template_library()
            return
        answer = QMessageBox.question(
            self,
            "删除图片",
            f"确定删除模板图片吗？\n\n{path}\n\n该图片当前没有被流程节点引用。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            path.unlink()
        except OSError as exc:
            QMessageBox.critical(self, "删除图片失败", str(exc))
            return
        self._append_log(f"已删除模板素材: {path}")
        self.statusBar().showMessage(f"已删除模板：{path.name}", 3500)
        self._refresh_template_library()

    def _open_template_directory(self) -> None:
        item = self.template_list.currentItem() if hasattr(self, "template_list") else None
        data = item.data(Qt.UserRole) if item is not None else None
        path = Path(str(data.get("path", ""))).parent if isinstance(data, dict) else self._base_dir()
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            QMessageBox.warning(self, "无法打开目录", str(exc))

    @staticmethod
    def _make_field_row(widget: QWidget) -> QWidget:
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)
        return row

    def _new_script(self) -> None:
        if not self._confirm_discard():
            return
        self._stop_all_window_tasks()
        self._wait_for_window_tasks()
        self._clear_autosave()
        self.current_file = None
        self.window_tasks = [default_window_task(1)]
        self.window_task_status.clear()
        self._refresh_window_task_list(0)
        self._refresh_template_library_if_ready()
        self._clear_log_preview()
        self._set_dirty(False)
        self._write_autosave()

    def _draft_payload(self) -> dict[str, Any]:
        if self._active_task() is not None and hasattr(self, "flow_canvas"):
            task = self._active_task()
            task["flow"] = copy.deepcopy(self.flow_canvas.flow)
            task["steps"] = [
                node.get("step")
                for node in task["flow"].get("nodes", [])
                if isinstance(node, dict)
                and node.get("type") == "action"
                and isinstance(node.get("step"), dict)
            ]
        return {
            "version": SCRIPT_VERSION,
            "name": self.current_file.stem if self.current_file else "自动草稿",
            "current_file": str(self.current_file) if self.current_file else "",
            "window_tasks": self.window_tasks,
        }

    def _schedule_autosave(self) -> None:
        if hasattr(self, "_autosave_timer"):
            self._autosave_timer.start()

    def _write_autosave(self) -> None:
        try:
            payload = self._draft_payload()
            draft = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            updated = time.strftime("%Y-%m-%d %H:%M:%S")
            self._draft_settings.setValue("draft", draft)
            self._draft_settings.setValue("draft_updated", updated)
            self._draft_settings.sync()
            if not self.is_dirty:
                self._last_accepted_draft = (draft, updated)
        except (OSError, TypeError, ValueError) as exc:
            self._append_log(f"自动保存草稿失败 | {exc}")

    def _clear_autosave(self) -> None:
        if hasattr(self, "_autosave_timer"):
            self._autosave_timer.stop()
        self._draft_settings.remove("draft")
        self._draft_settings.remove("draft_updated")
        self._draft_settings.sync()
        self._last_accepted_draft = ("", "")

    def _restore_accepted_autosave(self) -> None:
        draft, updated = self._last_accepted_draft
        if draft:
            self._draft_settings.setValue("draft", draft)
            self._draft_settings.setValue("draft_updated", updated)
            self._draft_settings.sync()
        else:
            self._clear_autosave()

    def _restore_autosave(self) -> bool:
        raw = self._draft_settings.value("draft", "")
        if not raw:
            return False
        try:
            data = json.loads(str(raw))
            raw_tasks = data.get("window_tasks", [])
            if not isinstance(raw_tasks, list) or not raw_tasks:
                return False
            normalized_tasks = [
                self._normalize_window_task(item, index + 1)
                for index, item in enumerate(raw_tasks)
            ]
            self.window_tasks = normalized_tasks
            current_file = str(data.get("current_file", "")).strip()
            self.current_file = self._resolve_script_file(current_file) if current_file else None
            self.window_task_status.clear()
            self._refresh_window_task_list(0)
            self._refresh_template_library_if_ready()
            self._clear_log_preview()
            self._set_dirty(False)
            updated = str(self._draft_settings.value("draft_updated", ""))
            self._last_accepted_draft = (str(raw), updated)
            suffix = f"（{updated}）" if updated else ""
            self._append_log(f"已恢复本地自动保存草稿{suffix}")
            return True
        except (TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
            self._draft_settings.remove("draft")
            self._draft_settings.sync()
            self._append_log(f"本地草稿无法恢复，已创建空白任务 | {exc}")
            return False

    def _bind_task_steps(self, row: int, selected_step: int = -1) -> None:
        """Bind the step editor directly to one task-owned step list."""
        if 0 <= row < len(self.window_tasks):
            self.active_task_index = row
            task = self.window_tasks[row]
            steps = task.setdefault("steps", [])
            if not isinstance(steps, list):
                steps = []
                task["steps"] = steps
            flow = task.get("flow")
            if not isinstance(flow, dict) or not flow.get("nodes"):
                flow = flow_from_steps(steps)
                task["flow"] = flow
            self.flow_canvas.set_flow(flow)
            task["flow"] = self.flow_canvas.flow
            flow = task["flow"]
            action_steps = [
                node.get("step") for node in flow.get("nodes", [])
                if isinstance(node, dict) and node.get("type") == "action" and isinstance(node.get("step"), dict)
            ]
            if action_steps:
                task["steps"] = action_steps
                self.steps = action_steps
            else:
                task["steps"] = []
                self.steps = task["steps"]
        else:
            self.active_task_index = -1
            self.steps = []
            self.flow_canvas.set_flow({"nodes": [], "edges": []})
        self._refresh_editor_task_box()
        self._refresh_list(selected_step)
        self._update_editor_run_buttons()
        self._update_workspace_context()

    def _active_task(self) -> dict[str, Any] | None:
        if 0 <= self.active_task_index < len(self.window_tasks):
            return self.window_tasks[self.active_task_index]
        return None

    def _flow_changed(self) -> None:
        task = self._active_task()
        if task is None or not hasattr(self, "flow_canvas"):
            return
        task["flow"] = self.flow_canvas.flow
        action_steps = [
            node.get("step") for node in self.flow_canvas.flow.get("nodes", [])
            if isinstance(node, dict) and node.get("type") == "action" and isinstance(node.get("step"), dict)
        ]
        task["steps"] = action_steps
        self.steps = action_steps
        if hasattr(self, "step_list") and self.step_list.count() != len(action_steps):
            self._refresh_list(-1)
        if hasattr(self, "task_list") and self.task_list.currentRow() == self.active_task_index:
            self._refresh_task_steps_preview()
        self._set_dirty(True)
        self._refresh_template_library_if_ready()

    def _on_flow_node_selected(self, node: dict[str, Any] | FlowNodeItem | None) -> None:
        if isinstance(node, FlowNodeItem):
            node = node.node
        if not isinstance(node, dict):
            self._clear_form()
            return
        self._expand_inspector()
        if node.get("type") == "action":
            action_nodes = [
                item for item in self.flow_canvas.flow.get("nodes", [])
                if isinstance(item, dict) and item.get("type") == "action"
            ]
            action_steps = [
                item.get("step") for item in action_nodes
                if isinstance(item.get("step"), dict)
            ]
            task = self._active_task()
            if task is not None:
                task["steps"] = action_steps
            self.steps = action_steps
            if self.step_list.count() != len(action_steps):
                self._refresh_list(-1)
            try:
                row = next(index for index, item in enumerate(action_nodes) if item.get("id") == node.get("id"))
            except StopIteration:
                return
            if self.step_list.currentRow() == row:
                self._on_step_selected(row)
            else:
                self.step_list.setCurrentRow(row)
            return
        if node.get("type") != "condition":
            self._clear_form()
            return
        self._cancel_mouse_capture()
        self._cancel_drag_recording()
        self.step_list.blockSignals(True)
        self.step_list.clearSelection()
        self.step_list.setCurrentRow(-1)
        self.step_list.blockSignals(False)
        self.properties_scroll.setVisible(True)
        if hasattr(self, "editor_empty_state"):
            self.editor_empty_state.setVisible(False)
        self._updating_form = True
        for widget in (
            self.node_name_edit, self.enabled_box, self.type_box, self.x_spin, self.y_spin, self.capture_position_button,
            self.drag_start_x_spin, self.drag_start_y_spin, self.drag_end_x_spin, self.drag_end_y_spin,
            self.drag_duration_spin, self.record_drag_button, self.key_edit, self.text_edit,
            self.macro_name_edit, self.macro_event_table, self.macro_mode_box,
            self.macro_repeat_spin, self.macro_interval_spin, self.window_widget,
            self.seconds_spin, self.ocr_target_edit, self.ocr_widget,
            self.image_edit, self.image_button, self.capture_button,
            self.confidence_spin, self.timeout_spin, self.image_offset_widget, self.path_edit,
        ):
            widget.setEnabled(False)
        self.node_name_edit.setEnabled(True)
        self.condition_widget.setEnabled(True)
        self.node_name_edit.setText(str(node.get("label", "")))
        stored_operator = str(node.get("operator", "and")).lower()
        if stored_operator == "not":
            # Preserve the old meaning of `not` (NOT(all images)) while
            # presenting the clearer base-operator + negate controls.
            stored_operator = "and"
            legacy_negate = True
        else:
            legacy_negate = bool(node.get("negate", False))
        operator_index = max(0, self.condition_operator_box.findData(stored_operator))
        self.condition_operator_box.setCurrentIndex(operator_index)
        self.condition_negate_box.setChecked(legacy_negate)
        conditions = node.get("conditions", [])
        condition_images = [
            str(condition.get("image", ""))
            for condition in conditions
            if isinstance(condition, dict) and str(condition.get("image", "")).strip()
        ]
        self.condition_image_edit.setText("; ".join(condition_images))
        first = conditions[0] if isinstance(conditions, list) and conditions and isinstance(conditions[0], dict) else {}
        try:
            confidence = min(0.99, max(0.1, float(first.get("confidence", 0.85))))
        except (TypeError, ValueError):
            confidence = 0.85
        try:
            timeout = max(0.1, float(first.get("timeout", 1.0)))
        except (TypeError, ValueError):
            timeout = 1.0
        self.condition_confidence_spin.setValue(confidence)
        self.condition_timeout_spin.setValue(timeout)
        self._updating_form = False
        self._set_form_row_visible(self.enabled_box, False)
        self._set_form_row_visible(self.type_box, False)
        self._set_form_row_visible(self.condition_widget, True)
        for field in (
            self.coordinate_widget, self.drag_widget, self.macro_widget, self.key_row,
            self.text_row, self.seconds_row, self.ocr_widget, self.image_row, self.confidence_row,
            self.timeout_row, self.image_offset_widget, self.path_row, self.window_widget,
        ):
            self._set_form_row_visible(field, False)

    def _selected_flow_node(self) -> dict[str, Any] | None:
        selected = self.flow_canvas.scene.selectedItems()
        for item in selected:
            if isinstance(item, FlowNodeItem):
                return item.node
        return None

    def _add_condition_node(self) -> None:
        if not self._ensure_editor_task_binding():
            QMessageBox.information(self, "无法添加", "请先选择一个窗口任务。")
            return
        self.flow_canvas.add_condition_node()
        node = self._selected_flow_node()
        if node is not None and node.get("type") == "condition":
            confidence = float(self._draft_settings.value("ui/default_confidence", 0.85))
            conditions = node.get("conditions", [])
            if isinstance(conditions, list) and conditions and isinstance(conditions[0], dict):
                conditions[0]["confidence"] = confidence
                self.condition_confidence_spin.setValue(confidence)
                self._flow_changed()

    def _choose_condition_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "选择判断图片", str(self._base_dir()), "图片 (*.png *.jpg *.jpeg *.bmp)")
        if filename:
            path = Path(filename)
            try:
                self.condition_image_edit.setText(str(path.relative_to(self._base_dir())))
            except ValueError:
                self.condition_image_edit.setText(str(path))
            self._refresh_template_library_if_ready()

    def _condition_form_changed(self, *_args) -> None:
        if self._updating_form:
            return
        node = self._selected_flow_node()
        if node is None or node.get("type") != "condition":
            return
        node["label"] = self.node_name_edit.text().strip()
        node["operator"] = self.condition_operator_box.currentData() or "and"
        node["negate"] = self.condition_negate_box.isChecked()
        images = [
            item.strip() for item in re.split(r"[;；]", self.condition_image_edit.text())
            if item.strip()
        ]
        node["conditions"] = [
            {
                "type": "image_exists",
                "image": image,
                "confidence": self.condition_confidence_spin.value(),
                "timeout": self.condition_timeout_spin.value(),
            }
            for image in images
        ] or [{
            "type": "image_exists",
            "image": "",
            "confidence": self.condition_confidence_spin.value(),
            "timeout": self.condition_timeout_spin.value(),
        }]
        self.flow_canvas.scene.update()
        self._flow_changed()

    def _refresh_editor_task_box(self) -> None:
        if not hasattr(self, "editor_task_box"):
            return
        self.editor_task_box.blockSignals(True)
        self.editor_task_box.clear()
        for index, task in enumerate(self.window_tasks):
            self.editor_task_box.addItem(str(task.get("name") or f"窗口任务 {index + 1}"), index)
        if 0 <= self.active_task_index < self.editor_task_box.count():
            self.editor_task_box.setCurrentIndex(self.active_task_index)
            self.editor_task_box.setEnabled(True)
        else:
            self.editor_task_box.setCurrentIndex(-1)
            self.editor_task_box.setEnabled(False)
        self.editor_task_box.blockSignals(False)
        self.editor_target_button.setEnabled(self.active_task_index >= 0)
        self.add_action_node_button.setEnabled(self.active_task_index >= 0)
        self.add_condition_button.setEnabled(self.active_task_index >= 0)

    def _editor_task_changed(self, combo_index: int) -> None:
        row = self.editor_task_box.itemData(combo_index) if combo_index >= 0 else -1
        if not isinstance(row, int) or not 0 <= row < len(self.window_tasks):
            return
        if hasattr(self, "task_list") and self.task_list.currentRow() != row:
            self.task_list.setCurrentRow(row)
        else:
            self._bind_task_steps(row)

    def _show_active_task_settings(self) -> None:
        if not 0 <= self.active_task_index < len(self.window_tasks):
            return
        self.task_list.setCurrentRow(self.active_task_index)
        self.main_tabs.setCurrentWidget(self.window_tasks_page)

    def _edit_selected_task_steps(self) -> None:
        row = self.task_list.currentRow()
        if not 0 <= row < len(self.window_tasks):
            return
        selected_step = self.task_steps_preview.currentRow()
        self._bind_task_steps(row, selected_step if selected_step >= 0 else 0)
        self.main_tabs.setCurrentWidget(self.editor_page)
        self.flow_canvas.fit_flow()

    def _ensure_editor_task_binding(self) -> bool:
        """Repair the editor binding if a script reload left a stale list reference."""
        row = self.task_list.currentRow() if hasattr(self, "task_list") else -1
        if not 0 <= row < len(self.window_tasks):
            return False
        task = self.window_tasks[row]
        flow = task.get("flow") if isinstance(task.get("flow"), dict) else None
        if not isinstance(flow, dict) or not flow.get("nodes"):
            flow = flow_from_steps(task.get("steps", []))
            task["flow"] = flow
        if self.active_task_index != row or self.flow_canvas.flow is not task.get("flow"):
            self._bind_task_steps(row)
        return self.active_task_index == row

    def _refresh_list(self, selected: int = -1) -> None:
        self.step_list.blockSignals(True)
        self.step_list.clear()
        for index, step in enumerate(self.steps):
            enabled = "" if step.get("enabled", True) else "[停用] "
            custom_label = str(step.get("label", "")).strip()
            title = custom_label or TYPE_LABELS.get(step.get("type", ""), step.get("type", "未知"))
            if step.get("type") == "macro" and not custom_label:
                title = f"{title}: {step.get('name', '未命名动作')}"
            item = QListWidgetItem(f"{index + 1:02d}  {enabled}{title}")
            self.step_list.addItem(item)
        self.step_list.blockSignals(False)
        if self.steps:
            if selected < 0:
                self.step_list.setCurrentRow(-1)
                self._clear_form()
            else:
                self.step_list.setCurrentRow(max(0, min(selected, len(self.steps) - 1)))
        else:
            self._clear_form()
        self._update_editor_run_buttons()

    def _refresh_bound_task_preview(self) -> None:
        if (
            hasattr(self, "task_list")
            and self.task_list.currentRow() == self.active_task_index
            and 0 <= self.active_task_index < len(self.window_tasks)
        ):
            self._refresh_task_steps_preview()
        self._update_editor_run_buttons()

    @staticmethod
    def _window_task_step_label(step: dict[str, Any]) -> str:
        step_type = str(step.get("type", "未知"))
        label = TYPE_LABELS.get(step_type, step_type)
        custom_label = str(step.get("label", "")).strip()
        if custom_label:
            return custom_label
        if step_type in {"click", "double_click", "move"}:
            return f"{label} ({int(step.get('x', 0))}, {int(step.get('y', 0))})"
        if step_type == "drag":
            return (
                f"{label} ({int(step.get('start_x', 0))}, {int(step.get('start_y', 0))})"
                f" -> ({int(step.get('end_x', 0))}, {int(step.get('end_y', 0))})"
            )
        if step_type == "press":
            return f"{label}: {step.get('key', 'ENTER')}"
        if step_type == "type":
            value = str(step.get("text", "")).replace("\n", " ")
            return f"{label}: {value[:40]}"
        if step_type == "wait":
            return f"{label}: {float(step.get('seconds', 1)):.2f} 秒"
        if step_type in {"wait_image", "click_image", "window_wait_image", "window_click_image"}:
            return f"{label}: {step.get('image', '') or '未设置图片'}"
        if step_type in {"ocr", "window_ocr"}:
            return f"{label}: {step.get('target_text', '') or '任意文字'}"
        if step_type == "macro":
            return f"{label}: {step.get('name', '未命名动作')}"
        if step_type == "screenshot":
            return f"{label}: {step.get('path', 'screenshot.png')}"
        return label

    def _refresh_window_task_list(self, selected: int = -1) -> None:
        if not hasattr(self, "task_list"):
            return
        if hasattr(self, "task_count_label"):
            self.task_count_label.setText(f"{len(self.window_tasks)} 个任务")
        self.task_list.blockSignals(True)
        self.task_list.clear()
        for index, task in enumerate(self.window_tasks):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 58))
            self.task_list.addItem(item)
            self._update_window_task_item(index)
        self.task_list.blockSignals(False)
        if self.window_tasks:
            if selected < 0:
                self.task_list.setCurrentRow(-1)
                self._clear_window_task_form()
            else:
                self.task_list.setCurrentRow(max(0, min(selected, len(self.window_tasks) - 1)))
        else:
            self._clear_window_task_form()
        self._update_window_task_status_label()
        self._update_window_task_buttons()
        self._update_workspace_context()

    def _update_window_task_item(self, row: int) -> None:
        if not 0 <= row < len(self.window_tasks):
            return
        item = self.task_list.item(row)
        if item is None:
            return
        task = self.window_tasks[row]
        task_key = id(task)
        status = self.window_task_status.get(task_key, "未运行")
        target = task.get("title_contains") or task.get("process_name") or "未选择窗口"
        name = task.get("name", f"窗口任务 {row + 1}")
        item.setText(f"{row + 1:02d}  {name}\n{status}  ·  {target}")
        item.setData(Qt.UserRole, task_key)
        item.setToolTip(f"{status} | {target}")

    def _update_window_task_status_label(self) -> None:
        if not hasattr(self, "task_status_label"):
            return
        row = self.task_list.currentRow()
        if 0 <= row < len(self.window_tasks):
            task_key = id(self.window_tasks[row])
            self._set_task_status_label(self.window_task_status.get(task_key, "未运行"))
        else:
            self._set_task_status_label("未运行")

    def _set_task_status_label(self, status: str) -> None:
        status = str(status)
        if any(keyword in status for keyword in ("失败", "错误", "缺少", "未就绪", "无法")):
            state = "error"
        elif status in {"已完成", "已停止"}:
            state = "success"
        elif any(keyword in status for keyword in ("运行中", "正在", "启动")):
            state = "running"
        else:
            state = "idle"
        self.task_status_label.setText(status)
        self.task_status_label.setToolTip("")
        if self.task_status_label.property("state") != state:
            self.task_status_label.setProperty("state", state)
            self.task_status_label.style().unpolish(self.task_status_label)
            self.task_status_label.style().polish(self.task_status_label)

    def _clear_window_task_form(self) -> None:
        if not hasattr(self, "task_name_edit"):
            return
        self._updating_task_form = True
        for widget in (
            self.task_name_edit,
            self.task_window_choice_box,
            self.task_window_refresh_button,
            self.task_title_edit,
            self.task_process_edit,
            self.task_timeout_spin,
            self.task_background_check,
            self.task_activate_check,
            self.task_run_mode_box,
            self.task_repeat_spin,
            self.task_interval_spin,
            self.task_edit_steps_button,
            self.task_clear_steps_button,
        ):
            widget.setEnabled(False)
        self.task_window_choice_box.clear()
        self.task_steps_preview.clear()
        self.task_steps_preview.setFixedHeight(76)
        self._set_task_status_label("未运行")
        self._updating_task_form = False
        if not self.window_tasks:
            self._bind_task_steps(-1)

    def _on_window_task_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.window_tasks):
            self._clear_window_task_form()
            return
        task = self.window_tasks[row]
        self._updating_task_form = True
        for widget in (
            self.task_name_edit,
            self.task_window_choice_box,
            self.task_window_refresh_button,
            self.task_title_edit,
            self.task_process_edit,
            self.task_timeout_spin,
            self.task_background_check,
            self.task_activate_check,
            self.task_run_mode_box,
            self.task_repeat_spin,
            self.task_interval_spin,
            self.task_edit_steps_button,
            self.task_clear_steps_button,
        ):
            widget.setEnabled(True)
        self.task_name_edit.setText(str(task.get("name", f"窗口任务 {row + 1}")))
        self.task_title_edit.setText(str(task.get("title_contains", "")))
        self.task_process_edit.setText(str(task.get("process_name", "")))
        self.task_timeout_spin.setValue(max(0.1, float(task.get("window_timeout", 10.0))))
        self.task_background_check.setChecked(True)
        self.task_activate_check.setChecked(False)
        run_mode = str(task.get("run_mode", "once"))
        run_mode_index = self.task_run_mode_box.findData(run_mode)
        self.task_run_mode_box.setCurrentIndex(max(0, run_mode_index))
        self.task_repeat_spin.setValue(max(1, int(task.get("repeat", 2))))
        self.task_interval_spin.setValue(max(0.0, float(task.get("interval", 0.5))))
        self._refresh_task_window_choices()
        self._refresh_task_steps_preview()
        if self.active_task_index != row or self.steps is not task.get("steps"):
            self._bind_task_steps(row)
        else:
            self._refresh_editor_task_box()
        self._set_task_status_label(self.window_task_status.get(id(task), "未运行"))
        self._updating_task_form = False
        self._update_task_mode_controls()
        self._update_window_task_buttons()

    def _window_task_form_changed(self, *_args) -> None:
        if self._updating_task_form:
            return
        row = self.task_list.currentRow()
        if row < 0 or row >= len(self.window_tasks):
            return
        task = self.window_tasks[row]
        task.update({
            "name": self.task_name_edit.text().strip() or f"窗口任务 {row + 1}",
            "title_contains": self.task_title_edit.text(),
            "process_name": self.task_process_edit.text(),
            "window_timeout": self.task_timeout_spin.value(),
            "background_input": True,
            "activate_window": False,
            "run_mode": self.task_run_mode_box.currentData() or "once",
            "repeat": self.task_repeat_spin.value(),
            "interval": self.task_interval_spin.value(),
        })
        self._refresh_editor_task_box()
        self._update_window_task_item(row)
        self._update_window_task_buttons()
        self._set_dirty(True)
        self._refresh_template_library_if_ready()

    def _update_task_mode_controls(self, *_args) -> None:
        if hasattr(self, "task_activate_check") and hasattr(self, "task_background_check"):
            self.task_activate_check.setEnabled(not self.task_background_check.isChecked())
        if hasattr(self, "task_run_mode_box"):
            mode = self.task_run_mode_box.currentData() or "once"
            repeat_visible = mode == "repeat"
            interval_visible = mode in {"repeat", "loop"}
            self.task_repeat_label.setVisible(repeat_visible)
            self.task_repeat_spin.setVisible(repeat_visible)
            self.task_interval_label.setVisible(interval_visible)
            self.task_interval_spin.setVisible(interval_visible)

    def _refresh_task_window_choices(self) -> None:
        if not hasattr(self, "task_window_choice_box"):
            return
        title_contains = self.task_title_edit.text() if hasattr(self, "task_title_edit") else ""
        process_name = self.task_process_edit.text() if hasattr(self, "task_process_edit") else ""
        try:
            windows = ScriptWorker._enumerate_windows()
        except (AutomationError, OSError) as exc:
            self.task_window_choice_box.blockSignals(True)
            self.task_window_choice_box.clear()
            self.task_window_choice_box.addItem("无法枚举窗口", None)
            self.task_window_choice_box.blockSignals(False)
            self._set_task_status_label(str(exc))
            return
        combo = self.task_window_choice_box
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("选择当前已打开的窗口…", None)
        matching_index = 0
        for window in windows:
            process = window.get("process_name") or "未知进程"
            state = "  [已最小化]" if window.get("minimized") else ""
            width = window.get("normal_width") if window.get("minimized") else window.get("width")
            height = window.get("normal_height") if window.get("minimized") else window.get("height")
            combo.addItem(f"{window['title']}  [{process}]  {width}×{height}{state}", window)
            if matching_index == 0 and ScriptWorker._window_matches(window, title_contains, process_name):
                matching_index = combo.count() - 1
        if matching_index:
            combo.setCurrentIndex(matching_index)
        combo.blockSignals(False)

    def _task_window_choice_changed(self, index: int) -> None:
        if self._updating_task_form or index <= 0:
            return
        window = self.task_window_choice_box.itemData(index)
        if not isinstance(window, dict):
            return
        self._updating_task_form = True
        self.task_title_edit.setText(str(window.get("title", "")))
        self.task_process_edit.setText(str(window.get("process_name", "")))
        self._set_task_status_label("窗口已选择")
        self.task_status_label.setToolTip(
            f"{window['title']} | 外框 {window['width']}×{window['height']} "
            f"@ ({window['x']}, {window['y']})"
        )
        self._updating_task_form = False
        self._window_task_form_changed()

    def _refresh_task_steps_preview(self) -> None:
        row = self.task_list.currentRow()
        self.task_steps_preview.clear()
        if row < 0 or row >= len(self.window_tasks):
            return
        task = self.window_tasks[row]
        flow = task.get("flow") if isinstance(task.get("flow"), dict) else flow_from_steps(task.get("steps", []))
        display_index = 0
        for node in flow.get("nodes", []):
            if not isinstance(node, dict) or node.get("type") in {"start", "end"}:
                continue
            display_index += 1
            if node.get("type") == "condition":
                operator = str(node.get("operator", "and")).upper()
                if node.get("negate", False):
                    operator = f"非{operator}"
                conditions = node.get("conditions", [])
                images = [
                    str(condition.get("image", ""))
                    for condition in conditions
                    if isinstance(condition, dict) and str(condition.get("image", "")).strip()
                ] if isinstance(conditions, list) else []
                image_text = "; ".join(images) or "未设置图片"
                label = str(node.get("label", "")).strip() or f"判断 {operator} ({len(images)} 张): {image_text}"
            else:
                step = node.get("step", {})
                enabled = "" if step.get("enabled", True) else "[停用] "
                label = enabled + self._window_task_step_label(step)
            self.task_steps_preview.addItem(f"{display_index:02d}  {label}")
        count = self.task_steps_preview.count()
        if count:
            row_height = max(30, self.task_steps_preview.sizeHintForRow(0))
            preview_height = min(230, max(76, row_height * count + 8))
        else:
            preview_height = 76
        self.task_steps_preview.setFixedHeight(preview_height)

    def _add_window_task(self) -> None:
        task = default_window_task(len(self.window_tasks) + 1)
        self.window_tasks.append(task)
        self._refresh_window_task_list(len(self.window_tasks) - 1)
        self._set_dirty(True)
        self._refresh_template_library_if_ready()

    def _delete_window_task(self) -> None:
        row = self.task_list.currentRow()
        if row < 0 or row >= len(self.window_tasks):
            return
        task_key = id(self.window_tasks[row])
        if task_key in self.window_task_runs:
            QMessageBox.information(self, "任务正在运行", "请先停止该任务，再删除它")
            return
        del self.window_tasks[row]
        self.window_task_status.pop(task_key, None)
        next_row = min(row, len(self.window_tasks) - 1) if self.window_tasks else -1
        self._refresh_window_task_list(next_row)
        self._set_dirty(True)
        self._refresh_template_library_if_ready()

    def _clear_window_task_steps(self) -> None:
        row = self.task_list.currentRow()
        if row < 0 or row >= len(self.window_tasks):
            return
        self.window_tasks[row]["steps"] = []
        self.window_tasks[row]["flow"] = flow_from_steps([])
        self._bind_task_steps(row)
        self._refresh_task_steps_preview()
        self._set_dirty(True)
        self._refresh_template_library_if_ready()

    def _update_window_task_buttons(self) -> None:
        if not hasattr(self, "task_list"):
            return
        row = self.task_list.currentRow()
        selected_key = id(self.window_tasks[row]) if 0 <= row < len(self.window_tasks) else None
        selected_running = selected_key in self.window_task_runs if selected_key is not None else False
        any_running = bool(self.window_task_runs)
        self.task_run_button.setEnabled(selected_key is not None and not selected_running)
        self.task_stop_button.setEnabled(selected_running)
        self.task_run_all_button.setEnabled(bool(self.window_tasks) and not all(id(task) in self.window_task_runs for task in self.window_tasks))
        self.task_stop_all_button.setEnabled(any_running)
        self.task_delete_button.setEnabled(selected_key is not None and not selected_running)
        self._update_editor_run_buttons()

    def _update_editor_run_buttons(self) -> None:
        if not hasattr(self, "run_button"):
            return
        if not 0 <= self.active_task_index < len(self.window_tasks):
            self.run_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            return
        task_key = id(self.window_tasks[self.active_task_index])
        running = task_key in self.window_task_runs
        recording = self.macro_mouse_listener is not None or self.macro_keyboard_listener is not None
        self.run_button.setEnabled(bool(self.steps) and not running and not recording)
        self.stop_button.setEnabled(running)

    def _task_script_steps(self, task: dict[str, Any]) -> list[dict[str, Any]]:
        target_step = default_step("find_window")
        target_step.update({
            "title_contains": task.get("title_contains", ""),
            "process_name": task.get("process_name", ""),
            "window_timeout": task.get("window_timeout", 10.0),
            "background_input": True,
            "activate_window": False,
        })
        return [target_step] + [copy.deepcopy(step) for step in task.get("steps", [])]

    def _run_selected_window_task(self) -> None:
        row = self.task_list.currentRow()
        if 0 <= row < len(self.window_tasks):
            self._start_window_task(row)

    def _run_all_window_tasks(self) -> None:
        if self.window_tasks:
            self._clear_log_preview()
        for row in range(len(self.window_tasks)):
            # The batch run has one shared log preview; individual task starts
            # must not clear entries written by earlier tasks in the batch.
            self._start_window_task(row, clear_log=False)

    def _start_window_task(self, row: int, *, clear_log: bool = True) -> None:
        if row < 0 or row >= len(self.window_tasks):
            return
        task = self.window_tasks[row]
        selected_row = self.task_list.currentRow()
        task_key = id(task)
        task_name = str(task.get("name", f"窗口任务 {row + 1}"))
        if task_key in self.window_task_runs:
            message = f"[{task_name}] 任务已经在运行，请先点击停止"
            self._append_log(message)
            self.statusBar().showMessage("当前任务已经在运行", 3000)
            self._update_window_task_status_label()
            return
        if clear_log:
            self._clear_log_preview()
        self._append_log(f"[{task_name}] 收到运行请求")
        flow = task.get("flow") if isinstance(task.get("flow"), dict) else flow_from_steps(task.get("steps", []))
        if not any(isinstance(node, dict) and node.get("type") == "action" for node in flow.get("nodes", [])):
            self._append_log(f"[{task_name}] 无法运行：当前任务还没有操作节点")
            QMessageBox.information(self, "无法运行", "当前任务还没有操作节点。")
            return
        flow_errors = validate_flow(flow)
        if flow_errors:
            message = "流程图尚未连接完整：\n" + "\n".join(f"• {error}" for error in flow_errors[:8])
            self.window_task_status[task_key] = "流程未就绪"
            self._append_log(f"[{task_name}] {message.replace(chr(10), '；')}")
            QMessageBox.information(self, "无法运行", message)
            return
        if not str(task.get("title_contains", "")).strip() and not str(task.get("process_name", "")).strip():
            self.window_task_status[task_key] = "缺少窗口匹配条件"
            self._append_log(f"[{task_name}] 无法运行：未填写标题关键词或进程名")
            self._refresh_window_task_list(selected_row if selected_row >= 0 else row)
            return
        self._append_log(f"[{task_name}] 正在启动任务线程")
        thread = QThread(self)
        target_step = default_step("find_window")
        target_step.update({
            "title_contains": task.get("title_contains", ""),
            "process_name": task.get("process_name", ""),
            "window_timeout": task.get("window_timeout", 10.0),
            "background_input": True,
            "activate_window": False,
        })
        worker = ScriptWorker(
            [],
            self._base_dir(),
            output_dir=self._task_asset_dir(task),
            flow=copy.deepcopy(flow),
            initial_step=target_step,
            run_mode=str(task.get("run_mode", "once")),
            repeat=int(task.get("repeat", 2)),
            interval=float(task.get("interval", 0.5)),
        )
        worker.moveToThread(thread)
        self.window_task_runs[task_key] = {
            "thread": thread,
            "worker": worker,
            "row": row,
            "stop_requested": False,
        }
        self.window_task_status[task_key] = "运行中"
        self._window_worker_meta[id(worker)] = (task_key, task_name)
        worker.log.connect(self._on_window_worker_log, Qt.QueuedConnection)
        worker.completed.connect(self._on_window_worker_completed, Qt.QueuedConnection)
        # QThread.quit is thread-safe. A direct connection lets the worker
        # stop its own event loop immediately instead of waiting for the GUI
        # event queue to deliver a queued quit request.
        worker.completed.connect(thread.quit, Qt.DirectConnection)
        worker.step_started.connect(self._on_window_worker_step_started, Qt.QueuedConnection)
        thread.started.connect(worker.run)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_window_task_thread_finished, Qt.QueuedConnection)
        try:
            thread.start()
        except RuntimeError as exc:
            self.window_task_runs.pop(task_key, None)
            self._window_worker_meta.pop(id(worker), None)
            self.window_task_status[task_key] = f"启动失败: {exc}"
            self._append_log(f"[{task_name}] 任务线程启动失败 | {exc}")
            thread.deleteLater()
            self._refresh_window_task_list(selected_row if selected_row >= 0 else row)
            self._update_window_task_buttons()
            return
        self._append_log(f"[{task_name}] 任务线程已启动，等待执行日志")
        self._refresh_window_task_list(selected_row if selected_row >= 0 else row)
        self._update_window_task_buttons()

    @Slot(str)
    def _on_window_worker_log(self, message: str) -> None:
        worker = self.sender()
        meta = self._window_worker_meta.get(id(worker)) if worker is not None else None
        if meta is None:
            self._append_log(str(message))
            return
        _task_key, task_name = meta
        self._append_log(f"[{task_name}] {message}")

    @Slot(bool, str)
    def _on_window_worker_completed(self, success: bool, message: str) -> None:
        worker = self.sender()
        meta = self._window_worker_meta.get(id(worker)) if worker is not None else None
        if meta is None:
            self._append_log(str(message))
            return
        task_key, task_name = meta
        self._window_task_finished(task_key, task_name, success, message)

    @Slot(int)
    def _on_window_worker_step_started(self, _step: int) -> None:
        worker = self.sender()
        meta = self._window_worker_meta.get(id(worker)) if worker is not None else None
        if meta is not None:
            self._window_task_status_update(meta[0], "运行中")

    @Slot()
    def _on_window_task_thread_finished(self) -> None:
        thread = self.sender()
        for task_key, run in list(self.window_task_runs.items()):
            if run.get("thread") is thread:
                self._window_task_thread_finished(task_key)
                return

    def _window_task_status_update(self, task_key: int, status: str) -> None:
        if task_key in self.window_task_status:
            self.window_task_status[task_key] = status
            self._update_window_task_status_label()
            self._update_editor_run_buttons()

    def _window_task_finished(self, task_key: int, task_name: str, success: bool, message: str) -> None:
        if not any(id(task) == task_key for task in self.window_tasks):
            return
        selected = self.task_list.currentRow()
        stopped = "停止" in str(message) and not success
        self.window_task_status[task_key] = "已停止" if stopped else ("已完成" if success else f"失败: {message}")
        self._append_log(f"[{task_name}] {message}")
        self._update_window_task_status_label()
        self._refresh_window_task_list(selected)

    def _window_task_thread_finished(self, task_key: int) -> None:
        run = self.window_task_runs.pop(task_key, None)
        selected = self.task_list.currentRow()
        # A queued completed signal can be overtaken by QThread.finished when
        # the worker exits during shutdown. Never leave the UI in the transient
        # "正在停止" state in that case.
        if self.window_task_status.get(task_key) == "正在停止" or (run and run.get("stop_requested")):
            self.window_task_status[task_key] = "已停止"
            self._append_log("窗口任务已停止")
        if run is not None:
            self._window_worker_meta.pop(id(run.get("worker")), None)
            run["thread"].deleteLater()
            if selected < 0:
                selected = int(run.get("row", -1))
        self._refresh_window_task_list(selected)
        self._update_window_task_buttons()

    def _stop_selected_window_task(self) -> None:
        row = self.task_list.currentRow()
        if row < 0 or row >= len(self.window_tasks):
            return
        run = self.window_task_runs.get(id(self.window_tasks[row]))
        if run:
            run["worker"].stop()
            run["stop_requested"] = True
            self.window_task_status[id(self.window_tasks[row])] = "正在停止"
            self._update_window_task_status_label()
            self._refresh_window_task_list(row)

    def _stop_all_window_tasks(self) -> None:
        if not hasattr(self, "window_task_runs"):
            return
        for task_key, run in list(self.window_task_runs.items()):
            run["worker"].stop()
            run["stop_requested"] = True
            self.window_task_status[task_key] = "正在停止"
        if hasattr(self, "task_list"):
            self._update_window_task_status_label()
            self._refresh_window_task_list(self.task_list.currentRow())

    def _wait_for_window_tasks(self, timeout_ms: int = 1500) -> None:
        """Request task threads to exit and wait briefly during document/window shutdown."""
        runs = list(self.window_task_runs.items())
        if not runs:
            return
        for _task_key, run in runs:
            run["thread"].quit()
        deadline = time.monotonic() + max(0, timeout_ms) / 1000.0
        for _task_key, run in runs:
            remaining = max(0, int((deadline - time.monotonic()) * 1000))
            if remaining <= 0:
                break
            run["thread"].wait(remaining)
        for task_key, run in runs:
            if not run["thread"].isRunning():
                self.window_task_runs.pop(task_key, None)

    def _clear_form(self) -> None:
        self._cancel_mouse_capture()
        self._cancel_drag_recording()
        if hasattr(self, "step_list"):
            self.step_list.blockSignals(True)
            self.step_list.clearSelection()
            self.step_list.setCurrentRow(-1)
            self.step_list.blockSignals(False)
        self.properties_scroll.setVisible(False)
        if hasattr(self, "editor_empty_state"):
            self.editor_empty_state.setVisible(True)
        if hasattr(self, "editor_inspector_panel"):
            self._collapse_inspector()
        self._updating_form = True
        for widget in (self.node_name_edit, self.enabled_box, self.type_box, self.x_spin, self.y_spin, self.capture_position_button,
                       self.drag_start_x_spin, self.drag_start_y_spin, self.drag_end_x_spin, self.drag_end_y_spin,
                       self.drag_duration_spin, self.record_drag_button, self.key_edit, self.text_edit,
            self.macro_name_edit, self.macro_event_table, self.macro_mode_box,
                       self.macro_repeat_spin, self.macro_interval_spin,
                       self.window_widget,
                       self.seconds_spin, self.ocr_target_edit, self.ocr_widget,
                       self.image_edit, self.image_button, self.capture_button,
                       self.confidence_spin, self.timeout_spin, self.image_offset_widget, self.path_edit, self.condition_widget):
            widget.setEnabled(False)
        self.macro_event_table.clearContents()
        self.macro_event_table.setRowCount(0)
        self.window_choice_box.clear()
        self._updating_form = False

    def _on_step_selected(self, row: int) -> None:
        self._cancel_mouse_capture()
        self._cancel_drag_recording()
        if row < 0 or row >= len(self.steps):
            self._clear_form()
            return
        self._expand_inspector()
        self.properties_scroll.setVisible(True)
        if hasattr(self, "editor_empty_state"):
            self.editor_empty_state.setVisible(False)
        self._updating_form = True
        for widget in (self.node_name_edit, self.enabled_box, self.type_box, self.x_spin, self.y_spin, self.capture_position_button,
                       self.drag_start_x_spin, self.drag_start_y_spin, self.drag_end_x_spin, self.drag_end_y_spin,
                       self.drag_duration_spin, self.record_drag_button, self.key_edit, self.text_edit,
                       self.macro_name_edit, self.macro_event_table, self.macro_mode_box,
                       self.macro_repeat_spin, self.macro_interval_spin,
                       self.window_widget,
                       self.seconds_spin, self.ocr_target_edit, self.ocr_widget,
                       self.image_edit, self.image_button, self.capture_button,
                       self.confidence_spin, self.timeout_spin, self.image_offset_widget, self.path_edit, self.condition_widget):
            widget.setEnabled(True)
        step = self.steps[row]
        self.node_name_edit.setText(str(step.get("label", "")))
        type_index = max(0, self.type_box.findData(step.get("type", "wait")))
        self.type_box.setCurrentIndex(type_index)
        self.enabled_box.setChecked(step.get("enabled", True))
        self.x_spin.setValue(int(step.get("x", 0)))
        self.y_spin.setValue(int(step.get("y", 0)))
        self.drag_start_x_spin.setValue(int(step.get("start_x", 0)))
        self.drag_start_y_spin.setValue(int(step.get("start_y", 0)))
        self.drag_end_x_spin.setValue(int(step.get("end_x", 0)))
        self.drag_end_y_spin.setValue(int(step.get("end_y", 0)))
        self.drag_duration_spin.setValue(float(step.get("duration", 0.8)))
        self.macro_name_edit.setText(str(step.get("name", "未命名动作")))
        mode_index = max(0, self.macro_mode_box.findData(step.get("mode", "once")))
        self.macro_mode_box.setCurrentIndex(mode_index)
        self.macro_repeat_spin.setValue(int(step.get("repeat", 2)))
        self.macro_interval_spin.setValue(float(step.get("interval", 0.2)))
        events = step.get("events", [])
        self.macro_event_count_label.setText(f"{len(events) if isinstance(events, list) else 0} 个事件")
        self._refresh_macro_event_table(events if isinstance(events, list) else [])
        self.window_title_edit.setText(str(step.get("title_contains", "")))
        self.window_process_edit.setText(str(step.get("process_name", "")))
        self.window_timeout_spin.setValue(float(step.get("window_timeout", 10)))
        self.window_background_check.setChecked(True)
        self.window_activate_check.setChecked(False)
        self.window_result_label.setText("尚未查找")
        self._refresh_window_choices()
        self.key_edit.setText(str(step.get("key", "ENTER")))
        self.text_edit.setPlainText(str(step.get("text", "")))
        self.seconds_spin.setValue(float(step.get("seconds", 1)))
        self.ocr_target_edit.setText(str(step.get("target_text", "")))
        self.image_edit.setText(str(step.get("image", "")))
        self.confidence_spin.setValue(float(step.get("confidence", 0.85)))
        self.timeout_spin.setValue(float(step.get("timeout", 10)))
        self.image_offset_x_spin.setValue(int(step.get("offset_x", 0)))
        self.image_offset_y_spin.setValue(int(step.get("offset_y", 0)))
        self.path_edit.setText(str(step.get("path", "screenshot.png")))
        self._updating_form = False
        self._update_form_visibility()
        self._update_window_mode_controls()

    @staticmethod
    def _macro_event_display(event: dict[str, Any]) -> tuple[str, str]:
        """Return a concise operation label and parameter string for the event table."""
        event_type = str(event.get("type", "未知事件"))
        if event_type == "mouse_move":
            return "移动鼠标", f"({int(event.get('x', 0))}, {int(event.get('y', 0))})"
        if event_type in {"mouse_down", "mouse_up"}:
            action = "按下鼠标" if event_type == "mouse_down" else "释放鼠标"
            button = str(event.get("button", "left")).lower()
            point = f"({int(event.get('x', 0))}, {int(event.get('y', 0))})"
            return action, f"{button} @ {point}"
        if event_type == "mouse_scroll":
            point = f"({int(event.get('x', 0))}, {int(event.get('y', 0))})"
            return "滚动滚轮", f"dx={int(event.get('dx', 0))}, dy={int(event.get('dy', 0))} @ {point}"
        if event_type in {"key_down", "key_up"}:
            action = "按下按键" if event_type == "key_down" else "释放按键"
            kind = event.get("key_kind", "special")
            value = event.get("key", "")
            if kind == "char":
                key = str(value).replace("\n", "\\n").replace("\r", "\\r")
                key = repr(key) if len(key) != 1 else key
            elif kind == "vk":
                key = f"VK {value}"
            else:
                key = str(value).upper()
            return action, key
        return event_type, str({key: value for key, value in event.items() if key != "dt"})

    def _refresh_macro_event_table(self, events: list[dict[str, Any]]) -> None:
        table = self.macro_event_table
        table.setUpdatesEnabled(False)
        try:
            table.clearContents()
            table.setRowCount(len(events))
            for row, event in enumerate(events):
                operation, parameters = self._macro_event_display(event)
                sequence_item = QTableWidgetItem(str(row + 1))
                operation_item = QTableWidgetItem(operation)
                parameters_item = QTableWidgetItem(parameters)
                sequence_item.setTextAlignment(Qt.AlignCenter)
                for column, item in enumerate((sequence_item, operation_item, parameters_item)):
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    table.setItem(row, column, item)

                try:
                    delay = max(0.0, float(event.get("dt", 0.0)))
                except (TypeError, ValueError):
                    delay = 0.0
                delay_spin = QDoubleSpinBox(table)
                delay_spin.setRange(0.0, 86400.0)
                delay_spin.setDecimals(3)
                delay_spin.setSingleStep(0.05)
                delay_spin.setSuffix(" 秒")
                delay_spin.setValue(delay)
                delay_spin.setToolTip("该操作开始前等待的时间，可直接修改")
                delay_spin.valueChanged.connect(
                    lambda value, event_row=row: self._macro_delay_changed(event_row, value)
                )
                table.setCellWidget(row, 3, delay_spin)
            table.setEnabled(bool(events))
        finally:
            table.setUpdatesEnabled(True)

    def _macro_delay_changed(self, row: int, value: float) -> None:
        if self._updating_form:
            return
        current = self.step_list.currentRow()
        if current < 0 or current >= len(self.steps):
            return
        step = self.steps[current]
        if step.get("type") != "macro":
            return
        events = step.get("events", [])
        if not isinstance(events, list) or not 0 <= row < len(events):
            return
        events[row]["dt"] = max(0.0, float(value))
        self._refresh_bound_task_preview()
        self._set_dirty(True)

    def _update_form_visibility(self) -> None:
        step_type = self.type_box.currentData()
        self._set_form_row_visible(self.enabled_box, True)
        self._set_form_row_visible(self.type_box, True)
        self._set_form_row_visible(self.coordinate_widget, step_type in {"click", "double_click", "move"})
        self._set_form_row_visible(self.drag_widget, step_type == "drag")
        self._set_form_row_visible(self.macro_widget, step_type == "macro")
        macro_repeat_visible = step_type == "macro" and self.macro_mode_box.currentData() == "repeat"
        self.macro_repeat_label.setVisible(macro_repeat_visible)
        self.macro_repeat_spin.setVisible(macro_repeat_visible)
        self.macro_interval_label.setVisible(macro_repeat_visible)
        self.macro_interval_spin.setVisible(macro_repeat_visible)
        self._set_form_row_visible(self.key_row, step_type == "press")
        self._set_form_row_visible(self.text_row, step_type == "type")
        self._set_form_row_visible(self.seconds_row, step_type == "wait")
        ocr_visible = step_type in {"ocr", "window_ocr"}
        self._set_form_row_visible(self.ocr_widget, ocr_visible)
        image_visible = step_type in {
            "wait_image",
            "click_image",
            "window_wait_image",
            "window_click_image",
        }
        self._set_form_row_visible(self.image_row, image_visible)
        recognition_visible = image_visible or ocr_visible
        self._set_form_row_visible(self.confidence_row, recognition_visible)
        self._set_form_row_visible(self.timeout_row, recognition_visible)
        self._set_form_row_visible(
            self.image_offset_widget,
            step_type in {"click_image", "window_click_image"},
        )
        self._set_form_row_visible(self.path_row, step_type == "screenshot")
        self._set_form_row_visible(self.window_widget, step_type == "find_window")
        self._set_form_row_visible(self.condition_widget, False)

    def _set_form_row_visible(self, field: QWidget, visible: bool) -> None:
        label = self.form.labelForField(field)
        if label is not None:
            label.setVisible(visible)
        field.setVisible(visible)

    def _update_window_mode_controls(self, *_args) -> None:
        if hasattr(self, "window_activate_check") and hasattr(self, "window_background_check"):
            self.window_activate_check.setEnabled(not self.window_background_check.isChecked())

    def _form_changed(self) -> None:
        if self._updating_form:
            return
        row = self.step_list.currentRow()
        if row < 0 or row >= len(self.steps):
            return
        action_nodes = [
            node for node in self.flow_canvas.flow.get("nodes", [])
            if isinstance(node, dict) and node.get("type") == "action"
        ]
        node = action_nodes[row] if row < len(action_nodes) else None
        if node is None:
            return
        step = node.get("step")
        if not isinstance(step, dict):
            step = self.steps[row]
            node["step"] = step
        # Keep the compatibility list and the flow node on the same object.
        self.steps[row] = step
        old_type = step.get("type")
        new_type = self.type_box.currentData()
        if old_type != new_type:
            custom_label = self.node_name_edit.text().strip()
            replacement = default_step(new_type)
            if new_type in {"wait_image", "click_image", "window_wait_image", "window_click_image"}:
                replacement["confidence"] = float(
                    self._draft_settings.value("ui/default_confidence", 0.85)
                )
            replacement["enabled"] = self.enabled_box.isChecked()
            replacement["label"] = custom_label
            step.clear()
            step.update(replacement)
            self._refresh_list(row)
            self._refresh_bound_task_preview()
            self.flow_canvas.scene.update()
            self._update_form_visibility()
            self._set_dirty(True)
            self._refresh_template_library_if_ready()
            return
        step["label"] = self.node_name_edit.text().strip()
        step["enabled"] = self.enabled_box.isChecked()
        if new_type in {"click", "double_click", "move"}:
            step.update({"x": self.x_spin.value(), "y": self.y_spin.value()})
        elif new_type == "drag":
            step.update({
                "start_x": self.drag_start_x_spin.value(),
                "start_y": self.drag_start_y_spin.value(),
                "end_x": self.drag_end_x_spin.value(),
                "end_y": self.drag_end_y_spin.value(),
                "duration": self.drag_duration_spin.value(),
            })
        elif new_type == "macro":
            step.update({
                "name": self.macro_name_edit.text(),
                "mode": self.macro_mode_box.currentData(),
                "repeat": self.macro_repeat_spin.value(),
                "interval": self.macro_interval_spin.value(),
            })
        elif new_type == "press":
            step["key"] = self.key_edit.text()
        elif new_type == "type":
            step["text"] = self.text_edit.toPlainText()
        elif new_type == "wait":
            step["seconds"] = self.seconds_spin.value()
        elif new_type == "find_window":
            step.update({
                "title_contains": self.window_title_edit.text(),
                "process_name": self.window_process_edit.text(),
                "window_timeout": self.window_timeout_spin.value(),
                "background_input": True,
                "activate_window": False,
            })
        elif new_type in {"ocr", "window_ocr"}:
            step.update({
                "target_text": self.ocr_target_edit.text(),
                "confidence": self.confidence_spin.value(),
                "timeout": self.timeout_spin.value(),
            })
        elif new_type in {"wait_image", "click_image", "window_wait_image", "window_click_image"}:
            step.update({
                "image": self.image_edit.text(),
                "confidence": self.confidence_spin.value(),
                "timeout": self.timeout_spin.value(),
                "offset_x": self.image_offset_x_spin.value(),
                "offset_y": self.image_offset_y_spin.value(),
            })
        elif new_type == "screenshot":
            step["path"] = self.path_edit.text()
        current_item = self.step_list.currentItem()
        if current_item is not None:
            title = str(step.get("label", "")).strip() or TYPE_LABELS.get(step["type"], step["type"])
            if step["type"] == "macro" and not str(step.get("label", "")).strip():
                title = f"{title}: {step.get('name', '未命名动作')}"
            current_item.setText(f"{row + 1:02d}  {' ' if step['enabled'] else '[停用] '}{title}")
        self._update_form_visibility()
        self._refresh_bound_task_preview()
        self.flow_canvas.scene.update()
        self._set_dirty(True)
        self._refresh_template_library_if_ready()

    def _add_step(self) -> None:
        if not self._ensure_editor_task_binding():
            QMessageBox.information(self, "无法添加", "请先选择一个窗口任务。")
            return
        self.flow_canvas.add_action_node(default_step("wait"))
        self._flow_changed()

    def _delete_step(self) -> None:
        self.flow_canvas.delete_selected()
        self._flow_changed()

    def _move_step(self, direction: int) -> None:
        selected = self._selected_flow_node()
        if selected is None or selected.get("type") != "action":
            return
        nodes = [node for node in self.flow_canvas.flow.get("nodes", []) if node.get("type") == "action"]
        try:
            index = next(i for i, node in enumerate(nodes) if node.get("id") == selected.get("id"))
        except StopIteration:
            return
        target = index + direction
        if not 0 <= target < len(nodes):
            return
        nodes[index]["x"], nodes[target]["x"] = nodes[target].get("x", 0), nodes[index].get("x", 0)
        nodes[index]["y"], nodes[target]["y"] = nodes[target].get("y", 0), nodes[index].get("y", 0)
        self.flow_canvas.set_flow(self.flow_canvas.flow)
        self._flow_changed()

    def _auto_layout_flow(self) -> None:
        if self._active_task() is None:
            return
        self.flow_canvas.auto_layout()
        self._append_log("已按流程拓扑自动排列节点")

    def _refresh_window_choices(self) -> None:
        if not hasattr(self, "window_choice_box"):
            return
        title_contains = self.window_title_edit.text() if hasattr(self, "window_title_edit") else ""
        process_name = self.window_process_edit.text() if hasattr(self, "window_process_edit") else ""
        try:
            windows = ScriptWorker._enumerate_windows()
        except (AutomationError, OSError) as exc:
            self.window_choice_box.blockSignals(True)
            self.window_choice_box.clear()
            self.window_choice_box.addItem("无法枚举窗口", None)
            self.window_choice_box.blockSignals(False)
            if hasattr(self, "window_result_label"):
                self.window_result_label.setText(str(exc))
            return

        combo = self.window_choice_box
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("选择当前已打开的窗口…", None)
        matching_index = 0
        for window in windows:
            process = window.get("process_name") or "未知进程"
            state = "  [已最小化]" if window.get("minimized") else ""
            width = window.get("normal_width") if window.get("minimized") else window.get("width")
            height = window.get("normal_height") if window.get("minimized") else window.get("height")
            display = f"{window['title']}  [{process}]  {width}×{height}{state}"
            combo.addItem(display, window)
            if matching_index == 0 and ScriptWorker._window_matches(window, title_contains, process_name):
                matching_index = combo.count() - 1
        if matching_index:
            combo.setCurrentIndex(matching_index)
        combo.blockSignals(False)

    def _window_choice_changed(self, index: int) -> None:
        if self._updating_form or index <= 0:
            return
        window = self.window_choice_box.itemData(index)
        if not isinstance(window, dict):
            return
        self._updating_form = True
        self.window_title_edit.setText(str(window.get("title", "")))
        self.window_process_edit.setText(str(window.get("process_name", "")))
        size_text = (
            f"还原尺寸 {window['normal_width']}×{window['normal_height']}"
            if window.get("minimized")
            else f"外框 {window['width']}×{window['height']}"
        )
        position_text = (
            f"@ ({window['normal_x']}, {window['normal_y']})"
            if window.get("minimized")
            else f"@ ({window['x']}, {window['y']})"
        )
        state_text = " | 当前已最小化" if window.get("minimized") else ""
        self.window_result_label.setText(
            f"{window['title']} | {size_text} {position_text} | 客户区 "
            f"{window['client_width']}×{window['client_height']}{state_text}"
        )
        self._updating_form = False
        self._form_changed()

    def _probe_window(self) -> None:
        if self.type_box.currentData() != "find_window":
            return
        title_contains = self.window_title_edit.text()
        process_name = self.window_process_edit.text()
        if not title_contains.strip() and not process_name.strip():
            QMessageBox.information(self, "需要匹配条件", "请填写标题关键词或进程名")
            return
        try:
            windows = ScriptWorker._enumerate_windows()
        except (AutomationError, OSError) as exc:
            QMessageBox.warning(self, "无法查找窗口", str(exc))
            return
        matches = [
            window for window in windows
            if ScriptWorker._window_matches(window, title_contains, process_name)
        ]
        if not matches:
            self.window_result_label.setText(f"未找到（已扫描 {len(windows)} 个可见窗口）")
            self._append_log(f"未找到窗口: {title_contains.strip() or process_name.strip()}")
            return
        window = matches[0]
        for index in range(1, self.window_choice_box.count()):
            choice = self.window_choice_box.itemData(index)
            if isinstance(choice, dict) and choice.get("hwnd") == window.get("hwnd"):
                self.window_choice_box.blockSignals(True)
                self.window_choice_box.setCurrentIndex(index)
                self.window_choice_box.blockSignals(False)
                break
        suffix = f"，共 {len(matches)} 个匹配" if len(matches) > 1 else ""
        size_text = (
            f"还原尺寸 {window['normal_width']}×{window['normal_height']}"
            if window.get("minimized")
            else f"外框 {window['width']}×{window['height']}"
        )
        position_text = (
            f"@ ({window['normal_x']}, {window['normal_y']})"
            if window.get("minimized")
            else f"@ ({window['x']}, {window['y']})"
        )
        state_text = "，当前已最小化" if window.get("minimized") else ""
        self.window_result_label.setText(
            f"{window['title']} | {size_text} {position_text} | 客户区 "
            f"{window['client_width']}×{window['client_height']}{state_text}{suffix}"
        )
        self._append_log(
            "找到窗口: "
            f"{window['title']} [{window.get('process_name') or '未知进程'}] "
            f"外框=({window['x']}, {window['y']}, {window['width']}x{window['height']}) "
            f"客户区={window['client_width']}x{window['client_height']}"
        )

    def _choose_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "选择模板图片", str(self._base_dir()), "图片 (*.png *.jpg *.jpeg *.bmp)")
        if filename:
            path = Path(filename)
            try:
                self.image_edit.setText(str(path.relative_to(self._base_dir())))
            except ValueError:
                self.image_edit.setText(str(path))
            self._refresh_template_library_if_ready()

    def _capture_mouse_position(self) -> None:
        if self.type_box.currentData() not in {"click", "double_click", "move"}:
            return
        if self.position_listener is not None:
            self._cancel_mouse_capture()
            return
        try:
            from pynput.mouse import Button, Listener
        except ImportError as exc:
            QMessageBox.warning(self, "无法监听鼠标", "缺少 pynput，请先安装 requirements.txt。")
            return

        def on_click(x, y, button, pressed):
            if pressed and button == Button.left:
                self.mouse_position_captured.emit(int(x), int(y))
                return False
            return True

        try:
            self.position_listener = Listener(on_click=on_click)
            self.position_listener.start()
        except Exception as exc:  # noqa: BLE001 - platform permissions vary
            self.position_listener = None
            QMessageBox.warning(self, "无法监听鼠标", str(exc))
            return
        self.capture_position_button.setText("点击目标位置...")
        self.statusBar().showMessage("请在目标位置点击鼠标左键，按 F8 或再次点击按钮可取消")

    def _finish_mouse_capture(self, x: int, y: int) -> None:
        self._cancel_mouse_capture()
        self._updating_form = True
        self.x_spin.setValue(int(x))
        self.y_spin.setValue(int(y))
        self._updating_form = False
        self._form_changed()
        self._append_log(f"已读取鼠标坐标: ({int(x)}, {int(y)})")

    def _cancel_mouse_capture(self) -> None:
        listener = self.position_listener
        self.position_listener = None
        if listener is not None:
            listener.stop()
        self.capture_position_button.setText("读取当前坐标")
        self.statusBar().clearMessage()

    def _record_drag(self) -> None:
        if self.type_box.currentData() != "drag":
            return
        if self.drag_listener is not None:
            self._cancel_drag_recording()
            return
        try:
            from pynput.mouse import Button, Listener
        except ImportError:
            QMessageBox.warning(self, "无法监听鼠标", "缺少 pynput，请先安装 requirements.txt。")
            return

        start_position = None
        start_time = None

        def on_click(x, y, button, pressed):
            nonlocal start_position, start_time
            if button != Button.left:
                return True
            if pressed and start_position is None:
                start_position = (int(x), int(y))
                start_time = time.monotonic()
                return True
            if not pressed and start_position is not None and start_time is not None:
                end_position = (int(x), int(y))
                if abs(end_position[0] - start_position[0]) + abs(end_position[1] - start_position[1]) < 3:
                    start_position = None
                    start_time = None
                    return True
                elapsed = max(0.05, time.monotonic() - start_time)
                self.drag_recorded.emit(
                    start_position[0],
                    start_position[1],
                    end_position[0],
                    end_position[1],
                    elapsed,
                )
                return False
            return True

        try:
            self.drag_listener = Listener(on_click=on_click)
            self.drag_listener.start()
        except Exception as exc:  # noqa: BLE001 - platform permissions vary
            self.drag_listener = None
            QMessageBox.warning(self, "无法监听鼠标", str(exc))
            return
        self.record_drag_button.setText("录制中...请拖拽")
        self.statusBar().showMessage("按住鼠标左键拖动目标，松开后自动记录；再次点击按钮可取消")

    def _finish_drag_recording(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float) -> None:
        self._cancel_drag_recording()
        self._updating_form = True
        self.drag_start_x_spin.setValue(start_x)
        self.drag_start_y_spin.setValue(start_y)
        self.drag_end_x_spin.setValue(end_x)
        self.drag_end_y_spin.setValue(end_y)
        self.drag_duration_spin.setValue(duration)
        self._updating_form = False
        self._form_changed()
        self._append_log(f"已记录拖拽: ({start_x}, {start_y}) -> ({end_x}, {end_y})")

    def _cancel_drag_recording(self) -> None:
        listener = self.drag_listener
        self.drag_listener = None
        if listener is not None:
            listener.stop()
        self.record_drag_button.setText("录制下一次拖拽")
        self.statusBar().clearMessage()

    def _toggle_macro_recording(self) -> None:
        if self.macro_mouse_listener is not None or self.macro_keyboard_listener is not None:
            self._stop_macro_recording()
        else:
            self._start_macro_recording()

    def _start_macro_recording(self) -> None:
        if self.worker_thread is not None or self.window_task_runs:
            self._append_log("任务运行中，不能开始录制")
            return
        self._cancel_mouse_capture()
        self._cancel_drag_recording()
        try:
            from pynput.keyboard import Listener as KeyboardListener
            from pynput.mouse import Listener as MouseListener
        except ImportError:
            QMessageBox.warning(self, "无法录制动作", "缺少 pynput，请先安装 requirements.txt。")
            return

        self.macro_events = []
        self.macro_last_event_time = time.monotonic()
        self.macro_last_move = None
        recording_rect = self.frameGeometry()

        def record_event(event: dict[str, Any]) -> None:
            now = time.monotonic()
            with self.macro_lock:
                previous = self.macro_last_event_time or now
                event["dt"] = max(0.0, now - previous)
                self.macro_last_event_time = now
                self.macro_events.append(event)

        def on_move(x, y):
            nonlocal recording_rect
            point = QPoint(int(x), int(y))
            if recording_rect.contains(point):
                return
            position = (int(x), int(y))
            if self.macro_last_move is not None:
                distance = abs(position[0] - self.macro_last_move[0]) + abs(position[1] - self.macro_last_move[1])
                if distance < 3:
                    return
            self.macro_last_move = position
            record_event({"type": "mouse_move", "x": position[0], "y": position[1]})

        def button_name(button) -> str:
            return str(getattr(button, "name", str(button).split(".")[-1])).lower()

        def on_click(x, y, button, pressed):
            if recording_rect.contains(QPoint(int(x), int(y))):
                return True
            record_event({
                "type": "mouse_down" if pressed else "mouse_up",
                "button": button_name(button),
                "x": int(x),
                "y": int(y),
            })
            return True

        def on_scroll(x, y, dx, dy):
            if recording_rect.contains(QPoint(int(x), int(y))):
                return
            record_event({"type": "mouse_scroll", "x": int(x), "y": int(y), "dx": int(dx), "dy": int(dy)})

        def serialize_key(key):
            return self._serialize_macro_key(key)

        def on_press(key):
            data = serialize_key(key)
            if data is None or data.get("key") == "f9":
                return
            record_event({"type": "key_down", **data})

        def on_release(key):
            data = serialize_key(key)
            if data is None or data.get("key") == "f9":
                return
            record_event({"type": "key_up", **data})

        try:
            self.macro_mouse_listener = MouseListener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
            self.macro_keyboard_listener = KeyboardListener(on_press=on_press, on_release=on_release)
            self.macro_mouse_listener.start()
            self.macro_keyboard_listener.start()
        except Exception as exc:  # noqa: BLE001 - platform permissions vary
            self._cancel_macro_listeners()
            QMessageBox.warning(self, "无法录制动作", str(exc))
            return

        self.record_macro_button.setChecked(True)
        self.record_macro_button.setText("停止录制")
        self.statusBar().showMessage("正在录制鼠标和键盘操作，按 F9 或再次点击按钮停止")
        self.run_button.setEnabled(False)
        self.step_list.setEnabled(False)
        self.add_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.up_button.setEnabled(False)
        self.action_new.setEnabled(False)
        self.action_open.setEnabled(False)
        self.action_save.setEnabled(False)

    def _stop_macro_recording(self) -> None:
        self._cancel_macro_listeners()
        self.record_macro_button.setChecked(False)
        self.record_macro_button.setText("录制动作")
        self.step_list.setEnabled(True)
        self.add_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.up_button.setEnabled(True)
        self.action_new.setEnabled(True)
        self.action_open.setEnabled(True)
        self.action_save.setEnabled(True)
        self._update_editor_run_buttons()
        self.statusBar().clearMessage()
        with self.macro_lock:
            events = [dict(event) for event in self.macro_events]
        if not events:
            self._append_log("未录制到动作")
            return
        self.macro_recorded.emit(events)

    def _cancel_macro_listeners(self) -> None:
        listeners = [self.macro_mouse_listener, self.macro_keyboard_listener]
        self.macro_mouse_listener = None
        self.macro_keyboard_listener = None
        for listener in listeners:
            if listener is not None:
                listener.stop()
        for listener in listeners:
            if listener is not None:
                listener.join(0.5)

    def _finish_macro_recording(self, events: list[dict[str, Any]]) -> None:
        name, accepted = QInputDialog.getText(self, "保存宏动作", "动作名称:", text="未命名动作")
        if not accepted:
            self._append_log("已放弃保存宏动作")
            return
        name = name.strip() or "未命名动作"
        step = default_step("macro")
        step.update({"name": name, "events": events})
        if self._active_task() is None:
            self._append_log("未选择窗口任务，宏动作未保存")
            return
        self.flow_canvas.add_action_node(step)
        self._flow_changed()
        self._set_dirty(True)
        self._append_log(f"已保存宏动作: {name} ({len(events)} 个事件)")

    @staticmethod
    def _serialize_macro_key(key) -> dict[str, Any] | None:
        char = getattr(key, "char", None)
        if char:
            return {"key_kind": "char", "key": char}
        name = getattr(key, "name", None)
        if name:
            return {"key_kind": "special", "key": str(name).lower()}
        vk = getattr(key, "vk", None)
        if vk is not None:
            return {"key_kind": "vk", "key": int(vk)}
        return None

    def _capture_template(self) -> None:
        dialog = TemplateCaptureDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        image = dialog.selected_image()
        if image is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存模板图片",
            str(self._task_asset_dir() / "template.png"),
            "PNG 图片 (*.png)",
        )
        if not filename:
            return
        try:
            import cv2

            destination = Path(filename)
            destination.parent.mkdir(parents=True, exist_ok=True)
            encoded, data = cv2.imencode(".png", image)
            if not encoded:
                raise OSError("无法编码模板图片")
            destination.write_bytes(data.tobytes())
            try:
                self.image_edit.setText(str(destination.relative_to(self._base_dir())))
            except ValueError:
                self.image_edit.setText(str(destination))
            self._append_log(f"已保存模板: {destination}")
            self._refresh_template_library_if_ready()
        except (ImportError, OSError) as exc:
            QMessageBox.critical(self, "保存模板失败", str(exc))

    def _base_dir(self) -> Path:
        if self.current_file is not None:
            return self._resolve_script_file(self.current_file).parent
        # Shortcuts and packaged executables can start with an unrelated CWD
        # (for example, System32). Keep task assets beside the application
        # until the user chooses a script file explicitly.
        return self._application_dir()

    @staticmethod
    def _application_dir() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).expanduser().resolve(strict=False).parent
        return Path(__file__).expanduser().resolve(strict=False).parent

    def _resolve_script_file(self, value: str | Path) -> Path:
        """Return an absolute script path even when an old draft was relative."""
        raw = Path(str(value)).expanduser()
        if raw.is_absolute():
            # Preserve the spelling selected by the user (including a
            # Windows 8.3 alias such as ``ADMINI~1``) while still ensuring it
            # is absolute.  Canonicalising here would make autosave/import
            # paths compare differently from the path shown in the dialog.
            return raw.absolute()
        roots = [Path.cwd().resolve(), self._application_dir()]
        if getattr(sys, "frozen", False):
            roots.insert(1, Path(sys.executable).resolve(strict=False).parent)
        seen: set[str] = set()
        for root in roots:
            candidate = (root / raw).resolve(strict=False)
            key = os.path.normcase(str(candidate))
            if key in seen:
                continue
            seen.add(key)
            if candidate.is_file():
                return candidate
        return (self._application_dir() / raw).resolve(strict=False)

    @staticmethod
    def _safe_folder_name(value: str, fallback: str = "未命名任务") -> str:
        """Keep Chinese names while making a Windows-safe directory name."""
        name = unicodedata.normalize("NFC", str(value or "")).strip()
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
        name = name.rstrip(" .") or fallback
        if name.upper() in {"CON", "PRN", "AUX", "NUL"}:
            name = f"_{name}"
        if re.match(r"^(COM|LPT)[0-9]$", name.upper()):
            name = f"_{name}"
        # Truncation can expose a trailing dot/space again, so normalize once
        # after applying the Windows path-length guard as well.
        return name[:80].rstrip(" .") or fallback

    def _task_asset_dir(self, task: dict[str, Any] | None = None) -> Path:
        if task is None and hasattr(self, "task_list"):
            row = self.task_list.currentRow()
            if 0 <= row < len(self.window_tasks):
                task = self.window_tasks[row]
        if task is not None:
            folder = self._safe_folder_name(str(task.get("name", "")))
        else:
            folder = "screenshots"
        destination = self._base_dir() / folder
        destination.mkdir(parents=True, exist_ok=True)
        return destination

    def _open_script(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "打开脚本", str(self._base_dir()), "自动化脚本 (*.json)")
        if not filename:
            return
        if not self._confirm_discard():
            return
        try:
            data = json.loads(Path(filename).read_text(encoding="utf-8"))
            legacy_steps = data.get("steps", [])
            if not isinstance(legacy_steps, list):
                raise ValueError("脚本中的 steps 必须是数组")
            normalized_legacy_steps = [self._normalize_step(item) for item in legacy_steps]
            raw_tasks = data.get("window_tasks", [])
            if not isinstance(raw_tasks, list):
                raise ValueError("脚本中的 window_tasks 必须是数组")
            normalized_tasks = [
                self._normalize_window_task(item, index + 1)
                for index, item in enumerate(raw_tasks)
            ]
            migrated_legacy = False
            ignored_legacy_duplicate = False
            if normalized_legacy_steps:
                legacy_task = self._task_from_legacy_steps(
                    normalized_legacy_steps,
                    len(normalized_tasks) + 1,
                    str(data.get("name") or "旧版脚本步骤"),
                )
                duplicate = any(
                    task.get("steps", []) == legacy_task["steps"]
                    and str(task.get("title_contains", "")) == str(legacy_task.get("title_contains", ""))
                    and str(task.get("process_name", "")) == str(legacy_task.get("process_name", ""))
                    for task in normalized_tasks
                )
                only_default_wait = legacy_task["steps"] == [default_step("wait")]
                has_target = bool(legacy_task.get("title_contains") or legacy_task.get("process_name"))
                if not normalized_tasks or (not duplicate and (not only_default_wait or has_target)):
                    normalized_tasks.append(legacy_task)
                    migrated_legacy = True
                else:
                    ignored_legacy_duplicate = duplicate or only_default_wait
            if not normalized_tasks:
                normalized_tasks = [default_window_task(1)]
            self._autosave_timer.stop()
            self._stop_all_window_tasks()
            self._wait_for_window_tasks()
            self.window_task_status.clear()
            self.window_tasks = normalized_tasks
            self.current_file = self._resolve_script_file(filename)
            self._refresh_window_task_list(0)
            self._refresh_template_library_if_ready()
            self._clear_log_preview()
            self._set_dirty(False)
            self._append_log(f"已打开: {filename}")
            self._write_autosave()
            if migrated_legacy:
                self._append_log("已将旧版顶层步骤迁移为独立窗口任务")
            elif ignored_legacy_duplicate:
                self._append_log("已忽略与窗口任务重复的旧版顶层步骤")
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, "打开失败", str(exc))

    def _normalize_step(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") not in TYPE_LABELS:
            raise ValueError("脚本包含无效步骤")
        step_type = str(value["type"])
        step = default_step(step_type)
        fields_by_type = {
            "click": ("x", "y"),
            "double_click": ("x", "y"),
            "move": ("x", "y"),
            "drag": ("start_x", "start_y", "end_x", "end_y", "duration"),
            "macro": ("name", "events", "mode", "repeat", "interval"),
            "press": ("key",),
            "type": ("text",),
            "wait": ("seconds",),
            "wait_image": ("image", "confidence", "timeout"),
            "click_image": ("image", "confidence", "timeout", "offset_x", "offset_y"),
            "window_wait_image": ("image", "confidence", "timeout"),
            "window_click_image": ("image", "confidence", "timeout", "offset_x", "offset_y"),
            "ocr": ("target_text", "confidence", "timeout"),
            "window_ocr": ("target_text", "confidence", "timeout"),
            "find_window": (
                "title_contains", "process_name", "window_timeout",
                "background_input", "activate_window",
            ),
            "screenshot": ("path",),
        }
        step["enabled"] = bool(value.get("enabled", True))
        step["label"] = str(value.get("label", "") or "").strip()
        for field in fields_by_type[step_type]:
            if field in value:
                step[field] = value[field]
        if step_type in {"click", "double_click", "move"}:
            step["x"] = _safe_int(step.get("x", 0), 0)
            step["y"] = _safe_int(step.get("y", 0), 0)
        elif step_type == "drag":
            for field in ("start_x", "start_y", "end_x", "end_y"):
                step[field] = _safe_int(step.get(field, 0), 0)
            step["duration"] = _safe_float(step.get("duration", 0.8), 0.8, 0.05)
        elif step_type == "macro":
            step["repeat"] = _safe_int(step.get("repeat", 1), 1, 1)
            step["interval"] = _safe_float(step.get("interval", 0.2), 0.2, 0.0)
            step["events"] = step.get("events", []) if isinstance(step.get("events", []), list) else []
        elif step_type == "wait":
            step["seconds"] = _safe_float(step.get("seconds", 1.0), 1.0, 0.0)
        elif step_type in {"wait_image", "click_image", "window_wait_image", "window_click_image"}:
            step["confidence"] = _safe_float(step.get("confidence", 0.85), 0.85, 0.1, 0.99)
            step["timeout"] = _safe_float(step.get("timeout", 10.0), 10.0, 0.1)
            if step_type in {"click_image", "window_click_image"}:
                step["offset_x"] = _safe_int(step.get("offset_x", 0), 0)
                step["offset_y"] = _safe_int(step.get("offset_y", 0), 0)
        if step_type == "find_window":
            step["window_timeout"] = _safe_float(step.get("window_timeout", 10.0), 10.0, 0.1)
            # Normalize legacy scripts to the fixed background-only policy.
            # Normalize legacy scripts to the fixed background-only policy.
            step["background_input"] = True
            step["activate_window"] = False
        elif step_type in {"ocr", "window_ocr"}:
            step["target_text"] = str(step.get("target_text", "") or "")
            step["confidence"] = _safe_float(step.get("confidence", 0.6), 0.6, 0.1, 0.99)
            step["timeout"] = _safe_float(step.get("timeout", 10.0), 10.0, 0.1)
        return step

    def _normalize_window_task(self, value: Any, index: int) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("window_tasks 包含无效任务")
        task = default_window_task(index)
        task.update({key: value[key] for key in (
            "name", "title_contains", "process_name", "window_timeout",
            "background_input", "activate_window", "run_mode", "repeat", "interval",
        ) if key in value})
        task["name"] = str(task.get("name") or f"窗口任务 {index}")
        task["title_contains"] = str(task.get("title_contains") or "")
        task["process_name"] = str(task.get("process_name") or "")
        task["window_timeout"] = _safe_float(task.get("window_timeout", 10.0), 10.0, 0.1)
        # Keep these fields in the file for compatibility, but normalize every
        # imported task to the application's fixed background-only policy.
        task["background_input"] = True
        task["activate_window"] = False
        run_mode = str(task.get("run_mode", "once"))
        task["run_mode"] = run_mode if run_mode in {"once", "repeat", "loop"} else "once"
        task["repeat"] = _safe_int(task.get("repeat", 2), 2, 1)
        task["interval"] = _safe_float(task.get("interval", 0.5), 0.5, 0.0)
        raw_steps = value.get("steps", [])
        if not isinstance(raw_steps, list):
            raise ValueError("窗口任务的 steps 必须是数组")
        task_steps: list[dict[str, Any]] = []
        for item in raw_steps:
            step = self._normalize_step(item)
            if step.get("type") == "find_window":
                for key in ("title_contains", "process_name"):
                    if not task.get(key) and step.get(key):
                        task[key] = step[key]
                for key in ("window_timeout", "background_input", "activate_window"):
                    if key not in value and key in step:
                        task[key] = step[key]
                continue
            task_steps.append(step)
        task["background_input"] = True
        task["activate_window"] = False
        task["steps"] = task_steps
        raw_flow = value.get("flow")
        if isinstance(raw_flow, dict) and isinstance(raw_flow.get("nodes"), list) and isinstance(raw_flow.get("edges"), list):
            normalized_nodes: list[dict[str, Any]] = []
            for raw_node in raw_flow["nodes"]:
                if not isinstance(raw_node, dict) or not raw_node.get("id"):
                    continue
                node = {
                    "id": str(raw_node["id"]),
                    "type": str(raw_node.get("type", "action")),
                    "x": _safe_float(raw_node.get("x", 0), 0.0),
                    "y": _safe_float(raw_node.get("y", 0), 0.0),
                }
                if node["type"] == "action":
                    raw_step = raw_node.get("step", default_step("wait"))
                    node["step"] = self._normalize_step(raw_step)
                elif node["type"] == "condition":
                    node["label"] = str(raw_node.get("label", "") or "").strip()
                    operator = str(raw_node.get("operator", "and")).lower()
                    if operator == "not":
                        node["operator"] = "and"
                        node["negate"] = True
                    else:
                        node["operator"] = operator if operator in {"and", "or"} else "and"
                        node["negate"] = bool(raw_node.get("negate", False))
                    node["conditions"] = [
                        {
                            "type": "image_exists",
                            "image": str(condition.get("image", "")),
                            "confidence": _safe_float(condition.get("confidence", 0.85), 0.85, 0.1, 0.99),
                            "timeout": _safe_float(condition.get("timeout", 1.0), 1.0, 0.1),
                        }
                        for condition in raw_node.get("conditions", [])
                        if isinstance(condition, dict)
                    ] or [{"type": "image_exists", "image": "", "confidence": 0.85, "timeout": 1.0}]
                normalized_nodes.append(node)
            node_ids = {node["id"] for node in normalized_nodes}
            normalized_edges = [
                {"from": str(edge.get("from")), "to": str(edge.get("to")), "port": str(edge.get("port", "next"))}
                for edge in raw_flow["edges"]
                if isinstance(edge, dict) and str(edge.get("from")) in node_ids and str(edge.get("to")) in node_ids
            ]
            task["flow"] = {"nodes": normalized_nodes, "edges": normalized_edges}
            task["steps"] = steps_from_flow(task["flow"])
        else:
            task["flow"] = flow_from_steps(task_steps)
        return task

    def _task_from_legacy_steps(self, steps: list[dict[str, Any]], index: int, name: str) -> dict[str, Any]:
        task = default_window_task(index)
        task["name"] = name.strip() or f"窗口任务 {index}"
        task["steps"] = []
        for step in steps:
            if step.get("type") == "find_window":
                task.update({
                    "title_contains": str(step.get("title_contains", "")),
                    "process_name": str(step.get("process_name", "")),
                    "window_timeout": _safe_float(step.get("window_timeout", 10.0), 10.0, 0.1),
                    "background_input": True,
                    "activate_window": False,
                })
            else:
                task["steps"].append(step)
        if not task["steps"]:
            task["steps"] = [default_step("wait")]
        task["flow"] = flow_from_steps(task["steps"])
        return task

    def _export_asset_copies(self, destination: Path, tasks: list[dict[str, Any]]) -> list[tuple[Path, Path]]:
        source_root = self._base_dir().resolve()
        target_root = destination.parent.resolve()
        if source_root == target_root:
            return []

        copies: dict[Path, Path] = {}
        for task in tasks:
            folder = self._safe_folder_name(str(task.get("name", "")))
            task_source = source_root / folder
            task_target = target_root / folder
            references = list(task.get("steps", []))
            flow = task.get("flow", {})
            for node in flow.get("nodes", []) if isinstance(flow, dict) else []:
                if not isinstance(node, dict):
                    continue
                if node.get("type") == "action":
                    references.append(node.get("step"))
                elif node.get("type") == "condition":
                    references.extend(node.get("conditions", []))
            seen_references: set[int] = set()
            for item in references:
                if not isinstance(item, dict) or "image" not in item:
                    continue
                if id(item) in seen_references:
                    continue
                seen_references.add(id(item))
                if item.get("type") not in {
                    "wait_image", "click_image", "window_wait_image", "window_click_image", "image_exists",
                }:
                    continue
                image = str(item.get("image", "")).strip()
                if not image:
                    continue
                relative = Path(image)
                if relative.is_absolute():
                    continue
                task_image = task_source / relative
                from_task = task_image.is_file()
                source = (task_image if from_task else source_root / relative).resolve()
                if not source.is_file():
                    raise FileNotFoundError(f"模板图片不存在，无法导出可用脚本: {source}")
                target = ((task_target if from_task else target_root) / relative).resolve()
                if not target.is_relative_to(target_root):
                    # An external ../ path cannot be reproduced inside the export folder.
                    name = f"{uuid.uuid5(uuid.NAMESPACE_URL, str(source)).hex[:12]}_{source.name}"
                    item["image"] = str(Path("script_assets") / name)
                    target = target_root / "script_assets" / name
                task_resolution = (task_target / Path(str(item["image"]))).resolve()
                if task_resolution != target and task_resolution.is_file() and task_resolution.read_bytes() != source.read_bytes():
                    raise FileExistsError(f"任务目录中的同名图片会覆盖导出后的模板: {task_resolution}")
                if target == destination.resolve():
                    raise FileExistsError(f"模板图片与导出脚本路径冲突: {target}")
                existing_source = copies.get(target)
                if existing_source is not None and existing_source != source:
                    if existing_source.read_bytes() != source.read_bytes():
                        raise FileExistsError(f"多个任务引用不同图片但导出路径相同: {target}")
                copies[target] = source

        for target, source in copies.items():
            if target.exists() and (not target.is_file() or target.read_bytes() != source.read_bytes()):
                raise FileExistsError(f"导出目录存在内容不同的模板图片: {target}")
        return [(source, target) for target, source in copies.items() if not target.exists()]

    @staticmethod
    def _copy_export_assets(copies: list[tuple[Path, Path]]) -> list[Path]:
        created: list[Path] = []
        try:
            for source, target in copies:
                target.parent.mkdir(parents=True, exist_ok=True)
                staged: Path | None = None
                try:
                    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp", delete=False) as temporary:
                        staged = Path(temporary.name)
                        with source.open("rb") as input_file:
                            shutil.copyfileobj(input_file, temporary)
                    if target.exists():
                        if target.read_bytes() != source.read_bytes():
                            raise FileExistsError(f"导出目录存在内容不同的模板图片: {target}")
                    else:
                        os.replace(staged, target)
                        created.append(target)
                finally:
                    if staged is not None:
                        staged.unlink(missing_ok=True)
            return created
        except OSError:
            for target in reversed(created):
                target.unlink(missing_ok=True)
            raise

    def _sync_exported_image_paths(self, tasks: list[dict[str, Any]]) -> None:
        def sync_image(source: Any, exported: Any) -> None:
            if isinstance(source, dict) and isinstance(exported, dict) and "image" in exported:
                if source.get("image") != exported["image"]:
                    source["image"] = exported["image"]

        for source_task, exported_task in zip(self.window_tasks, tasks):
            for source_step, exported_step in zip(source_task.get("steps", []), exported_task.get("steps", [])):
                sync_image(source_step, exported_step)
            source_flow = source_task.get("flow", {})
            exported_flow = exported_task.get("flow", {})
            if not isinstance(source_flow, dict) or not isinstance(exported_flow, dict):
                continue
            for source_node, exported_node in zip(source_flow.get("nodes", []), exported_flow.get("nodes", [])):
                if not isinstance(source_node, dict) or not isinstance(exported_node, dict):
                    continue
                if source_node.get("type") == "action":
                    sync_image(source_node.get("step"), exported_node.get("step"))
                elif source_node.get("type") == "condition":
                    for source_condition, exported_condition in zip(
                        source_node.get("conditions", []), exported_node.get("conditions", []),
                    ):
                        sync_image(source_condition, exported_condition)

    def _export_json(self) -> bool:
        suggested = self.current_file or (self._base_dir() / "script.json")
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出 JSON", str(suggested), "自动化脚本 (*.json)"
        )
        if not filename:
            return False
        destination = Path(filename)
        if self._active_task() is not None and hasattr(self, "flow_canvas"):
            self._flow_changed()
        payload = {
            "version": SCRIPT_VERSION,
            "name": destination.stem,
            "window_tasks": [copy.deepcopy(task) for task in self.window_tasks],
        }
        created_assets: list[Path] = []
        staged_json: Path | None = None
        try:
            copies = self._export_asset_copies(destination, payload["window_tasks"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            created_assets = self._copy_export_assets(copies)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=destination.parent,
                prefix=f".{destination.name}.", suffix=".tmp", delete=False,
            ) as temporary:
                staged_json = Path(temporary.name)
                json.dump(payload, temporary, ensure_ascii=False, indent=2)
            os.replace(staged_json, destination)
            self._sync_exported_image_paths(payload["window_tasks"])
            self.current_file = self._resolve_script_file(destination)
            self._set_dirty(False)
            self._write_autosave()
            self._append_log(f"已导出 JSON: {self.current_file}")
            return True
        except (OSError, TypeError, ValueError) as exc:
            for target in reversed(created_assets):
                target.unlink(missing_ok=True)
            QMessageBox.critical(self, "导出失败", str(exc))
            return False
        finally:
            if staged_json is not None:
                staged_json.unlink(missing_ok=True)

    # Keep the internal name for older signal/call sites; the UI action is an
    # explicit JSON export, while normal edits are handled by the local draft.
    def _save_script(self) -> bool:
        return self._export_json()

    def _run_script(self) -> None:
        if not 0 <= self.active_task_index < len(self.window_tasks):
            QMessageBox.information(self, "无法运行", "请先选择一个窗口任务。")
            return
        task = self.window_tasks[self.active_task_index]
        task_name = str(task.get("name", f"窗口任务 {self.active_task_index + 1}"))
        if not self.steps:
            self._clear_log_preview()
            self._append_log(f"[{task_name}] 无法运行：当前任务没有操作步骤")
            QMessageBox.information(self, "无法运行", "请先为当前任务添加至少一个步骤。")
            return
        self._cancel_mouse_capture()
        self._cancel_drag_recording()
        self._start_window_task(self.active_task_index)

    def _stop_script(self) -> None:
        if not 0 <= self.active_task_index < len(self.window_tasks):
            return
        task = self.window_tasks[self.active_task_index]
        run = self.window_task_runs.get(id(task))
        if run:
            run["worker"].stop()
            run["stop_requested"] = True
            self.window_task_status[id(task)] = "正在停止"
            self._append_log(f"[{task.get('name', '未命名任务')}] 正在停止...")
            self._update_window_task_status_label()
            self._update_editor_run_buttons()

    @Slot(bool, str)
    def _run_finished(self, success: bool, message: str) -> None:
        self._append_log(message)
        self.statusBar().showMessage(message, 5000)

    def _thread_finished(self) -> None:
        if self.worker:
            self.worker.deleteLater()
        if self.worker_thread:
            self.worker_thread.deleteLater()
        self.worker = None
        self.worker_thread = None
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.record_macro_button.setEnabled(True)
        self.add_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    @Slot(str)
    def _append_log(self, message: str) -> None:
        if not hasattr(self, "log_view"):
            return
        message = str(message)
        # Keep a visible gap after each round boundary so consecutive rounds
        # remain scannable in the log preview. The worker message itself stays
        # unchanged for consumers of the worker signal.
        if "========== 第 " in message and " 轮结束：" in message:
            message += "\n\n"
        timestamp = time.strftime("%H:%M:%S")
        self.log_view.append(f"[{timestamp}] {message}")
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self._log_message_count = int(getattr(self, "_log_message_count", 0)) + 1
        if any(keyword in message for keyword in ("失败", "错误", "超时", "无法", "未识别")):
            self._log_error_count = int(getattr(self, "_log_error_count", 0)) + 1
        if hasattr(self, "status_metrics_label"):
            self.status_metrics_label.setText(
                f"日志 {self._log_message_count}  ·  错误 {self._log_error_count}"
            )
        if hasattr(self, "status_primary_label"):
            summary = message.splitlines()[0].strip()
            self.status_primary_label.setText(summary[:100] or "就绪")
        if hasattr(self, "log_session_item"):
            self.log_session_item.setText(
                f"当前会话\n{self._log_message_count} 条 · {self._log_error_count} 个错误"
            )
        if hasattr(self, "log_summary_label"):
            self.log_summary_label.setText(
                f"最近更新 {timestamp}\n{self._log_message_count} 条日志，{self._log_error_count} 个错误"
            )
        round_match = re.search(r"第\s*(\d+)\s*轮", message)
        if round_match and hasattr(self, "log_round_label"):
            self.log_round_label.setText(f"轮次  {round_match.group(1)}")

    def _clear_log_preview(self) -> None:
        if hasattr(self, "log_view"):
            self.log_view.clear()
        self._log_message_count = 0
        self._log_error_count = 0
        if hasattr(self, "status_metrics_label"):
            self.status_metrics_label.setText("日志 0  ·  错误 0")
        if hasattr(self, "status_primary_label"):
            self.status_primary_label.setText("就绪")
        if hasattr(self, "log_session_item"):
            self.log_session_item.setText("当前会话\n尚未运行")
        if hasattr(self, "log_summary_label"):
            self.log_summary_label.setText("尚无执行日志")
        if hasattr(self, "log_round_label"):
            self.log_round_label.setText("轮次  —")

    def _set_dirty(self, dirty: bool) -> None:
        self.is_dirty = bool(dirty)
        title = APP_NAME
        if self.current_file:
            title += f" - {self.current_file.name}"
        if self.is_dirty:
            title += " *"
        self.setWindowTitle(title)
        autosave_enabled = True
        if hasattr(self, "_draft_settings"):
            autosave_enabled = bool(
                self._draft_settings.value("ui/autosave_enabled", True, type=bool)
            )
        if self.is_dirty and autosave_enabled:
            self._schedule_autosave()

    def _confirm_discard(self) -> bool:
        self._discarded_changes = False
        if not self.is_dirty:
            return True
        answer = QMessageBox.question(
            self,
            "未保存修改",
            "当前脚本有未保存修改，是否保存？",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if answer == QMessageBox.Save:
            return self._save_script()
        self._discarded_changes = answer == QMessageBox.Discard
        return self._discarded_changes

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._confirm_discard():
            event.ignore()
            return
        self._autosave_timer.stop()
        self._cancel_mouse_capture()
        self._cancel_drag_recording()
        self._cancel_macro_listeners()
        if self.worker:
            self.worker.stop()
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait(1500)
        self._stop_all_window_tasks()
        self._wait_for_window_tasks()
        if self._discarded_changes:
            self._restore_accepted_autosave()
        else:
            self._write_autosave()
        event.accept()


def enable_dark_title_bar(widget: QWidget) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        enabled = ctypes.c_int(1)
        hwnd = int(widget.winId())
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(enabled),
                ctypes.sizeof(enabled),
            )
            if result == 0:
                break
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    configure_ui_font(app)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()

    def handle_unhandled_exception(exc_type, exc_value, exc_traceback) -> None:
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        try:
            base_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
            log_path = base_dir / "automation_error.log"
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n{details}")
        except OSError:
            log_path = None
        message = f"界面操作发生错误：{exc_value}"
        if log_path is not None:
            message += f"\n\n错误详情已保存到：\n{log_path}"
        QMessageBox.critical(window, "操作失败", message)

    sys.excepthook = handle_unhandled_exception
    window.show()
    enable_dark_title_bar(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
