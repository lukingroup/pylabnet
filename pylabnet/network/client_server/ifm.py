import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):
    def exposed_Request_data(self, ):
        v_rms, a_peak, a_rms, crest, temperature = self._module.Request_data()
        return pickle.dumps(v_rms), pickle.dumps(a_peak), pickle.dumps(a_rms), pickle.dumps(crest), pickle.dumps(temperature)


class Client(ClientBase):
    def Request_data(self,):
        v_rms_pickle, a_peak_pickle, a_rms_pickle, crest_pickle, temperature_pickle = self._service.exposed_Request_data()
        return pickle.loads(v_rms_pickle), pickle.loads(a_peak_pickle), pickle.loads(a_rms_pickle), pickle.loads(crest_pickle), pickle.loads(temperature_pickle)
