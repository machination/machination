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
      <wu id="/Time/NtpEnabled" op="modify">
        <NtpEnabled>1</NtpEnabled>
      </wu>
      <wu id="/Time/TimeServer1" op="add">
        <TimeServer1>timeserver1</TimeServer1>
      </wu>
      <wu id="/AutomaticUpdates/NoAutoReboot" op="modify">
        <NoAutoReboot>1</NoAutoReboot>
      </wu>
    </call>

Example ``do_work`` return from tweaks.

.. code-block:: xml

    <!-- outer 'return' element only for OL workers -->
    <return method="do_work">
      <wu id="/Time/NtpEnabled" status="success"/>
      <wu id="/Time/TimeServer1" status="error" message="something"/>
    </return>

Information Given on All Method Calls
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


The ``generate_status`` Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Input
"""""

Output
""""""

Example
"""""""


The ``do_work`` Method
^^^^^^^^^^^^^^^^^^^^^^

Input
"""""

Output
""""""

Example
"""""""


Configuration Information
^^^^^^^^^^^^^^^^^^^^^^^^^


Worker Description Files
------------------------


Status Description Files
^^^^^^^^^^^^^^^^^^^^^^^^

Configuration Description Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^





.. rubric:: Footnotes

.. [#wuwu] Also known as wu:wus (pronounced 'woo-woo') because of
   the way they are commonly marked up in worker description files.
