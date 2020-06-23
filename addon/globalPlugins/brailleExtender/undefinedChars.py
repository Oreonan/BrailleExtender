# coding: utf-8
# undefinedChars.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import re

import wx

import addonHandler
from . import brailleTablesExt
import characterProcessing
import config
import gui
import louis

from . import huc
from .common import *
from .utils import getCurrentBrailleTables, getTextInBraille
from . import brailleRegionHelper

addonHandler.initTranslation()


HUCDotPattern = "12345678-78-12345678"
undefinedCharPattern = huc.cellDescriptionsToUnicodeBraille(HUCDotPattern)
CHOICE_tableBehaviour = 0
CHOICE_allDots8 = 1
CHOICE_allDots6 = 2
CHOICE_emptyCell = 3
CHOICE_otherDots = 4
CHOICE_questionMark = 5
CHOICE_otherSign = 6
CHOICE_liblouis = 7
CHOICE_HUC8 = 8
CHOICE_HUC6 = 9
CHOICE_hex = 10
CHOICE_dec = 11
CHOICE_oct = 12
CHOICE_bin = 13

dotPatternSample = "6-123456"
signPatternSample = "??"

CHOICES_LABELS = {
	CHOICE_tableBehaviour: _("Use braille table behavior") + " (%s)" % _("no description possible"),
	CHOICE_allDots8: _("Dots 1-8 (⣿)"),
	CHOICE_allDots6: _("Dots 1-6 (⠿)"),
	CHOICE_emptyCell: _("Empty cell (⠀)"),
	CHOICE_otherDots: _("Other dot pattern (e.g.: {dotPatternSample})").format(
		dotPatternSample=dotPatternSample
	),
	CHOICE_questionMark: _("Question mark (depending output table)"),
	CHOICE_otherSign: _("Other sign/pattern (e.g.: {signPatternSample})").format(
		signPatternSample=signPatternSample
	),
	CHOICE_hex: _("Hexadecimal, Liblouis style"),
	CHOICE_HUC8: _("Hexadecimal, HUC8"),
	CHOICE_HUC6: _("Hexadecimal, HUC6"),
	CHOICE_hex: _("Hexadecimal"),
	CHOICE_dec: _("Decimal"),
	CHOICE_oct: _("Octal"),
	CHOICE_bin: _("Binary"),
}

def getHardValue():
	selected = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if selected == CHOICE_otherDots:
		return config.conf["brailleExtender"]["undefinedCharsRepr"]["hardDotPatternValue"]
	elif selected == CHOICE_otherSign:
		return config.conf["brailleExtender"]["undefinedCharsRepr"]["hardSignPatternValue"]
	else:
		return ''


def setUndefinedChar(t=None):
	if not t or t > CHOICE_HUC6 or t < 0:
		t = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if t == 0:
		return
	louis.compileString(getCurrentBrailleTables(), bytes(
		f"undefined {HUCDotPattern}", "ASCII"))


def getExtendedSymbolsForString(s: str, lang) -> dict:
	global extendedSymbols, localesFail
	if lang in localesFail: lang = "en"
	if not lang in extendedSymbols.keys():
		try:
			extendedSymbols[lang] = getExtendedSymbols(lang)
		except LookupError:
			log.warning(f"Unable to load extended symbols for: {lang}, using english")
			localesFail.append(lang)
			lang = "en"
			extendedSymbols[lang] = getExtendedSymbols(lang)
	return {
		c: (d, [(m.start(), m.end()-1) for m in re.finditer(re.escape(c), s)])
		for c, d in extendedSymbols[lang].items()
		if c in s
	}


def getAlternativeDescChar(c, method):
	if method in [CHOICE_HUC6, CHOICE_HUC8]:
		HUC6 = method == CHOICE_HUC6
		return huc.translate(c, HUC6=HUC6)
	elif method in [CHOICE_bin, CHOICE_oct, CHOICE_dec, CHOICE_hex]:
		return getTextInBraille("".join(getUnicodeNotation(c)))
	elif method == CHOICE_liblouis:
		return getTextInBraille(getLiblouisStyle(c))
	else:
		return getUndefinedCharSign(method)


