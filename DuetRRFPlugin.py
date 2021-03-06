import os.path
import json

from PyQt5.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtQml import QQmlComponent, QQmlContext

from UM.Message import Message
from UM.Logger import Logger

from UM.Application import Application
from UM.Preferences import Preferences
from UM.Extension import Extension
from UM.PluginRegistry import PluginRegistry
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin

from . import DuetRRFOutputDevice
from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")


class DuetRRFPlugin(QObject, Extension, OutputDevicePlugin):
    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Extension.__init__(self)
        OutputDevicePlugin.__init__(self)
        self.addMenuItem(catalog.i18n("DuetRRF Connections"), self.showSettingsDialog)
        self._dialogs = {}
        self._dialogView = None

        Preferences.getInstance().addPreference("duetrrf/instances", json.dumps({}))
        self._instances = json.loads(Preferences.getInstance().getValue("duetrrf/instances"))

    def start(self):
        manager = self.getOutputDeviceManager()
        for name, instance in self._instances.items():
            manager.addOutputDevice(DuetRRFOutputDevice.DuetRRFOutputDevice(name, instance["url"], instance["duet_password"], instance["http_user"], instance["http_password"], device_type=DuetRRFOutputDevice.DeviceType.print))
            manager.addOutputDevice(DuetRRFOutputDevice.DuetRRFOutputDevice(name, instance["url"], instance["duet_password"], instance["http_user"], instance["http_password"], device_type=DuetRRFOutputDevice.DeviceType.simulate))
            manager.addOutputDevice(DuetRRFOutputDevice.DuetRRFOutputDevice(name, instance["url"], instance["duet_password"], instance["http_user"], instance["http_password"], device_type=DuetRRFOutputDevice.DeviceType.upload))

    def stop(self):
        manager = self.getOutputDeviceManager()
        for name in self._instances.keys():
            manager.removeOutputDevice(name + "-print")
            manager.removeOutputDevice(name + "-simulate")
            manager.removeOutputDevice(name + "-upload")

    def _createDialog(self, qml):
        path = QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), qml))
        self._component = QQmlComponent(Application.getInstance()._engine, path)
        self._context = QQmlContext(Application.getInstance()._engine.rootContext())
        self._context.setContextProperty("manager", self)
        dialog = self._component.create(self._context)
        if dialog is None:
            Logger.log("e", "QQmlComponent status %s", self._component.status())
            Logger.log("e", "QQmlComponent errorString %s", self._component.errorString())
            raise RuntimeError(self._component.errorString())
        return dialog

    def _showDialog(self, qml):
        if not qml in self._dialogs:
            self._dialogs[qml] = self._createDialog(qml)
        self._dialogs[qml].show()

    def showSettingsDialog(self):
        self._showDialog("DuetRRFPlugin.qml")

    serverListChanged = pyqtSignal()
    @pyqtProperty("QVariantList", notify=serverListChanged)
    def serverList(self):
        return list(self._instances.keys())

    @pyqtSlot(str, result=str)
    def instanceUrl(self, name):
        if name in self._instances.keys():
            return self._instances[name]["url"]
        return None

    @pyqtSlot(str, result=str)
    def instanceDuetPassword(self, name):
        if name in self._instances.keys():
            return self._instances[name]["duet_password"]
        return None

    @pyqtSlot(str, result=str)
    def instanceHTTPUser(self, name):
        if name in self._instances.keys():
            return self._instances[name]["http_user"]
        return None

    @pyqtSlot(str, result=str)
    def instanceHTTPPassword(self, name):
        if name in self._instances.keys():
            return self._instances[name]["http_password"]
        return None

    @pyqtSlot(str, str, str, str, str, str)
    def saveInstance(self, oldName, name, url, duet_password, http_user, http_password):
        manager = self.getOutputDeviceManager()
        if oldName and oldName != name:
            manager.removeOutputDevice(oldName)
            if oldName in self._instances:
                del self._instances[oldName]
        self._instances[name] = {
            "url": url,
            "duet_password": duet_password,
            "http_user": http_user,
            "http_password": http_password
        }
        manager.addOutputDevice(DuetRRFOutputDevice.DuetRRFOutputDevice(name, url, duet_password, http_user, http_password, device_type=DuetRRFOutputDevice.DeviceType.print))
        manager.addOutputDevice(DuetRRFOutputDevice.DuetRRFOutputDevice(name, url, duet_password, http_user, http_password, device_type=DuetRRFOutputDevice.DeviceType.simulate))
        manager.addOutputDevice(DuetRRFOutputDevice.DuetRRFOutputDevice(name, url, duet_password, http_user, http_password, device_type=DuetRRFOutputDevice.DeviceType.upload))
        Preferences.getInstance().setValue("duetrrf/instances", json.dumps(self._instances))
        self.serverListChanged.emit()

    @pyqtSlot(str)
    def removeInstance(self, name):
        self.getOutputDeviceManager().removeOutputDevice(name + "-print")
        self.getOutputDeviceManager().removeOutputDevice(name + "-simulate")
        self.getOutputDeviceManager().removeOutputDevice(name + "-upload")
        del self._instances[name]
        Preferences.getInstance().setValue("duetrrf/instances", json.dumps(self._instances))
        self.serverListChanged.emit()

    @pyqtSlot(str, str, result = bool)
    def validName(self, oldName, newName):
        # empty string isn't allowed
        if not newName:
            return False
        # if name hasn't changed, not a duplicate, just no rename
        if oldName == newName:
            return True

        # duplicates not allowed
        return (not newName in self._instances.keys())
