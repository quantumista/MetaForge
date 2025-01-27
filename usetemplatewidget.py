# This Python file uses the following encoding: utf-8
import shutil
from typing import List

from uploader import Uploader
import json
from datetime import datetime
from pathlib import Path

from PySide2.QtWidgets import QMainWindow, QFileDialog, QProgressDialog, QDialog, QWidget
from PySide2.QtCore import QFile, QDir, Qt, QStandardPaths, QSortFilterProxyModel, Signal, QThread, QModelIndex, QEvent
from PySide2.QtGui import QCursor
import PySide2.QtCore

from ezmodel.ezmetadataentry import EzMetadataEntry
from ezmodel.ezmetadatamodel import EzMetadataModel, TemplateModel
from hyperthoughtdialogimpl import HyperthoughtDialogImpl
from qeztablemodel import QEzTableModel
from uselistmodel import ListModel
from trashdelegate import TrashDelegate
from quseeztablemodel import QUseEzTableModel
from usefiledelegate import UseFileDelegate
from metaforgestyledatahelper import MetaForgeStyleDataHelper
from available_parsers_model import AvailableParsersModel
import widget_utilities as widget_utils

from ht_requests.ht_requests import ht_utilities
from ht_requests.ht_requests import htauthcontroller
from ht_requests.ht_requests import ht_requests

qt_version = PySide2.QtCore.__version_info__
if qt_version[1] == 12:
    from generated_5_12.ui_usetemplatewidget import Ui_UseTemplateWidget
elif qt_version[1] == 15:
    from generated_5_15.ui_usetemplatewidget import Ui_UseTemplateWidget