def getDescChar(c, lang="Windows", start="", end=""):
	method = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if lang == "Windows":
		lang = languageHandler.getLanguage()
	desc = characterProcessing.processSpeechSymbols(
		lang, c, characterProcessing.SYMLVL_CHAR).replace(' ', '').strip()
	if not desc or desc == c:
		return getAlternativeDescChar(c, method)
	return f"{start}{desc}{end}"


def getLiblouisStyle(c):
	if isinstance(c, str):
		if not c or len(c) > 1:
			raise ValueError(f"Please provide one character only. Received: {c}")
		c = ord(c)
	if not isinstance(c, int):
		raise TypeError("wrong type")
	if c < 0x10000:
		return r"\x%.4x" % c
	elif c <= 0x100000:
		return r"\y%.5x" % c
	else:
		return r"\z%.6x" % c


def getUnicodeNotation(s, notation=None):
	if not isinstance(s, str):
		raise TypeError("wrong type")
	if not notation:
		notation = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	matches = {
		CHOICE_bin: bin,
		CHOICE_oct: oct,
		CHOICE_dec: lambda s: s,
		CHOICE_hex: hex,
		CHOICE_liblouis: getLiblouisStyle,
	}
	if notation not in matches.keys():
		raise ValueError(f"Wrong value ({notation})")
	fn = matches[notation]
	return getTextInBraille("".join(["'%s'" % fn(ord(c)) for c in s]))


def getUndefinedCharSign(method):
	if method == CHOICE_allDots8:
		return '⣿'
	elif method == CHOICE_allDots6:
		return '⠿'
	elif method == CHOICE_otherDots:
		return huc.cellDescriptionsToUnicodeBraille(config.conf["brailleExtender"]["undefinedCharsRepr"]["hardDotPatternValue"])
	elif method == CHOICE_questionMark:
		return getTextInBraille('?')
	elif method == CHOICE_otherSign:
		return getTextInBraille(config.conf["brailleExtender"]["undefinedCharsRepr"]["hardSignPatternValue"])
	else:
		return '⠀'


def getReplacement(text, method=None):
	if not method:
		method = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if not text:
		return ''
	if config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"]:
		start = config.conf["brailleExtender"]["undefinedCharsRepr"]["start"]
		end = config.conf["brailleExtender"]["undefinedCharsRepr"]["end"]
		if start:
			start = getTextInBraille(start)
		if end:
			end = getTextInBraille(end)
		lang = config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"]
		table = [config.conf["brailleExtender"]["undefinedCharsRepr"]["table"]]
		return getTextInBraille(getDescChar(
			text,
			lang=lang,
			start=start,
			end=end
		), table)
	elif method in [CHOICE_HUC6, CHOICE_HUC8]:
		HUC6 = method == CHOICE_HUC6
		return huc.translate(text, HUC6=HUC6)
	elif method in [CHOICE_bin, CHOICE_oct, CHOICE_dec, CHOICE_hex, CHOICE_liblouis]:
		return getUnicodeNotation(text)
	else:
		return getUndefinedCharSign(method)


