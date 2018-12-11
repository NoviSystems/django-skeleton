from redislite import Redis

from project.common_settings import *  # noqa: F401,F403
from project.common_settings import path


# Create a Redis instance using redislite
redis = Redis(path('db.redis'))

# Use redislite for the Celery broker
CELERY_BROKER_URL = 'redis+socket://%s' % (redis.socket_file, )
