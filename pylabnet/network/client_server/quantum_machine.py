import pickle

from pylabnet.network.core.service_base import ServiceBase
from pylabnet.network.core.client_base import ClientBase


class Service(ServiceBase):
    def exposed_execute(self, config, prog_pickle ):
        job = self._module.execute(config,  pickle.loads(prog_pickle))
        return job
        
    def exposed_simulate(self, config, prog_pickle, duration=2000):
        job, samples = self._module.simulate(config, pickle.loads(prog_pickle), duration)
        return job, pickle.dumps(samples)


class Client(ClientBase):
    def execute(self, config, prog_pickle):
        job = self._service.exposed_execute(config, prog_pickle)
        return job

    def simulate(self, config, prog_pickle, duration=2000):
        job, samples_pickle= self._service.exposed_simulate(config, prog_pickle, duration)
        return job, pickle.loads(samples_pickle)


