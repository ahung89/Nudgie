from .celery import app as celery_app

# This variable defines the public interface for this package. When you use a wildcard import,
# e.g. from Nudgie import *, this is the list of names that will be imported. If __all__ is not
# defined, then the wildcard will import all names that do not begin with an underscore.
# In this case __all__ is defined as celery_app, so if someone writes from Nudgie import *, then only
# celery_app will be imported. It's good practice to define __all__ to prevent unintended imports.
__all__ = ('celery_app',)