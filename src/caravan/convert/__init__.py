"""Converting a trained model into the form a microcontroller runs.

Behind the ``train`` extra, and therefore Python 3.13: conversion needs the training framework, and
there is no framework-free converter today — the standalone runtime package is a runtime, and the
vendor's own conversion documentation describes only the framework path (checked 2026-10-22). That
is the answer to the question the Technical Baseline left open, and it is why the published floor
stays where feature 002 put it.

What this package must never do is *describe* what it produced. That is ``caravan.runtime.inspect``
reading the file, for the reason written at the top of that module.
"""
