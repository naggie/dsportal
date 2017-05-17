from __future__ import division # TODO just use py3
from base import Entity,HealthCheck,Metric

class WebApp(Entity):
    description = "Web application"

class HTTPStatusCheck(HealthCheck):
    description = "Checks service returns 200 OK"

class CertificateExpiryCheck(HealthCheck):
    description = "Checks certificate isn't near expiry"
    # https://stackoverflow.com/questions/7689941/how-can-i-retrieve-the-tls-ssl-peer-certificate-of-a-remote-host-using-python
