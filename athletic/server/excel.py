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
    print 'Start row event'

  def process(self, row, col, value):
    raise NotImplementedError("Please implement this method")

  def endRow(self):
    print 'End row event'


class OutputCellHandler(ExcelCellHandler):

  def process(self, row, col, value):
    if row == 5:
      return ExcelReadEvent.ABORT_SHEET
    print cellName, 'row', row, '-', 'col', col, '-', value
    return ExcelReadEvent.CONTINUE


class ExcelWriteHandler(object):

  def __init__(self, file=None, mapSheet={}, mapCol={}, hasHeader=True):
    self.file = fileUtils.guardFile(file) if file else fileUtils.createTempFile(ext='.xlsx')
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

  def __init__(self, excelFile, saveError=True):
    self.excelFile = excelFile
    self.writeHandler = ExcelWriteHandler(excelFile)
    self.errorCount = 0
    self.successCount = 0

  def getErrorFile(self):
    return self.writeHandler.file

  def stream(self, cellHandler):
    book = open_workbook(self.excelFile)
    sheet = book.sheet_by_index(0)
    worksheet = self.writeHandler.add_worksheet()
    event = ExcelReadEvent.CONTINUE
    for row_index in range(sheet.nrows):
      if ExcelReadEvent.ABORT_SHEET == event:
        break
      print '================='
      cellHandler.startRow()
      rowData = {}
      errorEvent = ExcelReadEvent.CONTINUE
      for col_index in range(sheet.ncols):
        event = self.__processCell__(cellHandler, sheet, row_index, col_index, rowData, sheet.ncols)
        if ExcelReadEvent.ABORT_SHEET == event:
          break
        if ExcelReadEvent.ABORT_ROW == event:
          errorEvent = ExcelReadEvent.ABORT_ROW
      if ExcelReadEvent.CONTINUE == event and ExcelReadEvent.ABORT_ROW != errorEvent:
        try:
          cellHandler.endRow()
          self.successCount += 1
        except ValidationError as e:
          rowData[sheet.ncols] = str(e)
          errorEvent == ExcelReadEvent.ABORT_ROW
      print 'EVENT ', event
      if ExcelReadEvent.HEADER == event:
        rowData[sheet.ncols] = "Reason"
        self.writeHandler.writeRow(worksheet, rowData, 0)
      if ExcelReadEvent.ABORT_ROW == errorEvent:
        rowIndex = self.errorCount if cellHandler.hasHeader else self.errorCount + 1
        self.writeHandler.writeRow(worksheet, rowData, rowIndex)
        self.errorCount += 1
    self.writeHandler.close()

  def __processCell__(self, cellHandler, sheet, row_index, col_index, rowData, errorCol):
    value = sheet.cell(row_index, col_index).value
    rowData[col_index] = value
    try:
      return cellHandler.process(row_index, col_index, value)
    except ValidationError as e:
      rowData[errorCol] = str(e)
      return ExcelReadEvent.ABORT_ROW
