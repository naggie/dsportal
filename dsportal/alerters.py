from dsportal.base import Alerter
import boto3
from dsportal.util import slug
import logging
log = logging.getLogger(__name__)

class AwsSnsSmsAlerter(Alerter):
    def __init__(self,
            region_name,
            aws_access_key_id,
            aws_secret_access_key,
            phone_numbers,
            **kwargs):

        super(AwsSnsSmsAlerter,self).__init__(**kwargs)

        if type(phone_numbers) != list:
            raise ValueError('Phone numbers must be list')

        self.phone_numbers = phone_numbers

        self.sns = boto3.client(
                service_name='sns',
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                )


    def broadcast_alert(self,text):
        for pn in self.phone_numbers:
            try:
                self.sns.publish(
                        PhoneNumber=pn,
                        Message=text,
                        MessageAttributes={
                            'AWS.SNS.SMS.SenderID': {
                                'DataType': 'String',
                                'StringValue': slug(self.name).replace('_','')[:11],
                                }
                            }
                        )

            except:
                log.exception('SNS client failure')
                raise
