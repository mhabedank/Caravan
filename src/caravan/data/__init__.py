"""Resolving and reading the dataset a manifest names.

Two things live here that must not be confused, and are deliberately in different modules:

``fingerprint`` resolves a reference and identifies the data by hashing its bytes. It is core: the
stage cache has to answer "did the dataset change" on an installation with no training framework,
and a content hash answers it honestly where a modification time does not.

``reader`` turns records into arrays. It imports ``numpy`` and is therefore reachable only with
the ``train`` extra installed. Nothing in the core imports it.
"""
