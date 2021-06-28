
from PyQt5.QtCore import QObject, QThread, pyqtSignal


class DataTakerExperimentWorker(QObject):

    def __init__(self, dataset_name):
        self.dataset_name = dataset_name

    def define_dataset(self):
        return self.dataset_name

    def run_experiment(self):
        pass

    def run(self):
        """Long-running task."""
        self.run_experiment()
        self.finished.emit()

