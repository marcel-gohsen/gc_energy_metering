from settings import settings

class RunSpecification:
    def __init__(self, id, sw_config, hw_conf_id=1):
        self.id = id

        self.sw_config = sw_config
        self.hw_conf_id = hw_conf_id

    def get_exc_cmd(self):
        return settings.BENCHMARK.create_exc_cmd(self.sw_config)
