from pattern_stack.atoms.patterns.services import BaseService

from .models import Job
from .schemas.input import JobCreate, JobUpdate


class JobService(BaseService[Job, JobCreate, JobUpdate]):  # type: ignore[misc]
    model = Job
