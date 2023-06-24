Python VHS
==========

Python-VHS is a tiny python wrapper around VHS_,
a tool by charm_ that renders terminal commands into GIFs.

This package searches for VHS and its dependencies
in system's ``PATH``, and invokes them.
On Linux, if VHS is not found in the system,
Python-VHS can download necessary binaries from GitHub.

.. _VHS: https://github.com/charmbracelet/vhs

.. _charm: https://charm.sh/

Quickstart
----------

Install VHS:

.. code-block:: shell

   pip3 install vhs

Then resolve VHS binary and run it:

.. code-block:: python

   import vhs

   vhs_runner = vhs.resolve()
   vhs_runner.run('./example.tape', './example.gif')

Reference
---------

.. automodule:: vhs
