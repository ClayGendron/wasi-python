"""Seen failing first (spec 085): today's gather, fed the new synthetic set; the three new Inputs
fields are dropped, since today's gather has none of them."""
import dataclasses


def pytest_configure(config):
    from harness import gather

    real = gather.Inputs
    names = {f.name for f in dataclasses.fields(real)}

    def shim(**kw):
        return real(**{k: v for k, v in kw.items() if k in names})

    gather.Inputs = shim
