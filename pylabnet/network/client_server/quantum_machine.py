import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):
    def exposed_execute(self, prog, config):
        job = self._module.execute()
        return pickle.dumps(job)
        
    def exposed_execute(self, prog, config):
        job = self._module.execute()
        return pickle.dumps(job)


class Client(ClientBase):
    def Request_data(self,):
        v_rms_pickle, a_peak_pickle, a_rms_pickle, crest_pickle, temperature_pickle = self._service.exposed_Request_data()
        return pickle.loads(v_rms_pickle), pickle.loads(a_peak_pickle), pickle.loads(a_rms_pickle), pickle.loads(crest_pickle), pickle.loads(temperature_pickle)
