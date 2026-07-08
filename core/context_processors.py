from core.models import Module

# The nav-gated feature modules. (home/bugometro/profile are always-on core
# screens and never appear here.)
MODULE_CANDIDATES = {"catalog", "community", "alerts"}


def modules(request):
    """Expose ``visible_modules``: the set of module keys whose nav link
    should be shown. A module is visible unless a ``Module`` row exists for
    it with ``enabled=False`` (unknown modules default to visible).

    Django templates can't call a lambda with an argument, so instead of a
    ``module_on(key)`` callable we expose a set the template tests with
    ``{% if 'community' in visible_modules %}``.
    """
    disabled = set(Module.objects.filter(enabled=False).values_list("key", flat=True))
    return {"visible_modules": MODULE_CANDIDATES - disabled}
