import os
import io
import sys
import json

import pandas as pd
import threading
import asyncio
from cryptography.fernet import Fernet

from PyQt6.QtWidgets import (
    QDialog,
    QApplication,
    QComboBox,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QListWidget,
    QTabWidget,
    QSpinBox,
    QLineEdit,
    QScrollArea,
    QAbstractItemView,
    QListWidgetItem,
    QTreeWidgetItem,
    QHeaderView,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
)

from PyQt6.QtCore import (
    QTimer,
    QSize,
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtSlot,
    pyqtSignal,
)

from server import run as run_server

from PyQt6.QtGui import (
    QFont,
    QColor,
    QIcon,
    QPainter,
    QPixmap, 
    QImage,
)

from colors import colorTheme
from threadingShared import bot_stop_event

import threadingShared

from games import games
from separatorDelegate import SeparatorDelegate, BorderDelegate
from custom_titlebar import CUSTOM_TITLEBAR, TitleBarMixin
from ui_widgets import ClearSelectionListWidget, ClearSelectionTreeWidget

import SearchDialog
import configparser

if sys.executable.endswith("pythonw.exe"):
    sys.stdout = open("bot_output.log", "w")
    sys.stderr = open("bot_errors.log", "w")

window = None

config = configparser.ConfigParser()
config.read('resources/config.cfg')

queryAccuracy = float(config['user_settings']['query_accuracy'])
maxRequestsPerUser = int(config['user_settings']['max_requests_per_user'])
displayName = config['user_credentials']['user']
port = int(config['user_settings']['port']) if 'port' in config['user_settings'] else 3000
songQueueFilePath = config['file_paths']['song_queue_file_path']

TOKEN_FILE = config['file_paths']['token_file_path']
with open('resources/auth/twitch_credentials.json', 'r') as f:
    credentials = json.load(f)
APP_ID = credentials['APP_ID']
APP_SECRET = credentials['APP_SECRET']
TARGET_CHANNEL = displayName

with open('resources/auth/fernet_key.json', 'r') as f:
    key_data = json.load(f)
    key = key_data['key'].encode()
cipher = Fernet(key)
with open(config['file_paths']['data_csv_enc'], "rb") as f:
    encrypted_data = f.read()
decrypted_data = cipher.decrypt(encrypted_data)
text_data = decrypted_data.decode("utf-8")
df = pd.read_csv(io.StringIO(text_data))
dfb = df.copy()

try:
    with open('resources/songLists/selected_games.json', 'r') as f:
        selected_games = json.load(f)
    if selected_games:
        game_filter = [g for g in selected_games if g != 'JD+']
        condition = df['game'].isin(game_filter)
        if 'JD+' in selected_games:            
            condition = condition | (df['JD+'] == True)
        df = df[condition]
        df = df.reset_index(drop=True)
    else:
        print('No selected games found in selected_games.json')
except FileNotFoundError:
    pass

if os.path.exists(config['file_paths']['banned_songs_csv']):
    banned_df = pd.read_csv(config['file_paths']['banned_songs_csv'])
else:
    banned_df = pd.DataFrame()

try:
    with open(config['file_paths']['commands_file_path'], 'r') as f:
        commands = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    commands = []

def recolor_png(path, color):
    color = QColor(color)

    img = QImage(path).convertToFormat(QImage.Format.Format_ARGB32)
    tinted = QImage(img.size(), QImage.Format.Format_ARGB32)
    tinted.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted)
    painter.fillRect(tinted.rect(), color)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, img)
    painter.end()

    return QIcon(QPixmap.fromImage(tinted))

def send_chat(text: str) -> None:
    chat = getattr(threadingShared.state, "chat", None)
    if chat is None:
        return

    loop = getattr(chat, "_Chat__socket_loop", None)
    if loop is None or not loop.is_running():
        return

    asyncio.run_coroutine_threadsafe(
        chat.send_message(room=TARGET_CHANNEL, text=text),
        loop,
    )

