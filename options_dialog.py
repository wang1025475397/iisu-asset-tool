"""
Options Dialog for Icon Generator
Handles configuration with categorized tabs and full settings persistence
"""
import os
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QFileDialog,
    QGroupBox, QDialogButtonBox, QMessageBox, QScrollArea, QWidget,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QTabWidget,
    QSlider
)

from source_priority_widget import SourcePriorityWidget
from api_key_manager import get_manager
from rom_parser import get_available_drives, find_iisu_directory
from device_asset_dialog import DeviceAssetDialog
from background_music import get_music_manager
import i18n


class OptionsDialog(QDialog):
    """Options dialog for configuring Icon Generator settings with categorized tabs."""

    def __init__(self, parent=None, config_path="", workers=8, limit=0, source_priority_widget=None,
                 rom_directory_settings=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("Settings"))
        # Allow dialog to be smaller on smaller screens
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        # Set preferred size based on parent window
        if parent:
            parent_size = parent.size()
            self.resize(min(700, int(parent_size.width() * 0.7)),
                       min(650, int(parent_size.height() * 0.85)))

        # Store initial values
        self.config_path_value = config_path
        self.workers_value = workers
        self.limit_value = limit
        self.source_priority_widget_ref = source_priority_widget

        # ROM directory settings
        self.rom_directory_settings = rom_directory_settings or {
            "mode": "manual",
            "rom_path": "",
            "auto_detect": False,
            "remember_last_path": True
        }

        # Hero image settings
        self.hero_settings = {
            "enabled": True,
            "count": 1,
            "save_with_icons": True
        }

        # SteamGridDB settings
        self.steamgriddb_settings = {
            "square_only": True
        }

        # Fallback icon settings
        self.fallback_settings = {
            "use_platform_icon_fallback": False,
            "skip_scraping_use_platform_icon": False
        }

        # Screenshot settings
        self.screenshot_settings = {
            "enabled": False,
            "count": 3
        }

        # Device copy settings
        self.device_settings = {
            "enabled": False,
            "path": "/sdcard/Android/media/com.iisulauncher/iiSULauncher/assets/media/roms/consoles"
        }

        # Logo/Title settings
        self.logo_settings = {
            "scrape_logos": True,
            "fallback_to_boxart": True
        }

        # Export format settings
        self.export_settings = {
            "format": "PNG",
            "jpeg_quality": 95
        }

        # Custom border settings
        self.custom_border_settings = {
            "enabled": False,
            "path": "",
            "per_platform": {}
        }

        # Custom platforms
        self.custom_platforms = {}

        # Hidden titles by platform
        self.hidden_titles = {}

        # Interactive mode settings per asset type
        self.interactive_settings = {
            "icons": True,
            "heroes": False,
            "logos": False,
            "screenshots": False
        }

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Create tab widget for categories
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("options_tabs")

        # Create tabs (5 tabs)
        self.tab_widget.addTab(self._create_general_tab(), i18n.tr("General"))
        self.tab_widget.addTab(self._create_artwork_tab(), i18n.tr("Artwork"))
        self.tab_widget.addTab(self._create_output_tab(), i18n.tr("Output"))
        self.tab_widget.addTab(self._create_platforms_tab(), i18n.tr("Platforms"))
        self.tab_widget.addTab(self._create_app_tab(), i18n.tr("App"))

        layout.addWidget(self.tab_widget, 1)

        # Dialog buttons (styled)
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addStretch()

        btn_cancel = QPushButton(i18n.tr("Cancel"))
        btn_cancel.setMinimumHeight(36)
        btn_cancel.setMinimumWidth(90)
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.clicked.connect(self.reject)
        button_row.addWidget(btn_cancel)

        btn_save = QPushButton(i18n.tr("Save Settings"))
        btn_save.setMinimumHeight(36)
        btn_save.setMinimumWidth(110)
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._apply_and_accept)
        button_row.addWidget(btn_save)

        layout.addLayout(button_row)

        # Populate hidden titles list after UI is created
        self._populate_hidden_titles_list()

    def _create_general_tab(self):
        """Create the General settings tab (API Keys, ROM Directory, Processing)."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(8, 8, 8, 8)

        # API Keys Group (compact)
        api_group = QGroupBox(i18n.tr("API Keys"))
        api_layout = QFormLayout()
        api_layout.setSpacing(6)
        api_layout.setContentsMargins(10, 14, 10, 10)

        key_manager = get_manager()

        # SteamGridDB API Key
        self.sgdb_key = QLineEdit()
        self.sgdb_key.setPlaceholderText(i18n.tr("SteamGridDB API key"))
        self.sgdb_key.setEchoMode(QLineEdit.Password)
        self.sgdb_key.setMinimumHeight(36)
        current_sgdb = key_manager.get_key("steamgriddb")
        if current_sgdb:
            self.sgdb_key.setText(current_sgdb)
        sgdb_row = QHBoxLayout()
        sgdb_row.setSpacing(4)
        sgdb_row.addWidget(self.sgdb_key, 1)
        btn_sgdb_show = QPushButton(i18n.tr("Show"))
        btn_sgdb_show.setMinimumWidth(50)
        btn_sgdb_show.setMinimumHeight(36)
        btn_sgdb_show.clicked.connect(lambda: self._toggle_password_visibility(self.sgdb_key))
        sgdb_row.addWidget(btn_sgdb_show)
        api_layout.addRow(i18n.tr("SteamGridDB:"), sgdb_row)

        sgdb_help = QLabel(f'<a href="https://www.steamgriddb.com/profile/preferences/api">{i18n.tr("Get key")}</a>')
        sgdb_help.setOpenExternalLinks(True)
        sgdb_help.setObjectName("label_accent")
        api_layout.addRow("", sgdb_help)

        # IGDB API Keys (combined row)
        self.igdb_client_id = QLineEdit()
        self.igdb_client_id.setPlaceholderText(i18n.tr("IGDB Client ID"))
        self.igdb_client_id.setEchoMode(QLineEdit.Password)
        self.igdb_client_id.setMinimumHeight(36)
        current_igdb_id = key_manager.get_key("igdb_client_id")
        if current_igdb_id:
            self.igdb_client_id.setText(current_igdb_id)
        igdb_id_row = QHBoxLayout()
        igdb_id_row.setSpacing(4)
        igdb_id_row.addWidget(self.igdb_client_id, 1)
        btn_igdb_id_show = QPushButton(i18n.tr("Show"))
        btn_igdb_id_show.setMinimumWidth(50)
        btn_igdb_id_show.setMinimumHeight(36)
        btn_igdb_id_show.clicked.connect(lambda: self._toggle_password_visibility(self.igdb_client_id))
        igdb_id_row.addWidget(btn_igdb_id_show)
        api_layout.addRow(i18n.tr("IGDB ID:"), igdb_id_row)

        self.igdb_client_secret = QLineEdit()
        self.igdb_client_secret.setPlaceholderText(i18n.tr("IGDB Client Secret"))
        self.igdb_client_secret.setEchoMode(QLineEdit.Password)
        self.igdb_client_secret.setMinimumHeight(36)
        current_igdb_secret = key_manager.get_key("igdb_client_secret")
        if current_igdb_secret:
            self.igdb_client_secret.setText(current_igdb_secret)
        igdb_secret_row = QHBoxLayout()
        igdb_secret_row.setSpacing(4)
        igdb_secret_row.addWidget(self.igdb_client_secret, 1)
        btn_igdb_secret_show = QPushButton(i18n.tr("Show"))
        btn_igdb_secret_show.setMinimumWidth(50)
        btn_igdb_secret_show.setMinimumHeight(36)
        btn_igdb_secret_show.clicked.connect(lambda: self._toggle_password_visibility(self.igdb_client_secret))
        igdb_secret_row.addWidget(btn_igdb_secret_show)
        api_layout.addRow(i18n.tr("IGDB Secret:"), igdb_secret_row)

        igdb_help = QLabel(f'<a href="https://api-docs.igdb.com/#account-creation">{i18n.tr("Get credentials")}</a> · TheGamesDB: built-in')
        igdb_help.setOpenExternalLinks(True)
        igdb_help.setObjectName("label_accent")
        api_layout.addRow("", igdb_help)

        api_group.setLayout(api_layout)
        scroll_layout.addWidget(api_group)

        # ROM Directory Group (compact)
        rom_group = QGroupBox(i18n.tr("ROM Directory"))
        rom_layout = QFormLayout()
        rom_layout.setSpacing(6)
        rom_layout.setContentsMargins(10, 14, 10, 10)

        rom_path_row = QHBoxLayout()
        rom_path_row.setSpacing(4)
        self.rom_path = QLineEdit(self.rom_directory_settings.get("rom_path", ""))
        self.rom_path.setPlaceholderText(i18n.tr("Select ROM folder..."))
        self.rom_path.setMinimumHeight(36)
        rom_path_row.addWidget(self.rom_path, 1)
        btn_browse_rom = QPushButton(i18n.tr("Browse"))
        btn_browse_rom.setMinimumHeight(36)
        btn_browse_rom.clicked.connect(self._browse_rom_path)
        rom_path_row.addWidget(btn_browse_rom)
        btn_auto_detect = QPushButton(i18n.tr("Auto"))
        btn_auto_detect.setMinimumHeight(36)
        btn_auto_detect.setToolTip(i18n.tr("Auto-detect ROM folders"))
        btn_auto_detect.clicked.connect(self._auto_detect_rom_folder)
        rom_path_row.addWidget(btn_auto_detect)
        rom_layout.addRow(i18n.tr("Folder:"), rom_path_row)

        self.remember_rom_path = QCheckBox(i18n.tr("Remember selected folder"))
        self.remember_rom_path.setChecked(self.rom_directory_settings.get("remember_last_path", True))
        self.remember_rom_path.setObjectName("cb_small")
        rom_layout.addRow("", self.remember_rom_path)

        self.deep_search_checkbox = QCheckBox(i18n.tr("Deep search (scan subdirectories for games)"))
        self.deep_search_checkbox.setChecked(self.rom_directory_settings.get("deep_search", False))
        self.deep_search_checkbox.setObjectName("cb_small")
        self.deep_search_checkbox.setToolTip(i18n.tr("When enabled, scans subdirectories recursively for game folders.\nUse this if your games are organized in categories like:\nPlatform/Category/GameFolder"))
        rom_layout.addRow("", self.deep_search_checkbox)

        rom_group.setLayout(rom_layout)
        scroll_layout.addWidget(rom_group)

        # Android Apps Path Group
        android_apps_group = QGroupBox(i18n.tr("Android Apps Path"))
        android_apps_layout = QFormLayout()
        android_apps_layout.setSpacing(6)
        android_apps_layout.setContentsMargins(10, 14, 10, 10)

        android_apps_desc = QLabel(i18n.tr("Path to Android app assets for editing existing app icons"))
        android_apps_desc.setObjectName("label_muted")
        android_apps_layout.addRow(android_apps_desc)

        android_apps_row = QHBoxLayout()
        android_apps_row.setSpacing(4)
        default_android_apps_path = "/storage/emulated/0/Android/media/com.iisulauncher/iiSULauncher/assets/media/android/apps"
        self.android_apps_path = QLineEdit(self.rom_directory_settings.get("android_apps_path", default_android_apps_path))
        self.android_apps_path.setPlaceholderText(i18n.tr("Android apps asset path..."))
        self.android_apps_path.setMinimumHeight(36)
        android_apps_row.addWidget(self.android_apps_path, 1)
        btn_reset_android_apps = QPushButton(i18n.tr("Reset"))
        btn_reset_android_apps.setMinimumHeight(36)
        btn_reset_android_apps.setToolTip(i18n.tr("Reset to default iiSU Launcher path"))
        btn_reset_android_apps.clicked.connect(lambda: self.android_apps_path.setText(default_android_apps_path))
        android_apps_row.addWidget(btn_reset_android_apps)
        android_apps_layout.addRow(i18n.tr("Path:"), android_apps_row)

        android_apps_group.setLayout(android_apps_layout)
        scroll_layout.addWidget(android_apps_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    def _create_artwork_tab(self):
        """Create the Artwork settings tab (Priority, Hero, Screenshots, Logos, Fallback, Interactive)."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)

        # Source Priority Group
        source_group = QGroupBox(i18n.tr("Artwork Source Priority"))
        source_layout = QVBoxLayout()
        source_layout.setSpacing(8)

        self.source_priority = SourcePriorityWidget()
        if self.source_priority_widget_ref:
            current_order = self.source_priority_widget_ref.get_source_order()
            self.source_priority.set_source_order(current_order)

        source_layout.addWidget(QLabel(i18n.tr("Drag to reorder priority:")))
        source_layout.addWidget(self.source_priority)

        # Square only toggle for SteamGridDB
        self.square_only_toggle = QCheckBox(i18n.tr("Square images only (SteamGridDB)"))
        self.square_only_toggle.setChecked(getattr(self, 'steamgriddb_settings', {}).get("square_only", True))
        self.square_only_toggle.setToolTip(i18n.tr("Filter SteamGridDB results to only show square (1:1) images"))
        source_layout.addWidget(self.square_only_toggle)

        source_group.setLayout(source_layout)
        scroll_layout.addWidget(source_group)

        # Hero Images Group
        hero_group = QGroupBox(i18n.tr("Hero Images"))
        hero_layout = QFormLayout()
        hero_layout.setSpacing(10)

        self.hero_enabled = QCheckBox(i18n.tr("Download hero images"))
        self.hero_enabled.setChecked(self.hero_settings.get("enabled", True))
        self.hero_enabled.setToolTip(i18n.tr("Download hero/banner images from SteamGridDB"))
        hero_layout.addRow("", self.hero_enabled)

        self.hero_count = QSpinBox()
        self.hero_count.setRange(1, 5)
        self.hero_count.setValue(self.hero_settings.get("count", 1))
        hero_layout.addRow(i18n.tr("Count per game:"), self.hero_count)

        self.hero_save_with_icons = QCheckBox(i18n.tr("Save in same folder as icons"))
        self.hero_save_with_icons.setChecked(self.hero_settings.get("save_with_icons", True))
        hero_layout.addRow("", self.hero_save_with_icons)

        hero_group.setLayout(hero_layout)
        scroll_layout.addWidget(hero_group)

        # Screenshots Group
        screenshot_group = QGroupBox(i18n.tr("Screenshots"))
        screenshot_layout = QFormLayout()
        screenshot_layout.setSpacing(10)

        self.screenshot_enabled = QCheckBox(i18n.tr("Download screenshots"))
        self.screenshot_enabled.setChecked(self.screenshot_settings.get("enabled", False))
        screenshot_layout.addRow("", self.screenshot_enabled)

        self.screenshot_count = QSpinBox()
        self.screenshot_count.setRange(1, 10)
        self.screenshot_count.setValue(self.screenshot_settings.get("count", 3))
        screenshot_layout.addRow(i18n.tr("Count per game:"), self.screenshot_count)

        screenshot_group.setLayout(screenshot_layout)
        scroll_layout.addWidget(screenshot_group)

        # Logo/Title Group
        logo_group = QGroupBox(i18n.tr("Game Logos"))
        logo_layout = QFormLayout()
        logo_layout.setSpacing(10)

        self.scrape_logos = QCheckBox(i18n.tr("Download transparent game logos from SteamGridDB"))
        self.scrape_logos.setChecked(self.logo_settings.get("scrape_logos", True))
        logo_layout.addRow("", self.scrape_logos)

        self.logo_fallback_boxart = QCheckBox(i18n.tr("Use boxart as fallback when no logo is available"))
        self.logo_fallback_boxart.setChecked(self.logo_settings.get("fallback_to_boxart", True))
        logo_layout.addRow("", self.logo_fallback_boxart)

        logo_group.setLayout(logo_layout)
        scroll_layout.addWidget(logo_group)

        # Fallback Icons Group
        fallback_group = QGroupBox(i18n.tr("Fallback Icons"))
        fallback_layout = QFormLayout()
        fallback_layout.setSpacing(10)

        self.use_fallback = QCheckBox(i18n.tr("Use platform icon when artwork not found"))
        self.use_fallback.setChecked(self.fallback_settings.get("use_platform_icon_fallback", False))
        fallback_layout.addRow("", self.use_fallback)

        self.skip_scraping = QCheckBox(i18n.tr("Skip scraping - always use platform icon"))
        self.skip_scraping.setChecked(self.fallback_settings.get("skip_scraping_use_platform_icon", False))
        self.skip_scraping.toggled.connect(self._on_skip_scraping_changed)
        fallback_layout.addRow("", self.skip_scraping)

        fallback_path_row = QHBoxLayout()
        self.fallback_icons_path = QLineEdit()
        self.fallback_icons_path.setPlaceholderText(i18n.tr("Default: fallback_icons folder"))
        fallback_path_row.addWidget(self.fallback_icons_path, 1)
        btn_browse_fallback = QPushButton(i18n.tr("Browse..."))
        btn_browse_fallback.clicked.connect(self._browse_fallback_icons)
        fallback_path_row.addWidget(btn_browse_fallback)
        fallback_layout.addRow(i18n.tr("Fallback Folder:"), fallback_path_row)

        fallback_group.setLayout(fallback_layout)
        scroll_layout.addWidget(fallback_group)

        # Interactive Mode Settings Group
        interactive_group = QGroupBox(i18n.tr("Interactive Mode"))
        interactive_layout = QVBoxLayout()
        interactive_layout.setSpacing(8)

        interactive_desc = QLabel(i18n.tr("When interactive mode is enabled, you can manually select artwork for each game. Choose which asset types to enable interactive selection for:"))
        interactive_desc.setWordWrap(True)
        interactive_desc.setObjectName("label_muted")
        interactive_layout.addWidget(interactive_desc)

        # Interactive mode checkboxes for each asset type
        self.interactive_icons = QCheckBox(i18n.tr("Icons - Select from multiple icon options"))
        self.interactive_icons.setChecked(self.interactive_settings.get("icons", True))
        self.interactive_icons.setObjectName("cb_small")
        interactive_layout.addWidget(self.interactive_icons)

        self.interactive_heroes = QCheckBox(i18n.tr("Heroes - Select from SteamGridDB hero images (wide banners)"))
        self.interactive_heroes.setChecked(self.interactive_settings.get("heroes", False))
        self.interactive_heroes.setObjectName("cb_small")
        interactive_layout.addWidget(self.interactive_heroes)

        self.interactive_logos = QCheckBox(i18n.tr("Logos - Select from SteamGridDB logo images (transparent)"))
        self.interactive_logos.setChecked(self.interactive_settings.get("logos", False))
        self.interactive_logos.setObjectName("cb_small")
        interactive_layout.addWidget(self.interactive_logos)

        self.interactive_screenshots = QCheckBox(i18n.tr("Screenshots - Select from available screenshots"))
        self.interactive_screenshots.setChecked(self.interactive_settings.get("screenshots", False))
        self.interactive_screenshots.setObjectName("cb_small")
        interactive_layout.addWidget(self.interactive_screenshots)

        interactive_note = QLabel(i18n.tr("Note: Heroes and logos are sourced from SteamGridDB. Non-square images can be cropped."))
        interactive_note.setWordWrap(True)
        interactive_note.setObjectName("label_accent")
        interactive_layout.addWidget(interactive_note)

        interactive_group.setLayout(interactive_layout)
        scroll_layout.addWidget(interactive_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    def _create_output_tab(self):
        """Create the Output settings tab (Export Format, Device Copy, Borders)."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)

        # Export Format Group
        export_group = QGroupBox(i18n.tr("Export Format"))
        export_layout = QFormLayout()
        export_layout.setSpacing(10)

        self.export_format = QComboBox()
        self.export_format.addItems(["JPEG", "PNG"])
        self.export_format.setCurrentText(self.export_settings.get("format", "JPEG"))
        self.export_format.currentTextChanged.connect(self._on_export_format_changed)
        export_layout.addRow(i18n.tr("Image Format:"), self.export_format)

        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(1, 100)
        self.jpeg_quality.setValue(self.export_settings.get("jpeg_quality", 95))
        export_layout.addRow(i18n.tr("JPEG Quality:"), self.jpeg_quality)

        export_note = QLabel(i18n.tr("JPEG recommended for iiSU Launcher"))
        export_note.setObjectName("label_muted")
        export_layout.addRow(export_note)

        export_group.setLayout(export_layout)
        scroll_layout.addWidget(export_group)

        # Device Copy Group
        device_group = QGroupBox(i18n.tr("Copy to Device (ADB)"))
        device_layout = QFormLayout()
        device_layout.setSpacing(10)

        self.copy_to_device = QCheckBox(i18n.tr("Auto-copy to Android device after processing"))
        self.copy_to_device.setChecked(self.device_settings.get("enabled", False))
        device_layout.addRow("", self.copy_to_device)

        self.device_path = QLineEdit()
        self.device_path.setText(self.device_settings.get("path", "/sdcard/Android/media/com.iisulauncher/iiSULauncher/assets/media/roms/consoles"))
        device_layout.addRow(i18n.tr("Device Path:"), self.device_path)

        btn_manage_device = QPushButton(i18n.tr("Manage Device Assets..."))
        btn_manage_device.clicked.connect(self._open_device_asset_dialog)
        device_layout.addRow("", btn_manage_device)

        device_group.setLayout(device_layout)
        scroll_layout.addWidget(device_group)

        # Custom Border Group
        custom_border_group = QGroupBox(i18n.tr("Custom Borders"))
        custom_border_layout = QFormLayout()
        custom_border_layout.setSpacing(10)

        self.use_custom_border = QCheckBox(i18n.tr("Use single custom border for ALL platforms"))
        self.use_custom_border.setChecked(self.custom_border_settings.get("enabled", False))
        self.use_custom_border.toggled.connect(self._on_custom_border_toggled)
        custom_border_layout.addRow("", self.use_custom_border)

        custom_border_path_row = QHBoxLayout()
        self.custom_border_path = QLineEdit()
        self.custom_border_path.setPlaceholderText(i18n.tr("Select a custom border image..."))
        self.custom_border_path.setText(self.custom_border_settings.get("path", ""))
        custom_border_path_row.addWidget(self.custom_border_path, 1)
        self.btn_browse_custom_border = QPushButton(i18n.tr("Browse..."))
        self.btn_browse_custom_border.clicked.connect(self._browse_custom_border)
        custom_border_path_row.addWidget(self.btn_browse_custom_border)
        custom_border_layout.addRow(i18n.tr("Global Border:"), custom_border_path_row)

        # NOTE: border_preview is a custom objectName for image preview thumbnails with border
        self.custom_border_preview = QLabel()
        self.custom_border_preview.setFixedSize(96, 96)
        self.custom_border_preview.setObjectName("border_preview")
        self.custom_border_preview.setScaledContents(True)
        self._update_custom_border_preview()
        custom_border_layout.addRow(i18n.tr("Preview:"), self.custom_border_preview)

        # Per-platform borders
        per_platform_label = QLabel(f"<b>{i18n.tr('Per-Platform Borders')}</b>")
        custom_border_layout.addRow(per_platform_label)

        per_platform_row = QHBoxLayout()
        self.border_platform_combo = QComboBox()
        self.border_platform_combo.setMinimumWidth(150)
        self.border_platform_combo.currentIndexChanged.connect(self._on_border_platform_changed)
        per_platform_row.addWidget(self.border_platform_combo)

        self.per_platform_border_path = QLineEdit()
        self.per_platform_border_path.setPlaceholderText(i18n.tr("Default (uses built-in)"))
        per_platform_row.addWidget(self.per_platform_border_path, 1)

        self.btn_browse_per_platform_border = QPushButton(i18n.tr("Browse..."))
        self.btn_browse_per_platform_border.clicked.connect(self._browse_per_platform_border)
        per_platform_row.addWidget(self.btn_browse_per_platform_border)

        self.btn_clear_per_platform_border = QPushButton(i18n.tr("Clear"))
        self.btn_clear_per_platform_border.clicked.connect(self._clear_per_platform_border)
        per_platform_row.addWidget(self.btn_clear_per_platform_border)

        custom_border_layout.addRow(i18n.tr("Platform:"), per_platform_row)

        # NOTE: border_preview_small is a custom objectName for smaller image preview thumbnails
        self.per_platform_border_preview = QLabel()
        self.per_platform_border_preview.setFixedSize(64, 64)
        self.per_platform_border_preview.setObjectName("border_preview_small")
        self.per_platform_border_preview.setScaledContents(True)
        custom_border_layout.addRow("", self.per_platform_border_preview)

        custom_border_group.setLayout(custom_border_layout)
        scroll_layout.addWidget(custom_border_group)

        self._on_custom_border_toggled(self.use_custom_border.isChecked())
        self._load_platforms_for_border_selector()

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    def _create_platforms_tab(self):
        """Create the Custom Platforms settings tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)

        # Custom Platforms Group
        custom_platform_group = QGroupBox(i18n.tr("Custom Platforms"))
        custom_platform_layout = QVBoxLayout()
        custom_platform_layout.setSpacing(12)

        custom_platform_desc = QLabel(i18n.tr("Add custom platforms like Steam, older consoles, or obscure systems."))
        custom_platform_desc.setWordWrap(True)
        custom_platform_desc.setObjectName("label_muted")
        custom_platform_layout.addWidget(custom_platform_desc)

        self.custom_platforms_list = QListWidget()
        self.custom_platforms_list.setMaximumHeight(120)
        self.custom_platforms_list.itemClicked.connect(self._on_custom_platform_selected)
        custom_platform_layout.addWidget(self.custom_platforms_list)

        platform_form = QFormLayout()
        platform_form.setSpacing(8)

        self.new_platform_key = QLineEdit()
        self.new_platform_key.setPlaceholderText(i18n.tr("e.g., STEAM, ATARI_2600"))
        platform_form.addRow(i18n.tr("Platform Key:"), self.new_platform_key)

        self.new_platform_name = QLineEdit()
        self.new_platform_name.setPlaceholderText(i18n.tr("e.g., Steam, Atari 2600"))
        platform_form.addRow(i18n.tr("Display Name:"), self.new_platform_name)

        self.new_platform_publisher = QLineEdit()
        self.new_platform_publisher.setPlaceholderText(i18n.tr("e.g., Valve, Atari"))
        platform_form.addRow(i18n.tr("Publisher:"), self.new_platform_publisher)

        self.new_platform_year = QSpinBox()
        self.new_platform_year.setRange(1970, 2030)
        self.new_platform_year.setValue(2000)
        platform_form.addRow(i18n.tr("Year:"), self.new_platform_year)

        self.new_platform_type = QComboBox()
        self.new_platform_type.addItems(["console", "handheld", "pc", "arcade", "mobile", "hybrid", "other"])
        platform_form.addRow(i18n.tr("Type:"), self.new_platform_type)

        border_row = QHBoxLayout()
        self.new_platform_border = QLineEdit()
        self.new_platform_border.setPlaceholderText(i18n.tr("Select or leave blank..."))
        border_row.addWidget(self.new_platform_border, 1)
        btn_browse_platform_border = QPushButton(i18n.tr("Browse..."))
        btn_browse_platform_border.clicked.connect(self._browse_new_platform_border)
        border_row.addWidget(btn_browse_platform_border)
        platform_form.addRow(i18n.tr("Border File:"), border_row)

        icon_row = QHBoxLayout()
        self.new_platform_icon = QLineEdit()
        self.new_platform_icon.setPlaceholderText(i18n.tr("Select or leave blank..."))
        icon_row.addWidget(self.new_platform_icon, 1)
        btn_browse_platform_icon = QPushButton(i18n.tr("Browse..."))
        btn_browse_platform_icon.clicked.connect(self._browse_new_platform_icon)
        icon_row.addWidget(btn_browse_platform_icon)
        platform_form.addRow(i18n.tr("Platform Icon:"), icon_row)

        custom_platform_layout.addLayout(platform_form)

        platform_btn_row = QHBoxLayout()
        self.btn_add_platform = QPushButton(i18n.tr("Add Platform"))
        self.btn_add_platform.clicked.connect(self._add_custom_platform)
        platform_btn_row.addWidget(self.btn_add_platform)

        self.btn_remove_platform = QPushButton(i18n.tr("Remove Selected"))
        self.btn_remove_platform.clicked.connect(self._remove_custom_platform)
        platform_btn_row.addWidget(self.btn_remove_platform)

        platform_btn_row.addStretch()
        custom_platform_layout.addLayout(platform_btn_row)

        custom_platform_group.setLayout(custom_platform_layout)
        scroll_layout.addWidget(custom_platform_group)

        self._load_custom_platforms_list()

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    def _create_app_tab(self):
        """Create the App settings tab (Language, Background Music, Hidden Titles, Processing, Config File)."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(8, 8, 8, 8)

        # Language Group
        import i18n
        language_group = QGroupBox(i18n.tr("Language"))
        language_layout = QFormLayout()
        language_layout.setSpacing(6)
        language_layout.setContentsMargins(10, 14, 10, 10)

        self.language_combo = QComboBox()
        self.language_combo.setMinimumHeight(36)
        
        # Add "Auto (System)" option first
        auto_label = i18n.tr("Auto (System)")
        detected = i18n.detect_system_language()
        # Show the detected language in the dropdown
        if i18n.get_language() == "zh_CN":
            # Chinese UI: show in Chinese
            detected_name = "简体中文" if detected == "zh_CN" else "English"
        else:
            # English UI: show in English
            detected_name = "Chinese (Simplified)" if detected == "zh_CN" else "English"
        auto_label = f"{auto_label} - {detected_name}"
        self.language_combo.addItem(auto_label, "auto")
        
        # Add other languages
        available_langs = i18n.get_available_languages()
        for code, name in available_langs.items():
            if code != "auto":
                self.language_combo.addItem(name, code)
        
        # Set current language
        current_lang = i18n.get_language()
        # Check if config has explicit language or auto
        try:
            import yaml
            config_path = Path(__file__).parent / "config.yaml"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                config_lang = cfg.get("ui", {}).get("language", "auto")
            else:
                config_lang = "auto"
        except Exception:
            config_lang = "auto"
        
        if config_lang == "auto":
            idx = self.language_combo.findData("auto")
        else:
            idx = self.language_combo.findData(current_lang)
        
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        
        language_note = QLabel(i18n.tr("Restart required to apply language change"))
        language_note.setObjectName("label_muted")
        
        language_layout.addRow(i18n.tr("Language") + ":", self.language_combo)
        language_layout.addRow("", language_note)
        
        language_group.setLayout(language_layout)
        scroll_layout.addWidget(language_group)

        # Background Music Group
        music_group = QGroupBox(i18n.tr("Background Music"))
        music_layout = QVBoxLayout()
        music_layout.setSpacing(8)
        music_layout.setContentsMargins(10, 14, 10, 10)

        music_desc = QLabel(i18n.tr("Play the iiSU OST while using the app"))
        music_desc.setObjectName("label_muted")
        music_layout.addWidget(music_desc)

        # Enable music checkbox
        self.music_enabled = QCheckBox(i18n.tr("Enable Background Music"))
        music_manager = get_music_manager()
        self.music_enabled.setChecked(music_manager.is_enabled())
        self.music_enabled.toggled.connect(self._on_music_enabled_changed)
        music_layout.addWidget(self.music_enabled)

        # Volume slider row
        volume_row = QHBoxLayout()
        volume_row.setSpacing(8)
        volume_label = QLabel(i18n.tr("Volume"))
        volume_label.setMinimumWidth(50)
        volume_row.addWidget(volume_label)

        self.music_volume_slider = QSlider(Qt.Horizontal)
        self.music_volume_slider.setRange(0, 100)
        self.music_volume_slider.setValue(music_manager.get_volume())
        self.music_volume_slider.setMinimumHeight(24)
        self.music_volume_slider.valueChanged.connect(self._on_music_volume_changed)
        volume_row.addWidget(self.music_volume_slider, 1)

        self.music_volume_label = QLabel(f"{music_manager.get_volume()}%")
        self.music_volume_label.setMinimumWidth(40)
        self.music_volume_label.setObjectName("label_accent")
        volume_row.addWidget(self.music_volume_label)

        music_layout.addLayout(volume_row)

        # Music credit
        music_credit = QLabel(i18n.tr("Music by Thaddeus Silva"))
        music_credit.setObjectName("label_credit")
        music_layout.addWidget(music_credit)

        music_group.setLayout(music_layout)
        scroll_layout.addWidget(music_group)

        # Hidden Titles Group
        hidden_group = QGroupBox(i18n.tr("Hidden Titles"))
        hidden_layout = QVBoxLayout()
        hidden_layout.setSpacing(6)
        hidden_layout.setContentsMargins(10, 14, 10, 10)

        hidden_desc = QLabel(i18n.tr("Titles hidden from the library view (right-click a title → Hide)"))
        hidden_desc.setObjectName("label_muted")
        hidden_layout.addWidget(hidden_desc)

        self.hidden_titles_list = QListWidget()
        self.hidden_titles_list.setMinimumHeight(100)
        self.hidden_titles_list.setMaximumHeight(150)
        self.hidden_titles_list.setSelectionMode(QListWidget.ExtendedSelection)
        hidden_layout.addWidget(self.hidden_titles_list)

        hidden_btn_row = QHBoxLayout()
        hidden_btn_row.setSpacing(4)
        self.btn_unhide = QPushButton(i18n.tr("Unhide Selected"))
        self.btn_unhide.setMinimumHeight(32)
        self.btn_unhide.clicked.connect(self._unhide_selected_titles)
        hidden_btn_row.addWidget(self.btn_unhide)
        self.btn_clear_hidden = QPushButton(i18n.tr("Clear All"))
        self.btn_clear_hidden.setMinimumHeight(32)
        self.btn_clear_hidden.clicked.connect(self._clear_all_hidden_titles)
        hidden_btn_row.addWidget(self.btn_clear_hidden)
        hidden_btn_row.addStretch()
        hidden_layout.addLayout(hidden_btn_row)

        hidden_group.setLayout(hidden_layout)
        scroll_layout.addWidget(hidden_group)

        # Processing Group
        processing_group = QGroupBox(i18n.tr("Processing"))
        processing_layout = QFormLayout()
        processing_layout.setSpacing(6)
        processing_layout.setContentsMargins(10, 14, 10, 10)

        self.workers = QSpinBox()
        self.workers.setRange(1, 64)
        self.workers.setValue(self.workers_value)
        self.workers.setMinimumHeight(36)
        self.workers.setToolTip(i18n.tr("Number of concurrent download/processing threads"))
        processing_layout.addRow(i18n.tr("Parallel Workers:"), self.workers)

        self.limit = QSpinBox()
        self.limit.setRange(0, 2_000_000_000)
        self.limit.setValue(self.limit_value)
        self.limit.setMinimumHeight(36)
        self.limit.setToolTip(i18n.tr("Max games to process per platform (0 = unlimited)"))
        processing_layout.addRow(i18n.tr("Games per Platform Limit:"), self.limit)

        processing_note = QLabel(i18n.tr("Higher values use more memory but process faster"))
        processing_note.setObjectName("label_muted")
        processing_layout.addRow("", processing_note)

        processing_group.setLayout(processing_layout)
        scroll_layout.addWidget(processing_group)

        # Updates Group (only in frozen/packaged builds)
        import sys
        if getattr(sys, 'frozen', False):
            from app_paths import get_config
            updates_group = QGroupBox(i18n.tr("Updates"))
            updates_layout = QVBoxLayout()
            updates_layout.setSpacing(8)
            updates_layout.setContentsMargins(10, 14, 10, 10)

            updates_desc = QLabel(i18n.tr("Check for new versions of iiSU Asset Tool"))
            updates_desc.setObjectName("label_muted")
            updates_layout.addWidget(updates_desc)

            cfg = get_config()
            updater_cfg = cfg.get("updater", {})

            self.check_updates_startup = QCheckBox(i18n.tr("Check for updates on startup"))
            self.check_updates_startup.setChecked(updater_cfg.get("check_on_startup", True))
            updates_layout.addWidget(self.check_updates_startup)

            btn_check_updates = QPushButton(i18n.tr("Check for Updates Now"))
            btn_check_updates.setMinimumHeight(36)
            btn_check_updates.clicked.connect(self._manual_check_for_updates)
            updates_layout.addWidget(btn_check_updates)

            updates_group.setLayout(updates_layout)
            scroll_layout.addWidget(updates_group)

        # Config File Group
        config_group = QGroupBox(i18n.tr("Config File"))
        config_layout = QFormLayout()
        config_layout.setSpacing(6)
        config_layout.setContentsMargins(10, 14, 10, 10)

        config_row = QHBoxLayout()
        config_row.setSpacing(4)
        self.config_path = QLineEdit(self.config_path_value)
        self.config_path.setMinimumHeight(36)
        btn_browse = QPushButton(i18n.tr("Browse"))
        btn_browse.setMinimumHeight(36)
        btn_browse.clicked.connect(self._browse_config)
        config_row.addWidget(self.config_path, 1)
        config_row.addWidget(btn_browse)
        config_layout.addRow(i18n.tr("Path:"), config_row)

        config_group.setLayout(config_layout)
        scroll_layout.addWidget(config_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return tab

    # --- Helper Methods ---

    def _browse_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("Select Config File"), str(Path.home()), "YAML (*.yaml *.yml)"
        )
        if path:
            self.config_path.setText(path)

    def _toggle_password_visibility(self, line_edit: QLineEdit):
        if line_edit.echoMode() == QLineEdit.Password:
            line_edit.setEchoMode(QLineEdit.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.Password)

    def _browse_rom_path(self):
        current_path = self.rom_path.text()
        start_dir = current_path if current_path and Path(current_path).exists() else str(Path.home())
        path = QFileDialog.getExistingDirectory(self, i18n.tr("Select ROM Directory"), start_dir, QFileDialog.ShowDirsOnly)
        if path:
            self.rom_path.setText(path)

    def _auto_detect_rom_folder(self):
        QMessageBox.information(self, i18n.tr("Searching"), i18n.tr("Searching for ROM folders..."))
        found_path = find_iisu_directory()
        if found_path:
            self.rom_path.setText(str(found_path))
            QMessageBox.information(self, i18n.tr("Found"), i18n.tr("Found ROM directory at:\n{path}", path=found_path))
        else:
            QMessageBox.information(self, i18n.tr("Not Found"), i18n.tr("No ROM directories found. Use Browse to select manually."))

    def _populate_hidden_titles_list(self):
        """Populate the hidden titles list widget from self.hidden_titles."""
        self.hidden_titles_list.clear()
        for platform, titles in self.hidden_titles.items():
            for title in titles:
                item = QListWidgetItem(f"[{platform}] {title}")
                item.setData(Qt.UserRole, {"platform": platform, "title": title})
                self.hidden_titles_list.addItem(item)

    def _unhide_selected_titles(self):
        """Unhide selected titles from the list."""
        selected_items = self.hidden_titles_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            data = item.data(Qt.UserRole)
            if data:
                platform = data["platform"]
                title = data["title"]
                if platform in self.hidden_titles and title in self.hidden_titles[platform]:
                    self.hidden_titles[platform].remove(title)
                    if not self.hidden_titles[platform]:
                        del self.hidden_titles[platform]

        self._populate_hidden_titles_list()

    def _clear_all_hidden_titles(self):
        """Clear all hidden titles."""
        if not self.hidden_titles:
            return

        reply = QMessageBox.question(
            self, i18n.tr("Clear Hidden Titles"),
            i18n.tr("Are you sure you want to unhide all titles?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.hidden_titles.clear()
            self._populate_hidden_titles_list()

    def _manual_check_for_updates(self):
        """Manually check for updates from the Settings dialog."""
        from update_dialog import show_update_check
        from ui_app_with_tabs import MainWindowWithTabs
        show_update_check(MainWindowWithTabs.APP_VERSION, parent=self, silent=False)

    def _on_music_enabled_changed(self, checked: bool):
        """Handle music enabled toggle."""
        music_manager = get_music_manager()
        music_manager.set_enabled(checked)
        self.music_volume_slider.setEnabled(checked)

    def _on_music_volume_changed(self, value: int):
        """Handle music volume slider change."""
        self.music_volume_label.setText(f"{value}%")
        music_manager = get_music_manager()
        music_manager.set_volume(value)

    def _on_skip_scraping_changed(self, checked: bool):
        if checked:
            self.use_fallback.setChecked(False)
            self.use_fallback.setEnabled(False)
        else:
            self.use_fallback.setEnabled(True)

    def _browse_fallback_icons(self):
        current_path = self.fallback_icons_path.text()
        start_dir = current_path if current_path and Path(current_path).exists() else str(Path.home())
        path = QFileDialog.getExistingDirectory(self, i18n.tr("Select Fallback Icons Directory"), start_dir, QFileDialog.ShowDirsOnly)
        if path:
            self.fallback_icons_path.setText(path)

    def _on_export_format_changed(self, format_text: str):
        is_jpeg = format_text.upper() in ("JPEG", "JPG")
        self.jpeg_quality.setEnabled(is_jpeg)

    def _open_device_asset_dialog(self):
        config_path = Path(self.config_path_value) if self.config_path_value else Path(".")
        output_dir = str(config_path.parent / "output") if config_path.exists() else "./output"
        dialog = DeviceAssetDialog(parent=self, output_dir=output_dir, device_path=self.device_path.text().strip())
        dialog.exec()

    def _on_custom_border_toggled(self, checked: bool):
        self.custom_border_path.setEnabled(checked)
        self.btn_browse_custom_border.setEnabled(checked)

    def _browse_custom_border(self):
        current_path = self.custom_border_path.text()
        start_dir = current_path if current_path and Path(current_path).exists() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, i18n.tr("Select Custom Border Image"), start_dir, i18n.tr("Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"))
        if path:
            self.custom_border_path.setText(path)
            self._update_custom_border_preview()

    def _update_custom_border_preview(self):
        path = self.custom_border_path.text()
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.custom_border_preview.setPixmap(pixmap)
                return
        self.custom_border_preview.clear()

    def _load_platforms_for_border_selector(self):
        import yaml
        self.border_platform_combo.clear()
        config_path = Path(self.config_path_value) if self.config_path_value else None
        if config_path and config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                platforms = cfg.get("platforms", {})
                for platform_key in sorted(platforms.keys()):
                    self.border_platform_combo.addItem(platform_key, platform_key)
            except Exception:
                pass
        for platform_key in sorted(self.custom_platforms.keys()):
            if self.border_platform_combo.findData(platform_key) == -1:
                self.border_platform_combo.addItem(f"{platform_key} (Custom)", platform_key)

    def _on_border_platform_changed(self, index: int):
        if index < 0:
            return
        platform_key = self.border_platform_combo.currentData()
        if not platform_key:
            return
        per_platform = self.custom_border_settings.get("per_platform", {})
        border_path = per_platform.get(platform_key, "")
        self.per_platform_border_path.setText(border_path)
        self._update_per_platform_border_preview()

    def _browse_per_platform_border(self):
        current_path = self.per_platform_border_path.text()
        start_dir = current_path if current_path and Path(current_path).exists() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, i18n.tr("Select Custom Border for Platform"), start_dir, i18n.tr("Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"))
        if path:
            self.per_platform_border_path.setText(path)
            platform_key = self.border_platform_combo.currentData()
            if platform_key:
                if "per_platform" not in self.custom_border_settings:
                    self.custom_border_settings["per_platform"] = {}
                self.custom_border_settings["per_platform"][platform_key] = path
            self._update_per_platform_border_preview()

    def _clear_per_platform_border(self):
        platform_key = self.border_platform_combo.currentData()
        if platform_key:
            per_platform = self.custom_border_settings.get("per_platform", {})
            if platform_key in per_platform:
                del per_platform[platform_key]
            self.per_platform_border_path.clear()
            self._update_per_platform_border_preview()

    def _update_per_platform_border_preview(self):
        path = self.per_platform_border_path.text()
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.per_platform_border_preview.setPixmap(pixmap)
                return
        self.per_platform_border_preview.clear()

    def _load_custom_platforms_list(self):
        self.custom_platforms_list.clear()
        for platform_key, config in self.custom_platforms.items():
            display_name = config.get("display_name", platform_key)
            publisher = config.get("publisher", "")
            year = config.get("year", "")
            item_text = f"{platform_key} - {display_name}"
            if publisher:
                item_text += f" ({publisher}"
                if year:
                    item_text += f", {year}"
                item_text += ")"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, platform_key)
            self.custom_platforms_list.addItem(item)

    def _on_custom_platform_selected(self, item):
        platform_key = item.data(Qt.UserRole)
        if platform_key and platform_key in self.custom_platforms:
            config = self.custom_platforms[platform_key]
            self.new_platform_key.setText(platform_key)
            self.new_platform_name.setText(config.get("display_name", ""))
            self.new_platform_publisher.setText(config.get("publisher", ""))
            self.new_platform_year.setValue(config.get("year", 2000))
            type_idx = self.new_platform_type.findText(config.get("type", "console"))
            if type_idx >= 0:
                self.new_platform_type.setCurrentIndex(type_idx)
            self.new_platform_border.setText(config.get("border_file", ""))
            self.new_platform_icon.setText(config.get("icon_file", ""))

    def _browse_new_platform_border(self):
        path, _ = QFileDialog.getOpenFileName(self, i18n.tr("Select Border Image"), str(Path.home()), i18n.tr("Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"))
        if path:
            self.new_platform_border.setText(path)

    def _browse_new_platform_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, i18n.tr("Select Platform Icon"), str(Path.home()), i18n.tr("Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"))
        if path:
            self.new_platform_icon.setText(path)

    def _add_custom_platform(self):
        platform_key = self.new_platform_key.text().strip().upper().replace(" ", "_")
        if not platform_key:
            QMessageBox.warning(self, i18n.tr("Error"), i18n.tr("Platform key is required."))
            return
        display_name = self.new_platform_name.text().strip() or platform_key
        self.custom_platforms[platform_key] = {
            "display_name": display_name,
            "publisher": self.new_platform_publisher.text().strip(),
            "year": self.new_platform_year.value(),
            "type": self.new_platform_type.currentText(),
            "border_file": self.new_platform_border.text().strip(),
            "icon_file": self.new_platform_icon.text().strip(),
            "custom": True
        }
        self._load_custom_platforms_list()
        self._load_platforms_for_border_selector()
        self.new_platform_key.clear()
        self.new_platform_name.clear()
        self.new_platform_publisher.clear()
        self.new_platform_year.setValue(2000)
        self.new_platform_type.setCurrentIndex(0)
        self.new_platform_border.clear()
        self.new_platform_icon.clear()
        QMessageBox.information(self, i18n.tr("Success"), i18n.tr("Platform '{key}' added.", key=platform_key))

    def _remove_custom_platform(self):
        current_item = self.custom_platforms_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, i18n.tr("Error"), i18n.tr("Select a platform to remove."))
            return
        platform_key = current_item.data(Qt.UserRole)
        if platform_key and platform_key in self.custom_platforms:
            reply = QMessageBox.question(self, i18n.tr("Confirm"), i18n.tr("Remove platform '{key}'?", key=platform_key), QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.custom_platforms[platform_key]
                self._load_custom_platforms_list()
                self._load_platforms_for_border_selector()

    def _apply_and_accept(self):
        """Save API keys, music settings, updater settings, language, and accept dialog."""
        key_manager = get_manager()
        key_manager.set_key("steamgriddb", self.sgdb_key.text().strip())
        key_manager.set_key("igdb_client_id", self.igdb_client_id.text().strip())
        key_manager.set_key("igdb_client_secret", self.igdb_client_secret.text().strip())

        # Save music volume setting
        music_manager = get_music_manager()
        music_manager.save_volume()

        # Save language setting
        if hasattr(self, 'language_combo'):
            try:
                import yaml
                import i18n
                from app_paths import get_config_path, invalidate_config_cache
                selected_lang = self.language_combo.currentData()
                cfg_path = Path(get_config_path())
                if cfg_path.exists():
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    if "ui" not in cfg:
                        cfg["ui"] = {}
                    cfg["ui"]["language"] = selected_lang
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
                    invalidate_config_cache()
                    # Update current session language
                    # If "auto", detect system language; otherwise use selected
                    if selected_lang == "auto":
                        i18n.set_language(i18n.detect_system_language())
                    else:
                        i18n.set_language(selected_lang)
            except Exception as e:
                print(f"Failed to save language settings: {e}")

        # Save updater preference (frozen builds only)
        import sys
        if getattr(sys, 'frozen', False) and hasattr(self, 'check_updates_startup'):
            try:
                import yaml
                from app_paths import get_config_path, invalidate_config_cache
                cfg_path = Path(get_config_path())
                if cfg_path.exists():
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    if "updater" not in cfg:
                        cfg["updater"] = {}
                    cfg["updater"]["check_on_startup"] = self.check_updates_startup.isChecked()
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
                    invalidate_config_cache()
            except Exception as e:
                print(f"Failed to save updater settings: {e}")

        self.accept()

    # --- Getter Methods ---

    def get_config_path(self):
        return self.config_path.text()

    def get_workers(self):
        return self.workers.value()

    def get_limit(self):
        return self.limit.value()

    def get_source_order(self):
        return self.source_priority.get_source_order()

    def get_rom_directory_settings(self):
        rom_path = self.rom_path.text().strip()
        return {
            "mode": "manual" if not rom_path else "remembered",
            "rom_path": rom_path,
            "auto_detect": False,
            "remember_last_path": self.remember_rom_path.isChecked(),
            "deep_search": self.deep_search_checkbox.isChecked(),
            "android_apps_path": self.android_apps_path.text().strip()
        }

    def get_hero_settings(self):
        return {
            "enabled": self.hero_enabled.isChecked(),
            "count": self.hero_count.value(),
            "save_with_icons": self.hero_save_with_icons.isChecked()
        }

    def get_fallback_settings(self):
        return {
            "use_platform_icon_fallback": self.use_fallback.isChecked(),
            "skip_scraping_use_platform_icon": self.skip_scraping.isChecked(),
            "fallback_icons_path": self.fallback_icons_path.text().strip()
        }

    def get_screenshot_settings(self):
        return {
            "enabled": self.screenshot_enabled.isChecked(),
            "count": self.screenshot_count.value()
        }

    def get_device_settings(self):
        return {
            "enabled": self.copy_to_device.isChecked(),
            "path": self.device_path.text().strip()
        }

    def get_logo_settings(self):
        return {
            "scrape_logos": self.scrape_logos.isChecked(),
            "fallback_to_boxart": self.logo_fallback_boxart.isChecked()
        }

    def get_export_settings(self):
        return {
            "format": self.export_format.currentText(),
            "jpeg_quality": self.jpeg_quality.value()
        }

    def get_custom_border_settings(self):
        per_platform = dict(self.custom_border_settings.get("per_platform", {}))
        return {
            "enabled": self.use_custom_border.isChecked(),
            "path": self.custom_border_path.text().strip(),
            "per_platform": per_platform
        }

    def get_custom_platforms(self):
        return dict(self.custom_platforms)

    # --- Setter Methods ---

    def set_fallback_settings(self, settings: dict):
        self.fallback_settings = settings
        self.use_fallback.setChecked(settings.get("use_platform_icon_fallback", False))
        self.skip_scraping.setChecked(settings.get("skip_scraping_use_platform_icon", False))
        self.fallback_icons_path.setText(settings.get("fallback_icons_path", ""))

    def set_screenshot_settings(self, settings: dict):
        self.screenshot_settings = settings
        self.screenshot_enabled.setChecked(settings.get("enabled", False))
        self.screenshot_count.setValue(settings.get("count", 3))

    def set_device_settings(self, settings: dict):
        self.device_settings = settings
        self.copy_to_device.setChecked(settings.get("enabled", False))
        self.device_path.setText(settings.get("path", "/sdcard/Android/media/com.iisulauncher/iiSULauncher/assets/media/roms/consoles"))

    def set_logo_settings(self, settings: dict):
        self.logo_settings = settings
        self.scrape_logos.setChecked(settings.get("scrape_logos", True))
        self.logo_fallback_boxart.setChecked(settings.get("fallback_to_boxart", True))

    def set_export_settings(self, settings: dict):
        self.export_settings = settings
        self.export_format.setCurrentText(settings.get("format", "JPEG"))
        self.jpeg_quality.setValue(settings.get("jpeg_quality", 95))
        self._on_export_format_changed(self.export_format.currentText())

    def set_custom_border_settings(self, settings: dict):
        self.custom_border_settings = settings
        self.use_custom_border.setChecked(settings.get("enabled", False))
        self.custom_border_path.setText(settings.get("path", ""))
        self._update_custom_border_preview()
        self._on_custom_border_toggled(self.use_custom_border.isChecked())
        if hasattr(self, 'border_platform_combo') and self.border_platform_combo.count() > 0:
            self._on_border_platform_changed(self.border_platform_combo.currentIndex())

    def set_custom_platforms(self, platforms: dict):
        self.custom_platforms = dict(platforms) if platforms else {}
        if hasattr(self, 'custom_platforms_list'):
            self._load_custom_platforms_list()
        if hasattr(self, 'border_platform_combo'):
            self._load_platforms_for_border_selector()

    def set_hero_settings(self, settings: dict):
        self.hero_settings = settings
        self.hero_enabled.setChecked(settings.get("enabled", True))
        self.hero_count.setValue(settings.get("count", 1))
        self.hero_save_with_icons.setChecked(settings.get("save_with_icons", True))

    def set_steamgriddb_settings(self, settings: dict):
        """Set SteamGridDB-specific settings (placeholder for compatibility)."""
        # This method exists for API compatibility with icon_generator_tab.py
        # The actual SteamGridDB API key is handled separately via the API Keys section
        self.steamgriddb_settings = settings
        # Update square_only toggle if it exists
        if hasattr(self, 'square_only_toggle'):
            self.square_only_toggle.setChecked(settings.get("square_only", True))

    def set_interactive_settings(self, settings: dict):
        """Set interactive mode settings and update UI checkboxes."""
        self.interactive_settings = settings if settings else {}
        # Update checkboxes if they exist
        if hasattr(self, 'interactive_icons'):
            self.interactive_icons.setChecked(self.interactive_settings.get("icons", True))
        if hasattr(self, 'interactive_heroes'):
            self.interactive_heroes.setChecked(self.interactive_settings.get("heroes", False))
        if hasattr(self, 'interactive_logos'):
            self.interactive_logos.setChecked(self.interactive_settings.get("logos", False))
        if hasattr(self, 'interactive_screenshots'):
            self.interactive_screenshots.setChecked(self.interactive_settings.get("screenshots", False))

    def get_interactive_settings(self) -> dict:
        """Get interactive mode settings from UI checkboxes."""
        settings = {}
        if hasattr(self, 'interactive_icons'):
            settings["icons"] = self.interactive_icons.isChecked()
        if hasattr(self, 'interactive_heroes'):
            settings["heroes"] = self.interactive_heroes.isChecked()
        if hasattr(self, 'interactive_logos'):
            settings["logos"] = self.interactive_logos.isChecked()
        if hasattr(self, 'interactive_screenshots'):
            settings["screenshots"] = self.interactive_screenshots.isChecked()
        return settings if settings else getattr(self, 'interactive_settings', {})

    def get_steamgriddb_settings(self) -> dict:
        """Get SteamGridDB settings including square_only."""
        settings = getattr(self, 'steamgriddb_settings', {})
        # Update square_only from toggle if it exists
        if hasattr(self, 'square_only_toggle'):
            settings['square_only'] = self.square_only_toggle.isChecked()
        return settings

    def set_hidden_titles(self, hidden_titles: dict):
        """Set hidden titles from config."""
        self.hidden_titles = hidden_titles if hidden_titles else {}
        if hasattr(self, 'hidden_titles_list'):
            self._populate_hidden_titles_list()

    def get_hidden_titles(self) -> dict:
        """Get hidden titles dict."""
        return getattr(self, 'hidden_titles', {})
