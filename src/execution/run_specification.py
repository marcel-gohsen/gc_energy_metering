class RunSpecification:
    def __init__(self, id, benchmark, sw_config, hw_conf_id=1, repetitions=2, nodes=9):
        self.id = id
        self.benchmark = benchmark

        self.sw_config = sw_config
        self.hw_conf_id = hw_conf_id

        self.repetitions = repetitions
        self.nodes = nodes

    def get_exc_cmd(self):
        return self.benchmark.create_exc_cmd(self.sw_config)