class MainWindow(TitleBarMixin, QMainWindow):
    banned_songs = []
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._setup_titlebar()
        self.status_signal.connect(self.update_status)
        self.running = False
        threadingShared.botIsRunning = False
        self.selected_games = []
        try:
            with open('resources/songLists/selected_games.json', 'r') as f:
                self.selected_games = json.load(f)
        except FileNotFoundError:
            self.selected_games = []
        tempTheme = config['user_settings']['theme'] if 'theme' in config['user_settings'] else 'default_theme'
        allThemes = colorTheme.getAllThemesAsDict()
        self.theme = allThemes[tempTheme] if tempTheme in allThemes else colorTheme.getDarkGrayTheme()
        self.init_ui()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.check_bot_status)
        self.status_timer.start(10000)

        self.load_banned_songs()

    def init_ui(self):
        self.setWindowTitle("Just Dance Song Requests")
        icon = recolor_png("resources/icons/icon.png", self.theme.textColorMain)
        self.setWindowIcon(icon)
        self.setIconSize(QSize(64, 64))
        self.setMinimumSize(650, 400)
        self.resize(900, 835)
        self.setWindowOpacity(0.0)

        self.update_colors()

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(8, 8, 8, 8)

        control_card = QFrame()
        control_card.setObjectName("controlCard")
        self._add_shadow(control_card, blur=22, offset_y=5, alpha=75)

        control_layout = QVBoxLayout(control_card)
        control_layout.setSpacing(12)
        control_layout.setContentsMargins(20, 18, 20, 16)

        button_layout_top = QHBoxLayout()
        button_layout_top.setSpacing(15)

        btn_size = QSize(120, 50)

        self.start_btn = QPushButton("✅ START BOT")
        self.start_btn.clicked.connect(self.start_bot)
        self.start_btn.setMinimumSize(btn_size)
        button_layout_top.addWidget(self.start_btn)

        self.stop_btn = QPushButton("❌ STOP BOT")
        self.stop_btn.clicked.connect(self.stop_bot)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumSize(btn_size)
        button_layout_top.addWidget(self.stop_btn)

        sep = QFrame()
        sep.setObjectName("buttonSeparator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)

        button_layout_bottom = QHBoxLayout()
        button_layout_bottom.setSpacing(15)

        self.next_btn = QPushButton("⏭️ NEXT SONG")
        self.next_btn.clicked.connect(self.next_song)
        self.next_btn.setMinimumSize(btn_size)
        button_layout_bottom.addWidget(self.next_btn)

        self.clear_btn = QPushButton("🗑️ CLEAR QUEUE")
        self.clear_btn.clicked.connect(self.clear_queue)
        self.clear_btn.setMinimumSize(btn_size)
        button_layout_bottom.addWidget(self.clear_btn)

        self.ending_btn = QPushButton("🏁 END REQUESTS")
        self.ending_btn.clicked.connect(self.endSongRequest)
        self.ending_btn.setMinimumSize(btn_size)
        button_layout_bottom.addWidget(self.ending_btn)

        control_layout.addLayout(button_layout_top)
        control_layout.addWidget(sep)
        control_layout.addLayout(button_layout_bottom)

        self.status_label = QLabel("")
        self.update_status("STATUS: Offline!")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(self.status_label)

        main_layout.addWidget(control_card)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.make_queue_tab(), "📋 Queue")
        self.tabs.addTab(self.make_banned_tab(), "🚫 Banned")
        self.tabs.addTab(self.make_settings_tab(), "⚙️ Settings")
        self.tabs.addTab(self.make_commands_tab(), "💬 Commands")
        self.tabs.addTab(self.make_game_selection_tab(), "🎮 Game Selection")
        self.tabs.addTab(self.make_songs_tab(), "🎵 All Selected Songs")

        main_layout.addWidget(self.tabs, 1)

        central = QWidget()
        central.setObjectName("mainScrollWidget")
        central.setLayout(main_layout)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainScrollArea")
        scroll_area.setWidget(central)
        scroll_area.setWidgetResizable(True)
        self.setCentralWidget(self._build_central(scroll_area))
        self.show()

        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(500)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_in.start()

    def refresh(self):
        self.update_queue()

    def start_bot(self):
        if self.running: return
        self.update_status("STATUS: Initializing...")
        self.running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        bot_stop_event.clear()
        self.bot_thread = threading.Thread(target=run, daemon=True, args=(self,))
        self.bot_thread.start()

        run_server(songQueue=songQueue, port=port)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)
    
    def stop_bot(self):
        self.running = False
        bot_stop_event.set()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if hasattr(self, 'timer'):
            self.timer.stop()

    def next_song(self):
        if len(songQueue) == 0:
            send_chat("No songs in queue!")
        elif len(songQueue) == 1:
            currentSong = songQueue[0]
            send_chat(f'Song "{currentSong.songName}" was played. Queue is now empty!')
            songQueue.clear()
            songQueue.save()
        else:
            currentSong = songQueue[0]
            songQueue.remove(songQueue[0])
            songQueue.save()
            send_chat(f'Song "{currentSong.songName}" was played. "{songQueue[0].songName}" is up next!')
        
    def clear_queue(self):
        if len(songQueue) == 0:
            send_chat("Queue is already empty!")
        else:
            songQueue.clear()
            songQueue.save()
            send_chat("Cleared queue!")            

    def endSongRequest(self):
        threadingShared.streamEnding = True
        if threadingShared.state.chat is not None:
            send_chat("No more song requests will be taken today!")

    def make_queue_tab(self):
        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget)

        queue_layout.setContentsMargins(15, 15, 15, 15)
        queue_layout.setSpacing(10)

        queue_layout.addWidget(QLabel("🎶 Current Song Queue:"))

        self.songQueueWidget = ClearSelectionTreeWidget()
        self.songQueueWidget.setColumnCount(2)
        self.songQueueWidget.setMouseTracking(True)
        self.songQueueWidget.setRootIsDecorated(False)
        self.songQueueWidget.setAlternatingRowColors(False)
        self.songQueueWidget.setUniformRowHeights(True)
        self.songQueueWidget.setItemsExpandable(False)
        self.songQueueWidget.setAllColumnsShowFocus(True)
        self.songQueueWidget.setExpandsOnDoubleClick(False)
        self.songQueueWidget.setHeaderLabels(["  #", "   Song Title and Artist - Requester, Game Version(s)"])
        self.songQueueWidget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.songQueueWidget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.songQueueWidget.setRootIsDecorated(False)
        self.songQueueWidget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.songQueueWidget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self.border_delegate = BorderDelegate(self.theme.borderColor)
        self.songQueueWidget.setItemDelegate(self.border_delegate)

        self.songQueueWidget.setMinimumHeight(200)

        queue_layout.addWidget(self.songQueueWidget)

        queue_btn_layout = QHBoxLayout()
        self.remove_selected_btn = QPushButton("❌ Remove Selected")
        self.remove_selected_btn.clicked.connect(self.remove_selected_song)
        queue_btn_layout.addWidget(self.remove_selected_btn)
        queue_btn_layout.addStretch()

        queue_layout.addLayout(queue_btn_layout)

        return queue_widget
    
    def update_queue(self):
        current_count = self.songQueueWidget.topLevelItemCount()
        target_count = len(songQueue)

        while current_count > target_count:
            self.songQueueWidget.takeTopLevelItem(current_count - 1)
            current_count -= 1

        for i, song in enumerate(songQueue):

            if i < current_count:
                item = self.songQueueWidget.topLevelItem(i)
            else:
                item = QTreeWidgetItem()
                self.songQueueWidget.addTopLevelItem(item)

            song_text = f"{song.getRequestAsString()} | requested by {song.user.display_name}, {song.gameVersions}"

            is_now_playing = (i == 0)

            item.setText(0, str(i + 1))
            item.setText(1, ("▶ Now Playing: " if is_now_playing else "") + song_text)

            font = item.font(1)
            font.setBold(is_now_playing)
            item.setFont(1, font)

            if is_now_playing:
                fg = QColor(self.theme.textColorSecondary)
                bg0 = QColor(self.theme.currentSongColor)
                bg1 = QColor(self.theme.currentSongColorLight)

                item.setBackground(0, bg0)
                item.setBackground(1, bg1)
            else:
                fg = QColor(self.theme.textColorMain)

                item.setBackground(0, QColor("transparent"))
                item.setBackground(1, QColor("transparent"))

            item.setForeground(0, fg)
            item.setForeground(1, fg)

    def remove_selected_song(self):
        current_item = self.songQueueWidget.currentItem()
        if current_item:
            index = self.songQueueWidget.indexOfTopLevelItem(current_item)
            if index >= 0 and index < len(songQueue):
                songQueue.pop(index)
                songQueue.save()
                self.songQueueWidget.clearSelection()
                self.update_queue()
                self.update_colors()

    def make_banned_tab(self):
        banned_widget = QWidget()
        banned_layout = QVBoxLayout(banned_widget)
        banned_layout.setContentsMargins(15, 15, 15, 15)
        banned_layout.setSpacing(10)

        banned_layout.addWidget(QLabel("🚫 Banned Songs List:"))
        self.banned_list = ClearSelectionListWidget()
        self.banned_list.setMinimumHeight(200)
        self.banned_list.setItemDelegate(SeparatorDelegate(color=self.theme.borderColor))
        banned_layout.addWidget(self.banned_list)

        banned_btn_layout = QHBoxLayout()
        self.remove_banned_btn = QPushButton("❌ Remove Selected")
        self.remove_banned_btn.clicked.connect(self.remove_banned_song)
        self.add_banned_btn = QPushButton(" Add Banned Song")
        self.add_banned_btn.setIcon(QIcon("resources/icons/plus_icon.png"))
        self.add_banned_btn.setIconSize(QSize(16, 16))
        self.add_banned_btn.clicked.connect(self.add_banned_song)
        banned_btn_layout.addWidget(self.remove_banned_btn)
        banned_btn_layout.addWidget(self.add_banned_btn)
        banned_btn_layout.addStretch()
        banned_layout.addLayout(banned_btn_layout)
        return banned_widget

    def add_banned_song(self):
        data = dfb
        try:
            dialog = SearchDialog.SongSearchDialog(data, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            row_index = dialog.get_selected_row_index()
            if row_index is None:
                return

            song_row = data.loc[row_index]

            for _, banned_row in self.banned_songs_df.iterrows():
                if song_row['songName'] == banned_row['songName'] and song_row['alternate'] == banned_row['alternate']:
                    self.status_label.setText("Already Banned!")
                    return

            new_row = pd.DataFrame([song_row]).reset_index(drop=True)
            self.banned_songs_df = pd.concat([self.banned_songs_df, new_row], ignore_index=True)
            self.banned_songs = self.banned_songs_df.copy()

            extreme_str = " (Extreme)" if song_row['extreme'] else ""
            self.banned_list.addItem(f"{song_row['songName']} - {song_row['ContributingArtists']}{extreme_str}")

            self.save_banned_songs()
            self.status_label.setText(f"Banned: {song_row['songName']}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {str(e)}")

    def remove_banned_song(self):
        current_row = self.banned_list.currentRow()
        if current_row >= 0:
            display_text = self.banned_list.item(current_row).text()
            song_name = display_text.split(" - ")[0]
            
            self.banned_songs_df = self.banned_songs_df[self.banned_songs_df['songName'] != song_name].reset_index(drop=True)
            self.banned_songs = self.banned_songs_df.copy()
            
            self.banned_list.takeItem(current_row)
            self.save_banned_songs()
            self.status_label.setText("Removed Banned Song!")

    def save_banned_songs(self):
        self.banned_songs_df.to_csv(config['file_paths']['banned_songs_csv'], index=False, header=True)

    def load_banned_songs(self):
        try:
            self.banned_songs_df = pd.read_csv(config['file_paths']['banned_songs_csv'])
            self.banned_songs = self.banned_songs_df
            self.banned_list.clear()
            
            for _, row in self.banned_songs.iterrows():
                self.banned_list.addItem(f"{row['songName']} - {row['ContributingArtists']} {'(Extreme)' if row['extreme'] else ''}")
        except FileNotFoundError:
            self.banned_songs_df = pd.DataFrame()
            self.banned_songs = []

    def make_settings_tab(self):
        maxRequestsPerUser = config['user_settings']['max_requests_per_user']
        accuracy = config['user_settings']['query_accuracy']

        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setSpacing(15)

        settings_layout.addWidget(QLabel("⚙️ Bot Settings (Application Needs to be Restarted for Changes to Take Effect):"))

        theme_row = QHBoxLayout()

        themeLabel = QLabel("Theme (No restart required):")

        self.theme_dropdown = QComboBox()
        self.theme_dropdown.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.theme_dropdown.wheelEvent = lambda event: None

        allThemes = colorTheme.getAllThemesAsDict()
        self.theme_keys = list(allThemes.keys())

        for key in self.theme_keys:
            self.theme_dropdown.addItem(allThemes[key].name)

        current_theme = config['user_settings'].get('theme', 'default_theme')
        if current_theme in self.theme_keys:
            self.theme_dropdown.setCurrentIndex(self.theme_keys.index(current_theme))

        settings_layout.addWidget(self.theme_dropdown)

        theme_row.addWidget(themeLabel)
        theme_row.addWidget(self.theme_dropdown, 1)

        theme_row.setStretch(0, 7)
        theme_row.setStretch(1, 4)

        settings_layout.addLayout(theme_row)

        port_row = QHBoxLayout()

        port_label = QLabel("Port for Web Interface (1-65535, default: 3000):")

        self.port_spin = QSpinBox()
        self.port_spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.port_spin.wheelEvent = lambda event: None
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(int(config['user_settings']['port']))

        port_row.addWidget(port_label)
        port_row.addWidget(self.port_spin, 1)

        port_row.setStretch(0, 7)
        port_row.setStretch(1, 4)

        settings_layout.addLayout(port_row)

        max_queue_row = QHBoxLayout()

        max_queue_label = QLabel("Max Requests Per User:")

        self.max_queue_spin = QSpinBox()
        self.max_queue_spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.max_queue_spin.wheelEvent = lambda event: None
        self.max_queue_spin.setRange(1, 20)
        self.max_queue_spin.setValue(int(maxRequestsPerUser))

        max_queue_row.addWidget(max_queue_label)
        max_queue_row.addWidget(self.max_queue_spin, 1)

        max_queue_row.setStretch(0, 7)
        max_queue_row.setStretch(1, 4)

        settings_layout.addLayout(max_queue_row)

        accuracy_row = QHBoxLayout()

        accuracy_label = QLabel(
            "Minimum accuracy needed for song request (0-100, 59 is recommended):"
        )

        self.accuracy_spin = QSpinBox()
        self.accuracy_spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.accuracy_spin.wheelEvent = lambda event: None
        self.accuracy_spin.setRange(0, 100)
        self.accuracy_spin.setValue(int(accuracy))

        accuracy_row.addWidget(accuracy_label)
        accuracy_row.addWidget(self.accuracy_spin, 1)

        accuracy_row.setStretch(0, 7)
        accuracy_row.setStretch(1, 4)

        settings_layout.addLayout(accuracy_row)

        username_row = QHBoxLayout()

        username_label = QLabel("Username:")

        self.username = QLineEdit(config['user_credentials']['user'] if config['user_credentials']['user'] else 'Null')
        self.username.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.username.wheelEvent = lambda event: None

        username_row.addWidget(username_label)
        username_row.addWidget(self.username, 1)

        username_row.setStretch(0, 7)
        username_row.setStretch(1, 4)

        settings_layout.addLayout(username_row)

        mode_row = QHBoxLayout()

        mode_label = QLabel("Mode:")

        self.admin_mode_checkbox = QCheckBox("  Enable Admin Mode")
        self.admin_mode_checkbox.setChecked(threadingShared.adminMode)
        self.mode = QLineEdit('Null' if not threadingShared.adminMode else '')
        self.mode.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.mode.wheelEvent = lambda event: None
        self.mode.setEnabled(threadingShared.adminMode)

        def toggle_mode(state):
            self.mode.setEnabled(state == Qt.CheckState.Checked.value)
        self.admin_mode_checkbox.stateChanged.connect(toggle_mode)

        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.admin_mode_checkbox)

        mode_row.setStretch(0, 7)
        mode_row.setStretch(1, 4)

        settings_layout.addLayout(mode_row)

        message_row = QHBoxLayout()

        message_label = QLabel("Custom Message:")

        self.message = QLineEdit(threadingShared.customMessage)
        self.message.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.message.wheelEvent = lambda event: None

        message_row.addWidget(message_label)
        message_row.addWidget(self.message, 1)

        message_row.setStretch(0, 2)
        message_row.setStretch(1, 8)

        settings_layout.addLayout(message_row)
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_settings)
        settings_layout.addWidget(save_btn)

        settings_layout.addStretch()
        return settings_widget

    def update_colors(self):
        with open('style/main.qss', 'r') as f:
            qss = f.read()
            
            qss = qss.replace("{textColorMain}", self.theme.textColorMain)
            qss = qss.replace("{textColorSecondary}", self.theme.textColorSecondary)
            qss = qss.replace("{backgroundGradientDark}", self.theme.backgroundGradientDark)
            qss = qss.replace("{backgroundGradientLight}", self.theme.backgroundGradientLight)
            qss = qss.replace("{buttonGradientDark}", self.theme.buttonGradientDark)
            qss = qss.replace("{buttonGradientLight}", self.theme.buttonGradientLight)
            qss = qss.replace("{buttonDisabled}", self.theme.buttonDisabled)
            qss = qss.replace("{darkAccent}", self.theme.darkAccent)
            qss = qss.replace("{lightAccent}", self.theme.lightAccent)
            qss = qss.replace("{borderColor}", self.theme.borderColor)
            qss = qss.replace("{selectedColor}", self.theme.selectedColor)
            qss = qss.replace("{hoverColor}", self.theme.hoverColor)
            qss = qss.replace("{currentSongColor}", self.theme.currentSongColor)
            qss = qss.replace("{currentSongColorLight}", self.theme.currentSongColorLight)
            qss = qss.replace("{statusHighlight}", self.theme.statusHighlight)
            self.setStyleSheet(qss)

        if CUSTOM_TITLEBAR and hasattr(self, '_titlebar'):
            icon = recolor_png("resources/icons/icon.png", self.theme.textColorMain)
            self._titlebar.update_icon(icon.pixmap(28, 28))

    def save_settings(self):
        theme = self.theme_dropdown.currentIndex()
        config['user_settings']['theme'] = self.theme_keys[theme]

        maxRequestsPerUser = self.max_queue_spin.value()
        config['user_settings']['max_requests_per_user'] = maxRequestsPerUser.__str__()

        accuracy = self.accuracy_spin.value()
        config['user_settings']['query_accuracy'] = accuracy.__str__()

        port = self.port_spin.value()
        config['user_settings']['port'] = port.__str__()

        customMessageTemp = self.message.text().strip()
        if customMessageTemp:
            config['user_settings']['custom_message'] = customMessageTemp

        userMode = self.admin_mode_checkbox.isChecked()
        if userMode:
            config['user_settings']['admin_mode'] = 'True'
        else:
            config['user_settings']['admin_mode'] = ''

        text = self.username.text().strip()
        if text:
            config['user_credentials']['user'] = text
            displayName = text
            TARGET_CHANNEL = text
            config.write(open('config.cfg', 'w'))

        self.theme = colorTheme.getAllThemesAsDict()[self.theme_keys[theme]]
        self.update_colors()

        delegate = self.commands_list_widget.itemDelegate()
        if isinstance(delegate, SeparatorDelegate):
            delegate.setColor(self.theme.borderColor)
        delegate = self.banned_list.itemDelegate()
        if isinstance(delegate, SeparatorDelegate):
            delegate.setColor(self.theme.borderColor)
        delegate = self.songQueueWidget.itemDelegate()
        if isinstance(delegate, BorderDelegate):
            delegate.setColor(self.theme.borderColor)

        self.commands_list_widget.viewport().update()
        self.songQueueWidget.viewport().update()
        self.banned_list.viewport().update()
        
        self.setUpdatesEnabled(False)
        self.setUpdatesEnabled(True)
        self.update()

        for w in self.findChildren(QWidget):
            w.update()

        self.status_label.setText("Settings have been successfully saved! Restart the application for the changes to take effect.")

    def make_commands_tab(self):
        commands_widget = QWidget()
        commands_layout = QVBoxLayout(commands_widget)
        commands_layout.setContentsMargins(15, 15, 15, 15)
        commands_layout.setSpacing(10)

        commands_layout.addWidget(QLabel("📜 Available Chat Commands:"))

        self.commands_list_widget = QListWidget()
        self.commands_list_widget.setObjectName("commandsList")
        self.commands_list_widget.setItemDelegate(SeparatorDelegate(color=self.theme.borderColor))

        self.commands_list_widget.addItems(commands)

        self.commands_list_widget.setMinimumHeight(200)
        self.commands_list_widget.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)

        commands_layout.addWidget(self.commands_list_widget)
        self._add_shadow(self.commands_list_widget)

        return commands_widget

    def make_game_selection_tab(self):
        game_widget = QWidget()
        game_layout = QVBoxLayout(game_widget)
        game_layout.setContentsMargins(15, 10, 15, 13)
        game_layout.setSpacing(6)

        select_row = QHBoxLayout()
        select_label = QLabel("🎮 Selected Games:")

        self.select_all_checkbox = QCheckBox(" Select All Games")
        self.select_all_checkbox.setStyleSheet("QCheckBox { padding: 5px 5px; }")
        self.select_all_checkbox.setChecked(False)
        self.select_all_checkbox.toggled.connect(self.on_select_all_games)

        select_row.addWidget(select_label)
        select_row.addWidget(self.select_all_checkbox)
        select_row.setStretch(0, 8)
        select_row.setStretch(1, 2)
        select_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        game_layout.addLayout(select_row)

        self.game_list_widget = QListWidget()
        self.game_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.game_keys = list(games.keys())

        for full_name in games.values():
            item = QListWidgetItem(full_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.game_list_widget.addItem(item)

        for i, key in enumerate(self.game_keys):
            if key in self.selected_games:
                self.game_list_widget.item(i).setCheckState(Qt.CheckState.Checked)

        self.game_list_widget.setMinimumHeight(200)
        game_layout.addWidget(self.game_list_widget)

        self.save_games_btn = QPushButton("💾 Save Selected Games")
        self.save_games_btn.clicked.connect(self.on_save_games)
        game_layout.addWidget(self.save_games_btn)

        self.update_select_all_checkbox()
        return game_widget

    def on_select_all_games(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.game_list_widget.count()):
            self.game_list_widget.item(i).setCheckState(state)

    def update_select_all_checkbox(self):
        total = self.game_list_widget.count()
        checked = sum(
            1 for i in range(total)
            if self.game_list_widget.item(i).checkState() == Qt.CheckState.Checked
        )
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(total > 0 and checked == total)
        self.select_all_checkbox.blockSignals(False)

    def on_save_games(self):
        selected_keys = [self.game_keys[i] for i in range(self.game_list_widget.count())
                        if self.game_list_widget.item(i).checkState() == Qt.CheckState.Checked]
        self.handle_selected_games(selected_keys)

    def handle_selected_games(self, game_keys):
        global df

        self.selected_games = game_keys
        with open('resources/songLists/selected_games.json', 'w') as f:
            json.dump(game_keys, f)

        if game_keys:
            game_filter = [game for game in game_keys if game != 'JD+']
            condition = dfb['game'].isin(game_filter)
            if 'JD+' in game_keys:
                condition = condition | (dfb['JD+'] == True)
            filtered_df = dfb[condition].reset_index(drop=True)
        else:
            filtered_df = dfb.copy()

        df.drop(df.index, inplace=True)
        for column in filtered_df.columns:
            df[column] = filtered_df[column].to_numpy()

        self.refresh_songs_list()
        self.status_label.setText("Game selection saved and song list updated!")

    def make_songs_tab(self):
        songs_widget = QWidget()
        songs_layout = QVBoxLayout(songs_widget)
        songs_layout.setContentsMargins(15, 15, 15, 15)
        songs_layout.setSpacing(10)

        songs_header_layout = QHBoxLayout()
        songs_header_layout.addWidget(QLabel("🎵 All Songs from Selected Games:"))
        songs_header_layout.addStretch()

        self.songs_total_label = QLabel("Total Number of Songs: 0")
        self.songs_total_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        songs_header_layout.addWidget(self.songs_total_label)

        songs_layout.addLayout(songs_header_layout)

        self.songs_search_box = QLineEdit()
        self.songs_search_box.setPlaceholderText("Search by song name or artist...")
        self.songs_search_box.textChanged.connect(self.on_songs_search_changed)
        songs_layout.addWidget(self.songs_search_box)

        self.songs_list_widget = QListWidget()
        self.songs_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.songs_list_widget.setMinimumHeight(200)

        self.refresh_songs_list()

        songs_layout.addWidget(self.songs_list_widget)

        self.add_song_to_queue_btn = QPushButton(" Add to Queue")
        self.add_song_to_queue_btn.setIcon(QIcon("resources/icons/plus_icon.png"))
        self.add_song_to_queue_btn.clicked.connect(self.add_selected_song_to_queue)
        songs_layout.addWidget(self.add_song_to_queue_btn)

        return songs_widget

    def refresh_songs_list(self, search_text=""):
        self.songs_list_widget.clear()
        sorted_df = df.sort_values(by='songName', key=lambda col: col.str.lower())

        if search_text:
            search_lower = search_text.lower()
            sorted_df = sorted_df[
                sorted_df['songName'].str.lower().str.contains(search_lower, na=False) |
                sorted_df['ContributingArtists'].str.lower().str.contains(search_lower, na=False)
            ]

        if hasattr(self, 'songs_total_label'):
            self.songs_total_label.setText(f"Total Number of Songs: {len(sorted_df)}")

        for row_index, row in sorted_df.iterrows():
            extreme_str = "| (Extreme)" if row['extreme'] else ""
            alternate_str = f"| ({row['alternate']})" if row['alternate'] and row['alternate'] != '-' else ""
            if alternate_str == "| (Extreme)" or alternate_str == "| (extreme)" or alternate_str == "| (EXTREME)":
                alternate_str = ""
            game_versions = f"({row['game']}"
            if row['JD+'] and row['game'] != 'JD+':
                game_versions += "/JD+"
            game_versions += ")"
            item_text = f"{row['songName']} - {row['ContributingArtists']} {extreme_str}{alternate_str} | Games: {game_versions}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, row_index)
            self.songs_list_widget.addItem(item)

    def on_songs_search_changed(self, text):
        self.refresh_songs_list(search_text=text)

    def add_selected_song_to_queue(self):
        self.clearFocus()
        selected_items = self.songs_list_widget.selectedItems()
        if not selected_items:
            self.update_status("Select a song first!")
            return

        row_index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        song = df.iloc[row_index]

        if any(
            queued_song.songName == song['songName']
            and queued_song.alternate == song['alternate']
            for queued_song in songQueue
        ):
            self.update_status("Song is already in the queue!")
            self.songs_list_widget.clearSelection()
            return

        user = type('User', (), {'display_name': displayName})()
        game_versions = f"({song['game']}"
        if song['JD+'] and song['game'] != 'JD+':
            game_versions += "/JD+"
        game_versions += ")"

        song_queue_item = SongRequest(
            song['songName'],
            song['ContributingArtists'],
            song['extreme'],
            song['alternate'],
            user,
            game_versions,
        )
        songQueue.append(song_queue_item)
        songQueue.save()
        self.update_queue()
        self.update_status(f'Added song "{song_queue_item.getRequestAsString()}" to queue!')
        self.songs_list_widget.clearSelection()

    def on_songs_tab_clicked(self, index):
        if self.tab_widget.widget(index) is self.songs_tab_widget:
            self.songs_list_widget.clearSelection()

    def _add_shadow(self, widget, blur=15, offset_y=3, alpha=60):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset_y)
        shadow.setColor(QColor(0, 0, 0, alpha))
        widget.setGraphicsEffect(shadow)

    @pyqtSlot(str)
    def update_status(self, text):
        if self.status_label.text() == text:
            return

        current_bot_status = "STATUS: Online!" if threadingShared.botIsRunning else "STATUS: Offline!"

        if not hasattr(self, '_status_revert_timer'):
            self._status_revert_timer = QTimer(self)
            self._status_revert_timer.setSingleShot(True)
            self._status_revert_timer.timeout.connect(self._revert_status)
        self._status_revert_timer.stop()

        self.status_label.setText(text)

        if text == current_bot_status:
            self._status_is_transient = False
            return

        self._status_is_transient = True
        self._status_revert_timer.start(5000)

    def _revert_status(self):
        self._status_is_transient = False
        new_status = "STATUS: Online!" if threadingShared.botIsRunning else "STATUS: Offline!"
        self.update_status(new_status)

    def check_bot_status(self):
        if getattr(self, '_status_is_transient', False):
            return 

        new_status = "STATUS: Online!" if threadingShared.botIsRunning else "STATUS: Offline!"
        if self.status_label.text() != new_status:
            self.update_status(new_status)

if __name__ == "__main__":
    from bot import run, songQueue, SongRequest, SongQueue
    
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())