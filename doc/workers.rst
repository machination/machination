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
worker does *not* implement should return the XML::

    <return method="$method" implemented="0"/>


Python Workers vs. Other Language Workers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Python workers will be instantiated as objects and the methods called
with an ``lxml.etree.Element`` object as their only argument. They should
return an ``lxml.etree.Element``.

Python example:

Pythonish pseudocode for what happens in ``update``:

.. code-block:: python
    :linenos:
    :emphasize-lines: 8,24

    # somewhere to store current status
    global_current_status = lxml.etree.Element("status")

    # iterate through the workers and find current worker status
    for worker_name in some_list_of_workers:
        worker = machination.workers.worker_name()
	# This is how generate_status() is called
        worker_current_status = worker.generate_status()

	# use the last stored worker status if the worker can't
	# generate_status
	if worker_status.get("implemented") == 0:
	    worker_current_status = last_status(worker_name)
	
	# add the worker status to the global status
	add_status(worker_current_status,global_current_status)

    # iterate through all work units
    work_iter = get_work_units(get_desired_status(),global_current_status)
    work_batch = [work_iter.next()]
    for wuwu in work_iter:
    	if get_worker_name(work_batch[-1]) == get_worker_name(wuwu):
	    # the same worker as last time - add wuwu to current batch
	    work_batch.append(wuwu)
	else:
	    # different worker, call what we have batched and reset
	    worker = machination.workers.worker_name()
	    # this is how do_work is called
	    results = worker.do_work(generate_work_xml(work_batch))
	    deal_with_results(results)
	    work_batch = [wuwu]

Lines 8 and 29 call the workers' ``generate_status`` and ``do_work``
methods respectively.

Workers implemented in other languages will be handed their input as
an XML string on ``STDIN``. The input will be encapsulated in a
``<call>`` element describing which method is being invoked. They
should return serialised XML on ``STDOUT``:

.. code-block:: xml

    <call method="generate_status"/>

.. code-block:: xml

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

.. code-block:: xml

    <call method="do_work">
      <wu id="/Time/NtpEnabled">
        <NtpEnabled>1</NtpEnabled>
      </wu>
      <wu id="/Time/TimeServer1">
        <TimeServer1>timeserver1</TimeServer1>
      </wu>
      <wu id="/AutomaticUpdates/NoAutoReboot">
        <NoAutoReboot>1</NoAutoReboot>
      </wu>
    </call>

.. code-block:: xml

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

.. [#wuwu] Also known as ``wu:wu``s (pronounced 'woo-woo') because of
   the way they are commonly marked up in worker description files.
