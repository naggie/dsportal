from __future__ import division # TODO just use py3
from base import Entity,HealthCheck,Metric

class WebApp(Entity):
    description = "Web application"

class HTTPStatusCheck(HealthCheck):
    description = "Checks service returns 200 OK"

