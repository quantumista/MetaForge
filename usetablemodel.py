from PySide2.QtNetwork import QNetworkReply
from PySide2.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide2.QtGui import QIcon, QColor
from PySide2.QtWidgets import QApplication, QStyle



class TableModelU(QAbstractTableModel):
    def __init__(self,data, metadataList ,parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.metadataList = metadataList
        self.treeDict = metadataList
        self.templatelist = []
        self.templatesources = []
        self.newmetadataList = []
        self.newmetadatasources = []

        self.hiddenList=[]


    def addTemplateList(self, newList):
        self.metadataList = []
        self.templatelist = []
        self.templatesources = []

        for i in range(len(newList)):
            self.templatelist.append(newList[i])
            self.templatesources.append("/".join(newList[i]['Source'].split("/")[1:]))


    def rowCount(self, parent=QModelIndex()):
        return len(self.metadataList)

    def columnCount(self, parent=QModelIndex()):
        return 6

    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.metadataList[index.row()]["Key"]
            elif index.column() == 1:
                return self.metadataList[index.row()]["Value"]
            elif index.column() == 2:
                return self.metadataList[index.row()]["Annotation"]
            elif index.column() == 3:
                return ""
            elif index.column() == 4:
                return self.metadataList[index.row()]["Source"]
            elif index.column() == 5:
               return ""

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return
        if orientation == Qt.Horizontal:
            if section == 0:
                return "HT Key"
            elif section == 1:
                return "Ht Value"
            elif section == 2:
                return "Ht Annotation"
            elif section == 3:
                return "HT Units"
            elif section == 4:
                return "Source"
            elif section == 5:
                return "UUID"

            return None
    def setData(self,index, value, role):
        if role == Qt.EditRole:
            if not index.isValid():
                return False
            elif index.column() == 0:
                if self.metadataList[index.row()]["Source"] == "Custom Input":
                    self.metadataList[index.row()]["Key"] = value
                    self.dataChanged.emit(index, index)
            elif index.column() == 1:
                if self.metadataList[index.row()]["Source"] == "Custom Input":
                    self.metadataList[index.row()]["Value"] = value
                    self.dataChanged.emit(index, index)
                else:
                    treeDict = self.treeDict
                    sourcePath = self.metadataList[index.row()]["Source"].split("/")
                    for i in range(len(sourcePath)-1):
                        treeDict = treeDict[sourcePath[i]]
                    treeDict[sourcePath[-1]] = value
                    self.metadataList[index.row()]["Value"] = value
                    self.dataChanged.emit(index, index)
            elif index.column() == 2:
                self.metadataList[index.row()]["Annotation"] = value
                self.dataChanged.emit(index, index)
            elif index.column() == 3:
                self.metadataList[index.row()]["Units"] = value
                self.dataChanged.emit(index, index)
            elif index.column() == 5:
                pass

            return True
        elif role == Qt.CheckStateRole:
            if index.column() == 6 or index.column() == 7:
                self.changeChecked(index)
            self.dataChanged.emit(index, index)
            return True

        return False


    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        if index.column() == 3:
            return Qt.ItemFlags(QAbstractTableModel.flags(self,index) | Qt.ItemIsEditable)
        else:
            if index.data() == "":
                return Qt.ItemFlags(QAbstractTableModel.flags(self,index) | Qt.ItemIsEditable)
            else:
                return Qt.ItemIsEnabled
    def prepRow(self, dataDict, source, value):
        self.newmetadataList.append({"Key":value,"Value":dataDict[value],"Source":source+value})
        newsource = source+value
        self.newmetadatasources.append("/".join(newsource.split("/")[1:]))

    def addRow(self, key, source, value):
        self.beginInsertRows(self.index(len(self.metadataList),0), len(self.metadataList),len(self.metadataList))
        self.metadataList.append({"Key":key,"Value":value,"Source":source, "Units": "", "Annotation":""})
        self.endInsertRows()

    def addEmptyRow(self):
        self.beginInsertRows(self.index(len(self.metadataList),0), len(self.metadataList),len(self.metadataList))
        self.metadataList.append({"Key":"","Value":"","Source":"Custom Input", "Units": "", "Annotation":""})
        self.endInsertRows()





