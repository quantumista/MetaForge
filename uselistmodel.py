from PySide2.QtCore import QAbstractListModel, Qt, QModelIndex, QFileInfo, Signal
from typing import List
from pathlib import Path

class ListModel(QAbstractListModel):
    rowAdded = Signal()
    rowRemoved = Signal()
    def __init__(self, fileList, parent=None):
        QAbstractListModel.__init__(self, parent)
        self.metadataList: List[Path] = fileList

    def flags(self, index):
        defaultFlags = QAbstractListModel.flags(self,index)
        return Qt.ItemIsDropEnabled | defaultFlags

    def canDropMimeData(self, data, action, row, column, parent):
        for file in data.urls():
            aFile = QFileInfo(file.path())
            if not aFile.isFile():
                return False
        return data.hasUrls()

    def dropMimeData(self, data, action, row, column, parent):
        for file in data.urls():
            #if file.isLocalDirectory():
            self.addRow(file.path())
        return True


    def rowCount(self, parent=QModelIndex()):
        return len(self.metadataList)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.metadataList[index.row()].name
        return None

    def setData(self,index, value, role):
        if role == Qt.EditRole:
            if not index.isValid():
                return False
            if index.column() == 0:
                self.dataChanged.emit(index, index)
                return index.row()

    def addRow(self, filename):
        self.beginInsertRows(self.index(len(self.metadataList),0), len(self.metadataList),len(self.metadataList))
        self.metadataList.append(filename)
        self.endInsertRows()
        self.rowAdded.emit()

    def removeRow(self, rowIndex):
        self.beginRemoveRows(QModelIndex(),rowIndex, rowIndex)
        del self.metadataList[rowIndex]
        self.endRemoveRows()
        self.rowRemoved.emit()

    def removeAllRows(self):
        newI = 0
        for i in range(len(self.metadataList)):
            self.removeRow(i-newI)
            newI+=1



