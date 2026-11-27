"""``caravan init``: a first manifest from one proposal (features 013 and 015).

One question engine (``session``), the proposal it makes (``proposal``) and one front end, the line
mode (``line``). Everything in this package runs in the default installation: the standard library
and Caravan's core only. It never imports the YAML library directly (only through
``caravan.manifest._yaml``) and never a training framework — the layering tests hold it to that.
"""
