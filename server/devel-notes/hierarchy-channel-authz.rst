*******************************
Hierarchy Channel Authorisation
*******************************

The hierarchy channel (``machination:hierarchy``) is the channel used
to authorise actions on the hierarchy itself. As such it is treated
somewhat specially.

``authz-inst``s are still grouped and attached to hcs. The ``mpath``
field has meaning *relative to the current hc*.

Representation
==============

Representation
--------------

* contents of hc in ``contents``
* attachments in ``attachments``
* hc fields: ``fields[fieldname]``
* objects specified by ``type[id]``
* object fields specified by ``type[id]/fields[fieldname]``

Authz Xpaths
------------

Consider the hollowing hierarchy tree (showing contents only):

+ machination:root/
|
--+ child1/
  |
  |- set:splat (has id 1)
  |
  --+ grandchild1/
|
--+ system/
  |
  --+ special/
    |
    --+ authz/
      |
      --+ objects/

* all contents: ``contents/*``
* all child hcs: ``contents/hc``
* all children of type set: ``contents/set``
* set 'splat' by id relative to /child1: ``contents/set[@id="1"]``
* same set relative to /:
  ``contents/hc[@id="child1"]/contents/set[@id="1"]``
* same set by name relative to /child1:
  ``contents/set[field[@id="name"]/text()="splat"]``
* all descendants (authz_inst): ``contents//*``

/sytem/special/authz/objects
----------------------------

When queried for authz purposes, this hc acts as if it has every
object in it. Further, any request will be checked against this hc
directly and then against all of the parent hcs in which the object in
question exists.

For example, to establish or reset a trust link with ( = get a new
signed certificate from or 'join') a Machination service, the user
attempting the join (joiner) needs 'settext' permission on the
'reset_trust' field of that object, but the hpath to the object is not
known. If you'd like to give this permission to someone for all
os_instance objects, this could be specified with either:

* authz_inst attached to /

  * op: settext
  * xpath: //contents/os_instance/fields[@id="reset_trust"]
  * is_allow: true

or:

* authz_inst attached to /sytem/special/authz/objects

  * op: settext
  * xpath: /contents/os_instance/fields[@id="reset_trust"]
  * is_allow: true

The joining script asks for permission (say for os_instance 12):

* op: settext
* hc: /system/special/authz/objects
* mpath: /contents/os_instance[12]/field[reset_trust]

