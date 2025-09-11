from celery import Celery

from app.configs import Settings
from app.container import container
from app.logs import configure_logger


def create_celery_app() -> Celery:
    with container.sync_context() as ctx:
        settings: Settings = ctx.resolve(Settings)

    app = Celery(
        "digitalsec",
        broker=f"redis://:{settings.external.redis.password}@{settings.external.redis.host}:{settings.external.redis.port}/{settings.external.redis.database}",
        backend=f"redis://:{settings.external.redis.password}@{settings.external.redis.host}:{settings.external.redis.port}/{settings.external.redis.database}",
        include=["app.tasks.routes"],
    )

    configure_logger(
        enabled=settings.internal.log.enable, log_level=settings.internal.log.level, log_file=settings.internal.log.file
    )

    app.conf.update(
        task_soft_time_limit=settings.internal.router.investigation_timeout,
        task_time_limit=settings.internal.router.investigation_timeout + 60,
        worker_hijack_root_logger=False,
        worker_redirect_stdouts=False,
    )

    app.conf.beat_schedule = {
        "check-stale-investigations": {
            "task": "app.tasks.routes.check_stale_investigations",
            "schedule": settings.internal.router.investigation_timeout,
        },
        "process-pending-routes": {
            "task": "app.tasks.routes.process_pending_routes",
            "schedule": 30.0,
        },
    }

    return app


celery_app = create_celery_app()
