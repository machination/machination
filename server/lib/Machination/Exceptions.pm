package Machination::Exceptions;

# Copyright 2008 Colin Higgs and Matthew Richardson
#
# This file is part of Machination.
#
# Machination is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Machination is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Machination.  If not, see <http://www.gnu.org/licenses/>.

use Exception::Class
  (
   MachinationException =>
   {
    description => "Machination generic exception",
   },
   OperationException =>
   {
    isa => "MachinationException",
    description => "Exception when applying an operation/revision",
   },
   ObjectException =>
   {
    isa=> "MachinationException",
    description => "Exception handling machination object",
    fields=>['otype','oid'],
   },
   ObjectDoesNotExistException =>
   {
    isa=> "ObjectException",
    description => "An object id was used which does not exist",
   },
   NoSuchTypeException =>
   {
    isa=> "ObjectException",
    description => "There is no type with the specified name or id",
    fields=>["type"],
   },
   EntityException =>
   {
    isa => "MachinationException",
    description => "Entity Exception",
   },
   DuplicateEntityException =>
   {
    isa => "EntityException",
    description => "Duplicate Entity Exception",
   },
   AuthzException =>
   {
    isa => "MachinationException",
    description => "Authorisation Exception",
   },
   AuthzDeniedException =>
   {
    isa=> "AuthzException",
    description=>"Permission denied",
   },
   AuthzConditionException =>
   {
    isa => "AuthzException",
    description => "Authorisation Condition Exception",
   },
   AuthzEntitiesException =>
   {
    isa => "AuthzException",
    description => "Authorisation Entities Exception",
   },
   SetException =>
   {
    isa => "MachinationException",
    description => "Set error",
   },
   MemberNotAllowedException =>
   {
    isa => "SetException",
    description => "Member not allowed in set",
   },
	 DBException =>
   {
    isa => "MachinationException",
    description => "DBConfig Exception",
   },
	 DBSourceStringException =>
   {
    isa => "DBException",
    description => "Error constructing the DBI string",
   },
	 DBIException =>
   {
    isa => "DBException",
    description => "Exception talking to database",
    fields => "ex_object",
   },
	 XMLException =>
   {
    isa => "MachinationException",
    description => "XML exception",
   },
   XMLParseException =>
   {
    isa => "XMLException",
    description => "XML parsing exception",
   },
   HierarchyException =>
   {
    isa => "MachinationException",
    description => "Hierarchy Exception",
   },
   HierarchyNameExistsException =>
   {
    isa=>"HierarchyException",
    description => "Tried to add an object to a container where the " .
    "name already exists\n",
   },
   HierarchyMTreeException =>
   {
    isa=>"HierarchyException",
    description => "Operation violates merge tree rules\n",
   },
   MalformedPathException =>
   {
    isa => "HierarchyException",
    description => "Malformed Path Exception",
   },
   AttachmentException =>
   {
    isa=>"HierarchyException",
    description => "Attachment exception\n",
   },
   CompilerException =>
   {
    isa => "MachinationException",
    description => "Profile Compiler Exception",
   },
   NonUniqueXPathException =>
   {
    isa => "CompilerException",
    description => "Non unique XPath provided",
   },
   NonConstructablePathException =>
   {
    isa => "CompilerException",
    description => "Could not auto-construct XPath",
   },
   WebException =>
   {
    isa => "MachinationException",
    description => "Machination web service exception",
   },
   ConfigException =>
   {
    isa => "MachinationException",
    description => "Configuration exception",
   },
   SvcException =>
   {
    isa => "MachinationException",
    description => "Service exception",
   }
  );

1;