class UseTemplateWidget(QWidget):
    K_MODEL_JSON_FILE_NAME = '.model.json'
    K_MODEL_KEY_NAME = 'model'
    K_FILELIST_KEY_NAME = 'file_list'
    K_TEMPLATEFILE_KEY_NAME = 'template_file'
    K_FILETOEXTRACT_KEY_NAME = 'file_to_extract'
    K_MISSINGENTRIES_KEY_NAME = 'missing_entries'
    K_METADATAFILECHOSEN_KEY_NAME = 'metadata_file_chosen'
    K_NO_ERRORS = "No errors."

    createUpload = Signal(list, htauthcontroller.HTAuthorizationController, str, str, list)
    
    def __init__(self, parent):
        super(UseTemplateWidget, self).__init__(parent)
        
        self.style_sheet_helper: MetaForgeStyleDataHelper = MetaForgeStyleDataHelper(self)
        self.ui = Ui_UseTemplateWidget()
        self.ui.setupUi(self)
        self.available_parsers_model = None
        self.hyperthoughtui = HyperthoughtDialogImpl()
        self.ui.hyperthoughtTemplateSelect.clicked.connect(self.select_template)
        self.ui.otherDataFileSelect.clicked.connect(self.load_other_data_file)
        self.ui.hyperthoughtUploadButton.clicked.connect(self.upload_to_hyperthought)
        self.ui.clearUseButton.clicked.connect(self.clear)
        self.hyperthoughtui.currentTokenExpired.connect(lambda:  self.ui.hyperThoughtExpiresIn.setText(self.hyperthoughtui.K_EXPIRED_STR))
        self.setAcceptDrops(True)

        widget_utils.notify_no_errors(self.ui.error_label)

        # Setup the blank Use Template table
        self.setup_metadata_table()

        # Setup the blank Use Template file list
        self.setup_file_upload_list()

        self.ui.addUploadFilesBtn.clicked.connect(self.add_upload_files)
        self.ui.clearUploadFilesBtn.clicked.connect(self.clear_upload_files)
        self.ui.removeUseTableRowButton.clicked.connect(self.remove_model_entry)
        self.ui.appendUseTableRowButton.clicked.connect(self.add_metadata_table_row)
        self.ui.hyperthoughtLocationButton.clicked.connect(self.authenticate_to_hyperthought)
    
        self.ui.useTemplateListSearchBar.textChanged.connect(self.filter_metadata_table)
        self.ui.addMetadataFileCheckBox.stateChanged.connect(self.check_file_list)

        self.fileType = ""
        self.accessKey = ""
        self.folderuuid = ""
        self.mThread = QThread()
        self.uploader = Uploader()
        self.uploader.moveToThread(self.mThread)
        self.mThread.start()

        self.createUpload.connect(self.uploader.performUpload)
        self.hyperthoughtui.apiSubmitted.connect(self.accept_key)
        self.ui.hyperthoughtTemplateLineEdit.installEventFilter(self)
        self.ui.otherDataFileLineEdit.installEventFilter(self)

    def setup_metadata_table(self, metadata_model: EzMetadataModel = EzMetadataModel()):
        self.usetrashDelegate = TrashDelegate(stylehelper=self.style_sheet_helper)
        self.use_ez_table_model = QEzTableModel(metadata_model, parent=self)
        self.use_ez_table_model_proxy = self.init_table_model_proxy(self.use_ez_table_model)
        self.ui.useTemplateTableView.setModel(self.use_ez_table_model_proxy)
        self.filter_metadata_table()
        self.ui.useTemplateTableView.setItemDelegateForColumn(self.use_ez_table_model_proxy.K_REMOVE_COL_INDEX, self.usetrashDelegate)
        self.usetrashDelegate.pressed.connect(self.remove_model_entry)
        self.polish_metadata_table()

    def polish_metadata_table(self):
        self.ui.useTemplateTableView.resizeColumnsToContents()
        self.ui.useTemplateTableView.setColumnWidth(self.use_ez_table_model.K_HTANNOTATION_COL_INDEX, self.width() * .1)
        self.ui.useTemplateTableView.setColumnWidth(self.use_ez_table_model.K_HTUNITS_COL_INDEX, self.width() * .1)
        self.ui.useTemplateTableView.horizontalHeader().setStretchLastSection(True)
    
    def setup_file_upload_list(self, file_list: list = []):
        self.uselistmodel = ListModel(file_list, self)
        self.ui.useTemplateListView.setModel(self.uselistmodel)
        self.uselistmodel.rowRemoved.connect(self.toggle_buttons)
        self.uselistmodel.rowAdded.connect(self.toggle_buttons)

        self.useFileDelegate = UseFileDelegate(self, stylehelper=self.style_sheet_helper)
        self.ui.useTemplateListView.setItemDelegate(self.useFileDelegate)

        self.ui.useTemplateListView.clicked.connect(
            self.removeRowfromUsefileType)
    
    def closeEvent(self, event):
        self.mThread.quit()
        self.mThread.wait(250)

        super().closeEvent(event)

    def clear(self):
        self.ui.hyperthoughtTemplateLineEdit.setText("")
        self.ui.otherDataFileLineEdit.setText("")
        self.ui.useTemplateListSearchBar.setText("")
        self.ui.addMetadataFileCheckBox.setChecked(True)
        self.setup_metadata_table()
        self.clear_upload_files()

    def accept_key(self, apikey):
        self.accessKey = apikey

    def add_upload_files(self):
        linetexts = QFileDialog.getOpenFileNames(self, self.tr("Select File"), QStandardPaths.displayName(
            QStandardPaths.HomeLocation), self.tr("Files (*.ctf *.xml *.ang *.tif *.tiff *.ini)"))[0]
        for line in linetexts:
            self.uselistmodel.addRow(Path(line))
        self.toggle_buttons()

    def clear_upload_files(self):
        self.uselistmodel.removeAllRows()

    def add_metadata_table_row(self):
        self.use_ez_table_model.addCustomRow(1)

    def check_file_list(self, checked):
        if checked == Qt.Checked:
          if self.ui.otherDataFileLineEdit.text() != "":
              self.uselistmodel.addRow(Path(self.ui.otherDataFileLineEdit.text()))
        elif checked == Qt.Unchecked:
            path = Path(self.ui.otherDataFileLineEdit.text())
            if path in self.uselistmodel.metadataList:
                rowIndex = self.uselistmodel.metadataList.index(path)
                self.uselistmodel.removeRow(rowIndex)

    def eventFilter(self, object, event):
        if object == self.ui.hyperthoughtTemplateLineEdit:
            if event.type() == QEvent.DragEnter:
                if str(event.mimeData().urls()[0])[-5:-2] == ".ez":
                    event.acceptProposedAction()
            if (event.type() == QEvent.Drop):
                if str(event.mimeData().urls()[0])[-5:-2] == ".ez":
                    event.acceptProposedAction()
                    self.ui.hyperthoughtTemplateLineEdit.setText(event.mimeData().urls()[0].toLocalFile())
                    self.load_template_file()
        if object == self.ui.otherDataFileLineEdit:
            if event.type() == QEvent.DragEnter:
                event.acceptProposedAction()
            if (event.type() == QEvent.Drop):
                event.acceptProposedAction()
                self.ui.otherDataFileLineEdit.setText(event.mimeData().urls()[0].toLocalFile())
                self.import_metadata_from_data_file()          

        return QMainWindow.eventFilter(self, object,  event)

    def filter_metadata_table(self):
        proxy = self.use_ez_table_model_proxy
        text = self.ui.useTemplateListSearchBar.text()
        self.filter_proxy(proxy, text)

    def filter_proxy(self, proxy_model: QSortFilterProxyModel, filter_text: str):
        proxy_model.invalidate()
        proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy_model.setFilterWildcard(f'*{filter_text}*')

    def remove_model_entry(self, source_row = -1):
        if source_row != -1:
            entry = self.use_ez_table_model.metadata_model.entry(source_row)
            if entry is not None and entry.source_type is EzMetadataEntry.SourceType.CUSTOM:
                self.use_ez_table_model.beginRemoveRows(QModelIndex(), source_row, source_row)
                self.use_ez_table_model.metadata_model.remove_by_index(source_row)
                self.use_ez_table_model.endRemoveRows()
            elif entry is not None and entry.source_type is EzMetadataEntry.SourceType.FILE:
                entry.enabled = False
        else:
            proxy_selected_rows = reversed(self.ui.useTemplateTableView.selectionModel().selectedRows())
            source_row = -1
            for index in proxy_selected_rows:
                source_row = (index.model().mapToSource(index)).row()
                entry = self.use_ez_table_model.metadata_model.entry(source_row)
                if entry is not None and entry.source_type is EzMetadataEntry.SourceType.CUSTOM:
                    self.use_ez_table_model.beginRemoveRows(QModelIndex(), source_row, source_row)
                    self.use_ez_table_model.metadata_model.remove_by_index(source_row)
                    self.use_ez_table_model.endRemoveRows()
                elif entry is not None and entry.source_type is EzMetadataEntry.SourceType.FILE:
                    entry.enabled = False
        
        self.use_ez_table_model_proxy.invalidate()
        index0 = self.use_ez_table_model_proxy.index(0, 0)
        index1 = self.use_ez_table_model_proxy.index(self.use_ez_table_model_proxy.rowCount() - 1, self.use_ez_table_model_proxy.K_COL_COUNT)
        self.use_ez_table_model_proxy.dataChanged.emit(index0, index1)
        # This toggle is for macOS Catalina to actual visually show the updated checkboxes.
        self.ui.useTemplateTableView.setVisible(False)
        self.ui.useTemplateTableView.setVisible(True)
        self.ui.useTemplateTableView.update()
        # End stupid macOS Catalina workaround.

    def open_package(self, pkgpath: Path):
        # Load model
        model_input_path = pkgpath / self.K_MODEL_JSON_FILE_NAME

        with model_input_path.open('r') as infile:
            model_dict = json.load(infile)

            metadata_model = EzMetadataModel.from_dict(model_dict[self.K_MODEL_KEY_NAME])
            self.setup_metadata_table(metadata_model=metadata_model)

            # Load file list
            upload_file_paths = model_dict[self.K_FILELIST_KEY_NAME]
            for file_path in upload_file_paths:
                self.uselistmodel.metadataList.append(Path(file_path))
            
            index0 = self.uselistmodel.index(0, 0)
            index1 = self.uselistmodel.index(len(self.uselistmodel.metadataList) - 1, 0)
            self.uselistmodel.dataChanged.emit(index0, index1)

            # Load template file
            template_file_path = model_dict[self.K_TEMPLATEFILE_KEY_NAME]
            self.ui.hyperthoughtTemplateLineEdit.setText(template_file_path)

            # Load file to extract metadata from
            extraction_file_path = model_dict[self.K_FILETOEXTRACT_KEY_NAME]
            self.ui.otherDataFileLineEdit.setText(extraction_file_path)
        
            # Load missing entries and metadata_file_chosen boolean
            missing_entry_srcs = model_dict[self.K_MISSINGENTRIES_KEY_NAME]
            metadata_model = self.use_ez_table_model.metadata_model
            missing_entries = []
            for missing_entry_src in missing_entry_srcs:
                metadata_entry = metadata_model.entry_by_source(missing_entry_src)
                missing_entries.append(metadata_entry)
            self.use_ez_table_model_proxy.missing_entries = missing_entries
            self.use_ez_table_model_proxy.metadata_file_chosen = model_dict[self.K_METADATAFILECHOSEN_KEY_NAME]

        self.use_ez_table_model_proxy.invalidate()
    
    def init_table_model_proxy(self, source_model: QEzTableModel) -> QUseEzTableModel:
        proxy = QUseEzTableModel(self)
        proxy.setSourceModel(source_model)
        proxy.setFilterKeyColumn(1)
        proxy.setDynamicSortFilter(True)
        return proxy

    def removeRowfromUsefileType(self, index):
        if self.ui.useTemplateListView.width() - 64 < self.ui.useTemplateListView.mapFromGlobal(QCursor.pos()).x():
            # this is where to remove the row
            self.uselistmodel.removeRow(index.row())

    def save_package(self, pkgpath: Path):
        # Create package
        if pkgpath.exists():
            shutil.rmtree(str(pkgpath))
            
        pkgpath.mkdir(parents=True)

        # Copy file list to package
        newfilepaths: List[str] = []
        for filepath in self.uselistmodel.metadataList:
            filename = filepath.name
            newfilepath = pkgpath / filename
            newfilepaths.append(str(newfilepath))
            QFile.copy(str(filepath), str(newfilepath))
        
        # Copy template file to package
        template_file_path = self.ui.hyperthoughtTemplateLineEdit.text()
        if template_file_path != "":
            template_file_path = Path(template_file_path)
            template_file_name = template_file_path.name
            new_template_file_path = pkgpath / template_file_name
            QFile.copy(str(template_file_path), str(new_template_file_path))

        # Copy "file to extract metadata from" to package
        extraction_file_path = self.ui.otherDataFileLineEdit.text()
        if extraction_file_path != "":
            extraction_file_path = Path(extraction_file_path)
            extraction_file_name = extraction_file_path.name
            new_extraction_file_path = pkgpath / extraction_file_name
            QFile.copy(str(extraction_file_path), str(new_extraction_file_path))

        # Save model, file list, template file, file_to_extract,
        # metadata_file_chosen, and missing_entries to json file
        model_dict = {}
        model_dict[self.K_MODEL_KEY_NAME] = self.use_ez_table_model.metadata_model.to_dict()

        model_dict[self.K_FILELIST_KEY_NAME] = newfilepaths
        model_dict[self.K_TEMPLATEFILE_KEY_NAME] = str(new_template_file_path)
        model_dict[self.K_FILETOEXTRACT_KEY_NAME] = str(new_extraction_file_path)
        model_dict[self.K_METADATAFILECHOSEN_KEY_NAME] = self.use_ez_table_model_proxy.metadata_file_chosen
        missing_entries: List[str] = []
        for missing_entry in self.use_ez_table_model_proxy.missing_entries:
            missing_entries.append(missing_entry.source_path)
        model_dict[self.K_MISSINGENTRIES_KEY_NAME] = missing_entries
        paths_output_path = pkgpath / self.K_MODEL_JSON_FILE_NAME
        with paths_output_path.open('w') as outfile:
            json.dump(model_dict, outfile, indent=4)

    def select_template(self):
        startLocation = self.ui.hyperthoughtTemplateLineEdit.text()
        if startLocation == "":
            startLocation = QStandardPaths.writableLocation(
                QStandardPaths.HomeLocation)

        templateFilePath = QFileDialog.getOpenFileName(self, self.tr(
            "Select File"), startLocation, self.tr("Files (*.ez)"))[0]

        self.ui.hyperthoughtTemplateLineEdit.setText(templateFilePath)
        self.load_template_file()

    def load_template_file(self):
        templateFilePath = self.ui.hyperthoughtTemplateLineEdit.text()

        if templateFilePath == "":
            return False

        # Load the EzMetadataModel from the json file (Template file)
        metadata_model = EzMetadataModel.from_json_file(templateFilePath)
        self.setup_metadata_table(metadata_model)
        self.currentTemplate = Path(templateFilePath).name
        self.update_metadata_table_model()
        self.polish_metadata_table()

    def load_other_data_file(self):
        datafile_input_path = QFileDialog.getOpenFileName(self, self.tr("Select File"), QStandardPaths.displayName(
                QStandardPaths.HomeLocation), self.tr("Files (*"+self.fileType+")"))[0]
        if datafile_input_path != "":
            self.ui.otherDataFileLineEdit.setText(datafile_input_path)
            self.import_metadata_from_data_file()

    def import_metadata_from_data_file(self):
        filePath = Path(self.ui.otherDataFileLineEdit.text())
        self.setWindowTitle(str(filePath))

        if self.ui.addMetadataFileCheckBox.checkState() == Qt.Checked:
            self.uselistmodel.removeAllRows()
            self.uselistmodel.addRow(filePath)
            self.toggle_buttons()
        self.update_metadata_table_model()


    def update_metadata_table_model(self):
        templateFilePath = self.ui.hyperthoughtTemplateLineEdit.text()
        file_path = self.ui.otherDataFileLineEdit.text()

        if file_path == "" or templateFilePath == "":
            self.use_ez_table_model_proxy.metadata_file_chosen = False
            index0 = self.use_ez_table_model.index(0, 0)
            index1 = self.use_ez_table_model.index(self.use_ez_table_model.rowCount() - 1, QEzTableModel.K_COL_COUNT)
            self.use_ez_table_model.dataChanged.emit(index0, index1)
            return
        
        file_path = Path(file_path)
        templateFilePath = Path(templateFilePath)
        
        # Load the dictionary from the newly inserted datafile
        parser_index, parser = self.available_parsers_model.find_compatible_parser(file_path)
        if (parser is None):
            widget_utils.notify_error_message(self.ui.error_label, f"No parser available for selected file '{file_path}'.")
        headerDict = parser.parse_header_as_dict(file_path)

        self.use_ez_table_model_proxy.missing_entries = self.use_ez_table_model.metadata_model.update_model_values_from_dict(headerDict)
        self.use_ez_table_model_proxy.metadata_file_chosen = True

        index0 = self.use_ez_table_model_proxy.index(0, 0)
        index1 = self.use_ez_table_model_proxy.index(self.use_ez_table_model_proxy.rowCount() - 1, QUseEzTableModel.K_COL_COUNT)
        self.use_ez_table_model_proxy.dataChanged.emit(index0, index1)

    def toggle_buttons(self):
        if (self.ui.hyperthoughtTemplateLineEdit.text() != "" and
            self.ui.useTemplateListView.model().rowCount() > 0 and
                self.ui.hyperThoughtUploadPath.text() != ""):

            self.ui.hyperthoughtUploadButton.setEnabled(True)

    def upload_to_hyperthought(self):
        auth_control = htauthcontroller.HTAuthorizationController(self.accessKey)

        metadataJson = ht_utilities.ezmodel_to_ht_metadata(self.use_ez_table_model.metadata_model,
                                                           self.use_ez_table_model_proxy.missing_entries,
                                                           self.use_ez_table_model_proxy.metadata_file_chosen)
        progress = QProgressDialog("Uploading files...", "Abort Upload", 0, len(
            self.uselistmodel.metadataList), self)

        progress.setWindowFlags(
            Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        progress.setAttribute(Qt.WA_DeleteOnClose)
        self.createUpload.emit(self.uselistmodel.metadataList, 
                    auth_control, 
                    self.chosen_ht_workspace["id"],
                    self.chosen_ht_folder['path'] + self.chosen_ht_folder['pk'] + ',',
                    metadataJson)
        self.uploader.notifyProgress.connect(progress.setValue)
        self.uploader.currentlyUploading.connect(progress.setLabelText)
        self.uploader.allUploadsDone.connect(progress.accept)
        progress.canceled.connect(lambda: self.uploader.interruptUpload())
        progress.setFixedSize(500, 100)
        progress.exec()

    def authenticate_to_hyperthought(self):
        ret = self.hyperthoughtui.exec()
        if ret == int(QDialog.Accepted):
            self.chosen_ht_workspace = self.hyperthoughtui.get_workspace()
            self.chosen_ht_folder = self.hyperthoughtui.get_chosen_folder()
            self.ui.hyperThoughtUploadPath.setText(self.chosen_ht_folder['path_string'])
            self.toggle_buttons()

            htUrl = self.hyperthoughtui.ui.ht_server_url.text()
            if htUrl == "":
                self.ui.hyperThoughtServer.setText("https://hyperthought.url")
            else:
                self.ui.hyperThoughtServer.setText(htUrl)
                self.ui.hyperThoughtProject.setText(self.chosen_ht_workspace["name"])
        
        if self.hyperthoughtui.authcontrol is not None:
            try:
                datetime_obj = datetime.strptime(self.hyperthoughtui.authcontrol.expires_at, '%Y-%m-%dT%X.%f%z')
            except ValueError:
                datetime_obj = datetime.strptime(self.hyperthoughtui.authcontrol.expires_at, '%Y-%m-%dT%H:%M:%S%z')
            expires_at = datetime_obj.strftime("%m/%d/%Y %I:%M:%S %p")
            self.ui.hyperThoughtExpiresIn.setText(expires_at)
    
    def set_parsers_model(self, model: AvailableParsersModel):
        self.available_parsers_model = model