Dsportal is a web application that exhibits web applications, applying health
checks to the applications and hosting platforms beneath.


# Architecture

## Entities

* `Host`
* `Service`

## Health checks

## Workers



# Installation

Server:
1. Install via pip
2. Set up nginx reverse proxy, preferably with SSL. Optionally serve static
   files via nginx.
2. Add systemd template to run dsportal-server.

Of course, the same but (2) applies to set up a worker.

`sudo pip install .` (python 3 pip!)

For development, `pip install -e .` will link a global install.





# Alarm fatigue
* False positives
* Multiple notifications for the same problem
* Notifications that require no human action
* Everything's fine notifications
* Toggling notifications due to intermittent test
* Cascade test failures
