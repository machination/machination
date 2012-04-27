*******************
Machination Workers
*******************

The main Machination program, ``update``, compares an input describing
the *desired* state of the system with another describing its
*current* state. Any differences are changes that need effected: work,
in other words. The modules or programs that carry out this work are
called *workers*.

Making New Workers
==================

Workers are the easiest part of Machination to extend: they have a
well defined job to do and a well defined, simple interface to the
rest of Machination. They are also the route through which all changes
are made to the target system, so they provide the most direct link to
the things you are likely to want to do.

Introduction to the Update <-> Worker Workflow
----------------------------------------------

The main Machination program is called ``update`` (perhaps more
completely ``update.py``). It runs at various times, like when the OS
boots or whenever a change is made on the configuration
server(s). Whenever ``update`` runs it compares the desired state of
the system (as compiled from the Machination services to which it is
subscribed) to the current state of the system (as reported by the
installed workers). ``update`` then calculates the differences between
these two states and parcels them up into pieces of work to do, called
*work units* [#wuwu]_. ``update`` also sorts the list of work
according to any dependencies between work units before finally
invoking workers to do the work.



Update <-> Worker Interface Details
-----------------------------------

Workers should support a number of *method* calls. The input to and
output from all methods is XML.

#. ``generate_status``
#. ``do_work``

Only ``do_work`` need have a full implementation. Any method which a
worker does *not* implement should be indicated in one of the
following ways:

* No method definition in a python worker.
* Return the following XML for a non python worker:

.. code-block:: xml

    <return method="$method" implemented="0"/>

* A special return value as specified by the method documentation.


Python Workers vs. Other Language Workers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Python Workers
""""""""""""""

Python workers will be instantiated as
``machination.workers.[workername].Worker`` objects and the methods
called with an ``lxml.etree.Element`` object as their arguments. When
asked to return XML, they should return an ``lxml.etree.Element``
object.

Python example for worker 'dummyordered' (a worker created for test,
bebugging and illustrative purposes):

In file ``machination/workers/dummyordered/__init__.py`` somewhere in
the python library path...

.. code-block:: python
  :linenos:

  # Machination is nearly all XML. You'll probably need this...
  from lxml import etree

  # We haven't used context in this example, but you'll probably need
  # it at least for the logger
  from machination import context

  class Worker(object):
    """dummyordered Machination worker"""

    def __init__(self):
      # The worker name is used at several points. The following line
      # autodiscovers it (from the module name). That means if you
      # copy this code as a worker template it should work.
      self.name = self.__module__.split('.')[-1]

      # Worker descriptions are described later
      self.wd = xmltools.WorkerDescription(self.name,
                                           prefix = '/status')

    def generate_status(self):
      """find status relavent to this worker"""

      # The following will create a 'worker' element with id
      # self.name. I.e. XML of the form:
      #
      #   <worker id='workername'/>
      st_elt = etree.Element("worker")
      st_elt.set('id', self.name)

      # find the status and fill in st_elt here

      return st_elt

    def do_work(self, wus):
      """Change system status as dictated by work units in 'wus'

      Args:
        wus: an etree element whose children are all 'wu' elements.
      """

      # Create a results element to fill in
      results = etree.Element('results')

      # Iterating over an etree element iterates over its children
      for wu in wus:
        # Do something Muttley!
        pass # so this code compiles if copied

      return results

And in ``machination/update.py``...

.. code-block:: python
    :linenos:
    :emphasize-lines: 8,9,15,21

    # somewhere to store current status
    current_status = lxml.etree.Element("status")

    # iterate through the workers and find current worker status
    for worker_name in some_list_of_workers:

        # make a Worker object
        wmodname = 'machination.workers.' + name
        worker = importlib.import_module(wmodname).Worker()

        # store the workers for later
        workers[worker_name] = worker

	# This is how generate_status() is called
        worker_current_status = worker.generate_status()

	# add the worker status to the global status
        current_status.append(worker_current_status)

    # ...
    # Some magic to compare desired status with current status goes
    # here. Required changes are generated (basically an XML-wise diff)
    # ...

    # ...
    # Dependency calculations are done and the changes are ordered and
    # then encoded as units of work (workunits, or 'wus') for the
    # workers.
    # ...

    # Iterate through all work unit parcels generated above and hand
    # them to the appropriate workers. These have the form:
    #
    # <wus worker='workername'>
    #   <wu id='xpath-to-change' op='add|remove|datamod|deepmod|move'>
    #     <!-- some types of wu (add, *mod) have data in here -->
    #   </wu>
    #   ...
    # </wus>
    for p in work_parcels:
      results = workers[p.get('worker')].do_work(p)

Lines 8 and 9 illustrate how your module is loaded and the worker
object instantiated. Line 15 shows an invokaction of
``generate_status()``, and line 21 shows an invokation of
``do_work()``.

Other Language Workers
""""""""""""""""""""""

Workers implemented in other languages (OL workers) will be handed
their input as an XML string on ``STDIN``. The input will be
encapsulated in a ``<call>`` element describing which method is being
invoked. They should return serialised XML on ``STDOUT``.

The ``generate_status`` call:

.. code-block:: xml

  <!-- only for OL workers: python workers will have the
       generate_status method called with no arguments -->
  <call method="generate_status"/>

Example abridged ``generate_status`` return from the tweaks worker:

.. code-block:: xml

    <!-- outer 'return' element only for OL workers -->
    <return method="generate_status">
      <worker id="tweaks">
        <Time>
	  <NtpEnabled>0</NtpEnabled>
	</Time>
	<automaticUpdates>
          <NoAutoReboot>0</NoAutoReboot>
	</automaticUpdates>
      </worker>
    </return>

Example abridged ``generate_status`` return from the packageman
worker:

.. code-block:: xml

  <!-- outer 'return' element only for OL workers -->
  <return method="generate_status">
    <worker id="packageman">
      <package id="emacs-23-1">
        <install type="msi"
	    startPoint="emacs-23.msi"
	    transform="some-transform.mst"/>
	<info displayName="GNU Emacs 23"/>
      </package>
    </worker>
  </return>

Example ``do_work`` call to the tweaks worker

.. code-block:: xml

    <!-- outer 'call' element only for OL workers -->
    <call method="do_work">
      <wus worker='tweaks'>
        <wu id="/Time/NtpEnabled" op="modify">
          <NtpEnabled>1</NtpEnabled>
        </wu>
        <wu id="/Time/TimeServer1" op="add">
          <TimeServer1>timeserver1</TimeServer1>
        </wu>
        <wu id="/AutomaticUpdates/NoAutoReboot" op="modify">
          <NoAutoReboot>1</NoAutoReboot>
        </wu>
      </wus>
    </call>

Example ``do_work`` return from tweaks.

.. code-block:: xml

    <!-- outer 'return' element only for OL workers -->
    <return method="do_work">
      <results>
        <wu id="/Time/NtpEnabled" status="success"/>
        <wu id="/Time/TimeServer1" status="error" message="something"/>
      </results>
    </return>


Work Units
----------

A worker's state (current or desired) is represented by XML. This in
turn is a representation of some aspect of the system: printers,
packages, firewall rules and so on. When the current and desired
states are different, something needs to be done. A package may need
to be added or removed or a firewall rule changed. For the most part,
an individual element or attribute of XML is too small a detail to
change on its own - it is likely to be a piece of information related
to a larger logical unit which the worker operates on as a whole.

For example, the ``printerman`` worker may have status XML that looks
like this:

.. code-block:: xml
  :linenos:
  :emphasize-lines: 3

  <worker id='printerman'>
    <printer id='queue1'>
      <displayName>Friendly Name 1</displayName>
      <!-- some other details -->
    </printer>
    <!-- other printers -->
  </worker>

and operate on ``/worker/printer`` elements as logical units since
they are the full representations of printers.

Now lets say we want to change the status to the following:

.. code-block:: xml
  :linenos:
  :emphasize-lines: 3

  <worker id='printerman'>
    <printer id='queue1'>
      <displayName>Another Name</displayName>
      <!-- some other details -->
    </printer>
    <!-- other printers -->
  </worker>

So we've changed the ``/worker/printer[queue1]/displayName`` element's
content to 'Another Name'. The ``update`` program now has to tell
``printerman`` that something has changed. ``printerman`` only
operates on whole printers, so ``update`` should tell ``printerman``
that ``/worker/printer[queue1]`` has changed - an ancestor of
``/worker/printer[queue1]/displayName``. Xpaths of the form
``/worker/printer`` are the *work units* of ``printerman``.

To collect the XML-wise changes into work units properly, ``update``
needs to know which xpaths a given worker thinks of as units of
work. To do this it will look at a worker's worker description file
(see :ref:`workerdesc`). If there is no worker description file, or if
no work units are defined in it, then all direct child elements of
``/worker`` are assumed to be valid work units and all others are not.

Now that ``update`` knows which xpaths to treat as work units (wus),
it needs to communicate what has changed to the worker. In Machination
wus are codified as one of five types of change:

``add``
^^^^^^^

The wu element needs to be added. This usually corresponds to an
object (package, printer, environment variable) being added to the
system. The wu element will contain the XML to be added and a ``pos``
attribute indicating the relative xpath of an existing sibling to be
added after (where ordering is important). The special relative xpath
'<first>' indiciates that the element should be added as the first
child of its parent.

.. code-block:: xml

  <!-- add emacs after vi -->

  <wu id='/status/worker[@id="packageman"]/package[@id="emacs"]'
      op='add'
      pos='package[@id="vi"]'>
    <package id='emacs'>
      <!-- package information -->
    </package>
  </wu>

``remove``
^^^^^^^^^^

The wu element needs to be removed. This usually corresponds to an
object (package, printer, environment variable) being removed from the
system.

.. code-block:: xml

  <!-- remove word -->

  <wu id='/status/worker[@id="packageman"]/package[@id="word"]'
      op='remove'/>

``move``
^^^^^^^^

The wu element needs to be moved (the element is present in both
current and desired status but not in the same position). This is only
relevant for workers where the order of items is important (for
example the order of firewall rules). The ``id`` attribute contains
the absolute xpath of the element to be moved, the ``pos`` attribute
contains the xpath of the sibling it is to be placed after, relative
to their parent. The special relative xpath '<first>' indicates that
the element should be placed as the first child of the parent.

.. code-block:: xml

  <!-- move vi after emacs -->

  <wu id='/status/worker[@id="packageman"]/package[@id="vi"]'
      op='move'
      pos='package[@id="emacs"]'>

``datamod``
^^^^^^^^^^^

The wu element's text (but nothing else) needs to be modified.

.. code-block:: xml

  <!-- change environment variable 'LICENSE_SERVER' to
    'server1.example.com' -->

  <wu id='/status/worker[@id="environment"]/var[@id="LICENSE_SERVER"]'
      op='datamod'>
    <var id='LICENSE_SERVER'>server1.example.com</var>
  </wu>

``deepmod``
^^^^^^^^^^^

Something other than (but possibly including) the wu element's text has
been modified. It may have had attributes changed or its children may
have changed.

.. code-block:: xml

  <!-- deep modify the XML representing an ini file -->

  <wu id='/status/worker[@id="example"]/inifile[@id="something"]'
      op='deepmod'>
    <inifile id="something">
      <comment>This file does nothing</comment>
      <section id='section 1'>
        <keyvalue id='key1.1'>value1.1</keyvalue>
        <keyvalue id='key1.2'>value1.2</keyvalue>
      </section>
      <section id='section 2'>
        <keyvalue id='key2.1'>value2.1</keyvalue>
        <keyvalue id='key2.2'>value2.2</keyvalue>
      </section>
    </inifile>
  </wu>

.. caution::
   If there are work unit descendants of a ``deepmod`` workunit, they
   will be sent separately. To prevent work from being done again, the
   ``deepmod`` wu will be constructed *with the wu descendant elements
   removed.* For example, if the example worker above is capable if
   changing individual sections without re-writing the entire file, it
   might designate ``inifile/section`` elements as wus. In that case,
   the same changes that resulted in the wu given above would instead
   generate something like:

   .. code-block:: xml

     <wus worker="example">
       <wu id='/status/worker[@id="example"]/inifile[@id="something"]'
           op='deepmod'>
         <inifile id='something'>
           <comment>This file does nothing</comment>
         </inifile>
       <wu>
       <wu id='/status/worker[@id="example"]/inifile[@id="something"]/section[@id="section 1"]'
           op='add'
           pos='<first>'>
         <section id='section 1'>
           <keyvalue id='key1.1'>value1.1</keyvalue>
           <keyvalue id='key1.2'>value1.2</keyvalue>
         </section>
       </wu>
       <wu id='/status/worker[@id="example"]/inifile[@id="something"]/section[@id="section 2"]'
           op='deepmod'>
         <section id='section 2'>
           <keyvalue id='key2.1'>value2.1</keyvalue>
           <keyvalue id='key2.2'>value2.2</keyvalue>
         </section>
       </wu>
     </wus>

   where the changes are assumed to have come from an ``add`` of
   section 1 and a ``deepmod`` of section 2.

.. _workerdesc:

Worker Description Files
------------------------


Status Description Files
^^^^^^^^^^^^^^^^^^^^^^^^

Configuration Description Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^





.. rubric:: Footnotes

.. [#wuwu] Also known as wu:wus (pronounced 'woo-woo') because of
   the way they are commonly marked up in worker description files.
