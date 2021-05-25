from PySide2.QtCore import QSortFilterProxyModel, Qt, QRegExp

class FilterModelU(QSortFilterProxyModel):
    def __init__(self,data ,parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.displayed=[]
        self.fileList=[]

    def filterAcceptsRow(self,source_row, source_parent):
        curSource = self.sourceModel().metadataList[source_row]['Source']
        if curSource != "Custom Input":
            splitSource= "/".join(curSource.split("/")[1:])
            if splitSource in self.sourceModel().templatesources:
                if self.sourceModel().metadataList[source_row] not in self.displayed:
                    self.displayed.append(self.sourceModel().metadataList[source_row])
                return True
            else:
                return False
        else:
            if self.sourceModel().metadataList[source_row] not in self.displayed:
                self.displayed.append(self.sourceModel().metadataList[source_row])

            return self.sourceModel().metadataList[source_row]['Source'] == "Custom Input"
