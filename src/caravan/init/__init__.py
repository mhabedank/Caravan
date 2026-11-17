"""``caravan init``: a guided way to write the manifest (feature 013).

One question engine (``session``) with two front ends: the line dialogue here (``line``) and the
full-screen interface of the ``authoring`` extra (``caravan.tui``). Everything in this package runs
in the default installation: the standard library and Caravan's core only. It never imports the
YAML library directly (only through ``caravan.manifest._yaml``), never a training framework, and
never ``caravan.tui`` — the layering tests hold it to that.
"""
