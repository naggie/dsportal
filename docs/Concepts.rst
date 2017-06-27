Operation of dsportal is based around Entities and Healthchecks. Entities
represent something physical such as a server or web application, Healthchecks
run periodically against Entities.

Healthchecks can run against the local server, or a remote *worker* if
specified in the Healthcheck configuration or the parent Entity.

