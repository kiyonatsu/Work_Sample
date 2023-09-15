from confluent_kafka import Producer


class _KafkaServerInfo:
    DEFAULT_BROKER = "10.132.68.18"
    BROKER_SERVER = f'{DEFAULT_BROKER}:9092'
    SCHEMA_REGISTRY = f'http://{DEFAULT_BROKER}:8081'

    AVRO_CONFIG = {
        'bootstrap.servers': BROKER_SERVER,
        'schema.registry.url': SCHEMA_REGISTRY
    }

    STRING_CONFIG = {'bootstrap.servers': BROKER_SERVER}


class KafkaTopic:
    AZURE_SUBSCRIPTIONS = 'azure-subscriptions-export'
    AZURE_RESOURCES = 'azure-resources-export'
    AZURE_VMS = 'azure-vms-export'
    AZURE_MON_METRICS = 'azure-mon-metrics-export'
    AZURE_MON_METRICS_POOL = 'azure-mon-metrics-pool-export'
    AZURE_NIS = "azure-nis-export"
    AWS_INSTANCES = 'aws-instances-export'
    AWS_MON_METRICS = 'aws-mon-metrics-export'
    AWS_MON_METRICS_POOL = 'aws-mon-metrics-pool-export'

    GCP_MONITORING_EMAIL = 'allmon-gcpmon-email'

    NAMP_DB_TESTS = 'namp-db-tests-json'
    NAMP_DB_TRANSACTIONS = 'namp-db-transactions'
    NAMP_DB_PW_CHANGE = 'namp_db0-pw_change'
    NAMP_DB_VM_REPORT = 'namp-db-vm_report'
    NAMP_DB_SUB_FUNC_PWC = 'namp-db-sub_func_pwc'
    NAMP_RAW = 'namp-raw'
    NAMP_WARNING_EXCLUSION = 'namp-db-warning-exclusion'


class NProducer(Producer):

    def __init__(self, config=None, p_type=None):
        if p_type is None:
            conf = _KafkaServerInfo.STRING_CONFIG
            if config is not None:
                conf.update(config)
            super().__init__(_KafkaServerInfo.STRING_CONFIG)
        else:
            raise NotImplementedError

    def clean_up(self):
        self.flush()

    def __del__(self):
        self.clean_up()
