"""The stages, the projection that feeds them, and the cache that lets a result be reused.

All core. A stage that needs a training framework loads it by name when it runs, so that
``import caravan.stages.train`` stays harmless in a default installation — the layering tests of
feature 001 assert exactly that, and they do it for these modules too.
"""
