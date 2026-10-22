"""Quality metrics, computed here rather than by a dependency.

The whole set is a confusion matrix and about thirty lines of arithmetic over it. Principle XII is
explicit that code the project could own in a few hundred readable lines must not become a
dependency, and pulling in a general machine-learning library for ``f1_score`` is the textbook
case of that.

Behind the ``train`` extra: it imports ``numpy``.
"""
