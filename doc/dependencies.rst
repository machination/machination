*************************
Inter Status Dependencies
*************************

The hierarchy service can contain *dependency* assertions. These
assertions may result in pieces of XML either being included or
excluded from the compiled profile without explicit instruction to do
so. For example, the XML representing package A may be inserted
because package B was chosen from a library and B asserts a 'requires'
dependency on A.

Most dependencies assert only the existence or lack of some xpath and
are fully resolved at the server end, never to be seen by the
client. The xpath need either exist in the profile or not. Some
dependencies, however, must be realised on the client in a certain
order. For example, a plugin for A might have to be installed after A
has been installed. Such dependencies are labelled *ordered*
dependencies and they are written into the profile so that ``update``
may calculate which units of work must come before others.

Client Side Dependencies
========================

.. literalinclude:: example-profile-dependencies.xml
   :language: xml
   :linenos:

sub
----------------------------------------------

subsub
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

subsubsub
"""""""""
