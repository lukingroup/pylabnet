import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):
    def exposed_execute(self, prog, config):
        job = self._module.execute()
        return pickle.dumps(job)
        
    def exposed_simulate(self, prog, config, duration=2000):
        job, samples = self._module.simulate()
        return pickle.dumps(job), pickle.dumps(samples)


class Client(ClientBase):
    def execute(self):
        job = self._service.exposed_execute()
        return pickle.loads(job)

    def simulate(self):
        job_pickle, samples_pickle= self._service.exposed_simulate()
        return pickle.loads(job_pickle), pickle.loads(samples_pickle)


