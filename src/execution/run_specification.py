class RunSpecification:
    def __init__(self, id, benchmark, rep_start, sw_config, hw_conf_id=1):
        self.id = id
        self.benchmark = benchmark

        self.sw_config = sw_config
        self.hw_conf_id = hw_conf_id
        self.rep_start = rep_start

    def get_exc_cmd(self):
        return self.benchmark.create_exc_cmd(self.sw_config)
