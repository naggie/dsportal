.. dsportal documentation master file, created by
   sphinx-quickstart on Sat Jun 24 10:11:20 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to dsportal's documentation!
====================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

    Concepts
    Installation
    Configuration
    Entities
    Healthchecks
    Alerters


Dsportal is a monitoring web portal that runs periodic health checks against
web appplications and servers.  Health checks are able to run server-side or
remotely on stateless workers for the sake of firewall limitations, location or
authorisation reasons.

Dsportal can also send alerts when healthchecks fail, rate limiting to avoid
alarm_fatigue_.

.. _alarm_fatigue: https://en.wikipedia.org/wiki/Alarm_fatigue

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
