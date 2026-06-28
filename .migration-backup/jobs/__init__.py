"""Jobs package — distributed Celery job submission and result polling.

Avoid importing submodules at package import time to prevent name shadowing
(`jobs.job_router` should be the module, not an APIRouter instance). Tests
import the module object and expect to access its `router` attribute; if the
package binds a symbol `job_router` to the router instance, `import
jobs.job_router` will return the APIRouter object instead of the module.
"""

__all__ = ["job_router"]
