from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QVBoxLayout, QWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal

import speech_recognition as sr
from PYinterception import Interception, KeyStroke

import time

from hdvs.core import *

class hdvs(QMainWindow):
    statusPrint = pyqtSignal(str)
    changeStatus = pyqtSignal(Status)

    def __init__(self, stratagems, config, parent=None):
        super(QMainWindow, self).__init__(parent)

        self.setWindowTitle("Helldivers Voice Stratagem")
        self.setWindowIcon(QIcon("data/icons/Icon.webp"))

        print("Starting stratagem recognition")
        print("SpeechRecognition Version: {0}".format(sr.__version__))

        self.stratagems = stratagems
        self.config = config

        self.strat_key = self.config["keys"]["stratagem"]

        self.recog = sr.Recognizer()
        self.mic = sr.Microphone()
        print("Calibrating for ambient noise...")
        with self.mic as source:
            self.recog.adjust_for_ambient_noise(source)

        print("Ready")

        self.status = StatusWidg(self)
        self.statusPrint.connect(self.status.print)
        self.changeStatus.connect(self.status.setStatus)

        self.stratagemopts = StratagemGroup(self.stratagems)
        self.options = Options(self.config, self.listen)

        rhsLayout = QVBoxLayout()
        rhsLayout.addWidget(self.status)
        rhsLayout.addWidget(self.options)

        rhs = QWidget()
        rhs.setLayout(rhsLayout)

        mainLayout = QHBoxLayout()
        mainLayout.addWidget(self.stratagemopts)
        mainLayout.addWidget(rhs)

        main = QWidget()
        main.setLayout(mainLayout)
        self.setCentralWidget(main)
        self.changeStatus.emit(Status.IDLE)

        self.active = False

    def execute_stratagem(self, stratagem):
        self.changeStatus.emit(Status.EXECUTING)
        config = self.config
        self.sPrint("Executing {0}.".format(stratagem["name"]))
        for key in stratagem["code"]:
            if key == "U":
                KeyStroke(config["keys"]["up"]).send()
            elif key == "D":
                KeyStroke(config["keys"]["down"]).send()
            elif key == "L":
                KeyStroke(config["keys"]["left"]).send()
            elif key == "R":
                KeyStroke(config["keys"]["right"]).send()
            else:
                self.sPrint("Warning: '{0}' is not a valid code symbol. Please check stratagem.yml.".format(key))

            # Ignore on last?
            time.sleep(config["dialling-speed"])

    def interpret_stratagem(self, command):
        command = format_command(command)

        for stratagem in self.stratagems:
            if not stratagem["enabled"]:
                continue

            # Could be accomplished using a trigger map
            # Has not been done in yaml file for readability
            for trigger in stratagem["trigger"]:
                if command == format_command(trigger):
                    self.sPrint("Found match: {0}".format(stratagem["name"]))
                    self.execute_stratagem(stratagem)
                    return True
        return False

    def listen(self):
        recog = self.recog

        self.changeStatus.emit(Status.LISTENING)
        self.sPrint("Listening...")
        with self.mic as source:
            audio = recog.listen(source)

        self.sPrint("Input received, converting... ")
        self.changeStatus.emit(Status.PROCESSING)
        try:
            command = recog.recognize_sphinx(audio, keyword_entries=self.stratagemopts.keyWords,language=("data/pocketsphinx-data/en-US/acoustic-model", "data/pocketsphinx-data/en-US/language-model.lm.bin", "data/pocketsphinx-data/en-US/pronunciation-dictionary.dict"))
            self.sPrint("Heard: {0}".format(command))

            if self.interpret_stratagem(command):
                while kb.is_pressed(self.strat_key):
                    time.sleep(1)           # I don't like this but keyboard module cannot properly detect KEY_UP events & without this hotkey will keep triggering
                
            else:
                self.sPrint("{0} was not a valid stratagem.".format(command))

        except sr.UnknownValueError:
            self.sPrint("Could not understand audio.")
        except sr.RequestError as e:
            self.sPrint("Could not decode, received error: {0}".format(e))

        self.changeStatus.emit(Status.IDLE)

    def sPrint(self, msg: str):
        self.statusPrint.emit(msg)
