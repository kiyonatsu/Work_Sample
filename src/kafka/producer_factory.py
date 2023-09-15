# from datetime import timedelta
# from object_pool import ObjectPool
import logging

from src.kafka.n_producer import NProducer, KafkaTopic

# _PRODUCER_POOL = ObjectPool(NProducer, min_init=1, max_capacity=8, expires=timedelta(days=1).total_seconds())


class StringProducer:

    def __init__(self, topic, config=None):
        self.__topic = topic
        self.producer = NProducer(config=config)

    def send(self, content):
        try:
            self.producer.produce(self.__topic, value=content)
            self.producer.poll(0)
        except BufferError:
            logging.exception("Kafka Error")
            self.producer.poll(1)

    def send_many(self, contents):
        for content in contents:
            try:
                self.producer.produce(self.__topic, value=content)
                self.producer.poll(0)
                break
            except BufferError:
                logging.exception("Kafka Error")
                self.producer.poll(1)

    def flush(self):
        self.producer.flush()


class IMS:

    @staticmethod
    def mon_gcp_mon_email():
        return StringProducer(KafkaTopic.GCP_MONITORING_EMAIL)


class NAMP:

    @staticmethod
    def tests():
        return StringProducer(KafkaTopic.NAMP_DB_TESTS)

    @staticmethod
    def transactions():
        return StringProducer(KafkaTopic.NAMP_DB_TRANSACTIONS)

    @staticmethod
    def pw_change():
        return StringProducer(KafkaTopic.NAMP_DB_PW_CHANGE)

    @staticmethod
    def vm_report():
        return StringProducer(KafkaTopic.NAMP_DB_VM_REPORT)

    @staticmethod
    def sub_func_pwc():
        return StringProducer(KafkaTopic.NAMP_DB_SUB_FUNC_PWC)

    @staticmethod
    def namp_raw():
        return StringProducer(KafkaTopic.NAMP_RAW)

    @staticmethod
    def warning_exclusion():
        return StringProducer(KafkaTopic.NAMP_WARNING_EXCLUSION)
