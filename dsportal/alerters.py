from dsportal.base import Alerter
import boto3
from dsportal.util import slug
import logging
import requests
log = logging.getLogger(__name__)

# TODO pass on excess kwargs to boto3 instead of individual vars

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
                                },
                            'AWS.SNS.SMS.SMSType': {
                                'DataType': 'String',
                                'StringValue': 'Transactional',
                                },
                            },
                        )

            except:
                log.exception('SNS client failure')


class SlackAlerter(Alerter):
    def __init__(self,webhook_url,username=None,channel='',**kwargs):
        super(SlackAlerter,self).__init__(**kwargs)
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username or self.name
        self.channel = channel

    def broadcast_alert(self,text):
        try:
            r = requests.post(self.webhook_url,data = {
                    'username': self.username,
                    'channel': self.channel,
                    'text': text,
                })
            r.raise_for_status()
        except:
            log.exception('SNS client failure')
