from app.configs import Settings
from app.infrastructure import ASchedulerManager, IntervalArgs, JobSchedule, TriggerType

from .routes import check_stale_investigations


def register_tasks(scheduler_manager: ASchedulerManager, settings: Settings) -> None:
    scheduler_manager.add_job(
        func=check_stale_investigations,
        schedule=JobSchedule(
            trigger_type=TriggerType.INTERVAL,
            trigger_args=IntervalArgs(seconds=60),
        ),
        job_id="check_stale_investigations",
        kwargs={"investigation_timeout": settings.internal.router.investigation_timeout},
    )


__all__ = ["register_tasks"]
