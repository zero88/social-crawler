import logging

import xlsxwriter
from xlrd import cellname, open_workbook

from exception import ExecutionError, ValidationError
from utils import fileUtils, textUtils

logger = logging.getLogger(__name__)


class ExcelReadEvent:
    ABORT_SHEET, ABORT_ROW, HEADER, CONTINUE = range(4)


class ExcelCellHandler(object):

    def startRow(self):
        raise NotImplementedError("Please implement this method")

    def process(self, row, col, value):
        raise NotImplementedError("Please implement this method")

    def endRow(self):
        raise NotImplementedError("Please implement this method")


class OutputCellHandler(ExcelCellHandler):

    def startRow(self):
        pass

    def process(self, row, col, value):
        if row == 5:
            return ExcelReadEvent.ABORT_SHEET
        print(cellName, 'row', row, '-', 'col', col, '-', value)

    def endRow(self):
        pass


class ExcelWriteHandler(object):

    def __init__(self, file=None, mapSheet={}, mapCol={}, hasHeader=True):
        self.file = fileUtils.createTempFile(file) if file else fileUtils.createTempFile(ext='.xlsx')
        self.workbook = xlsxwriter.Workbook(self.file)
        self.mapSheet = mapSheet
        self.mapCol = mapCol
        self.hasHeader = hasHeader

    def addWorkSheet(self, name=None):
        return self.workbook.add_worksheet(name)

    def writeWorkBook(self, sheets):
        for sheetIndex, rows in enumerate(sheets):
            sheet = self.addWorkSheet(self.mapSheet.get(sheetIndex))
            self.writeSheet(sheet, rows)
        self.close()

    def writeSheet(self, sheet, rows):
        self.writeHeader(sheet)
        for rowIndex, rowData in enumerate(rows):
            self.writeRow(sheet, rowData, rowIndex + 1 if self.hasHeader else rowIndex)

    def writeHeader(self, sheet):
        if self.hasHeader is False:
            return
        for key, value in self.mapCol.iteritems():
            label = value.get('label') if textUtils.isEmpty(value.get('label')) is False else key.title()
            sheet.write(0, value.get('index'), label)

    def writeRow(self, sheet, rowData, rowIndex):
        for key, value in rowData.iteritems():
            colIndex = key if self.mapCol == {} else (self.mapCol.get(key).get('index') if self.mapCol.get(key) else None)
            if colIndex is None:
                logger.debug('Column index \'{}\' is invalid'.format(key))
                continue
            sheet.write(rowIndex, colIndex, value)

    def close(self):
        self.workbook.close()


class ExcelReadHandler(object):

    def __init__(self, excelFile, hasHeader=True, saveError=True):
        self.excelFile = excelFile
        self.hasHeader = hasHeader
        self.saveError = saveError
        self.writeHandler = ExcelWriteHandler(excelFile)
        self.errorCount = 0
        self.successCount = 0

    def getErrorFile(self):
        return self.writeHandler.file

    def stream(self, cellHandler):
        book = open_workbook(self.excelFile)
        sheet = book.sheet_by_index(0)
        errorSheet = self.writeHandler.addWorkSheet()
        event = ExcelReadEvent.CONTINUE
        logger.debug('Start reading excel file: {}'.format(self.excelFile))
        for row_index in range(sheet.nrows):
            if ExcelReadEvent.ABORT_SHEET == event:
                break
            event = self.__startRow__(cellHandler, row_index)
            event, rowData = self.__processCells__(cellHandler, sheet, row_index)
            if event is not ExcelReadEvent.CONTINUE:
                self.__handleErrorRow__(event, errorSheet, rowData, sheet.ncols)
                continue
            self.__endRow__(cellHandler, row_index, sheet.ncols, rowData, errorSheet)
        self.writeHandler.close()

    def __startRow__(self, cellHandler, row_index):
        logging.debug('Start processing row: {}'.format(row_index))
        cellHandler.startRow()
        return ExcelReadEvent.HEADER if row_index == 0 and self.hasHeader else ExcelReadEvent.CONTINUE

    def __processCells__(self, cellHandler, sheet, row_index):
        rowData = {}
        rowEvent = ExcelReadEvent.CONTINUE
        for col_index in range(sheet.ncols):
            colEvent = self.__processCell__(cellHandler, sheet, row_index, col_index, rowData, sheet.ncols)
            rowEvent = rowEvent if ExcelReadEvent.ABORT_ROW == rowEvent or ExcelReadEvent.ABORT_SHEET == rowEvent else colEvent
        return rowEvent, rowData

    def __processCell__(self, cellHandler, sheet, row_index, col_index, rowData, errorCol):
        value = sheet.cell(row_index, col_index).value
        rowData[col_index] = value
        try:
            cellHandler.process(row_index, col_index, value)
            return ExcelReadEvent.CONTINUE
        except ValidationError as e:
            rowData[errorCol] = str(e)
            return ExcelReadEvent.ABORT_ROW

    def __endRow__(self, cellHandler, row_index, max_col, rowData, errorWorksheet):
        try:
            cellHandler.endRow()
            logging.debug('End processing row: {}'.format(row_index))
            self.successCount += 1
        except ValidationError as e:
            rowData[max_col] = str(e)
            self.__handleErrorRow__(ExcelReadEvent.ABORT_ROW, errorWorksheet, rowData, max_col)

    def __handleErrorRow__(self, rowEvent, errorWorksheet, rowData, max_col):
        if ExcelReadEvent.HEADER == rowEvent:
            rowData[max_col] = "Reason"
            self.writeHandler.writeRow(errorWorksheet, rowData, 0)
        if ExcelReadEvent.ABORT_ROW == rowEvent:
            rowIndex = self.errorCount + 1 if self.hasHeader else self.errorCount
            self.writeHandler.writeRow(errorWorksheet, rowData, rowIndex)
            self.errorCount += 1
