import dramatiq
from tasks.broker import setup_dramatiq
setup_dramatiq()

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


########################################################################################################################


scheduler = BackgroundScheduler()
scheduler.start()


########################################################################################################################


@dramatiq.actor(queue_name='sched')
def add_job(name, crontab='* * * * *'):
    scheduler.add_job(name,
                      trigger=CronTrigger.from_crontab(crontab),
                      args=(name,))