def undefinedCharProcess(self):
	Repl = brailleRegionHelper.BrailleCellReplacement
	fullExtendedDesc = config.conf["brailleExtender"]["undefinedCharsRepr"]["fullExtendedDesc"]
	startTag = config.conf["brailleExtender"]["undefinedCharsRepr"]["start"]
	endTag = config.conf["brailleExtender"]["undefinedCharsRepr"]["end"]
	if startTag:
		startTag = getTextInBraille(startTag)
	if endTag:
		endTag = getTextInBraille(endTag)
	lang = config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"]
	table = [config.conf["brailleExtender"]["undefinedCharsRepr"]["table"]]
	undefinedCharsPos = [e for e in brailleRegionHelper.findBrailleCellsPattern(
		self, undefinedCharPattern)]
	extendedSymbolsRawText = {}
	if config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"] and config.conf["brailleExtender"]["undefinedCharsRepr"]["extendedDesc"]:
		extendedSymbolsRawText = getExtendedSymbolsForString(
			self.rawText, lang)
	replacements = []
	for c, v in extendedSymbolsRawText.items():
		for start, end in v[1]:
			if start in undefinedCharsPos:
				toAdd = f":{len(c)}" if config.conf["brailleExtender"]["undefinedCharsRepr"]["showSize"] else ''
				replaceBy = getTextInBraille(
					f"{startTag}{v[0]}{toAdd}{endTag}", table)
				replacements.append(Repl(
					start,
					start if fullExtendedDesc else end,
					replaceBy=getReplacement(
						c[0]) if fullExtendedDesc else replaceBy,
					insertBefore=replaceBy if fullExtendedDesc else ''
				))
	replacements = [Repl(pos, replaceBy=getReplacement(self.rawText[pos]))
					for pos in undefinedCharsPos] + replacements
	if not replacements:
		return
	brailleRegionHelper.replaceBrailleCells(self, replacements)


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Representation of undefined characters")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: label of a dialog.
		label = _("Representation &method")
		self.undefinedCharReprList = sHelper.addLabeledControl(
			label, wx.Choice, choices=list(CHOICES_LABELS.values())
		)
		self.undefinedCharReprList.SetSelection(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
		)
		self.undefinedCharReprList.Bind(
			wx.EVT_CHOICE, self.onUndefinedCharReprList)
		# Translators: label of a dialog.
		self.undefinedCharReprEdit = sHelper.addLabeledControl(
			_("Specify another &pattern"), wx.TextCtrl, value=self.getHardValue()
		)
		self.undefinedCharDesc = sHelper.addItem(
			wx.CheckBox(self, label=(
				_("Show punctuation/symbol &name for undefined characters if available")
				+ " (%s)" % _("can cause a lag")
			))
		)
		self.undefinedCharDesc.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"]
		)
		self.undefinedCharDesc.Bind(wx.EVT_CHECKBOX, self.onUndefinedCharDesc)
		self.extendedDesc = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("Also describe e&xtended characters (e.g.: country flags)")
			)
		)
		self.extendedDesc.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["extendedDesc"]
		)
		self.extendedDesc.Bind(wx.EVT_CHECKBOX, self.onExtendedDesc)
		self.fullExtendedDesc = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("&Full extended description")
			)
		)
		self.fullExtendedDesc.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["fullExtendedDesc"]
		)
		self.showSize = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("Show the si&ze taken")
			)
		)
		self.showSize.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["showSize"]
		)
		self.startTag = sHelper.addLabeledControl(
			_("&Start tag"),
			wx.TextCtrl,
			value=config.conf["brailleExtender"]["undefinedCharsRepr"]["start"],
		)
		self.endTag = sHelper.addLabeledControl(
			_("&End tag"),
			wx.TextCtrl,
			value=config.conf["brailleExtender"]["undefinedCharsRepr"]["end"],
		)
		values = [lang[1] for lang in languageHandler.getAvailableLanguages()]
		keys = [lang[0] for lang in languageHandler.getAvailableLanguages()]
		undefinedCharLang = config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"]
		if not undefinedCharLang in keys:
			undefinedCharLang = keys[-1]
		undefinedCharLangID = keys.index(undefinedCharLang)
		self.undefinedCharLang = sHelper.addLabeledControl(
			_("&Language"), wx.Choice, choices=values
		)
		self.undefinedCharLang.SetSelection(undefinedCharLangID)
		values = [_("Use the current output table")] + brailleTablesExt.listTablesDisplayName(brailleTablesExt.listOutputTables())
		keys = ["current"] + brailleTablesExt.listTablesFileName(brailleTablesExt.listOutputTables())
		undefinedCharTable = config.conf["brailleExtender"]["undefinedCharsRepr"][
			"table"
		]
		if undefinedCharTable not in keys: undefinedCharTable = "current"
		undefinedCharTableID = keys.index(undefinedCharTable)
		self.undefinedCharTable = sHelper.addLabeledControl(
			_("Braille &table"), wx.Choice, choices=values
		)
		self.undefinedCharTable.SetSelection(undefinedCharTableID)
		self.onExtendedDesc()
		self.onUndefinedCharDesc()
		self.onUndefinedCharReprList()

	def getHardValue(self):
		selected = self.undefinedCharReprList.GetSelection()
		if selected == CHOICE_otherDots:
			return config.conf["brailleExtender"]["undefinedCharsRepr"][
				"hardDotPatternValue"
			]
		elif selected == CHOICE_otherSign:
			return config.conf["brailleExtender"]["undefinedCharsRepr"][
				"hardSignPatternValue"
			]
		else:
			return ""

	def onUndefinedCharDesc(self, evt=None):
		l = [
			self.extendedDesc,
			self.fullExtendedDesc,
			self.showSize,
			self.startTag,
			self.endTag,
			self.undefinedCharLang,
			self.undefinedCharTable,
		]
		for e in l:
			if self.undefinedCharDesc.IsChecked():
				e.Enable()
			else:
				e.Disable()

	def onExtendedDesc(self, evt=None):
		if self.extendedDesc.IsChecked():
			self.fullExtendedDesc.Enable()
			self.showSize.Enable()
		else:
			self.fullExtendedDesc.Disable()
			self.showSize.Disable()

	def onUndefinedCharReprList(self, evt=None):
		selected = self.undefinedCharReprList.GetSelection()
		if selected in [CHOICE_otherDots, CHOICE_otherSign]:
			self.undefinedCharReprEdit.Enable()
		else:
			self.undefinedCharReprEdit.Disable()
		self.undefinedCharReprEdit.SetValue(self.getHardValue())

	def postInit(self):
		self.undefinedCharDesc.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"method"
		] = self.undefinedCharReprList.GetSelection()
		repr_ = self.undefinedCharReprEdit.Value
		if self.undefinedCharReprList.GetSelection() == CHOICE_otherDots:
			repr_ = re.sub("[^0-8\-]", "", repr_).strip("-")
			repr_ = re.sub("\-+", "-", repr_)
			config.conf["brailleExtender"]["undefinedCharsRepr"][
				"hardDotPatternValue"
			] = repr_
		else:
			config.conf["brailleExtender"]["undefinedCharsRepr"][
				"hardSignPatternValue"
			] = repr_
		config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"] = self.undefinedCharDesc.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"]["extendedDesc"] = self.extendedDesc.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"]["fullExtendedDesc"] = self.fullExtendedDesc.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"]["showSize"] = self.showSize.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"start"
		] = self.startTag.Value
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"end"
		] = self.endTag.Value
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"lang"
		] = languageHandler.getAvailableLanguages()[
			self.undefinedCharLang.GetSelection()
		][
			0
		]
		undefinedCharTable = self.undefinedCharTable.GetSelection()
		keys = ["current"] + brailleTablesExt.listTablesFileName(brailleTablesExt.listOutputTables())
		config.conf["brailleExtender"]["undefinedCharsRepr"]["table"] = keys[
			undefinedCharTable
		]


def getExtendedSymbols(locale):
	if locale == "Windows":
		locale = languageHandler.getLanguage()
	b, u = characterProcessing._getSpeechSymbolsForLocale(locale)
	if not b and not u: return None
	a = {
		k.strip(): v.replacement.replace(' ', '').strip()
		for k, v in b.symbols.items()
		if k and len(k) > 1 and ' ' not in k and v and v.replacement and v.replacement.strip()
	}
	a.update(
		{
			k.strip(): v.replacement.replace(' ', '').strip()
			for k, v in u.symbols.items()
			if k and len(k) > 1 and ' ' not in k and v and v.replacement and v.replacement.strip()
		}
	)
	return a


extendedSymbols = {}
localesFail = []
