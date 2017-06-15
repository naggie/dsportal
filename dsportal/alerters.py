from dsportal.base import Alerter
import boto
import logging
log = logging.getLogger(__name__)

class AwsSnsSmsAlerter(Alerter):
    def __init__(self,
            region_name,
            aws_access_key_id,
            aws_secret_access_key,
            phone_numbers,
            **kwargs):

        self.phone_numbers = list(phone_numbers)
        self.sns = boto3.client(
                service_name='sns',
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                )

    def broadcast_alert(self,text):
        for pn in self.phone_numbers:
            try:
                sns_client.publish( PhoneNumber=pn,
                        Message=text,
                        MessageAttributes={
                            'AWS.SNS.SMS.SenderID': {
                                'DataType': 'String',
                                'StringValue': self.name,
                                }
                            }
                        )

            except:
                log.exception()
