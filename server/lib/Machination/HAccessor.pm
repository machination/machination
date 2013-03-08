use strict;
package Machination::HAccessor;

# Copyright 2010 Colin Higgs
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

use Carp;
use File::Temp qw(tempfile);
use Exception::Class;
use Machination::Exceptions;
use Machination::DBConstructor;
use Machination::HPath;
use Machination::HSet;
#use Machination::HObjSet;
#use Machination::HAuthzSet;
use Text::ParseWords;
use XML::LibXML;
use Machination::XML::Element;
use Machination::XMLConstructor;
use Machination::Log;
use Machination::XML2Assertions;

use Data::Dumper;

# TODO: this lot should really be moved to one of the bootstrap_*.xml files
my $defops =
	{
	 add_object_type => "add a new object type",
   add_setmember_type=>"",

	 add_channel => "add a new channel",
#	 svc_subscribe => "subscribe object type to service",

	 create_obj => "create_obj (\$type_id,\$name,\$parent,\$fields): Create a new object in specified parent",
   modify_obj => "modify_obj (\$type_id,\$obj_id,{\$field=>\$value,...}): change object data",
	 delete_obj => "delete_obj (\$type_id,\$obj_id)",
   create_path => "create_path(\$path,\$fields): recursively create path",
   assertion_group_from_xml => "create an assertion group populated with assertions derived from XML",

   add_valid_os => "",
   delete_valid_os => "",

	 add_to_hc => "add_to_hc (\$type_id,\$obj_id,\$parent)",
	 remove_from_hc => "remove_from_hc (\$type_id,\$obj_id,\$parent)",
	 move_hc => "move_hc (\$type_id,\$obj_id,\$from,\$to)",

	 attach_to_hc => "",
   modify_attachment => "",
	 detach_from_hc => "",
	 create_agroup=>"",
	 add_to_agroup=>"",
	 remove_from_agroup=>"",

	 add_to_set=>"",
	 remove_from_set=>"",
#	 set_special_set=>"",
   add_valid_condition_op=>"",
   add_set_direct_condition=>"",
   remove_set_direct_condition=>"",

   add_valid_action_op=>"",
   delete_valid_action_op=>"",
   add_valid_assertion_op=>"",
   delete_valid_assertion_op=>"",

#   create_action=>"",
#   modify_action=>"",
#   delete_action=>"",
#   tag_action=>"",
#   create_assertion=>"",
#   modify_assertion=>"",
#   delete_assertion=>"",
#   add_valid_lib_assertion_op=>"",
#   delete_valid_lib_assertion_op=>"",
	};

my $def_obj_types =
	[
	 {name=>"set", plural=>"sets",
    is_attachable_noag=>1,
		cols=>[["is_internal","boolean",{nullAllowed=>0}],
           ["member_type","varchar",{nullAllowed=>0}],
           ["direct","varchar"],
					 ["expression","varchar"]],
		fks=>[{table=>"setmember_types",cols=>[["member_type","type"]]}],
	 },
	 {name=>"person", plural=>"people",
		is_entity=>1,
		cols=>[
					 ["display_name","varchar"],
					 ["sn","varchar"],
					 ["given_name","varchar"],
					 ["unix_uid","bigint"],
					 ["uname","varchar"],
					],
	 },
   {name=>"os_instance", plural=>"os_instances",
    is_entity=>1,
    cols=>[
           ["os_id",Machination::DBConstructor::IDREF_TYPE,{nullAllowed=>0}],
          ],
    fks=>[
					{table=>"valid_oses",cols=>[["os_id","id"]]},
				 ],
   },
   {name=>"assertion",plural=>"assertions",
    is_attachable=>1,
    libraries=>1,
    cols=>[
           ["mpath","varchar",{nullAllowed=>0}],
           ["ass_op","varchar",{nullAllowed=>0}],
           ["ass_arg","varchar"],

           ["action_op","varchar",{nullAllowed=>0}],
           ["action_arg","varchar"],
          ],
    fks=>[
          {table=>"valid_assertion_ops",cols=>[["ass_op","op"]]},
          {table=>"valid_action_ops",cols=>[["action_op","op"]]}
         ],
   },
#   {name=>"lib_assertion",plural=>"lib_assertions",
#    is_attachable=>1,
#    cols=>[
#           ["op","varchar",{nullAllowed=>0}],
#           ["item","varchar",{nullAllowed=>0}],
#           ["arg","varchar"],
#          ],
#    fks=>[
#          {table=>"lib_assertion_ops",cols=>[["op","op"]]},
#         ],
#   },
	 {name=>"conf_inst",plural=>"conf_insts",
		is_attachable=>1,
		cols=>[
					 ["op","varchar"],
					 ["elt_path","varchar"],
					 ["args","varchar[]"],
					],
	 },
	 {name=>"authz_inst",plural=>"authz_insts",
		is_attachable=>1,
		cols=>[
					 ["is_allow","boolean",{nullAllowed=>0}],
					 ["entities","varchar",{nullAllowed=>0}],
					 ["op","varchar",{nullAllowed=>0}],
					 ["xpath","varchar",{nullAllowed=>0}],
#					 ["pattern","varchar"],
					],
    fks=>[
          {table=>"valid_action_ops",cols=>[["op","op"]]}
         ],
	 },
	 {name=>"mpolicy", plural=>"mpolicies",
		is_attachable=>1,
		cols=>[
					 ["mpath","varchar"],
					 ["policy_direction","smallint"],
					],
    cons=>[
           {type=>"general","check (1 >= policy_direction and policy_direction >= -1)"},
          ],
	 },
	 {name=>"dep", plural=>"dependencies",
		cols=>[
					 ["source",Machination::DBConstructor::IDREF_TYPE,{nullAllowed=>0}],
					 ["target",Machination::DBConstructor::IDREF_TYPE,{nullAllowed=>0}],
					 ["op","varchar(8)",{nullAllowed=>0}],
					 ["ordered","boolean",{nullAllowed=>0}],
					],
		fks=>[
					{
           objtable=>"agroup_conf_inst",cols=>[["source","id"]]},
					{
           objtable=>"agroup_conf_inst",cols=>[["target","id"]]},
				 ],
	 },
	 {name=>"search", plural=>"searches",
		cols=>[
					 ["search_for","varchar"],
					],
	 },
   {name=>"cert",plural=>"certs",
    cols=>[
           ["public","varchar"],
           ["private","varchar"],
           ["passphrase","varchar"],
          ],
    },
	];

#@Machination::HAccessor::ISA = qw(Machination::DBConstructor);

=pod

=head1 Machination::HAccessor

=head2 Access Machination database using application level operations

=head2 Synopsis

    $ha = Machination::HAccessor->new("/path/to/config/file");

=head2 Machination::HAccessor

=head3 Methods:

=over

=item B<new>

$ha = Machination::HAccessor->new($conf)

Create a new Machination::HAccessor

=cut

sub new {
	my $class = shift;
	my ($conf,$log,$dodgy_libxml) = @_;
	my $self = {};
	bless $self,$class;

	$self->dbc(Machination::DBConstructor->new($conf)) if($conf);
  $self->dbc->dbh->{RaiseError} = 1;
	$self->defops($defops);
	$self->def_obj_types($def_obj_types);
  $self->{type_info} = {};
  unless (defined $log) {
    $log = Machination::Log->new;
    my $elt = ($self->dbc->conf->doc->
      getElementById("subconfig.haccess")->findnodes("log"))[0];
#    print "starting logging to " . $self->dbc->conf->get_file("file.haccess.LOG") . "\n";
    $elt->appendTextChild("logFile",
                          $self->dbc->conf->get_file("file.haccess.LOG"));
    $log->from_xml($elt);
  }
  $self->log($log);
  $self->log->dmsg("HAccessor","*" x 27,1);
  $self->log->dmsg("HAccessor","*" x 10 . " START " . "*" x 10,1);
  $self->log->dmsg("HAccessor","*" x 27,1);

  $self->dodgy_libxml($dodgy_libxml);

	return $self;
}

sub log {
  my $self = shift;

  if(@_) {
    $self->{log} = shift;
  }
  return $self->{log};
}

=item B<dodgy_libxml>

=cut

sub dodgy_libxml {
  my $self = shift;

  if(@_) {
    $self->{dodgy_libxml} = shift;
  }
  return $self->{dosgy_libxml};
}

=item B<dlev>

$ha->dlev($debuglevel)

=cut

sub dlev {
  my $self = shift;

  if(@_) {
    $self->{dlev} = shift;
  }
  return $self->{dlev};
}

=item B<authen_str_to_object>

($type,$id) = $ha->authen_str_to_object($str)

=cut

sub authen_str_to_object {
  my $self = shift;
  my $str = shift;
  my $opts = shift;

  my ($type_name, $name) = split(/:/, $str);
  my $id = $self->entity_id($self->type_id($type_name), $name);
  $id ? return ($self->type_id($type_name),$id) : return;
}

=item B<entity_id>

$id = $ha->entity_id($type_id, $name);

=cut

sub entity_id {
  my $self = shift;
  my ($tid, $name, $opts) = @_;

  HierarchyException->throw
    ("cannot find entity id of non entity type " . $self->type_name($tid))
      unless $self->type_info($tid)->{is_entity};

	my $info = $self->fetch("objs_$tid",
													{fields=>["id"],
													 condition=>"name=?",
													 params=>[$name],
													 revision=>$opts->{revision}});
  $info ? return $info->{id} : return;
}

=item B<do_op>

$ha->do_op($op,$opts,@args)

Wrapper around all methods that write to the database. do_op ensures
that a revision number is generated and used in all writes.

    $opts->{parent}: revision of parent op
    $opts->{actor}: entity doing op

=cut

sub do_op {
	my $self = shift;
	my ($op,$opts,@args) = @_;
	my $dbh = $self->dbc->dbh;
	$opts = {} if(!defined $opts);
	my $actor = $opts->{actor};
	my $parent = $opts->{parent};

	# create a revisions entry for this op
	my $sth = $dbh->
		prepare_cached("insert into revisions (vop,actor,parent) " .
									 "values (?,?,?)",
									 {dbi_dummy=>"create_rev"});
	eval { $sth->execute($op,$actor,$parent); };
	if (my $e = $@) {
		if ($e=~/violates foreign key constraint \"c_revisions_fk_vop\"/) {
			$dbh->rollback;
			OperationException->
				throw("Operation \"$op\" is not valid.");
		} elsif ($e=~/violates foreign key constraint \"c_revisions_fk_parent\"/) {
			$dbh->rollback;
			OperationException->
				throw("Specified parent ($parent) doesn't exist.");
		} else {
			$dbh->rollback;
			MachinationException->
				throw("Unknown problem during do_op $op:\n$e");
		}
	}
	$sth->finish;

	# find the revision id we just created
	my $sth = $dbh->
		prepare_cached("select currval('revisions_id_seq')",
									 {dbi_dummy=>"current_rev"});
	eval { $sth->execute; };
	if (my $e = $@) {
		croak $e;
	}
	my ($rev) = $sth->fetchrow_array;
	$sth->finish;

	# call the method
	my $method = "op_$op";
	my @ret;
	my $ret;
  eval {
    if (wantarray) {
      @ret = $self->$method($actor,$rev,@args);
    } else {
      $ret = $self->$method($actor,$rev,@args);
    }
  };
  if(my $e = $@) {
    $dbh->rollback;
    die $e;
  }

	# commit if at end of parent op
	$dbh->commit unless(defined $parent);

	wantarray ? return @ret : return $ret;
}

=item B<conf>

$conf = $ha->conf or $ha->conf($newconf)

return (or set and return) Machination::ConfigFile

=cut

sub conf {
	my $self = shift;
	if (@_) {
		$self->dbc->disconnect if($self->dbc);
		$self->dbc(Machination::DBConstructor->new(shift));
	}
	return $self->dbc->conf;
}

=item B<dbc>

$dbc = $ha->dbc or $dbc = $ha->dbc($newdbc)

return (or set and return) Machination::DBConstructor object

=cut

sub dbc {
	my $self = shift;
	if (@_) {
		$self->{dbc} = shift;
	}
	$self->{dbc} = Machination::DBConstructor->new($self->conf)
		unless (exists $self->{dbc});
	return $self->{dbc};
}

=item B<read_dbh>

$rdbh = $ha->read_dbh

Get a database handle for reading data.

=cut

sub read_dbh {
	my $self = shift;
	return $self->dbc->dbh;
}

=item B<write_dbh>

$wdbh = $ha->write_dbh

Get a database handle for writing data.

=cut

sub write_dbh {
	my $self = shift;
	return $self->dbc->dbh;
}

sub defops {
	my $self = shift;
	$self->{ops} = shift if(@_);
	return $self->{ops};
}

sub def_obj_types {
	my $self = shift;
	$self->{def_obj_types} = shift if(@_);
	return $self->{def_obj_types};
}

=item B<imun>

$num = $ha->imun

imun stands for "in memory unique number".

returns a number that is unique for the lifetime of the daemon/service.

=cut

sub imun {
  my $self = shift;
  return ++$self->{imun};
}

=item B<ssl_get_dn>

$dn = $ha->ssl_get_dn($thing, $type_of_thing)

$thing is an x509 cert or a certificate signing request (csr)

$dn in form:
 {
  fulldn => 'CN=splat,OU=something,..',
  CN => 'splat',
  OU => 'something',
  ...
 }

=cut

sub ssl_get_dn {
  my $self = shift;
  my ($thing, $type) = @_;

  croak "type_of_thing must be either 'x509' or 'req'"
    unless($type eq "x509" or $type eq "req");

  # put the thing into a temporary file so that openssl can find it
  my $thingfh = File::Temp->new;
  $thingfh->unlink_on_destroy(1);
  my $thingfile = $thingfh->filename;
  print $thingfh $thing;

  # A place to put stderr from the openssl cmd
  my $errfh = File::Temp->new;
  $errfh->unlink_on_destroy(1);
  my $errfile = $errfh->filename;

  # parse out the various fields from the subject
  my $fulldn =
    qx"openssl $type -in $thingfile -noout -subject -nameopt RFC2253 2>$errfile";
  if($?) {
    $thingfh->DESTROY;
    my $msg;
    {
      local($/);
      $msg = <$errfh>;
    }
    $errfh->DESTROY;
    die $msg;
  }
  $errfh->DESTROY;
  chomp $fulldn;
  $fulldn =~ s/^subject=//;

  $self->log->dmsg('ssl_get_dn', $fulldn, 10);

  # we are now finished with the file
  $thingfh->DESTROY;

  my @fields = quotewords(",", 0,$fulldn);
  # store the fields and values in $dn
  my $dn = {fulldn => $fulldn};
  foreach my $field (@fields) {
    my ($name, $value) = quotewords("=",0,$field);
    $dn->{$name} = $value;
  }
  return $dn;
}

=item B<ssl_entity_from_cn>

($type, $name) = $ha->ssl_entity_from_cn($cn)

=cut

sub ssl_entity_from_cn {
  my $self = shift;
  my $cn = shift;

  $self->log->dmsg("ssl_entity_from_cn", "splitting $cn", 10);
  # TODO(colin) be more sophisticated parsing escaped ":" and so on
  return split(":", $cn);
}

=item B<sign_csr>

$signed_cert = $ha->sign_csr($csr, $force)

=cut

sub sign_csr {
  my $self = shift;
  my ($csr, $force) = @_;

  # get various parameters from config file
  my $haccess_node = $self->conf->doc->getElementById("subconfig.haccess");
  my $cs_elt = ($haccess_node->findnodes("authentication/certSign"))[0];
  my $lifetime = $cs_elt->findvalue('@lifetime');
  croak "certificate lifetime should be a whole number (of days), " .
    "not '$lifetime'"
      unless($lifetime =~ /^\d+$/);
  my $cafile = $cs_elt->findvalue('ca/@certfile');
  if(substr($cafile,0,1) ne "/") {
    $cafile = $self->conf->get_dir("dir.CONFIG") . "/" . $cafile;
  }
  my $keyfile = $cs_elt->findvalue('ca/@keyfile');
  if(substr($keyfile,0,1) ne "/") {
    $keyfile = $self->conf->get_dir("dir.CONFIG") . "/" . $keyfile;
  }

  # store the fields and values in $dn
  my $dn = $self->ssl_get_dn($csr, "req");
  my $fulldn = $dn->{fulldn};

  # check that obj exists
  my ($obj_type, $obj_name) = $self->ssl_entity_from_cn($dn->{CN});
  die "Could not sign csr: object $obj_type:$obj_name does not exist"
    unless($self->entity_id($self->type_id($obj_type), $obj_name));

  # Check if there is already a signed cert for object
  my $dbh = $self->write_dbh;
  my $existing_rows = $dbh->selectall_arrayref
    ("select * from certs where " .
     "type='V' and " .
     "rev_date is null and " .
     "current_timestamp < expiry_date and " .
     "name like ?", {Slice=>{}}, "CN=$obj_type:$obj_name,%");
#  $self->log->dmsg("sign_csr", Dumper($existing_rows),10);
  die "A valid certificate for $obj_type:$obj_name exists and force not set"
    if(@$existing_rows and not $force);

  # check conformance for various fields of $dn
  foreach my $node ($cs_elt->findnodes("clientDNForm/node")) {
    my $name = $node->findvalue('@id');
    my $check = $node->findvalue('@check');
    my $cfg_val = $node->findvalue('@value');
    my $dn_val = $dn->{$name};
    if($check eq "equal") {
      die "Could not sign csr: failed equality check on $name " .
        "('$dn_val' cf '$cfg_val')"
          unless($cfg_val eq $dn_val);
    } elsif($check eq "re") {
      die "Could not sign csr: failed regex check on $name " .
        "('$dn_val' matches '$cfg_val')"
          unless($dn_val =~ /$cfg_val/);
    } else {
      die "Could not sign csr: invalid check ($check) specified";
    }
  }

  # Get the next serial number
  my ($serial) = $dbh->
    selectrow_array("select nextval(?)", {}, 'certs_serial_seq');

  # put the csr into a temporary file so that openssl can find it
  my $csrfh = File::Temp->new();
  $csrfh->unlink_on_destroy(1);
  my $csrfile = $csrfh->filename;
  print $csrfh $csr;

  # A place to put stderr from the openssl cmd
  my $errfh = File::Temp->new;
  $errfh->unlink_on_destroy(1);
  my $errfile = $errfh->filename;

  # sign the csr
  my $cert = qx"openssl x509 -req -days $lifetime -in $csrfile -CA $cafile -CAkey $keyfile -set_serial $serial 2>$errfile";
  if($?) {
    $csrfh->DESTROY;
    my $msg;
    {
      local($/);
      $msg = <$errfh>;
    }
    $errfh->DESTROY;
    die $msg;
  }

  $cert =~ s/^.*(?=-----BEGIN CERTIFICATE-----)//;
  $self->log->dmsg("sign_csr",$cert,10);

  # should delete the temporary file
  $csrfh->DESTROY;
  $errfh->DESTROY;

  # revoke the old rows/certs in db
  foreach my $row (@$existing_rows) {
    $dbh->do("update certs set type='R', rev_date=current_timestamp where serial=?", {} , $row->{serial});
  }
  # add new row/cert to db
  $dbh->do("insert into certs (serial, name, type, expiry_date) " .
           "values (?,?,'V',current_timestamp + '$lifetime days')", {},
           $serial, $fulldn);
  $dbh->commit;

  # return the signed certificate
  return $cert;
}

=item B<fetcher>

$fetcher = $ha->fetcher(@fetcher_args)

returns a Machination::HFetcher object created with a database handle
$self->read_dbh and arguments @fetcher_args and calls $fetcher->prepare.

=cut

sub fetcher {
	my $self = shift;
	my $f = Machination::HFetcher->new($self->read_dbh,$self->log,@_);
	$f->prepare;
	return $f;
}

=item B<fetcher_cached>

$fetcher = $self->fetcher_cached(@fetcher_args)

returns a Machination::HFetcher object created with a database handle
$self->read_dbh and arguments @fetcher_args and calls
$fetcher->prepare_cached.

=cut

sub fetcher_cached {
	my $self = shift;
	my $f = Machination::HFetcher->new($self->read_dbh,$self->log,@_);
	$f->prepare_cached;
	return $f;
}

=item B<fetch>

@results = $self->fetch($tables,$opts)

$results_hashref = $self->fetch($tables,$opts)

Instantiate a fetcher and fetch all of the results.

=cut

sub fetch {
	my ($self,$tables,$opts) = @_;
	my $fc = $self->fetcher_cached($tables,$opts);
	$fc->execute;

	if (wantarray) {
		my @rows;
		while (my $row = $fc->fetchrow) {
			push @rows, $row;
		}
		$fc->finish;
		return @rows;
	} else {
		my $info = $fc->fetchrow;
		$fc->finish;
		return $info;
	}
}

=item B<valid_op>

$bool = $self->valid_op($op,$opts)

True if $op is a valid op, false otherwise.

=cut

sub valid_op {
	my $self = shift;
	my ($op,$opts) = @_;

	$self->{vops} = {} unless exists($self->{vops});
	if ($opts->{reread}) {
		delete $self->{vops}->{$op};
	}
	unless (exists $self->{vops}->{$op}) {
		if (exists $self->dbc->dbh->
				selectall_hashref("select name from valid_ops where name=?",
													"name",{},$op)->{$op}) {
			$self->{vops}->{$op} = undef;
		}
	}
	if (exists $self->{vops}->{$op}) {
		return 1;
	} else {
		return undef;
	}
}

=item B<object_types>

@type_ids = $ha->object_types;

return a list of all object types

=cut

sub object_types {
  my $self = shift;
  my ($opts) = @_;

  my @types;
  foreach my $row
    ($self->fetch("object_types",
                  {condition=>"",
                   fields=>["id"],
                   revision=>$opts->{revision}})) {
    push @types, $row->{id};
  }

  return @types;
}

=item B<all_types_info>

$info = $ha->all_types_info($opts)

See type_info for info format.

=cut

sub all_types_info {
  my $self = shift;
  my ($opts) = @_;
  $opts->{cache} = 1 unless(defined $opts->{cache});
  if($self->{_ALL_TYPE_INFO_DONE} && $opts->{cache}) {
    return $self->{type_info};
  }
  foreach my $row
    ($self->fetch("object_types",{condition=>"",fields=>["id"]})) {
    $self->type_info($row->{id},$opts);
  }
  $self->{_ALL_TYPE_INFO_DONE} = 1;
  return $self->type_info(undef,$opts);
}

=item B<type_info>

$info = $ha->type_info($type_id,$opts)

$info is hashref of the form:

$info = {
  id => $type_id,
  name => $name,
  plural => $plural_name,
  is_entity => $bool,
  is_attachable => $bool,
  agroup => $ag_type_id, # type id of attachment group type, if any
  columns => \@column_names,
  rev_id => $rev # revision of last change to type
}

=cut

sub type_info {
	my $self = shift;
	my ($type_id,$opts) = @_;

	$opts->{cache} = 1 unless(defined $opts->{cache});

	return $self->{type_info} unless($type_id);
	if (exists $self->{type_info}->{$type_id} && $opts->{cache}) {
		return $self->{type_info}->{$type_id};
	}

	my $dbh = $self->dbc->dbh;
	my $info = {};
	my $obj_table;

	if ($type_id eq "machination:hc") {
		$info->{'plural'} = "hcs";
		$info->{'is_entity'}=0;
		$info->{'is_attachable'}=0;
		$info->{name} = "machination:hc";
		$obj_table = "hcs";
		$self->{type_info}->{$type_id} = $info;
	} else {
		$info = $self->fetch("object_types",
												 {params=>[$type_id],
													revision=>$opts->{revision},
												 });
		$obj_table = "objs_" . $type_id if($info);
		$self->{type_info}->{$type_id} = $info;
	}
	if (defined $obj_table) {
		my $sth = $dbh->
			column_info(undef,undef,$obj_table,undef);
		my $cols = $sth->fetchall_arrayref;
		my @fields;
		foreach my $col (@$cols) {
			push @fields, $col->[3]
				unless($col->[3] eq "id");
		}
		$info->{'columns'}=\@fields;
	}

	return $self->{type_info}->{$type_id};
}

=item B<type_name>

$name = $ha->type_name($type_id,$opts)

return name of type with id $type_id

throws NoSuchTypeException if there is no type with id $id;

=cut

sub type_name {
	my ($self,$type_id,$opts) = @_;

	my $info = $self->type_info($type_id,$opts);
	if ($info) {
		return $info->{name};
	} else {
    NoSuchTypeException->
      throw(error=>"Type with id $type_id doesn't exist.",type=>$type_id);
	}
}

=item B<type_id>

$id = $ha->type_id($name,$opts)

return id of type with name $name

=cut

sub type_id {
	my ($self,$type,$opts) = @_;
  $opts->{cache} = 1 unless(exists $opts->{cache});

	return "machination:hc" if($type eq "machination:hc");
	return $self->{type_id}->{$type} if
		(exists $self->{type_id}->{$type} && $opts->{cache});
	my $info = $self->fetch("object_types",
													{fields=>["id"],
													 condition=>"name=?",
													 params=>[$type],
													 revision=>$opts->{revision}});
	if ($info) {
		$self->{type_id}->{$type} = $info->{id};
	} else {
    NoSuchTypeException->
      throw(error=>"Type with name $type doesn't exist.",type=>$type);
	}
  return $self->{type_id}->{$type};
}

=item B<type_exists_byname>

$id or undef = $ha->type_exists_byname($name, $opts)

=cut

sub type_exists_byname {
  my ($self, $name, $opts) = @_;

  my $id = eval {$self->type_id($name, $opts)};
  if(my $e = Exception::Class->caught('NoSuchTypeException')) {
    return;
  }
  return $id;
}

=item B<os_id>

=cut

sub os_id {
  my ($self,$name,$majver,$minver,$bitness,$opts) = @_;
	my $row = $self->fetch("valid_oses",
                         {fields=>["id"],
                          condition=>"name=? and major_version=? " .
                          "and minor_version=? and bitness=?",
                          params=>[$name,$majver,$minver,$bitness],
                          revision=>$opts->{revision}});
	if ($row) {
		return $row->{id};
	} else {
		return undef;
	}
}

=item B<channel_id>

$id = $ha->channel_id($name,$opts)

return id of channel with name $name

=cut

sub channel_id {
	my ($self,$channel,$opts) = @_;

	$opts->{cache} = 1 unless(defined $opts->{cache});

	if (exists $self->{channel_id}->{$channel} && $opts->{cache}) {
		return $self->{channel_id}->{$channel};
	}

	my $row = $self->fetch("valid_channels",
                         {fields=>["id"],condition=>"name=?",
                          params=>[$channel],revision=>$opts->{revision}});
	if ($row) {
		$self->{channel_id}->{$channel} = $row->{id};
	} else {
		$self->{channel_id}->{$channel} = undef;
	}

	return $self->{channel_id}->{$channel};
}

=item B<channel_info>

$info = $ha->channel_info($cid,$opts)

return info for channel $cid

=cut

sub channel_info {
	my ($self,$cid,$opts) = @_;

  # memoise
	$opts->{cache} = 1 unless(defined $opts->{cache});
	if (exists $self->{channel_info}->{$cid} && $opts->{cache}) {
		return $self->{channel_info}->{$cid};
	}

	return $self->fetch("valid_channels",
                      {params=>[$cid],revision=>$opts->{revision}});
}

=item B<channels_info>

$info_hash = $ha->channels_info($cidlist,$opts)

return info for channels in list $cidlist, or all if $cidlist is undef

=cut

sub channels_info {
	my ($self,$cidlist,$opts) = @_;

  unless(defined $cidlist) {
    my $tmplist = $self->read_dbh->selectall_arrayref("select id from valid_channels");

    my @cidlist;
    for my $item (@$tmplist) {
      push @cidlist, $item->[0];
    }
    $cidlist = \@cidlist;
  }

  my $all_info = {};
  foreach my $cid (@$cidlist) {
    $all_info->{$cid} = $self->channel_info($cid, $opts);
  }

  return $all_info;
}


=item B<profchannel>

Find the correct channel for assertions affecting type $type_id

$channel_id = $ha->profchannel($type_id)

=cut

sub profchannel {
  my $self = shift;
  my ($type_id) = @_;

  # TODO(colin) this should change to some link in the database
  # between object_type and valid_channels
  if($self->type_name($type_id) eq "os_instance") {
    return $self->channel_id('machination:osprofile');
  } elsif($self->type_name($type_id) eq "person") {
    return $self->channel_id('machination:userprofile');
  } else {
    HierarchyException->throw
      ("There is no channel associated with type " .
       $self->type_name($type_id));
  }
}

=item B<fetch_path_id>

$id = $ha->fetch_path_id($path,$opts)

=cut

sub fetch_path_id {
  my $self = shift;
  my ($path) = @_;

  my $hp = Machination::HPath->new($self,$path);
  return $hp->id;
}

=item B<fetch_id>

$id = $ha->fetch_id($type_id,$name,$parent,$opts)

return the id of object of type $type_id called $name in hc $parent

=cut

sub fetch_id {
	my ($self,$type_id,$name,$parent,$opts) = @_;
	$opts = {} unless defined $opts;

	if (! defined $type_id || $type_id eq "machination:hc") {
		if (defined $parent) {
			my $row = $self->fetch
				("hcs",{fields=>["id"],
								condition=>"name=? and parent=?",
								params=>[$name,$parent],
								revision=>$opts->{revision}});
			return unless $row;
			return $row->{id};
		} else {
			my $row = $self->fetch
				("hcs",{fields=>["id"],
								condition=>"name=? and parent is null",
								params=>[$name],
								revision=>$opts->{revision}});
			return unless $row;
			return $row->{id};
		}
	} else {
		#       $sql = "select o.id from objs_$type_id as o, " .
		#           "hccont_$type_id as h where o.name=? and h.hc_id=? " .
		#           "and o.id=h.obj_id";
		my $row = $self->fetch
			([["objs_$type_id","o"],["hccont_$type_id","h"]],
			 {fields=>["o.id"],
				condition=>"o.name=? and h.hc_id=? and o.id=h.obj_id",
				params=>[$name,$parent],
				revision=>$opts->{revision},
			 });
		return unless $row;
		return $row->{id};
	}

	return;
}

=item B<object_exists>

$id = $ha->object_exists($type,$id,$opts)

return $id if object exists, undef otherwise

=cut

sub object_exists {
  my ($self,$type,$id,$opts) = @_;

  my $table;
  if($type eq "machination:hc" || ! defined $type) {
    $table = "hcs";
  } else {
    $table = "objs_$type";
  }
	my $row = $self->fetch($table,
												 {fields=>["id"],
													params=>[$id],
													qid=>"HAccessor.object_exists",
													revision=>$opts->{revision}});
  return unless $row;
  return $id;
}

=item B<object_in_hc>

$id = $ha->object_in_hc($type, $id, $hc_id)

=cut

sub object_in_hc {
  my ($self, $tid, $id, $hc, $opts) = @_;
  my $sth = $self->read_dbh->prepare_cached
    ("select obj_id from hccont_$tid where obj_id=? and hc_id=?",
     {dbi_dummy=>"HAccessor.object_in_hc"});
  $sth->execute($id, $hc);
  my $row = $sth->fetchrow_arrayref;
  return unless $row;
  return $id;
}

=item B<attachment_exists>

$bool = $ha->attachment_exists($hc_id, $type_id, $id, $mandatory)

=cut

sub attachment_exists {
  my ($self, $hc, $tid, $id, $man) = @_;

  my $ret = 0;
  $man = 0 unless defined $man;

  my $sql = "select * from hcatt_$tid where obj_id=? and hc_id=?";
  my @params = ($id, $hc);
  # get column names
  my $sth = $self->write_dbh->prepare("select * from hcatt_$tid where 0=1");
  $sth->execute();
  my $has_man;
  foreach my $name ($sth->{NAME_lc}) {
    if($name eq "is_mandatory") {
      $sql .= " and is_mandatory=?";
      push @params, $man;
      last;
    }
  }
  $sth = $self->write_dbh->prepare_cached
    ($sql, {dbi_dummy=>"HAccessor.attachment_exists"});
  $sth->execute(@params);
  if($sth->fetchrow_arrayref) {
    $ret = 1;
  }
  $sth->finish;
  return $ret;
}

=item B<fetch_root_id>

$id = $ha->fetch_root_id($opts)

return the id of the root hc

=cut

sub fetch_root_id {
	my ($self,$opts) = @_;

	# cache the root id - it's not likely to change
	if (exists $self->{cache}->{root_id}) {
		return $self->{cache}->{root_id};
	}

	my $rootid = $self->fetch_id(undef,"machination:root",undef);

	return unless defined $rootid;

	$self->{cache}->{root_id} = $rootid;
	return $self->{cache}->{root_id};
}

=item B<fetch_parent>

$hc_id = $ha->fetch_parent($hid,$opts)

return id of the parent of an hc

=cut

sub fetch_parent {
	my ($self,$hid,$opts) = @_;

	my $row = $self->fetch("hcs",
												 {fields=>["parent"],
													params=>[$hid],
													qid=>"HAccessor.fetch_parent",
													revision=>$opts->{revision}});
	if ($row) {
		return $row->{parent};
	} else {
		HierarchyException->
			throw("cannot get parent of hc $hid - it doesn't exist.");
	}
}

=item B<fetch_parents>

@parent_ids = $ha->fetch_parents($type_id,$id,$opts)

return list of hcs in which object $id of type $type_id is contained

=cut

sub fetch_parents {
	my $self = shift;
	my ($type,$id,$opts) = @_;
	$type = "machination:hc" unless defined $type;

	my @parents;
	if ($type eq "machination:hc") {
		push @parents, $self->fetch_parent($id,$opts);
	} else {
		my @rows = $self->
			fetch([["objs_$type","o"],["hccont_$type","h"]],
						{type=>"multi",
						 fields=>["h.hc_id"],
						 condition=>"o.id=? and o.id=h.obj_id",
						 params=>[$id],
						 revision=>$opts->{revision},
						 qid=>"HAccessor.fetch_parents"});
		foreach (@rows) {
			push @parents, $_->{hc_id};
		}
	}
	return @parents;
}

=item B<fetch_name>

$name = $ha->fetch_name($type_id,$obj_id,$opts)

return name of object of type $type_id and id $id

=cut

sub fetch_name {
	my ($self,$type_id,$obj_id,$opts) = @_;
	my $table = "objs_$type_id";
	if (! defined $type_id || $type_id eq "machination:hc") {
		$table = "hcs";
	}
	my $info = $self->fetch($table,
													{fields=>["name"],
													 params=>[$obj_id],
													 revision=>$opts->{revision}});
	if ($info) {
		return $info->{name};
	} else {
		return;
	}
}

=item B<fetch_path_string>

$string = $ha->fetch_path_string($type_id,$obj_id,$parent_id,$opts)

return a string representation of path like:

/path/to/parent/type_name:obj_name

=cut

sub fetch_path_string {
	my $self = shift;
	my ($type_id,$obj_id,$parent,$opts) = @_;

	my $type = $self->type_name($type_id,$opts);

	if (! defined $type_id || $type_id eq "machination:hc") {
		return $self->fetch_hc_path_string($type_id,$opts);
	}
	my $parent_path = $self->
		fetch_hc_path_string($parent);
	$parent_path = "" if($parent_path eq "/");
	return "$parent_path/$type:" . $self->fetch_name($type_id,$obj_id,$opts);
}

=item B<fetch_hc_path>

$path_string = $ha->fetch_hc_path($hc_id,$opts)

=cut

sub fetch_hc_path_string {
	my $self = shift;
	my ($id,$opts) = @_;

	my $root_id = $self->fetch_root_id;
	return "/" if($id == $root_id);

	my @path;
	my $parent_id;
	do {
		my $info = $self->fetch("hcs",
														{fields=>["name","parent"],
														 params=>[$id],
														 revision=>$opts->{revision}});
		my $name = $info->{name};
		$parent_id = $info->{parent};
		unshift @path, $name;
		$id = $parent_id;
	} until ($parent_id eq $root_id);
	unshift @path, "";
	return join("/",@path);
}

#=item B<fetch_path_id>
#
#$obj_id = $ha->fetch_path_id($path,$opts)
#
#=cut
#
#sub fetch_path_id {
#	my ($self,$path,$opts) = @_;
#
#	if (eval{$path->isa("Machination::HPath")}) {
#		return $path->id;
#	} else {
#		return Machination::HPath->new($self,$path,$opts->{revision})->id;
#	}
#}

=item B<fetch_lineage>

@lineage = $ha->fetch_lineage($hc_id);

=cut

sub fetch_lineage {
  my ($self,$id,$opts) = @_;

  my @lineage;
  my $hc = $self->fetch("hcs",
                        {fields=>["id","parent","is_mp","ordinal"],
                         params=>[$id],
                         revision=>$opts->{revision}});
  unshift @lineage, $hc;
  unshift @lineage, $self->fetch_lineage($hc->{parent})
    if(defined $hc->{parent});
  return @lineage;
}

=item B<fetch_new_ordinal>

$ha->fetch_new_ordinal($type_id,$parent)

=cut

sub fetch_new_ordinal {
	my $self = shift;
	my ($type_id,$parent,$opts) = @_;

	if (!defined $type_id || $type_id eq "machination:hc") {
		# hc ordinals
		my $row = $self->fetch("hcs",
													 {fields=>["id","ordinal"],
														condition=>"parent=?",
														order=>[["ordinal","desc"]],
														params=>[$parent],
														revision=>$opts->{revision}});
		if ($row) {
			my $ord = $row->{ordinal};
			return $ord+1;
		} else {
			return 0;
		}
	} else {
		# attachment ordinals
		my $row = $self->fetch("hcatt_$type_id",
													 {fields=>["obj_id","ordinal"],
														condition=>"hc_id=?",
														order=>[["ordinal","desc"]],
														params=>[$parent],
														revision=>$opts->{revision}});
		if ($row) {
			my $ord = $row->{ordinal};
			return $ord+1;
		} else {
			return 0;
		}
	}
}

=item B<fetch_mp>

$hc_id = $ha->fetch_mp($hc_id,$opts)

=cut

sub fetch_mp {
	my $self = shift;
	my ($id,$opts) = @_;

	my $row = $self->fetch("hcs",
												 {fields=>["is_mp","parent"],
													params=>[$id],
													revision=>$opts->{revision},
												 });
	unless($row) {
		HierarchyException->
			throw("tried to fetch_mp for an hc that doesn't exist ($id).");
	}
	if ($row->{is_mp}) {
		return $id;
	} else {
		return $self->fetch_mp($row->{parent});
	}
}

=item B<mps>

$mps = $ha->mps($hcs,$opts)

Given a list $hcs of hc ids, return a list, $mps, of those that are
merge points

=cut

sub mps {
  my $self = shift;
  my ($hcs,$opts) = @_;

  my $query = "select id from hcs where is_mp=true and id in (" .
     join(",",("?") x scalar(@$hcs)) . ")";
  $self->log->dmsg("HAccessor.mps","$query :: " . join(",",@$hcs),9);
  my $rows = $self->read_dbh->selectall_arrayref($query,{},@$hcs);
  my @mps;
  foreach my $row (@$rows) {
    push @mps, $row->[0];
  }
  return \@mps;
}

=item B<get_contents_handle>

$sth = $ha->get_contents_handle($hc_id, $types,$opts);

=cut

sub get_contents_handle {
  my $self = shift;
  my $hc_id = shift;
  my $types = shift;
  my $opts;
  if(ref $_[0]) {
    $opts = shift;
  } else {
    my %opts = @_;
    $opts = \%opts
  }

  my $dbh = $self->read_dbh;
  my @subqs;
  my @params;
  foreach my $type (@$types) {
    if($type eq "machination:hc") {
      my $subq = "(select id as obj_id, " .
        "name, ?::text as ntype_id, ?::text as type_id " .
        "from hcs where parent=?)";
#      push @subqs, [$subq,"hc",$self->id];
      push @subqs, $subq;
      push @params, 0, "machination:hc", $hc_id;
    } else {
      my $subq = "(select objs_$type.id as obj_id, name, " .
        "?::text as ntype_id, ?::text as type_id " .
        "from objs_$type,hccont_$type " .
        "where hccont_$type.hc_id=? and objs_$type.id=hccont_$type.obj_id)";
#      push @subqs, [$subq,$type,$self->id];
      push @subqs, $subq;
      push @params, $type, $type, $hc_id;
    }
  }
  my $sql = join(" union ", @subqs) . " order by ntype_id";
  my $sth = $dbh->prepare($sql);
  $sth->execute(@params);
  return $sth;
}

=item B<get_typed_contents_fetcher>

$fetcher = $ha->get_typed_contents_fetcher($type_id,$hc_id,$opts)

=cut

sub get_typed_contents_fetcher {
	my $self = shift;
	my ($tid,$hc_id,$opts) = @_;
	$tid = "machination:hc" unless defined $tid;

	my @fields;
	if (defined $opts->{fields}) {
		push @fields, @{$opts->{fields}};
	}
  $opts->{show_type_id} = $tid if ($opts->{show_type_id});

	my $fetcher;
	if ($tid eq "machination:hc") {
		push @fields, "id";
		$fetcher = $self->fetcher_cached
			("hcs",
			 {fields=>\@fields,
				condition=>"parent=?",
				params=>[$hc_id],
				qid=>"HAccessor.fetch_contents",
				revision=>$opts->{revision}});
	} else {
		$fetcher = $self->fetcher_cached
			("hccont_$tid",
			 {fields=>[["obj_id","id"]],
				condition=>"hc_id=?",
				params=>[$hc_id],
				qid=>"HAccessor.fetch_contents",
				revision=>$opts->{revision}});
	}
	$fetcher->execute;
	return $fetcher;
}

=item B<get_typed_contents_fetcher>

$fetcher = $ha->get_typed_contents_fetcher($type_id,$hc_id,$opts)

=cut

sub get_typed_contents_handle {
	my $self = shift;
	my ($tid,$hc_id,$opts) = @_;
	$tid = "machination:hc" unless defined $tid;

	my @fields;
	if (defined $opts->{fields}) {
		push @fields, @{$opts->{fields}};
	}
  $opts->{show_type_id} = $tid if ($opts->{show_type_id});

  my $fetcher;
	my $handle;
	if ($tid eq "machination:hc") {
		push @fields, "id";
		$fetcher = $self->fetcher_cached
			("hcs",
			 {fields=>\@fields,
				condition=>"parent=?",
				params=>[$hc_id],
				qid=>"HAccessor.fetch_contents",
				revision=>$opts->{revision}});
	} else {
		$fetcher = $self->fetcher_cached
			("hccont_$tid",
			 {fields=>[["obj_id","id"]],
				condition=>"hc_id=?",
				params=>[$hc_id],
				qid=>"HAccessor.fetch_contents",
				revision=>$opts->{revision}});
	}
	$handle->execute;
	return $fetcher;
}

sub fetch_some_contents {
	my ($self,$f,$opts) = @_;
	my $limit = $opts->{limit};
	delete $opts->{limit};

	my @rows;
	if ($limit) {
		@rows = $f->fetch_some($limit);
	} else {
		@rows = $f->fetch_all;
		$f->finish;
	}
	if ($opts->{obj_fields}) {
		my ($tid) = @{$f->{tlist}};
		$tid =~ s/^zzh_//;
		$tid =~ s/^hccont_//;
		foreach my $row (@rows) {
			my $info = $self->fetch("objs_$tid",
															{
															 fields=>$opts->{obj_fields},
															 params=>[$row->{id}],
															 revision=>$opts->{revision}});
			@$row{keys %$info} = values %$info;
		}
	}
  if($opts->{show_type_id}) {
    foreach (@rows) {
      $_->{type_id} = $opts->{show_type_id};
    }
  }
	return @rows;
}

=item B<list_all_contents_of_type>

@contents = $ha->list_all_contents_of_type($type_id,$hc_id,$opts)

=cut

sub list_all_contents_of_type {
	my ($self,$tid,$hid,$opts) = @_;

	my $f = $self->get_typed_contents_fetcher($tid,$hid,$opts);
	return $self->fetch_some_contents($f,$opts);
}

=item B<list_contents>

@contents = $ha->list_contents($hc_id,$opts)

=cut

sub list_contents {
  my ($self,$hid,$opts) = @_;
  $self->log->dmsg("HAccessor.list_contents","hid: $hid, opts: " . Dumper($opts),9);
  $opts->{show_type_id} = 1;
  my @contents;
  foreach my $tid ("machination:hc",keys %{$self->all_types_info($opts)}) {
    push @contents, $self->list_all_contents_of_type($tid,$hid,$opts);
  }
  $self->log->dmsg("HAccessor.list_contents","returning " . Dumper(\@contents),9);
  return @contents;
}

sub object_is_in {
	my $self = shift;
	my ($tid,$oid,$parent,$opts) = @_;

	my $row = $self->fetch("hccont_$tid",
                         {fields=>["obj_id"],
                          condition=>"obj_id=? and hc_id=?",
                          params=>[$oid,$parent],
                          qid=>"HAccessor.object_is_in",
                          revision=>$opts->{revision},
                         });
	if ($row) {
		return $row->{obj_id};
	} else {
		return;
	}
}

=item B<mtree_contains>

$ha->mtree_contains($merge_id,$type_id,$obj_id)

return merge point id if object $obj_id of type $type_id is contained
in merge tree defined by merge point $merge_id. Return false otherwise.

=cut

sub mtree_contains {
	my $self = shift;
	my ($mid,$tid,$oid,$opts) = @_;

	return $mid if($self->object_is_in($tid,$oid,$mid,$opts));
	foreach my $hc ($self->fetch_mtree_hcs($mid,$opts)) {
		return $hc if($self->object_is_in($tid,$oid,$hc,$opts));
	}
	return;
}

=item B<fetch_mtree_hcs>

$ha->fetch_mtree_hcs($hid)

Find all the descendants of hc $hid which are in the same merge tree.

=cut

sub fetch_mtree_hcs {
	my $self = shift;
	my ($hid,$opts) = @_;

	my @hcs;
	my @rows = $self->fetch("hcs",
													{type=>"multi",
													 qid=>"HAccessor.fetch_mtree_hcs",
													 fields=>["id","is_mp"],
													 condition=>"parent=?",
													 params=>[$hid],
													 revision=>$opts->{revision}});
	foreach my $row (@rows) {
		unless ($row->{is_mp}) {
			push @hcs, $row->{id};
			# this child isn't a new merge point so grab its children
			push @hcs, $self->fetch_mtree_hcs($row->{id});
		}
	}

	return @hcs;
}

=item B<is_agroup>

$bool = $ha->is_agroup($type_id)

=cut

sub is_agroup {
  my $self = shift;
  my ($type_id) = @_;
  my $rows = $self->read_dbh->selectall_arrayref
    (
     "select o1.id from object_types as o1, object_types as o2 " .
     "where o1.id = o2.agroup and o1.id=?",
     {},
     $type_id
     );
  if($rows) {
    return 1;
  }
  return 0;
}

=item B<type_from_agroup_type>

$ha->type_from_agroup_type($agroup_type_id,$opts)

=cut

sub type_from_agroup_type {
	my $self = shift;
	my ($atid,$opts) = @_;

	my $tname = $self->type_name($atid,$opts);
	$tname =~ s/^agroup_//;
	return $self->type_id($tname,$opts);
}

=item B<fetch_from_agroup>

$ha->fetch_from_agroup($ag_type_id,$ag_id,$opts)

=cut

sub fetch_from_agroup {
	my $self = shift;
	my ($atid,$id,$opts) = @_;

	my $tid = $self->type_from_agroup_type($atid);
	my @rows = $self->
		fetch("objs_$tid",
					{type=>"multi",
					 fields=>["id"],
					 condition=>"agroup=?",
					 params=>[$id],
					 order=>[["ag_ordinal"]],
					 revision=>$opts->{revision},
					});

	my @ids;
	foreach (@rows) {
		push @ids, $_->{id};
	}
	return @ids;
}

=item B<get_attached_handle>

Get a handle to the direct attachments of an hc

$sth = $ha->get_attached_handle($hc, \@channel_ids, \@type_ids)

=cut

sub get_attached_handle {
  my $self = shift;
  my ($hc, $channels, $type_ids) = @_;

  my $hp = Machination::HPath->new($self,$hc);

  my @params;
  my @subqs;
  foreach my $tid (@$type_ids) {
    my $sq = "(select ${tid}::text as type_id, " .
      "a.obj_id, a.ordinal, o.name, ";
    if ($tid == $self->type_id("set")) {
      $sq .= $self->channel_id("machination:hierarchy") . " as channel_id";
      $sq .= ", false as is_mandatory ";
    } else {
      $sq .= "o.channel_id, a.is_mandatory ";
    }
    $sq .= "from hcatt_$tid as a, objs_$tid as o " .
      "where a.hc_id=?";
    $sq .= " and a.obj_id=o.id";
    push @params, $hp->id;
    unless($tid == $self->type_id("set")) {
      $sq .= " and o.channel_id in (" . join(",",('?') x @$channels) . ")";
      push @params, @$channels;
    }
    $sq .= ")";
    push @subqs, $sq;
  }
  my $sql = join(" union ", @subqs) .
    " order by type_id, ordinal";
  $self->log->dmsg("HAccessor.get_attached_handle",
                  "$sql",9);
  my $sth = $self->read_dbh->
    prepare_cached($sql,{dbi_dummy=>"HAccessor.get_attached_handle"});
  $sth->execute(@params);
  return $sth;
}

=item B<get_ag_member_handle>

$sth = $ha->get_ag_member_handle($ag_type_id, $ag_id)

=cut

sub get_ag_member_handle {
  my $self = shift;
  my ($agtid, $agid) = @_;

  my $tid = $self->read_dbh->selectall_arrayref
    ("select id from object_types where agroup=?",{},$agtid)->[0]->[0];
  my $sth = $self->read_dbh->prepare_cached
    ("select * from objs_$tid where agroup=? order by ag_ordinal",
     {dbi_dummy=>"get_ag_member_handle"});
  $sth->execute($agid);
  return $sth;
}

=item B<get_attachments_handle>

$sth = $ha->get_attachments_handle($channel, $hlist, $type, $opts)

=cut

sub get_attachments_handle {
  my $self = shift;
  my ($channel,$hlist,$type,$opts) = @_;


  if(ref($hlist) ne "ARRAY") {
    my $hpath = Machination::HPath->new($self,$hlist,$opts->{revision});
    HierarchyException->throw
      ("Can only fetch attachment list for an hc")
        unless $hpath->type_id eq 'machination:hc';
    $hlist = [ reverse @{$hpath->id_path} ];
  }

  my @q;
  my @params = ($channel);
  foreach (@$hlist) {
    push @q, "?";
    push @params, $_;
  }
  my $ag_tid = $self->type_id("agroup_$type");
  my $ob_tid = $self->type_id("$type");

  my $query = "select o.id as oid,o.name,q.is_mandatory," .
    "o.agroup,q.hc_id,q.att_ordinal,o.ag_ordinal";
  foreach my $f (@{$opts->{obj_fields}}) {
    $query .= ",o.$f";
  }
  $query .= " from objs_$ob_tid as o, " .
    "(select g.id as gid, a.hc_id, a.ordinal as att_ordinal, a.is_mandatory " .
      "from hcatt_$ag_tid as a, objs_$ag_tid as g where a.obj_id = g.id " .
        "and g.channel_id=? and a.active=true) as q ";
  $query .= "where o.agroup = q.gid and " .
    "(select q.hc_id in (" . join(",",@q) . "))";
#  $query .= " and q.is_mandatory=?";
#  push @params, $mand;
  if($opts->{obj_conditions}) {
    foreach my $cond (@{$opts->{obj_conditions}}) {
      $query .= " and " . $cond->[0];
      push @params, @{$cond->[1]};
    }
  }
  $query .= " order by ";
  my $i=0;
  $query .= " case";
  foreach my $hc_id (@$hlist){
    $query .= " when q.hc_id=? then $i";
    push @params, $hc_id;
    $i++;
  }
  $query .= " end";
#  $query .= ",q.is_mandatory,q.att_ordinal, o.ag_ordinal";
  $query .= ",q.att_ordinal, o.ag_ordinal";

  $self->log->dmsg("HAccessor.fetch_attachment_list",
                 "query:\n$query",9);
  $self->log->dmsg("HAccessor.fetch_attachment_list",
                 "params: " . join(",",@params),9);

  my $idx = {};
  my $sth = $self->read_dbh->
    prepare_cached($query,{dbi_dummy=>"HAccessor.fetch_attachment_list"});
  $sth->execute(@params);
#  return $sth->fetchall_arrayref({});
  return $sth;

  while (my $row = $sth->fetchrow_hashref) {
    my $hc_id = $row->{hc_id};
    my $mand = $row->{is_mandatory};
    $idx->{$hc_id}->{$mand} = []
      unless $idx->{$hc_id}->{$mand};
    if($mand) {
      push @{$idx->{$hc_id}->{$mand}}, $row;
    } else {
      unshift @{$idx->{$hc_id}->{$mand}}, $row;
    }
  }
  my $res = {mandatory=>[], default=>[]};
  foreach my $hc (@$hlist) {
#    $res->{mandatory} = []
#      unless $res->{mandatory};
    push @{$res->{mandatory}}, @{$idx->{$hc}->{1}}
      if(defined $idx->{$hc}->{1});
#    $res->{default} = []
#      unless $res->{default};
    unshift @{$res->{default}}, @{$idx->{$hc}->{0}}
      if(defined $idx->{$hc}->{0});
  }
  $self->log->dmesg("HAccessor.fetch_attachment_list",
                    "returning:\n" . Dumper($res),9);
  return $res;
}

=item B<get_authz_handle>

$ha->fetch_authz_list($channel,$hpath,$op,$opts)
$ha->fetch_authz_list($channel,$hc_id,$op,$opts)

fetch a list of authorisation instructions relavent to $channel and
$op attached to $hc_id and its parents.

List is returned as a hash ref:

  {
   'default' =>
    [
      {is_allow=>0,entities=>$string,op=>$op,xpath=>$string,...},
      {is_allow=>0,entities=>$string,op=>$op,xpath=>$string,...},
      ...
    ],
   'mandatory' =>
    [
      {is_allow=>0,entities=>$string,op=>$op,xpath=>$string,...},
      {is_allow=>0,entities=>$string,op=>$op,xpath=>$string,...},
      ...
    ]
  }


The list is properly ordered so that one can traverse the mandatory
list forwards, then the default list backwards and choose the first
match when checking authorisation.

=cut

sub get_authz_handle {
  my $self = shift;
  my ($channel,$hpath,$op,$opts) = @_;

  $opts->{obj_fields} = ["op","is_allow","entities","xpath"];
  $opts->{att_fields} = [];
  $opts->{obj_conditions} = [["(o.op=? or o.op=?)",[$op,"ALL"]]];
#  $self->log->dmsg("Haccessor.fetch_authz_list","args:\n $channel, " .
#                   "$hpath, 'authz_inst', " .
#                   Data::Dumper->Dump([$opts],[qw(opts)]),9);
  return $self->get_attachments_handle
    ($channel,$hpath,"authz_inst",$opts);
}

=item B<fetch_set_attachments>

=cut

sub fetch_set_attachments {
  my $self = shift;
  my ($hc) = @_;

}

=item B<authz_hash_from_object>

$ha->authz_hash_from_object($authz_inst_object,$hc_id)

=cut

sub authz_hash_from_object {
  my $self = shift;
  my ($obj,$hc_id,$opts) = @_;

  # can pass an id or an object - better create object if we get an id
  if(! ref $obj) {
    $obj = Machination::HObject->new($self,$self->type_id("authz_inst"),$obj);
  }

  my $data = $obj->fetch_data;

  # make sure the object really is an authz_inst
  unless($obj->type == $self->type_id("authz_inst")) {
    ObjectException->throw
      (message=>"object \'" . $data->{name} .
       "' is not of type authz_inst" );
  }

  my $hash = $data;
  my $agroup = Machination::HObject->
    new($self,$self->type_id("agroup_authz_inst"),$data->{agroup});
  $hash->{channel_id} = $agroup->fetch_data("channel_id")->{channel_id};
  my $row = $self->fetch("hcatt_" . $self->type_id("agroup_authz_inst"),
                        {condition=>"obj_id=? and hc_id=?",
                         params=>[$obj->id,$hc_id],
                         revision=>$opts->{revision}});
  MachinationException->throw
    ("authz_hash_from_object: object " . $obj->id . " (" . $data->{name} .
     ") isn't attached at hc $hc_id")
    unless $row;
  $hash->{is_mandatory} = $row->{is_mandatory};

  return $hash;
}

=item B<action_allowed>

$ha->action_allowed($request,$hc_id)

$request  = hash ref with following representation:
 {
  channel_id=>$channel_id,
  op=>$op,
  mpath=>$mpath,
  arg=>$arg,
  owner=>$authen_string,
  approval=>[$authen_string,$authen_string,...],

  # not yet implemented - to be used if authz instructions end
  # up with applies_to sets
  to_type=>$type,
  to_id=>$id,
 }

$authen_string is the string passed by whichever authentication system
is being used representing the active or approving entities.

return (0,$info) if authz_inst not relevant or (1,$authz->{is_allow})
if it is.

=cut

sub action_allowed {
	my $self = shift;
  my ($req,$hc_id,$opts) = @_;
  my $cat = "HAccessor.action_allowed";
  $self->log->dmsg($cat,"\n" . Dumper($req),8);

  if($req->{channel_id} == $self->channel_id('machination:hierarchy')) {
    # The hierarchy channel must be treated specially for three reasons:
    #
    # 1) The mpath is interpreted as relative to the hc to which the
    #    current $authz is attached. This means the dummy xml for the
    #    xpath to search has to be generated differently depending on
    #    current hc.
    #
    # 2) Details about the object in question must be fetched from the
    #    hierarchy (if the object exists) and placed into the xml
    #    element. This is so that authorisation on fields works.
    #
    # 3) If the hc is /system/special/authz/objects then populate the
    #    object element as long as it exists (even if not in that hc)

    # the mpath must be of the form /$branch or /$branch/type[id]

    my ($branch, $type_name, $obj_id) =
      $req->{mpath} =~ /^\/(contents|attachments)(?:\/(\w+:?\w*)(?:\[(\d+)\])?)?/;
    croak "don't know how to authorise branch " .
      "in hierarchy channel when processing mpath " . $req->{mpath}
        unless(defined $branch);
    my $type_id;
    $type_id = $self->type_id($type_name) if(defined $type_name);

    my @hcs = ($hc_id);
    # if $hc_id corresponds to /system/special/authz/objects then we really
    # need to check all parents of the object in question
    if(defined $obj_id) {
      if($hc_id == Machination::HPath->
         new($self,'/system/special/authz/objects')->id) {
        push @hcs, $self->fetch_parents($type_id,$obj_id);
      }
    }

    my $is_allow = undef;
    foreach my $cur_hc_id (@hcs) {
      my $sth = $self->
        get_authz_handle($req->{channel_id},$cur_hc_id,$req->{op},$opts);
      my $it = $self->att_iterator($sth);
      my $cur_hc_hp = Machination::HPath->new($self,$cur_hc_id);
      my @cur_hc_ancestors = reverse @{$cur_hc_hp->id_path};

      my $obj_elt;
      if(defined $type_name) {
        my $obj_mp = $req->{mpath};
        $obj_mp =~ s/^\/$branch//;
        $obj_elt = Machination::MPath->new($obj_mp)->construct_elt;
        # fill the object's fields if it exists
        if(defined $obj_id) {
          my $obj_hp = Machination::HPath->new($self,"$type_name:$obj_id");
          if($obj_hp->id) {
            my $hobj = Machination::HObject->new($self, $type_id, $obj_id);
            my $data = $hobj->fetch_data;
            foreach my $k (keys %$data) {
              my $child = XML::LibXML::Element->new('field');
              $child->setAttribute("id", $k);
              $child->appendText($data->{$k});
              $obj_elt->appendChild($child);
            }
          }
        }
      }

      while(my $authz = $it->()) {
        $self->log->dmsg($cat,"\n" . Dumper($authz),8);
        # need to modify the mpath to be relative to the current
        # $authz->{hc_id}
        my $cont_mp_str = "/$branch";
        foreach my $hid (@cur_hc_ancestors) {
          last if($hid == $authz->{hc_id});
          $cont_mp_str = "/contents/hc[$hid]$cont_mp_str";
        }
        my $cont_mp = Machination::MPath->new($cont_mp_str);
        my $cont_elt = $cont_mp->construct_elt;
        my $cont_doc = XML::LibXML::Document->new;
        $cont_doc->setDocumentElement($cont_elt);
        my $cont_inner = ($cont_elt->findnodes($cont_mp->to_xpath))[0];
        $cont_inner->appendChild($obj_elt) if(defined $type_name);
        unless($self->relevant_xpath($req->{channel_id},
                                     $cont_elt,
                                     $authz->{xpath})) {
          next;
        }
        next unless($self->relevant_entities
                    ($req->{owner},$req->{approval},$authz->{entities}));

        # if we got here then the current rule must be relevant
        if(@hcs > 1) {
          # we must have got here by looking up
          # /system/special/authz/objects - keep going through parent
          # hcs until the request is alloed or all prents resulted in
          # deny
          return 1 if $authz->{is_allow};
          # didn't get permission on this hc, remember the deny and
          # try the next one in the list
          $is_allow = 0;
        } else {
          return $authz->{is_allow};
        }
      }
    }

    return $is_allow if defined $is_allow;

    # If we got here then no authorisation instruction was
    # relevant. We treat that as an error.
    AuthzException->
      throw("No relevant authorisation instruction for request " .
            Dumper($req));
  }

  my $sth = $self->
    get_authz_handle($req->{channel_id},$hc_id,$req->{op},$opts);
  my $it = $self->att_iterator($sth);

  while(my $authz = $it->()) {
    $self->log->dmsg($cat,"\n" . Dumper($authz),8);
    unless($self->relevant_xpath($req->{channel_id},
                                 $req->{mpath},
                                 $authz->{xpath})) {
      next;
    }
    next unless($self->relevant_entities
                ($req->{owner},$req->{approval},$authz->{entities}));

    # if we got here then the current rule must be relevant
    return $authz->{is_allow};
  }

  # If we got here then no authorisation instruction was relevant. We
  # treat that as an error.
  AuthzException->
    throw("No relevant authorisation instruction for request " .
          Dumper($req));
}

sub att_iterator {
  my $self = shift;
  my $sth = shift;
  my @defs;
  return sub {
    my $ret;
    while(!$ret) {
      if ($sth->{Active} && (my $a = $sth->fetchrow_hashref)) {
        if($a->{is_mandatory}) {
          $ret = $a;
        } else {
          push @defs, $a;
        }
      } else {
        $ret = shift @defs;
        return unless defined $ret;
      }
    }
    return $ret;
  };
}

=item B<relevant_xpath>

$relevant = $ha->relevant_xpath($channel,$mpath,$xpath)

or

$relevant = $ha->relevant_xpath($channel,$element,$xpath)

=cut

sub relevant_xpath {
  my $self = shift;
  my ($channel,$mpath,$xpath) = @_;

  $self->log->dmsg("HAccessor.relevant_xpath",
                   "ch:$channel, mp:$mpath, xp:$xpath",9);

  my $elt;
  if(UNIVERSAL::isa($mpath, "XML::LibXML::Element")) {
    $elt = $mpath;
  } else {
    $elt = Machination::MPath->new($mpath)->construct_elt;
  }
  # elt must be part of a document for rooted xpaths to work properly
  my $doc = XML::LibXML::Document->new;
  $doc->setDocumentElement($elt);

  my @nodes;
  if($ENV{DODGY_XMLLIBXML}) {
    use XML::XPath;
    $self->log->dmsg("HAccessor.relevant_xpath", "via XML::XPath",9);
    @nodes = XML::XPath->new(xml=>$elt->toString)->findnodes($xpath);
  } else {
    $self->log->dmsg("HAccessor.relevant_xpath", "via XML::LibXML",9);
    @nodes = $elt->findnodes($xpath);
  }
  return scalar @nodes;
}

=item B<relevant_entities>

$relevant = $ha->relevant_entities($owner,$approval_list,$entities)

$owner = $authen_string

$approval_list = [$authen_string, $authen_string, ...]

collectively $owner and all in $approval_list are known as the full
aprovers list.

$entities = $stack

e.g.
$stack = ["and","nof",1,2,"nof",2,3]

means:
  (1 from set 2) AND (2 from set 3)

functions:

 nof: "nof",$n,$set_id

  Full approvers list must contain at least $n members of set
  $set_id.

 and: "and",$expression1,$expression2

 or: "or",$expression1,$expression2

=cut

sub relevant_entities {
  my $self = shift;
  my ($owner,$approval,$entities) = @_;
  my $cat = "HAccessor.relevant_entities";

#  my %app;
#  @app{$owner,@$approval} = (undef);
  my $todo = eval "$entities";
  my @stack;

  while (my $thing = pop @$todo) {
    if($thing eq "nof") {
      my $n = pop @stack;
      my $set_id = pop @stack;
      my $set = Machination::HSet->new($self,$set_id);
      my $members = $set->has_members("all",[$owner,@$approval]);
#      print Dumper($members);
      if(keys %$members >= $n) {
        push @stack, 1;
      } else {
        push @stack, 0;
      }
    } elsif($thing eq "and") {
      my $arg1 = pop @stack;
      my $arg2 = pop @stack;
      push @stack, $arg1 && $arg2;
    } elsif($thing eq "or") {
      my $arg1 = pop @stack;
      my $arg2 = pop @stack;
      push @stack, $arg1 || $arg2;
    } else {
      # an argument
      push @stack, $thing;
    }
  }

  $self->log->dmsg($cat, "relevant_entities returning $stack[0]",8);
  return $stack[0];
}

sub entities_to_stack {
  my $self = shift;
  my ($ent) = @_;
  my @stack;

  while() {

  }

  return \@stack;
}

=item B<action_allowed_hash>

$ha->action_allowed_hash($request,$authz_hash)

$authz_hash = hash ref with the following representation:
 {
  # from an authz_inst object:
  is_allow=>$is_allow,  # 0 or 1
  entities=>string,     # see $ha->authz_entities
  xpath=>$mpath,        # instruction applies if the xpath matches

  # not used if in hash because they should have been handled while
  # searching for relevant authz_inst objects (see fetch_authz_list):
  # from authz_inst object:
    # op=>$op,              # create, delete, settext, etc...
  # from agroup_authz_inst object:
    # channel_id=>$channel_id,      # string
  # from the agroup_authz_inst attachment:
    # is_mandatory=>$is_m,  # 0 or 1

# not yet implemented - held in reserve
#  applies_to_set=>$set, # set id
#  inherits=>$inherits,  # 0 or 1
 }

=cut

sub action_allowed_hash {
  my $self = shift;
  my ($req,$auth) = @_;
}

sub action_allowed_old {
  my $self = shift;
  my ($req,$auth) = @_;

	if (ref $auth eq "HASH") {
		# $auth is an authz instruction

		# not relevant - not the same channel_id
		return (0,{test=>"channel_id"})
	    if (exists $req->{channel_id} &&
          ($req->{channel_id} ne $auth->{channel_id}));

		# not relevant - not the same op
		return (0,{test=>"op"})
	    if (exists $req->{op} &&
					($auth->{op} ne "all" && $req->{op} ne $auth->{op}));

		# match action mpath against authorisation xpath
    if(exists $auth->{xpath}) {
      my $root_tag = $self->fetch("valid_channels",
                                 {fields=>["root_tag"],
                                 params=>[$req->{channel_id}]})->{root_tag};
      my $con = Machination::XMLConstructor->new($root_tag);
      $con->create();
    }
#		return (0,{test=>"mpath"})
#	    if (exists $req->{mpath} && ! $self->mpath_could_be_parent
#					($auth->{mpath},$req->{mpath}));


#		# not relevant - object of $req is not in $auth->{applies_to_set}
#		if (exists $req->{to} && defined $auth->{applies_to_set}) {
#	    my $set = Machination::HObjSet->new($self);
#	    return (0,{test=>"applies_to_set"})
#				unless ($set->has_member($req->{to}->{type},
#																 $req->{to}->{id},
#																 $auth->{applies_to_set}));
#		}

		# not relevant - owner/approved list not sufficient
		if (exists $req->{owner} || exists $req->{approval}) {
	    $req->{approval} = [] unless(defined $req->{approval});
	    $req->{approval} =
				$self->{dba}->db_arr_str_to_array($req->{approval})
					unless (ref $req->{approval} eq "ARRAY");
	    my %ent;
	    $ent{$req->{owner}} = undef;
	    foreach (@{$req->{approval}}) {
				$ent{$_} = undef;
	    }
	    return (0,{test=>"entities"})
				if (!$self->authz_entities(\%ent,$auth->{entities},
																	 Dumper(\%ent),
																	 $req->{owner},
																	 Dumper($req->{approval})));
		}

		# relevant - return $authz->{is_allow}
		return (1,$auth->{is_allow});

	} elsif (ref $auth eq "ARRAY") {
		# $auth is a ref to an array of authz instructions.
		# Try the request against each authz instruction in turn and
		# stop on the first relevant one.
		foreach my $a (@$auth) {
	    my ($rel,$ans) = $self->action_allowed($req,$a);
	    return (1,$ans) if $rel;
		}
		# no instruction was relevant
		return (0,{array=>1});
	} else {
		# $auth is an hc_id
		# Try all attached instructions in the hc's lineage. Try
		# mandatories first, then defaults.

		my @lineage = $self->hcontainer->fetch_lineage($auth);

		my $reason={};
		my @def_att;
		foreach my $hc (@lineage) {
			#	    print "doing hc " . $hc->{id} . "\n";
	    my $att = $self->hcontainer->
				list_att({types=>['agroup_authz_inst'],
									channel_id=>$req->{channel_id},
									fetch_applies_to_set=>1},
								 $hc->{id})->
									 {agroup_authz_inst};
			#	    print "att: " . Dumper($att);
	    # check mandatories
	    foreach my $agid (@{$att->{mandatory}}) {
				my $set = $att->{applies_to_set}->{$agid};
				my @aids = $self->fetch_from_agroup('authz_inst',$agid);
				foreach my $aid (@aids) {
					my $ai = {};
					$ai->{applies_to_set} = $set;
					$ai->{mandatory} = 1;
					my $ai_obj = $self->hobject->fetch('authz_inst',$aid);
					@{$ai}{keys %{$ai_obj->fields}} =
						values %{$ai_obj->fields};
					#		    print "checking ai: " . Dumper($req,$ai);
					my ($rel, $ans) = $self->action_allowed($req,$ai);
					#			Dumper($req),Dumper($ai));
					return (1,$ans) if $rel;
					$reason->{"hc:" . $hc->{id} . ",authz_inst:$aid"} = $ans;
				}
	    }
	    # store defaults for later
	    foreach my $agid (@{$att->{default}}) {
				unshift(@def_att,
								[$att->{applies_to_set}->{$agid},
								 $agid,
								 $hc->{id}]);
	    }
		}
		# check defaults
		foreach (@def_att) {
	    my ($set,$agid,$hc_id) = @{$_};
	    my @ais = $self->fetch_from_agroup('authz_inst',$agid);
	    foreach my $aid (@ais) {
				my $ai = {};
				$ai->{applies_to_set} = $set;
				$ai->{mandatory} = 0;
				my $ai_obj = $self->hobject->fetch('authz_inst',$aid);
				@{$ai}{keys %{$ai_obj->fields}} =
					values %{$ai_obj->fields};
				#		print "checking ai: " . Dumper($ai);
				my ($rel, $ans) = $self->action_allowed($req,$ai);
				return (1,$ans) if $rel;
				$reason->{"hc:$hc_id,authz_inst:$aid"} = $ans;
	    }
		}
		return(0,$reason);
	}
}

=item B<authz_condition_test>

$iface->authz_condition_test($value,$condition)

Test if $condition (from an authz pattern) is true or not.

$value should be a scalar.

$condition should have one of the following forms:

=over

=item - {type=>"string",value=>"example"}

Straight string match.

=item - {type=>"string_list",value=>{list=>undef,as=>undef,keys=>undef}}

Match if key $condition->{value}->{$value} exists.

=item - {type=>"regex",value=>"expression"}

Match if regex matches $value.

=item - {type=>"set",

value=>{set_id=>$id,obj_type=>$type,match_field=>"field"}}

Match if an object of type obj_type in set set_id has a value in field
match_field of $value.

=item - {type=>"program",value=>"shell cmd"}

Invoke a command, which should return a list of possible values, one per
line.

=back

return 0 or 1.

=cut

sub authz_condition_test {
    my $self = shift;
    my ($value,$condition) = @_;

    if($condition->{type} eq "string") {
	$value eq $condition->{value} ? return 1 : return 0;
    } elsif($condition->{type} eq "string_list") {
	exists ${$condition->{value}}{$value} ? return 1 : return 0;
    } elsif($condition->{type} eq "set") {
	my $set = Machination::HSet->
	    new($self->hobject);
	$set->object->id($condition->{value}->{set_id});
	my $members = $set->
	    fetch_members_of_type($condition->{value}->{obj_type});
	foreach my $member (keys %$members) {
	    my ($fval) = $self->fetch_fields
		("objectsoftype_" . $condition->{value}->{obj_type},
		 $member,$condition->{value}->{match_field});
	    return 1 if($fval eq $value);
	}
	return 0;
    } elsif($condition->{type} eq "regex") {
	$value=~$condition->{value} ? return 1 : return 0;
    } elsif($condition->{type} eq "program") {
	my $prog = $condition->{value};
	my @list = qx"$prog";
	chomp @list;
	foreach (@list) {
	    return  1 if($value eq $_);
	}
	return 0;
    } else {
	AuthzConditionException->
	    throw("unknown condition type \"" . $condition->{type} . "\"");
    }
}

=item *e $iface->authz_entities($requestors,$authz_entities)

$requestors has the following form:

#{ person => { 1=>undef, 5=>undef },
#  computer => { 1=>undef, 2=>undef } }

{ person:1=>undef, person:2=>undef, computer:1=>undef }

other entity types are possible.

$authz_entities is of the form:

=over

=item - list "$type:$id,$type:$id"

e.g. "person:1,person:2,computer:1"

=item - set "set:$id"

e.g "set:1"

=item - boolean function

Available functions:

=over

=item * [ "nof", $number, $list or $set ]

True if there are at least $number requestor entities in $list or
$set.

=item * [ "and", boolean expr, boolean expr ]

=item * [ "or", boolean expr, boolean expr ]

=back

Boolean expressions: $list or $set or function. $list is deemed to be
true if any requestor entity is in the list. $set is deemed to be true
if any requestor entity is a member of the set.

=back

=cut

sub authz_entities {
	my $self = shift;
	my ($r,$a) = @_;
	my $cat = "HAccessor.authz_entities";

	if (ref $a) {
		# function
		my $fn = shift @$a;
		if ($fn eq "nof") {
	    my ($n,$expr) = @$a;
	    my $count;
	    if (my($id)=$expr=~/^set:(\d+)/) {
				my $set = Machination::HSet->new($self->hobject);
				foreach my $r_ent (keys %$r) {
					my ($etype,$eid) = split(/:/,$r_ent);
					$count++ if ($set->has_member($etype,$eid,$id));
					return 1 if($count >= $n);
				}
	    } else {
				my @entities = split(/,/,$expr);
				$self->log->dmsg($cat,join(",",@entities),8);
				foreach my $ent (@entities) {
					$count++ if(exists $r->{$ent});
					return 1 if($count >= $n);
				}
	    }
	    return 0;
		} elsif ($fn eq "and") {
	    return ($self->authz_entities($r,$a->[0]) &&
							$self->authz_entities($r,$a->[1]));
		} elsif ($fn eq "or") {
	    return ($self->authz_entities($r,$a->[0]) ||
							$self->authz_entities($r,$a->[1]));
		} else {
	    AuthzEntitiesException->
				throw("unknown entity function \"$fn\"");
		}
	} elsif (my($id)=$a=~/^set:(.*)$/) {
		# a set

		# some special sets
		return 1 if($id eq "EVERYONE");
		return 0 if($id eq "NOBODY");

		# ordinary sets
		my $set = Machination::HSet->new($self->hobject);
		foreach my $r_ent (keys %$r) {
	    my ($etype,$eid) = split(/:/,$r_ent);
	    return 1 if ($set->has_member($etype,$eid,$id));
		}
		return 0;
	} else {
		# a list
		my @entities = split(/,/,$a);
		foreach my $ent (@entities) {
	    return 1 if(exists $r->{$ent});
		}
		return 0;
	}
}

=item * $self->osid($name,$major_version,$minor_version,$bitness)

return id of valid os with properties as args

=cut

sub osid {
  my $self = shift;
  my ($name,$majv,$minv,$bit) = @_;
  my $row = $self->write_dbh->
    selectrow_hashref("select id from valid_oses where " .
                      "name=? and major_version=? " .
                      "and minor_version=? and bitness=?",{},
                     $name,$majv,$minv,$bit);
  if($row) {
    return $row->{id};
  }
}

=item B<get_library_item>

$hpath_obj = $ha->get_library_item($assertion, $hc_id)

=cut

sub get_library_item {
  my $self = shift;
  my ($ass, $hid) = @_;

  # TODO(colin): investigate a more databasey way of doing this -
  # probably more efficient
  my $ass_mp = Machination::MPath->new($ass->{mpath});
  my $sth = $self->get_contents_handle
    ($hid, $self->type_id("agroup_assertion"));
  while(my $item = $sth->fetchrow_hashref) {
    # look for the first item which contains an assertion that will
    # satisfy our condition
    my $ag_sth = $self->get_ag_member_handle
      ($item->{type_id}, $item->{obj_id});
    while(my $item_ass = $ag_sth->fetchrow_hashref) {
      my $item_ass_mp = Machination::MPath($item_ass->{mpath});
      if($ass->{ass_op} eq "exists") {
        # will be satisfied where item action_op is create, settext or
        # choosetext and item mpath is ass mpath or a descendant
        if(
           (
            $item_ass->{action_op} eq 'create' or
            $item_ass->{action_op} eq 'settext' or
            $item_ass->{action_op} eq 'choosetext'
           )
           and
           $ass_mp->could_be_parent_of($item_ass_mp)
          ) {
          $ag_sth->finish;
          $sth->finish;
          return $item->{obj_id};
        }
      } elsif($ass->{ass_op} =~ /^hastext/) {
        # satisfied when item action_op is settext or choosetext and
        # action_arg satisifes the condition in ass->{ass_arg} and
        # item is ass mpath or a descendant of it
        if(
           (
            $item_ass->{action_op} eq 'settext' or
            $item_ass->{action_op} eq 'choosetext'
           )
           and
           $ass_mp->could_be_parent_of($item_ass_mp)
           and
           $self->meets_condition($item_ass->{action_arg},
                                  $ass->{ass_op},
                                  $ass->{ass_arg})
          ) {
          $ag_sth->finish;
          $sth->finish;
          return $item->{obj_id};
        }
      } elsif($ass->{ass_op} eq "notexists") {
        # satisfied when item action_op is delete and ass mpath is item
        # mpath or a descendent of it
        if($item_ass->{action_op} eq 'delete' and
           $item_ass_mp->could_be_parent_of($ass_mp)) {
          $ag_sth->finish;
          $sth->finish;
          return $item->{obj_id};
        }
      } else {
        MachinationException->throw
          ("Don't know how to find library item for assertion op " .
           $ass->{ass_op});
      }
    }
  }
  # We haven't found something yet. We'd better recurse down into any
  # hc children
  my $cont = $self->get_contents_handle($hid, ['machination:hc'])->
    fetchall_arrayref({});
  foreach my $hc (@$cont) {
    my $libitem = $self->get_library_item($ass, $hc->{obj_id});
    return $libitem if defined $libitem;
  }

  # didn't find anything
  return;
}


######################################################################
# bootstrapping
######################################################################

=head3 Bootstrapping

=item B<bootstrap_all>

=cut

sub bootstrap_all {
	my $self = shift;
	$self->bootstrap_functions;
	$self->bootstrap_tables;
	$self->bootstrap_ops;
  $self->bootstrap_basehcs;
	$self->bootstrap_object_types;
  $self->bootstrap_postobj_tables;
  $self->bootstrap_set_conditions;
  $self->bootstrap_setmember_types;
  $self->bootstrap_oses;
  $self->bootstrap_assertions;
	$self->bootstrap_channels;
#  $self->bootstrap_hierarchy;
  $self->bootstrap_special_sets;
#  $self->bootstrap_hierarchy2;
}

=item B<bootstrap_functions>

=cut

sub bootstrap_functions {
	my $self = shift;
	$self->dbc->config_base_functions;
}

=item B<bootstrap_tables>

=cut

sub bootstrap_tables {
	my $self = shift;
	$self->dbc->config_base_tables;
}

=item B<bootstrap_ops>

=cut

sub bootstrap_ops {
	my $self = shift;
	foreach my $op (keys %{$self->defops}) {
		$self->dbc->register_op($op,$self->defops->{$op});
	}
}

=item B<bootstrap_basehcs>

Create the basic hcs needed for things further on

=cut

sub bootstrap_basehcs {
  my $self = shift;

  # [ path, is_mp ]
  my @info =
    (
     ['/',1],
     ['/system',1],
     ['/system/sets/universal',0],
     ['/system/sets/empty',0],
    );

  foreach my $i (@info) {
    my $hp = Machination::HPath->new($self,$i->[0]);
    print $hp->to_string . "\n";
    $self->create_path({actor=>'Machination:System'}, $hp, {is_mp=>$i->[1]});
  }
}

=item B<bootstrap_object_types>

=cut

sub bootstrap_object_types {
	my $self = shift;

	foreach my $info (@{$self->def_obj_types}) {
		$self->add_object_type({actor=>'Machination:System'},$info->{name},$info->{plural},$info)
			unless ($self->type_exists_byname($info->{name},{cache=>0}));
	}
}

=item B<bootstrap_postobj_tables>

=cut

sub bootstrap_postobj_tables {
	my $self = shift;
	$self->dbc->config_postobj_tables;
}

=item B<bootstrap_channels>

=cut

sub bootstrap_channels {
	my ($self) = @_;
	my $file = $self->dbc->conf->get_file("file.database.BOOTSTRAP_CHANNELS");
	my $doc = $self->dbc->conf->parser->parse_file($file);
	my $elt = $doc->documentElement;

	foreach my $channel ($elt->findnodes("channel")->get_nodelist) {
    my $name = $channel->getAttribute("name");
		$self->add_channel({},$name,
                      $channel->getAttribute("root_tag"),
                      $channel->getAttribute("scratch_mpath"),
                      $channel->getAttribute("keep_scratch"))
      unless($self->channel_id($name));
	}
}

sub bootstrap_svc_subs {
	my ($self) = @_;

	foreach my $subs (@{$self->def_svc_subs}) {
		my $type = $subs->{type};
		my $svc = $subs->{svc};
		my @res = $self->dbc->dbh->
			selectrow_array("select type_id from svc_subscriptions " .
											"where type_id=? and svc_id=?",{},
											$self->type_id($type),$self->svc_id($svc));
		$self->svc_subscribe({},$self->type_id($type),$svc)
			unless(@res);
	}
}

=item B<path_from_xml_rep>

$string = $ha->path_from_xml_rep($element)

=cut

sub path_from_xml_rep {
	my ($self,$e) = @_;

	my $str;
	if ($e->nodeName eq "object") {
		my $ppath = $self->path_from_xml_rep($e->parentNode->parentNode);
		$str = $ppath . "/" .
			$e->getAttribute("type") . ":" . $e->getAttribute("name");
	} elsif ($e->nodeName eq "objlink") {
    return $self->path_from_xml_rep($e->parentNode->parentNode);
  } elsif ($e->nodeName eq "member") {
    return $self->path_from_xml_rep($e->parentNode);
  } elsif ($e->nodeName eq "hc") {
		if ($e->parentNode->nodeType == XML_DOCUMENT_NODE) {
			$str = "/";
		} else {
			my $ppath = $self->path_from_xml_rep($e->parentNode->parentNode);
			$ppath = "" if $ppath eq "/";
			$str =  $ppath . "/" . $e->getAttribute("name") . $str;
		}
	} else {
		MachinationException->
			throw("can't construct a path from an xml element with tag " .
            $e->nodeName);
	}
	return $str;
}

=item B<bootstrap_assertions>

=cut

sub bootstrap_assertions {
	my ($self) = @_;
	my $file = $self->dbc->conf->get_file("file.database.BOOTSTRAP_ASSERTIONS");
	my $doc = $self->dbc->conf->parser->parse_file($file);
	my $elt = $doc->documentElement;
  my $actions = $elt->findnodes("action_ops/op");
  my $assertions = $elt->findnodes("assertion_ops/op");

  foreach ($actions->get_nodelist) {
    my $action = $_->getAttribute("id");
    my $complete = $_->getAttribute("complete");
    my $overlay = $_->getAttribute("overlay");
    my $arg_meaning = $_->getAttribute("arg_meaning");
    my $desc = $_->getAttribute("description");
    # see if action already exists
    my @row = $self->write_dbh->selectrow_array
      ("select op from valid_action_ops where op=?",{},$action);
    unless(@row) {
      # if not create it
      $self->add_valid_action_op
        ({},$action,$complete,$overlay,$arg_meaning,$desc);
    }
  }
  foreach ($assertions->get_nodelist) {
    my $assertion = $_->getAttribute("id");
    my $arg_meaning = $_->getAttribute("arg_meaning");
    # see if op already exists
    my @row = $self->write_dbh->selectrow_array
      ("select op from valid_assertion_ops where op=?",{},$assertion);
    unless(@row) {
      # if not create it
      $self->add_valid_assertion_op({},$assertion,$arg_meaning);
    }
  }
}

#sub bootstrap_lib_assertions {
#	my ($self) = @_;
####	my $file = $self->dbc->conf->get_file("file.database.BOOTSTRAP_LIB_ASSERTIONS");
#	my $doc = $self->dbc->conf->parser->parse_file($file);
#	my $elt = $doc->documentElement;
#  my $assertions = $elt->findnodes("valid_ops/op");
#
#  foreach ($assertions->get_nodelist) {
#    my $assertion = $_->getAttribute("id");
#    my @row = $self->write_dbh->selectrow_array
#      ("select op from lib_assertion_ops where op=?",{},$assertion);
#    unless(@row) {
#      # if not create it
#      $self->add_valid_lib_assertion_op({},$assertion);
#    }
#  }
#}

=item B<bootstrap_setmember_types>

=cut

sub bootstrap_setmember_types {
	my ($self) = @_;
	my $file = $self->dbc->conf->
    get_file("file.database.BOOTSTRAP_SETMEMBER_TYPES");
	my $doc = $self->dbc->conf->parser->parse_file($file);
	my $elt = $doc->documentElement;
  my $types = $elt->findnodes("type");

  foreach ($elt->findnodes("type")->get_nodelist) {
    my $type = $_->getAttribute("id");
    # see if type already exists
    my @row = $self->write_dbh->selectrow_array
      ("select type from setmember_types where type=?",{},$type);
    unless(@row) {
      # if not create it
      $self->add_setmember_type({},$type,0,$_->getAttribute("is_set"));
    }
  }
}

=item B<bootstrap_set_conditions>

=cut

sub bootstrap_set_conditions {
	my ($self) = @_;
	my $file = $self->dbc->conf->
    get_file("file.database.BOOTSTRAP_SET_CONDITIONS");
	my $doc = $self->dbc->conf->parser->parse_file($file);
	my $elt = $doc->documentElement;
  my $ops = $elt->findnodes("op");

  foreach ($ops->get_nodelist) {
    my $op = $_->getAttribute("id");
    # see if op already exists
    my @row = $self->write_dbh->selectrow_array
      ("select op from valid_condition_ops where op=?",{},$op);
    unless(@row) {
      # if not create it
      $self->add_valid_condition_op({},$op);
    }
  }
}

=item B<bootstrap_oses>

=cut

sub bootstrap_oses {
	my ($self) = @_;
	my $file = $self->dbc->conf->
    get_file("file.database.BOOTSTRAP_OSES");
	my $doc = $self->dbc->conf->parser->parse_file($file);
	my $elt = $doc->documentElement;
#  my $oses = $elt->findnodes("os");

  foreach ($elt->findnodes("os")->get_nodelist) {
    # see if os already exists
    my @row = $self->write_dbh->selectrow_array
      ("select name,major_version,minor_version,bitness " .
       "from valid_oses where " .
       "name=? and major_version=? and " .
       "minor_version=? and bitness=?",{},
      $_->getAttribute("name"),
      $_->getAttribute("major_version"),
      $_->getAttribute("minor_version"),
      $_->getAttribute("bitness"));
    unless(@row) {
      # if not create it
      $self->add_valid_os
        ({},
         $_->getAttribute("name"),
         $_->getAttribute("major_version"),
         $_->getAttribute("minor_version"),
         $_->getAttribute("bitness"));
    }
  }
}

=item B<mexpand>

$expanded_string = $ha->mexpand($text,$data)

=cut

sub mexpand {
	my $self = shift;
	my ($text,$data) = @_;
  $data = {} unless defined $data;
  my $cat = "HAccessor.mexpand";

	my $escape;
	my @outstack = ("");
	while ($text=~/\G(.*?)(\\+|\{|\}|$)/g) {
		my $txt = $1;
		my $div = $2;
		push (@outstack, pop(@outstack) . $txt);
		if ($div=~/\\+/) {
			$escape = 1 if(length($div) % 2);
			my $newtext =  "\\";
			$newtext = $newtext x (length($div) / 2);
			push(@outstack, pop(@outstack) . $newtext);
		} elsif ($div eq "{") {
			if ($escape) {
				push(@outstack, pop(@outstack) . "{");
				$escape = 0;
			} else {
				push(@outstack, "");
			}
		} elsif ($div eq "}") {
			if ($escape) {
				push(@outstack, pop(@outstack) . "}");
				$escape = 0;
			} else {
				# evaluate macro
				my $macro = pop @outstack;
        if($macro=~/^ref\((.*?)\)/) {
          if(exists $data->{labels}->{$1}) {
            push(@outstack, pop(@outstack) .
                $data->{labels}->{$1}->{type} . ":" .
                $data->{labels}->{$1}->{id});
          } else {
            die "label not found: $1 (ref)";
          }
        }	elsif($macro=~/^ref_id\((.*?)\)/) {
          if(exists $data->{labels}->{$1}) {
            push(@outstack, pop(@outstack) .
                 $data->{labels}->{$1}->{id});
          } else {
            die "label not found: $1 (ref_id)";
          }
        } elsif ($macro=~/^f:(\w+)\((.*?)\)/) {
          my $func = $1;
          my $args = $2;
          my @args;
          while ($args=~/\G(.+?)(,|$)/g) {
            push @args, $1;
          }
          $self->log->dmsg($cat,"args: " . join(",",@args),8);
					push(@outstack, pop(@outstack) . $self->$func(@args));
        } elsif ($macro=~/^type_id\((.*?)\)/) {
					push(@outstack, pop(@outstack) . $self->type_id($1));
				} elsif ($macro=~/^fetch_path_id\((.*?)\)/) {
          push(@outstack, pop(@outstack) . $self->fetch_path_id($1));
        } elsif ($macro=~/^osid\((.*?),(.*?),(.*?),(.*?)\)/) {
#          print "calling osid($1,$2,$3,$4)\n";
          push(@outstack, pop(@outstack) . $self->osid($1,$2,$3,$4));
        } elsif ($macro=~/^\$(.*)/) {
          my $mname = $1;
          push(@outstack, pop(@outstack) . $data->{macros}->{$mname});
        } else {
					push(@outstack, pop(@outstack) . $macro);
				}
			}
		}
		#       print Dumper(\@outstack) . "\n";
	}

	#    print $outstack[0] . "\n";
	return $outstack[0];
}

=item B<bootstrap_hierarchy>

Create hcs, objects, attachments and links from XML file
(file.hierarchy.BOOTSTRAP from config.xml).

bootstrap_hierarchy runs after all object types are created, but
before some other bootstrap tasks which need an hc path to run (like
creating UNIVERSAL and EMPTY sets for all object types for
example). Sometimes one needs to refer to these things that are
bootstrapped later in order to create some piece of hierarchy (create
an authz instruction using a UNIVERSAL set, for example). For this,
use bootstrap_hierarchy2, which runs after everything else.

=cut

sub bootstrap_hierarchy {
	my ($self) = @_;
	my $hfile = $self->dbc->conf->get_file("file.hierarchy.BOOTSTRAP");
  $self->_bootstrap_hierarchy($hfile);
}

=item B<bootstrap_hierarchy2>

=cut

sub bootstrap_hierarchy2 {
	my ($self) = @_;
	my $hfile = $self->dbc->conf->get_file("file.hierarchy2.BOOTSTRAP");
  $self->_bootstrap_hierarchy($hfile);
}

sub _bootstrap_hierarchy {
  my ($self,$hfile) = @_;
  my $hdoc = $self->dbc->conf->parser->parse_file($hfile);
	my $h = $hdoc->documentElement;
  my $cat = "HAccessor._bootstrap_hierarchy";

  my $macrosets = {};
  my $labels = {};
  my $todo = {"/"=>undef};
  my $changed = 1;

  while (keys %$todo && $changed) {
    $todo = {};
    $changed = 0;
    my @stack = ($h);
  OBJECT: while (my $e = pop @stack) {
      my $strpath = $self->path_from_xml_rep($e);
#      $todo->{$strpath} = undef;
      my $hpath = Machination::HPath->new($self,$strpath);
      my $owner = $e->getAttribute("owner");
      # set the owner to the same as the parent object if not otherwise defined
      if(!defined $owner || $owner eq "") {
        if($hpath->parent_id) {
          $owner = Machination::HObject->
            new($self,"machination:hc",$hpath->parent_id)->
              fetch_data("owner")->{owner};
        }
      }

      # any node could have a label attribute
      my $nodelabel = $e->getAttribute("label");

      if ($e->nodeName eq "hc") {
        $todo->{$strpath} = undef;
        $self->log->lmsg($cat,"dealing with $strpath",1);
        my $id = $hpath->id;
        my $macros = {};
        if(exists $macrosets->{$hpath->parent_id}) {
          %$macros = %{$macrosets->{$hpath->parent_id}};
        };
        if (! $id) {
          # hc doesn't exist yet, create it
          $owner = $self->mexpand($owner,{macros=>$macros,labels=>$labels});
          my $is_mp = $e->getAttribute("is_mp");
          $is_mp = 0 unless defined $is_mp;
          $id = $self->create_obj({actor=>$owner},undef,
                                  $e->getAttribute("name"),
                                  $hpath->parent_id,
                                  {is_mp=>$is_mp});
          # we've made a change
          $changed = 1;
        }
        foreach my $m ($e->findnodes("macro")) {
          $macros->{$m->getAttribute("name")} = $m->textContent;
        }
        $macrosets->{$id} = $macros;

        # remember the label, if any
        if(defined $nodelabel && ! exists $labels->{$nodelabel}) {
          $labels->{$nodelabel} = {type=>"machination:hc",id=>$id};
          $changed = 1;
        }

        # put contents onto the stack
        push @stack, reverse($e->findnodes("contents/*"));

        # done with this path
        delete $todo->{$strpath};
      } elsif ($e->nodeName eq "object") {
        my $todoname = $strpath;
        $todo->{$todoname} = undef;
        $self->log->lmsg($cat,"dealing with $todoname",1);
        my $macros = $macrosets->{$hpath->parent};
        $owner = $self->mexpand($owner,{labels=>$labels,macros=>$macros});
        my $id = $hpath->id;
        my $type_name = $e->getAttribute("type");
        my $type_id = $self->type_id($type_name);

        #      my $owner = $self->mexpand($macros,$e->getAttribute("owner"));

        # try to create the object if it doesn't exist
        if (! $id) {
          my %fields;
          foreach my $fe ($e->findnodes("field")) {
            eval {
              $fields{$fe->getAttribute("name")} =
                $self->mexpand($fe->textContent,
                               {labels=>$labels,macros=>$macros});
            };
            if($@) {
              if($@ =~ /^label not found:/) {
                # The object to be created has a field that depends on another
                # object labelled object which hasn't been created yet.
                # Skip this object until label is resolved
                next OBJECT;
              } else {
                die $@;
              }
            }
          }
          #               print "creating " . $hpath->to_string . "  with fields:\n " . Dumper(\%fields) . "\n";
          $id = $self->create_obj
            ({actor=>$owner},
             $type_id,
             $e->getAttribute("name"),
             $hpath->parent_id,
             \%fields);

          # we've made a change
          $changed = 1;
        }

        # add members to stack if this is a set and there are any listed
        if($type_name eq "set") {
          push @stack, $e->findnodes("member");
        }

        # remember this object's label if there is one
        if(defined $nodelabel && ! exists $labels->{$nodelabel}) {
          $labels->{$nodelabel} = {type=>$type_id,id=>$id};
          $changed = 1;
        }

        # object is done if we get this far
        delete $todo->{$todoname};

      } elsif ($e->nodeName eq "member") {
        # $hpath is the containing set object

        my $todoname = "$strpath/member:" . $e->textContent;
        $todo->{$todoname} = undef;
        $self->log->lmsg($cat,"dealing with $todoname",1);

        my $macros = $macrosets->{$hpath->parent};
        $owner = $self->mexpand($owner,{labels=>$labels,macros=>$macros});

        # <member>ref_id(/path/to/member)</member>
        # <member>string</member>
        my $member;
        eval {$member = $self->
                mexpand($e->textContent,{macros=>$macros,labels=>$labels});};
        if($@) {
          if($@ =~ /^label not found:/) {
            # trying to add a member that hasn't been created yet
            next OBJECT;
          } else {
            die $@;
          }
        }

        my $set = Machination::HSet->new($self,$hpath->id);
        unless($set->has_member("direct",$member)) {
          # add $member to the set
          $self->add_to_set({actor=>$owner},$hpath->id,$member);

          # we've made a change
          $changed = 1;
        }

        # member is done if we get this far
        delete $todo->{$todoname};
      } elsif ($e->nodeName eq "objlink") {
        # $hpath,$strpath are containing hc

        my $macros = $macrosets->{$hpath->parent};
        my $ref = $e->getAttribute("ref");
        my $todoname = "$strpath/::objlink:$ref";
        $todo->{$todoname} = undef;
        $self->log->lmsg($cat,"dealing with $todoname",1);
        $owner = $self->mexpand($owner,{labels=>$labels,macros=>$macros});

        eval {$ref = $self->mexpand($ref,{macros=>$macros,labels=>$labels});};
        if($@) {
          if($@ =~ /^label not found:/) {
            # trying to add a member that hasn't been created yet
            next OBJECT;
          } else {
            die $@;
          }
        }
        my ($type_id,$obj_id) = split(":",$ref);
        my $obj = Machination::HObject->new($self,$type_id,$obj_id);
        my $obj_data = $obj->fetch_data;

        eval {
          $self->add_to_hc({actor=>$owner},
                          $type_id,$obj_id,$hpath->id);
        };
        my $e;
        if($e=Exception::Class->caught('HierarchyNameExistsException')) {
          # probably means we made this link before - do nothing
        } else {
          # a "real" error
          $e = Exception::Class->caught;
          ref $e ? $e->rethrow : die Dumper($e);
        }

        # link is done if we get this far
        delete $todo->{$todoname};
      }
    }
  }
  die "_bootstrap_hierarchy: no change and things to do:\n" .
    Dumper($todo) if(keys %$todo);

}

sub _bootstrap_hierarchy_old {
  my ($self, $hfile) = @_;
	my $hdoc = $self->dbc->conf->parser->parse_file($hfile);
	my $h = $hdoc->documentElement;

  my $macrosets = {};
  my $refs = {};
	my @stack = ($h);
	while (my $e = pop @stack) {
		print "dealing with " . $self->path_from_xml_rep($e) . "\n";
		my $hpath = Machination::HPath->new($self,$self->path_from_xml_rep($e));
    my $owner = $e->getAttribute("owner");
    # set the owner to the same as the parent object if not otherwise defined
    if(!defined $owner || $owner eq "") {
      if($hpath->parent) {
        $owner = Machination::HObject->
          new($self,"machination:hc",$hpath->parent)->
            fetch_data("owner")->{owner};
      }
    }
		if ($e->nodeName eq "hc") {
      my $id = $hpath->id;
      my $macros = {};
      if(exists $macrosets->{$hpath->parent}) {
        %$macros = %{$macrosets->{$hpath->parent}};
      };
			if (! $id) {
        $owner = $self->mexpand($macros,$owner);
				my $is_mp = $e->getAttribute("is_mp");
				$is_mp = 0 unless defined $is_mp;
				$id = $self->create_obj({actor=>$owner},undef,
                                $e->getAttribute("name"),
                                $hpath->parent,
                                {is_mp=>$is_mp});
			}
      foreach my $m ($e->findnodes("macro")) {
        $macros->{$m->getAttribute("name")} = $m->textContent;
      }
      $macrosets->{$id} = $macros;
			push @stack, reverse($e->findnodes("contents/*"));
		} elsif ($e->nodeName eq "object") {
      my $macros = $macrosets->{$hpath->parent};
      $owner = $self->mexpand($macros,$owner);
			my $id = $hpath->id;
      my $type_name = $e->getAttribute("type");
      my $type_id = $self->type_id($type_name);
#      my $owner = $self->mexpand($macros,$e->getAttribute("owner"));
      # create the object if it doesn't exist
			if (! $id) {
				my %fields;
				foreach my $fe ($e->findnodes("field")) {
					$fields{$fe->getAttribute("name")} =
						$self->mexpand($macros,$fe->textContent);
				}
				#               print "creating " . $hpath->get_string . "  with fields:\n " . Dumper(\%fields) . "\n";
				$id = $self->create_obj
          ({actor=>$owner},
           $type_id,
           $e->getAttribute("name"),
           $hpath->parent,
           \%fields);

        # add members if this is a set and there are any listed
        if($type_name eq "set") {
          my @members;
          foreach my $me ($e->findnodes("member")) {
            if(my $ref = $me->getAttribute("ref")) {
              $refs->{$ref} = {__pending=>1}
                unless(exists $refs->{$ref});
              if($refs->{$ref}->{__pending}) {
                $refs->{$ref}->{member} = []
                  unless(exists $refs->{$ref}->{member});
                push @{$refs->{$ref}->{member}}, $id;
              } else {
                # $refs->{$ref} represents the member object
                push @members, $refs->{$ref}->{obj_id};
              }
            } else {
              push @members, $self->mexpand($macros,$me->textContent);
            }
          }
          $self->add_to_set({actor=>$owner},$id,@members);
        }
			}

      # remember the ref to this object if there is one and add any
      # outstanding links, members etc
      if(my $ref = $e->getAttribute("ref")) {
        if(exists $refs->{$ref}) {
          # either an object with this ref already exists or there are
          # pending references waiting to be resolved
          if($refs->{$ref}->{__pending}) {
            # add any pending link references to the appropriate hcs
            foreach my $hc (@{$refs->{$ref}->{objlink}}) {
              $self->add_to_hc({actor=>$owner},
                               $type_id,
                               $id,
                               $hpath->parent)
                unless($self->object_is_in($type_id,$id,$hpath->parent));
            }
            # add any pending member references to the appropriate sets
            foreach my $set_id (@{$refs->{$ref}->{member}}) {
              $self->add_to_set({actor=>$owner},$set_id,$id);
            }
          } else {
            # an object with this ref already exists
            die "there seems to be more than one object " .
              "with the reference $ref";
          }
        }
        $refs->{$ref} = {type_id=>$type_id,
                         obj_id=>$id, owner=>$owner};
      }

    } elsif ($e->nodeName eq "objlink") {
      my $ref = $e->getAttribute("ref");
      if(!exists $refs->{$ref}) {
        # object not created yet and no other pending actions
        $refs->{$ref} = {__pending=>1};
      }
      if($refs->{$ref}->{__pending}) {
        $refs->{$ref}->{objlink} = []
          unless(exists $refs->{$ref}->{objlink});
        push @{$refs->{$ref}->{objlink}}, $hpath->id;
      } else {
        # object to link to
        my $objname = $self->fetch_name
          ($refs->{$ref}->{type_id},$refs->{$ref}->{obj_id});
        $self->add_to_hc({actor=>$refs->{$ref}->{owner}},
                         $refs->{$ref}->{type_id},
                         $refs->{$ref}->{obj_id},
                         $hpath->id)
          unless($self->fetch_id($refs->{$ref}->{type_id},
                                 $objname,
                                 $hpath->id));
      }
    }
	}

}

=item B<bootstrap_special_sets>

=cut

sub bootstrap_special_sets {
  my $self = shift;

  # create universal and empty sets for each object type

  foreach my $type ($self->fetch("setmember_types",
                                 {condition=>"",
                                  fields=>["type","is_internal"]})) {
    $self->create_special_sets($type->{type});
  }
}

sub create_special_sets {
  my $self = shift;
  my ($type) = @_;

#  my $univ_hpath = $self->conf->root->
#    findvalue('/config/subconfig[@xml:id="subconfig.hierarchy"]' .
#              '/hc[@id="/system/sets/universal"]/@hpath');
#  my $empty_hpath = $self->conf->root->
#    findvalue('/config/subconfig[@xml:id="subconfig.hierarchy"]' .
#              '/hc[@id="/system/sets/empty"]/@hpath');
#  $univ_hpath = "/system/sets/universal" unless(defined $univ_hpath);
#  $empty_hpath = "/system/sets/empty" unless(defined $empty_hpath);
  my $univ_hpath = "/system/sets/universal";
  my $empty_hpath = "/system/sets/empty";

#  print "$univ_hpath\n$empty_hpath\n";

  my $uhp = Machination::HPath->new($self,$univ_hpath);
  my $ehp = Machination::HPath->new($self,$empty_hpath);

  die "create_special_sets: $univ_hpath doesn't exist"
    unless($uhp->id);
  die "create_special_sets: $empty_hpath doesn't exist"
    unless($ehp->id);

  my $uhc = Machination::HObject->new($self,"machination:hc",$uhp->id);
  my $ehc = Machination::HObject->new($self,"machination:hc",$ehp->id);
  my $udata = $uhc->fetch_data;
  my $edata = $ehc->fetch_data;

  my $row = $self->fetch("setmember_types",
                         {condition=>"type=?",
                          params=>[$type],
                          fields=>["type","is_internal"]});
  my $type_name = $type;
  $type_name = $self->type_name($type) if($row->{is_internal});
  my $set_name;
  if($row->{is_internal}) {
    $set_name = $type_name;
  } else {
    $set_name = "external::$type_name";
  }

  $self->create_obj({actor=>$udata->{owner}},
                    $self->type_id("set"),
                    $set_name,
                    $udata->{id},
                    {is_internal=>$row->{is_internal},
                     member_type=>$type,
                     direct=>"UNIVERSAL"})
    unless($self->fetch_id($self->type_id("set"),
                           $set_name,
                           $udata->{id}));
  $self->create_obj({actor=>$edata->{owner}},
                    $self->type_id("set"),
                    $set_name,
                    $edata->{id},
                    {is_internal=>$row->{is_internal},
                     member_type=>$type,
                     direct=>"EMPTY"})
    unless($self->fetch_id($self->type_id("set"),
                           $set_name,
                           $edata->{id}));
}

######################################################################
# Operations
######################################################################

=head3 Operations

=item  B<op_add_object_type>

=item  B<add_object_type>

=cut

sub add_object_type {
	my $self = shift;
	$self->do_op("add_object_type",@_);
}
sub op_add_object_type {
	my $self = shift;
	my ($actor,$rev,$type,$plural,$opts) = @_;
  my $cat = "HAccessor.op_add_object_type";
	my $entity = $opts->{is_entity};
	$entity = 0 unless defined $entity;
	my $attachable = $opts->{is_attachable};
	$attachable = 0 unless defined $attachable;
	my $agroup = $opts->{is_agroup};
	$agroup = 0 unless defined $agroup;
	my $cols = $opts->{cols};
	$cols = [] unless defined $cols;
	my $fks = $opts->{fks};
	$fks = [] unless defined $fks;

  my $direct_attachable = int($agroup || ($type eq "set"));

  my $dbc = $self->dbc;
  my $dbh = $dbc->dbh;
#  my $dbh = $self->write_dbh;

	# can't add an existing type - the database will enforce this too
  if($self->type_exists_byname($type, {cache=>0})) {
		MachinationException->
      throw("Tried to add an object type that " .
            "already exists ($type)");
  }

	# there's a bootstrapping problem such that the type "set" has to be
	# added first (so that the foreign key constraints on the set
	# membership tables can be added).
	if ($type ne "set" && ! $self->type_exists_byname("set",{cache=>0})) {
		MachinationException->
      throw("Could not add type \"$type\" - " .
            "the object type \"set\" must be added first.");
	}

  # check that the table referred to in any "objtable" foreign
  # key constraints has been created
	foreach my $fk (@$fks) {
		if (my $objtable = $fk->{objtable}) {
			my $other_id;
			eval {
				$other_id = $dbh->selectall_hashref
          ("select id,name from object_types where name=?",
           'name',{},$objtable)->{$objtable}->{"id"};
			};
			if (my $e = $@) {
				croak "couldn't find $objtable type id:\n$e";
			}
			$fk->{table} = "objs_$other_id";
		}
	}

  my $agroup_type_id;
  if ($attachable) {
		$agroup_type_id = $self->do_op
      ("add_object_type",{actor=>$actor,parent=>$rev},
       "agroup_$type", "agroup_$plural",
       {is_agroup=>1,
        cols=>[["channel_id",Machination::DBConstructor::IDREF_TYPE,
                {nullAllowed=>0}]],
        fks=>[{table=>"valid_channels",
               cols=>[["channel_id","id"]]}],
       });
		push @$cols,
      ["agroup",Machination::DBConstructor::IDREF_TYPE,{nullAllowed=>0}],
        ["ag_ordinal","bigint",{nullAllowed=>0}];
		push @$fks,
      {table=>"objs_$agroup_type_id",
       cols=>[['agroup','id']]};
	}


	# Add a row to the object_types table and get the type id
	my $sth = $dbh->
    prepare_cached("insert into object_types " .
                   "(name,plural,is_entity,is_attachable,agroup,rev_id) " .
                   "values (?,?,?,?,?,?)",
                   {dbi_dummy=>"HAccessor.add_object_type"});
	eval {
		$sth->execute($type,$plural,$entity,$direct_attachable,$agroup_type_id,$rev);
	};
	if (my $e = $@) {
    print "ent: '$entity'\natt: '$direct_attachable'\n";
		croak $e;
	}
	$sth->finish;

	# find the id of the type we just created
	$sth = $dbh->
    prepare_cached("select currval('object_types_id_seq')",
                   {dbi_dummy=>"current_object_id"});
	eval {
		$sth->execute;
	};
	if (my $e = $@) {
		croak $e;
	}
	my ($type_id) = $sth->fetchrow_array;
	$sth->finish;

	my @tables;

  my $objs_table =
    {name=>"objs_$type_id",
     pk=>['id'],
     fks=>$fks,
     history=>1,
     cols=>[
            ['id',Machination::DBConstructor::ID_TYPE],
            ['name',Machination::DBConstructor::OBJECT_NAME_TYPE,
             {nullAllowed=>0}],
            ['owner',Machination::DBConstructor::OBJECT_NAME_TYPE,
             {nullAllowed=>0}],
            @$cols,
           ],
    };
  # entities must have globally unique names
  $objs_table->{cons} = [{type=>"UNIQUE",cols=>['name']}]
    if($entity);
	push @tables,
    (
     $dbc->gentable
     ($objs_table),
     $dbc->gentable
     ({name=>"hccont_$type_id",
       pk=>["obj_id","hc_id"],
       cols=>[["obj_id",Machination::DBConstructor::IDREF_TYPE],
              ["hc_id",Machination::DBConstructor::IDREF_TYPE]],
       fks=>[{table=>"objs_$type_id",
              cols=>[['obj_id','id']]},
             {table=>'hcs',
              cols=>[['hc_id','id']]}],
       history=>1,
      }),
    );

	if ($type eq "set") {
    #		push @tables, $dbc->gentable
    #      ({name=>"nested_sets",
    #        pk=>["child_id","parent_id"],
    #        cols=>[["child_id",Machination::DBConstructor::IDREF_TYPE],
    #               ["parent_id",Machination::DBConstructor::IDREF_TYPE]],
    #        fks=>[{table=>"objs_$type_id",
    #               cols=>[['child_id','id']]},
    #              {table=>"objs_$type_id",
    #               cols=>[['parent_id','id']]}],
    #        history=>1,
    #       });
    #		push @tables, $dbc->gentable
    #      (
    #       {name=>"special_sets",
    #        pk=>['name'],
    #        cols=>[['name','varchar'],
    #               ['set_id',Machination::DBConstructor::IDREF_TYPE],
    #							],
    #        fks=>[{table=>"objs_$type_id",cols=>[['set_id','id']]}],
    #        cons=>[{type=>"UNIQUE",cols=>['set_id']}],
    #        history=>1,
    #       }
    #      );
    push @tables,
      (
       $dbc->gentable
       ({name=>"setmembers_external",
         pk=>["set_id","obj_rep"],
         cols=>[["set_id",Machination::DBConstructor::IDREF_TYPE],
                ["obj_rep","varchar"]],
         fks=>[{table=>"objs_$type_id",cols=>[["set_id","id"]]}],
         history=>1,
        }),
       $dbc->gentable
       ({name=>"hcatt_$type_id",
         pk=>["obj_id","hc_id"],
         cols=>[["obj_id",Machination::DBConstructor::IDREF_TYPE],
                ["hc_id",Machination::DBConstructor::IDREF_TYPE],
                ['ordinal','bigint',{nullAllowed=>0}],
                ["owner",Machination::DBConstructor::OBJECT_NAME_TYPE,
                 {nullAllowed=>0}],
               ],
         fks=>[{table=>"objs_$type_id",
                cols=>[['obj_id','id']]},
               {table=>'hcs',
                cols=>[['hc_id','id']]},
               ],
         cons=>[{type=>"UNIQUE",cols=>['hc_id','ordinal']}],
         history=>1,
        }),
      )
    }
	my $set_type_id;
	if ($type eq "set") {
		$set_type_id = $type_id;
	} else {
		eval {
			$set_type_id = $dbh->selectall_hashref
        ("select id,name from object_types where name='set'",'name')
					->{"set"}->{"id"};
		};
		if (my $e = $@) {
			croak "couldn't find set type id:\n$e";
		}
	}
	push @tables, $dbc->gentable
    (
     {name=>"setmembers_$type_id",
      pk=>["obj_id","set_id"],
      cols=>[["obj_id",Machination::DBConstructor::IDREF_TYPE],
             ["set_id",Machination::DBConstructor::IDREF_TYPE]],
      fks=>[{table=>"objs_$type_id",
             cols=>[['obj_id','id']]},
            {table=>"objs_$set_type_id",
             cols=>[['set_id','id']]}],
      history=>1,
     }
    );

	if ($agroup) {
		push @tables,
      $dbc->gentable
				({name=>"hcatt_$type_id",
					pk=>["obj_id","hc_id"],
					cols=>[["obj_id",Machination::DBConstructor::IDREF_TYPE],
								 ["hc_id",Machination::DBConstructor::IDREF_TYPE],
								 ['ordinal','bigint',{nullAllowed=>0}],
								 ["is_mandatory","boolean",{nullAllowed=>0}],
								 ['applies_to_set',Machination::DBConstructor::IDREF_TYPE],
								 ["approval","varchar[]"],
								 ["owner",Machination::DBConstructor::OBJECT_NAME_TYPE,
									{nullAllowed=>0}],
#								 ["channel_id",Machination::DBConstructor::IDREF_TYPE,
#                  {nullAllowed=>0}],
                 ["active","boolean",{default=>1}],
                ],
					fks=>[{table=>"objs_$type_id",
								 cols=>[['obj_id','id']]},
								{table=>'hcs',
								 cols=>[['hc_id','id']]},
								{table=>"objs_$set_type_id",
								 cols=>[['applies_to_set','id']]},
#								{table=>"valid_channels",
#								 cols=>[["channel_id","id"]]},
               ],
					cons=>[{type=>"UNIQUE",cols=>['hc_id','ordinal']}],
					history=>1,
				 });
	}
	if ($type eq "authz_set") {
		push @tables,
      $dbc->gentable
				({name=>"authz_set_members",
					pk=>["set_id","identifier_type","identifier"],
					cols=>[["set_id",Machination::DBConstructor::IDREF_TYPE],
								 ["identifier_type","varchar"],
								 ["identifier","varchar"],],
					fks=>[{table=>"objs_$type_id",cols=>[["set_id","id"]]}],
					history=>1,
				 });
	}

	foreach my $t (@tables) {
		$self->log->dmsg($cat,$t->toString(1),8);
		$dbc->dbconfig->config_table_all($t);
	}

  my $is_set = $type eq "set";
  $is_set = 0 unless($is_set);
  $self->do_op("add_setmember_type",{actor=>$actor,parent=>$rev},
               $type_id,1,$is_set);

  print "creating special sets...\n";
#  return $type_id;
  print "here2\n";
  # create a universal and empty set for this type
  my $uhp = Machination::HPath->new($self, "/system/sets/universal");
  my $ehp = Machination::HPath->new($self, "/system/sets/empty");
  $self->do_op("create_obj",{actor=>$actor, parent=>$rev},
               $set_type_id,
               $type, # as the name of the set
               $uhp->id,
               {
                is_internal=>1,
                member_type=>$type_id,
                direct=>'UNIVERSAL',
               }
              );
  $self->do_op("create_obj",{actor=>$actor, parent=>$rev},
               $set_type_id,
               $type, # as the name of the set
               $ehp->id,
               {
                is_internal=>1,
                member_type=>$type_id,
                direct=>'EMPTY',
               }
              );

	return $type_id;
}

=item B<op_add_setmember_type>

=item B<add_setmember_type>

=cut

sub add_setmember_type {
	my $self = shift;
	$self->do_op("add_setmember_type",@_);
}
sub op_add_setmember_type {
  my ($self,$actor,$rev,$type,$is_internal,$is_set) = @_;

  my $info = $self->fetch("setmember_types",
                          {condition=>"type=?",
                           params=>[$type]});
  if ($info) {
    SetException->throw("Can't add a setmember type that already exists " .
                        "($type)");
  }
  $self->dbc->dbh->do
    ("insert into setmember_types (type,is_internal,is_set,rev_id) " .
     "values (?,?,?,?)",
     {
     },$type,$is_internal,$is_set,$rev);

#  eval {$self->create_special_sets($type);};
}


sub svc_subscribe {
	my $self = shift;
	$self->do_op("svc_subscribe",@_);
}
sub op_svc_subscribe {
	my ($self,$actor,$rev,$type_id,$svc) = @_;

	if (my $info = $self->type_info($type_id,{cache=>0})) {
		$self->dbc->dbh->
			do("insert into svc_subscriptions (rev_id,type_id,svc_id) " .
				 "values(?,?,?)",
				 {
         },$rev,$info->{id},$self->svc_id($svc));
	} else {
		SvcException->
			throw("cannot subscribe non existing type to a service");
	}
}

=item B<op_add_channel>

=item B<add_channel>

=cut

sub add_channel {
	my $self = shift;
	$self->do_op("add_channel",@_);
}
sub op_add_channel {
	my ($self,$actor,$rev,$channel,$root_tag,$scratch_mpath,$keep_scratch) = @_;

	$self->dbc->dbh->
		do("insert into valid_channels " .
       "(rev_id,name,root_tag,scratch_mpath,keep_scratch) " .
       "values (?,?,?,?,?)",
			 {},$rev,$channel,$root_tag,$scratch_mpath,$keep_scratch);
}

=item B<op_create_path>

=item B<create_path>

$obj_id = $ha->op_create_path($actor,$rev,$path,$fields);
$obj_id = $ha->create_path({actor=>$actor},$path,$fields);

Create object specified by $path, recursively creating any non
existent parents.

 - $path should be a string suitable for new in Machination::HPath

 - $fields will be passed to create_obj (see below) for object data

=cut

sub create_path {
	my $self = shift;
	$self->do_op("create_path",@_);
}
sub op_create_path {
	my ($self,$actor,$rev,$path,$fields) = @_;

  my $hp = $path;
  $hp = Machination::HPath->new($self,$path)
    unless(eval {$path->isa("Machination::HPath")});
  my ($idpath,$remainder) = $hp->defined_id_path;

  # path already exists if there is no remainder
  return unless(@$remainder);

#  print Data::Dumper->Dump([$idpath, $remainder],[qw(idpath remainder)]);
  my $parent_hc = $idpath->[-1];
  if(!@$idpath && @$remainder == @{$hp->{rep}}) {
    shift @$remainder;
    # machination root not created yet
    $parent_hc = $self->do_op
      ("create_obj",{actor=>$actor,parent=>$rev},
       undef,"machination:root",undef);
    # path is only the root element, return
    return $parent_hc if(@{$hp->{rep}} == 1);
  }

  my $lastelt = pop @$remainder;
  foreach my $elt (@$remainder) {
    $parent_hc = $self->do_op
      ("create_obj",{actor=>$actor,parent=>$rev},undef,$elt,$parent_hc);
  }

  return $self->do_op
    ("create_obj",{actor=>$actor,parent=>$rev},
     $hp->type_id([$lastelt]),$hp->name([$lastelt]),$parent_hc,$fields);

}

=item B<op_create_obj>

=item B<create_obj>

$obj_id = $ha->op_create_obj($actor,$rev,$type_id,$name,$parent,$fields);
$obj_id = $ha->create_obj({actor=>$actor},$type_id,$name,$parent,$fields);

Create object of type $type_id called $name in hc $parent.

 - object owner will be set to $actor

 - setting $parent to "noparent" will result in an object not
   contained in any hc

 - $fields should be a hash reference of data fields and their values
   for that object type. e.g. for a person object one might have:

    { given_name => "Colin",
      sn => "Higgs",
      display_name => "Colin Higgs",
      uname => "chiggs" }

   Fields which an object carries, but which are not specified will be
   set to NULL if that is allowed by the database, or an error will be
   raised. Similarly, trying to set fields to values which break any
   database constraints (like foreign key references) will raise an
   error.

   Some fields cannot be set this way because they are handled by the
   service. At time of writing these are:

    name,
    parent,
    owner,
    rev_id,
    id,
    ordinal,
    ag_ordinal,

   but check the code (module Machination::HAccessor, method
   create_obj) if you need to be sure.

=cut

sub create_obj {
	my $self = shift;
	$self->do_op("create_obj",@_);
}
sub op_create_obj {
	my ($self,$actor,$rev,$type_id,$name,$parent,$fields) = @_;
	my $dbh = $self->write_dbh;
	$type_id = "machination:hc" unless defined $type_id;

  # some defaults:
  if($type_id eq "machination:hc") {
    $fields->{is_mp} = 0 unless defined $fields->{is_mp};
  }

#  print "$actor,$rev  $type_id,$name,$parent\n";
#  print Dumper($fields);

	if (! defined $parent) {
		# trying to create root
		if (defined $self->fetch_id(undef,"machination:root",undef)) {
			HierarchyException->
				throw("machination root already exists");
		}
		if ($name ne "machination:root") {
			HierarchyException->
				throw("the root must be called \"machination:root\"");
		}
		my @fields = qw(name ordinal is_mp rev_id);
		my @params = ($name,0,1,$rev);
		if (defined $actor) {
			push @fields, "owner";
			push @params, $actor;
		}
		my @q = ("?") x @fields;
		$dbh->
			do("insert into hcs (" . join(",",@fields) . ") " .
				 "values (" . join(",",@q) . ")",{},@params);
		my ($id) = $dbh->selectrow_array("select currval('hcs_id_seq')");
		return $id;
	}

	if ($parent eq "noparent") {
    if($type_id eq "machination:hc") {
      HierarchyException->
        throw("Can't create an hc with no parent.");
    }
	}
  if ($self->fetch_id($type_id,$name,$parent)) {
    my $type = $self->type_name($type_id);
    my $ppath = $self->fetch_hc_path_string($parent);
    HierarchyNameExistsException->
      throw("Cannot create $type $name in $ppath because " .
            "a $type called $name already exists there.");
  }

	# don't allow $fields to set certain columns
	delete $fields->{name};				# from args
	delete $fields->{parent};			# from args
	delete $fields->{owner};			# from args ($actor)
	delete $fields->{rev_id};			# from args (derived by do_op)
	delete $fields->{id};					# derived
	delete $fields->{ordinal};		# derived
  delete $fields->{ag_ordinal};		# derived

	my $table = "objs_$type_id";
	if ($type_id eq "machination:hc") {
		# creating an hc
		$type_id = "machination:hc";
		$table = "hcs";
		$fields->{parent} = $parent;
	}
	my $seq = $table . "_id_seq";

	my @fieldnames = qw(rev_id);
	my @values = ($rev);
	my @q = qw(?);

  # if $name is empty or undefined we should name the object after
  # its id
  my $id;
  if($name eq "" or ! defined $name) {
    my $sth = $dbh->
		prepare_cached("select nextval(?)",
									 {dbi_dummy=>"HAccessor.create_obj"});
    $sth->execute($seq);
    ($id) = $sth->fetchrow_array;
    $sth->finish;
    $name = $id;
    push @fieldnames, "id";
    push @q, "?";
    push @values, $id;
  }

  push @fieldnames, "name";
  push @q, "?";
  push @values, $name;

	if (defined $actor) {
		$fields->{owner} = $actor;
	}
	my $type_info = $self->type_info($type_id);
	foreach my $fname (@{$type_info->{'columns'}}) {
		#       next if($type eq "machination:hc" && $fname eq "ordinal");
		if (exists $fields->{$fname}) {
			push @fieldnames, $fname;
			if (ref($fields->{$fname}) eq "ARRAY") {
				my @inq;
				foreach my $val (@{$fields->{$fname}}) {
					push @inq,"?";
					push @values, $val;
				}
				push @q, "array[" . join(",",@inq) . "]";
			} else {
				push @values, $fields->{$fname};
				push @q, "?";
			}
		}
	}

	# find the right ordinal for any new hc
	if ($type_id eq "machination:hc") {
		my $ord = $self->
			fetch_new_ordinal("machination:hc",$parent);
		push @fieldnames, "ordinal";
		push @q, "?";
		push @values, $ord;
	}

  # find the right ag_ordinal for any attachable put into an agroup
  if(my $ag_type_id = $self->type_info($type_id)->{agroup}) {
#  if($fields->{agroup}) {
    my $ord=0;
    my $rows = $dbh->selectall_arrayref
      ("select max(ag_ordinal) from objs_$type_id where agroup=?",
      {},$fields->{agroup});
    if ($rows->[0]->[0] eq '') {
      $ord=0;
    } else {
      $ord=$rows->[0]->[0]+1;
    }
    push @fieldnames, "ag_ordinal";
    push @q,"?";
    push @values, $ord;
  }

	# insert the new data
  my $sql = "insert into $table (" .
    join(",",@fieldnames) . ") " .
      "values (" . join(",",@q) . ")";
#  print "create_obj: $sql (" . join(",",@values) . ")\n";
	my $sth = $dbh->
		prepare_cached($sql,
                   {dbi_dummy=>"HAccessor.create_obj"});
	$sth->execute(@values);
	$sth->finish;

	# get the id for the entry we just made
	$sth = $dbh->
		prepare_cached("select currval(?)",
									 {dbi_dummy=>"HAccessor.create_obj"});
	$sth->execute($seq);
	($id) = $sth->fetchrow_array;
	$sth->finish;

	# insert the new object into $parent unless it's an hc or $parent is
  # "noparent"
	$self->do_op("add_to_hc",{actor=>$actor,parent=>$rev},
							 $type_id,$id,$parent)
		unless($type_id eq "machination:hc" || $parent eq "noparent");

	return $id;
}

=item B<op_modify_obj>

=item B<modify_obj>

$ha->modify_obj({actor=>$actor},$type_id,$obj_id,$fields)

=cut

sub modify_obj {
	my $self = shift;
	$self->do_op("modify_obj",@_);
}
sub op_modify_obj {
	my ($self,$actor,$rev,$type_id,$obj_id,$fields) = @_;
  my $cat = "HAccessor.op_modify_object";
	$type_id = "machination:hc" unless defined $type_id;
	my $dbh = $self->write_dbh;
	if ($type_id eq "machination:hc") {
		MachinationException->
			throw("can't modify hcs with modify_obj");
  }

  # don't allow $fields to set certain columns
	delete $fields->{parent};			# use move_hc instead
	delete $fields->{rev_id};			# from args (derived by do_op)
	delete $fields->{id};					# a very bad idea!
	delete $fields->{ordinal};		# derived

  my $table = "objs_" . $type_id;
	my @updates = ("rev_id=?");
	my @values = ($rev);
  #	my @q = qw(?);
	my $type_info = $self->type_info($type_id);
  $self->log->dmsg($cat,"\n" . Dumper($type_info->{columns}),8);
	foreach my $fname (@{$type_info->{'columns'}}) {
		if (exists $fields->{$fname}) {
			my $update="$fname=";
			if (ref($fields->{$fname}) eq "ARRAY") {
				my @inq;
				foreach my $val (@{$fields->{$fname}}) {
					push @inq,"?";
					push @values, $val;
				}
				$update .= "array[" . join(",",@inq) . "]";
			} else {
				push @values, $fields->{$fname};
				$update .= "?";
			}
      push @updates, $update;
		}
	}
  push @values, $obj_id;

	# update the data
  my $sql = "update $table set " . join(",",@updates) . " where id=?";
  $self->log->dmsg($cat,"$sql",8);
  $self->log->dmsg($cat,"\n" . Dumper(\@values),8);
	my $sth = $dbh->
		prepare_cached($sql,{dbi_dummy=>"HAccessor.modify_obj"});
	$sth->execute(@values);
	$sth->finish;

}

=item B<op_delete_obj>

=item B<delete_obj>

$ha->delete_obj({actor=>$actor},$type_id,$obj_id)

=cut

sub delete_obj {
	my $self = shift;
	$self->do_op("delete_obj",@_);
}
sub op_delete_obj {
	my ($self,$actor,$rev,$type_id,$obj_id,$opts) = @_;
	$type_id = "machination:hc" unless defined $type_id;
  $opts->{'delete_obj:recursive'} = 0
    unless defined $opts->{'delete_obj:recursive'};
  $opts->{'delete_obj:delete_orphans'} = 1
    unless defined $opts->{'delete_obj:delete_orphans'};
	my $dbh = $self->write_dbh;
	my $sth;

	if ($type_id eq "machination:hc") {
    my $ch = $self->get_contents_handle
      ($obj_id,
       ["machination:hc",keys %{$self->all_types_info}],
       $opts);
    my $row = $ch->fetchrow_hashref;
    if($row) {
      unless($opts->{'delete_obj:recursive'}) {
        my $hp = Machination::HPath->new($self,$obj_id);
        HierarchyException->
          throw("Cannot delete " . $hp->to_string . " because " .
                "it contains children and recursive is not set");
      }
      do {
#        print "deleting child " . $row->{type_id} . ":" . $row->{obj_id} . "\n";
        if($row->{type_id} eq "machination:hc") {
          # a child hc, delete it
          $self->do_op("delete_obj",{actor=>$actor,parent=>$rev,},
                       $row->{type_id}, $row->{obj_id}, $opts);
        } else {
          # not an hc, remove_from_hc from this one
          $self->do_op("remove_from_hc",{actor=>$actor,parent=>$rev},
                       $row->{type_id}, $row->{obj_id}, $obj_id);
          # delete_obj if no longer contained anywhere and
          # $opts->{delete_obj:delete_orphans} is set
          if($opts->{'delete_obj:delete_orphans'} &&
             ! $self->fetch_parents($row->{type_id}, $row->{obj_id})) {
            $self->do_op("delete_obj",{actor=>$actor,parent=>$rev},
                         $row->{type_id}, $row->{obj_id});
          }
        }
        $row = $ch->fetchrow_hashref;
      } while($row);
    }
    # shouldn't have any children any more
    $sth = $dbh->prepare_cached
      ("delete from hcs where id=?",
       {dbi_dummy=>"HAccessor.delete_obj"});
    $sth->execute($obj_id);
    $sth->finish;
	} else {
		# remove from hcs
		$sth = $dbh->prepare_cached
			("delete from hccont_$type_id where obj_id=?",
			 {dbi_dummy=>"HAccessor.delete_obj"});
		$sth->execute($obj_id);
		$sth->finish;

		# remove from sets
		$sth = $dbh->prepare_cached
			("delete from setmembers_$type_id where obj_id=?",
			 {dbi_dummy=>"HAccessor.delete_obj"});
		$sth->execute($obj_id);
		$sth->finish;

    # remove members if this is a set
    if($type_id eq $self->type_id("set")) {
      my $set = Machination::HSet->new($self, $obj_id);
      if ($set->is_internal) {
        $sth = $dbh->prepare_cached
          ("delete from setmembers_" . $set->member_type . " where set_id=?",
           {dbi_dummy=>"HAccessor.delete_obj"});
        $sth->execute($obj_id);
      } else {
        $sth = $dbh->prepare_cached
          ("delete from setmembers_external where set_id=?",
           {dbi_dummy=>"HAccessor.delete_obj"});
        $sth->execute($obj_id);
      }
    }

		# detach from hcs (if attachable)
		if ($self->type_info($type_id)->{is_attachable}) {
			# Some attachable types are attachment groups. Attachment
			# groups will have instructions that should be deleted so they
			# are not orphaned.
      if($self->type_name($type_id) =~ /^agroup/) {
        my $orig_tid = $self->type_from_agroup_type($type_id);
        foreach my $mem
          (@{$self->get_ag_member_handle($type_id, $obj_id)->
           fetchall_arrayref({})}) {
          $self->do_op
            ("delete_obj", {actor=>$actor,parent=>$rev},
             $orig_tid, $mem->{id});
        }
      }
      # now detach the object
			$sth = $dbh->prepare_cached
        (
         "delete from hcatt_$type_id where obj_id=?",
         {dbi_dummy=>"HAccessor.delete_obj"}
        );
			$sth->execute($obj_id);
			$sth->finish;
		}

		# delete the object
		$sth = $dbh->prepare_cached
			("delete from objs_$type_id where id=?",
			 {
				dbi_dummy=>"HAccessor.delete_obj"});
		$sth->execute($obj_id);
		$sth->finish;
	}
}

=item B<op_add_to_hc>

=item B<add_to_hc>

=cut

sub add_to_hc {
	my $self = shift;
	$self->do_op("add_to_hc",@_);
}
sub op_add_to_hc {
	my ($self,$actor,$rev,$type_id,$obj_id,$parent) = @_;
	my $dbh = $self->dbc->dbh;
	#    $type_id = "machination:hc" unless defined $type_id;

	if (! defined $type_id || $type_id eq "machination:hc") {
		HierarchyException->
			throw("You can't use \"add_to_hc\" on an hc because this " .
						"would result in the hc having two parents - use " .
						"\"move_hc\" if you want to move an hc to a different " .
						"parent");
	}
	my $name = $self->fetch_name($type_id,$obj_id);
	if (!defined $name) {
		HierarchyException->
			throw("Cannot add object " . $self->type_name($type_id) .
						":$obj_id to " . $self->fetch_path_string($parent) .
						". The object doesn't appear to exist.");
	}
	if ($self->fetch_id($type_id,$name,$parent)) {
		my $type = $self->type_name($type_id);
		my $ppath = $self->fetch_hc_path_string($parent);
		HierarchyNameExistsException->
			throw("Cannot add $type $name to $ppath because " .
						"a $type called $name already exists there.");
	}

	my $mp = $self->fetch_mp($parent);
	my $foundin = $self->mtree_contains($mp,$type_id,$obj_id);
	if ($foundin) {
		my $type = $self->type_name($type_id);
		HierarchyMTreeException->
			throw("object \"$type\" $obj_id already exists in mtree $mp," .
						" hc $foundin\n");
	}

	my $sth = $dbh->prepare_cached
		("insert into hccont_$type_id (obj_id,hc_id,rev_id) values (?,?,?)",
		 {
			dbi_dummy=>"HAccessor.add_to_hc"});
	$sth->execute($obj_id,$parent,$rev);
	$sth->finish;
}

=item B<op_remove_from_hc>

=item B<remove_from_hc>

=cut

sub remove_from_hc {
	my $self = shift;
	$self->do_op("remove_from_hc",@_);
}
sub op_remove_from_hc {
	my ($self,$actor,$rev,$type_id,$obj_id,$parent) = @_;
	my $dbh = $self->dbc->dbh;
	if (!defined $type_id || $type_id eq "machination:hc") {
		HierarchyException->
			throw("You can't use \"remove_from_hc\" on an hc, because this " .
						"would result in the hc having no parents - use " .
						"\"move_hc\" if you want to move an hc to a different " .
						"parent");
	}
	my $sth = $dbh->prepare_cached
		("delete from hccont_$type_id where obj_id=? and hc_id=?",
		 {
			dbi_dummy=>"HAccessor.remove_from_hc"});
	$sth->execute($obj_id,$parent);
	$sth->finish;
	return;
}

=item B<op_move_hc>

=item B<move_hc>

=cut

sub move_hc {
	my $self = shift;
	$self->do_op("move_hc",@_);
}
sub op_move_hc {
	my ($self,$actor,$rev,$type_id,$obj_id,$from,$to) = @_;
	$type_id = "machination:hc" unless defined $type_id;
	my $dbh = $self->dbc->dbh;

	return if ($from == $to);

	my $name = $self->fetch_name($type_id,$obj_id);
	if ($self->fetch_id($type_id,$name,$to)) {
		my $type = $self->type_name($type_id);
		my $ppath = $self->fetch_hc_path_string($to);
		HierarchyNameExistsException->
			throw("Cannot move $type $name to $ppath because " .
						"a $type called $name already exists there.");
	}

	my $sql;
	my @params;
	if ($type_id eq "machination:hc") {
		$from = $self->fetch_parent($obj_id);
		my $from_mp = $self->fetch_mp($from);
		my $to_mp = $self->fetch_mp($to);
		HierarchyMTreeException->
			throw("Can't move hcs between merge trees yet\n")
				unless($from_mp == $to_mp);
		my $ord = $self->
			fetch_new_ordinal("machination:hc",$to);
		$sql = "update hcs set (parent,ordinal,rev_id) = (?,?,?) where id=?";
		@params = ($to,$ord,$rev,$obj_id);
		my $sth = $dbh->prepare_cached($sql, {dbi_dummy=>"HAccessor.move_hc"});
		$sth->execute(@params);
		$sth->finish;
	} else {
		my $from_mp = $self->fetch_mp($from);
		my $to_mp = $self->fetch_mp($to);
		if ($from_mp != $to_mp) {
			my $foundin = $self->
				mtree_contains($to_mp,$type_id,$obj_id);
			if ($foundin) {
				my $type = $self->type_name($type_id);
				HierarchyMTreeException->
					throw("object \"$type\" $obj_id already exists in " .
								"mtree $to_mp, hc $foundin\n");
			}
		}
		$self->do_op("remove_from_hc",{actor=>$actor,parent=>$rev},
								 $type_id,$obj_id,$from);
		$self->do_op("add_to_hc",{actor=>$actor,parent=>$rev},
								 $type_id,$obj_id,$to);
	}
}

=item B<op_attach_to_hc>

=item B<attach_to_hc>

$ha->attach_to_hc({actor=>$actor},
   $type_id,$obj_id,$hc_id,
   $mandatory,$active,
   $optional_applies_to_set_id)

=cut

sub attach_to_hc {
	my $self = shift;
	$self->do_op("attach_to_hc",@_);
}
sub op_attach_to_hc {
	my ($self,$actor,$rev,$type,$id,$hc,$mandatory,$active,$set_id) = @_;
	$type = "machination:hc" unless(defined $type);

  # this op only works if the object is attachable :-)
	unless ($self->type_info($type)->{'is_attachable'}) {
		HierarchyException->
			throw("You can't attach objects of type " .
						$self->type_name($type) . ".\n");
	}

  # atachment groups for authorisation instructions shouldn't have
  # applies to sets
  if($self->type_name($type) eq "agroup_authz_inst" && defined $set_id) {
    HierarchyException->
      throw("authorisation instructions shouldn't be attached " .
            "with applies-to sets");
  }

  # make sure the object to be attached exists
	my $row = $self->fetch("objs_$type",
												 {fields=>["id"],
													params=>[$id],
													qid=>"HAccessor.attach_to_hc"});
	unless($row) {
		HierarchyException->
			throw("Trying to attach an object that doesn't exist (" .
            $self->type_name($type) . "," . $id . ")");
	}

	my $ord = $self->fetch_new_ordinal($type,$hc);
  my $sql;
  my @params = ($id,$hc,$ord);
  if($self->type_name($type) eq "set") {
    $sql = "insert into hcatt_$type (obj_id,hc_id,ordinal" .
      ",owner,rev_id) " .
        "values (?,?,?,?,?)";
  } else {
    $sql = "insert into hcatt_$type (obj_id,hc_id,ordinal" .
      ",is_mandatory,active,applies_to_set,owner,rev_id) " .
        "values (?,?,?,?,?,?,?,?)";
    push @params, $mandatory,$active,$set_id;
  }
  push @params, $actor,$rev;
#  print "$sql (@params)";
	my $sth = $self->dbc->dbh->prepare_cached
		($sql,{dbi_dummy=>"HAccessor.attach_to_hc"});
	$sth->execute(@params);
	$sth->finish;
}

=item B<op_detach_from_hc>

=item B<detach_from_hc>

$ha->detach_from_hc({actor=>$actor},$type_id,$obj_id,$hc_id)

=cut

sub detach_from_hc {
	my $self = shift;
	$self->do_op("detach_from_hc",@_);
}
sub op_detach_from_hc {
	my ($self,$actor,$rev,$type,$id,$hc) = @_;

	unless ($self->type_info($type)->{'is_attachable'}) {
		HierarchyException->
			throw("You can't detach objects of type " .
						$self->type_name($type) . ".\n");
	}

	my $sth = $self->dbc->dbh->prepare_cached
		("delete from hcatt_$type where obj_id=? and hc_id=?",
		 {dbi_dummy=>"HAccessor.detach_from_hc"});
	$sth->execute($id,$hc);
	$sth->finish;
}

sub create_agroup {
	my $self = shift;
	$self->do_op("create_agroup",@_);
}
sub op_create_agroup {
	my ($self,$actor,$rev,$type,$name,$parent,$channel_id,$ids) = @_;
	my $gid = $self->create_obj($type,$name,$parent,
															{owner=>$actor,
															 channel_id=>$channel_id});
	$self->do_op("add_to_agroup",{actor=>$actor,parent=>$rev},
							 $type,$gid,$ids);
	return $gid;
}

sub add_to_agroup {
	my $self = shift;
	$self->do_op("add_to_agroup",@_);
}
sub op_add_to_agroup {
	my ($self,$actor,$rev,$atid,$group,$ids) = @_;
	return unless($ids);
	my $dbh = $self->dbc->dbh;

	#    my $atname = $self->type_name($atid);
	#    my $tname = $atname;
	#    $tname =~ s/^agroup_//;
	my $tid = $self->type_from_agroup_type($atid);

	my $row;
	$row = $self->fetch("objs_$atid",
											{fields=>["channel_id"],
											 params=>[$group],
											 qid=>"HAccessor.add_to_agroup"});
	my $ag_chan_id = $row->{channel_id};

	my $sth;
	my $ord=0;
	my $rows = $dbh->selectall_arrayref
		("select max(ag_ordinal) from objs_$tid where agroup=$group");
	if ($rows->[0]->[0] eq '') {
		$ord=0;
	} else {
		$ord=$rows->[0]->[0]+1;
	}
	foreach my $item (@$ids) {
		$sth = $dbh->prepare_cached
			("select agroup,channel_id from objs_$tid where id=?",
			 {dbi_dummy=>"HAccessor.add_to_agroup"});
		$sth->execute($item);
		my ($db_agroup,$channel_id) = $sth->fetchrow_array;
		$sth->finish;

		# don't do anything if $item is already in $agroup
		next if(defined $db_agroup && $group == $db_agroup);

		if ($channel_id ne $ag_chan_id) {
			AttachmentException->
				throw("HAccessor.add_to_agroup: can't add " .
							"atachable $tid:$item to group $group - the " .
							"channel ids are different " .
							"($channel_id cf. $ag_chan_id).\n");
		}
		if (defined $db_agroup && $group != $db_agroup) {
			AttachmentException->
				throw("HAccessor.add_to_agroup: can't add " .
							"attachable $tid:$item to a new group - " .
							"it belongs to group $db_agroup already.\n");
		}
		$sth = $dbh->prepare_cached
			("update objs_$tid set agroup=?,ag_ordinal=?,rev_id=? " .
			 "where id=?",
			 {
				dbi_dummy=>"HAccessor.add_to_agroup"});
		$sth->execute($group,$ord,$rev,$item);
		$ord++;
	}
}

sub remove_from_agroup {
	my $self = shift;
	$self->do_op("remove_from_agroup",@_);
}
sub remove_from_agroup {
	my ($self,$actor,$rev,$atid,$group,$ids) = @_;

	my $tid = $self->type_from_agroup_type($atid);
	if ($ids) {
		# remove specified ids
		my $sth = $self->dbc->dbh->prepare_cached
			("update objs_$tid set (agroup,rev_id) = (null,?) " .
			 "where agroup=? and id=?",
			 {
				dbi_dummy=>"HAccessor.remove_from_agroup"});
		foreach my $id (@$ids) {
			$sth->execute($rev,$group,$id);
		}
		$sth->finish;
	} else {
		# remove all ids
		my $sth = $self->dbc->dbh->prepare_cached
			("update objs_$tid set (agroup,rev_id) = (null,?) " .
			 "where agroup=?",
			 {
				dbi_dummy=>"HAccessor.remove_from_agroup"});
		$sth->execute($rev,$group);
		$sth->finish;
	}
}

sub set_special_set {
	my $self = shift;
	$self->do_op("set_special_set",@_);
}
sub op_set_special_set {
	my ($self,$actor,$rev,$id,$name) = @_;

	# see if $id is special already
	my $row = $self->fetch("special_sets",
												 {fields=>["name"],
													condition=>"set_id=?",
													params=>[$id],
													qid=>"HAccessor.set_special_set"});
	if ($row) {
		# $id is special already - change its values
		$self->dbc->dbh->do
			("update special_sets set (name,rev_id) = (?,?) " .
			 "where set_id=?",{},$name,$rev,$id);
		delete $self->{cache}->{special_sets}->{$row->{name}};
		return $id;
	}

	# $id isn't special yet
	$self->dbc->dbh->do
		("insert into special_sets (name,set_id,rev_id) values (?,?,?)",
		 {
     },$name,$id,$rev);
	return $id;
}

=item B<op_add_to_set>

=item B<add_to_set>

$ha->add_to_set($op_opts,$set,@memberlist)
$ha->op_add_to_set($actor,$rev,$set,@memberlist)

add members to set $set

$set should either be a set id (i.e. the id number of an existing set)
or a Machination::HSet object.

@memberlist should be a list of object ids of type $set->member_type
for internal sets, or string representations of the appropriate kind
for external sets.

=cut

sub add_to_set {
	my $self = shift;
	$self->do_op("add_to_set",@_);
}
sub op_add_to_set {
	my ($self,$actor,$rev,$set,@mlist) = @_;

  # $set should be a Machination::HSet or an id
  if (!ref($set)) {
    $set = Machination::HSet->new($self,$set);
  }
  my $set_type_id = $self->type_id("set");
  my $mtype = $set->member_type;
  my $id_col = "obj_id";
  my $member_table = "setmembers_$mtype";
  my $sid = $set->id;
  unless($set->is_internal) {
    $id_col = "obj_rep";
    $member_table = "setmembers_external";
  }
  my $exists_sth = $self->write_dbh->prepare_cached
    ("select $id_col as obj_id from $member_table " .
     "where $id_col=? and set_id=?",
     {
      dbi_dummy=>"HAccessor.add_to_set"});
  my $add_sth = $self->write_dbh->prepare_cached
   ("insert into $member_table " .
     "($id_col,set_id,rev_id) values (?,?,?)",
     {
      dbi_dummy=>"HAccessor.add_to_set"});
  foreach my $oid (@mlist) {
    if ($exists_sth->execute($oid,$sid) != 0) {
      # object is already a member
      $exists_sth->finish;
      next;
    }
    eval {$add_sth->execute($oid,$sid,$rev);};
    if (my $e = $@) {
      # handle no object with id $oid
      if ($e=~/ERROR:.*violates foreign key constraint "c_setmembers${mtype}_fk_objid"/) {
        $add_sth->finish;
        $self->write_dbh->rollback;
        ObjectDoesNotExistException->throw
          (error=>"could not add object type=$mtype, id=$oid to " .
           "set $sid because the object doesn't exist",
           otype=>$mtype,oid=>$oid);
      }
      # unhandled
      else {
        $add_sth->finish;
        $self->write_dbh->rollback;
        die $e;
      }
    }
  }
}

=item B<op_remove_from_set>

=item B<remove_from_set>

$ha->remove_from_set($op_opts,$set,@memberlist)
$ha->op_remove_from_set($actor,$rev,$set,@memberlist)

=cut

sub remove_from_set {
	my $self = shift;
	$self->do_op("remove_from_set",@_);
}
sub op_remove_from_set {
  my $self = shift;
  #  print "args: " . Dumper(\@_);
	my ($actor,$rev,$set,@mlist) = @_;

  # $set should be a Machination::HSet or an id
  #  print Dumper($set) . "\n";
  if (!ref($set)) {
    $set = Machination::HSet->new($self,$set);
  }
  my $set_type_id = $self->type_id("set");
  my $mtype = $set->member_type;
  my $id_col = "obj_id";
  my $member_table = "setmembers_$mtype";
  my $sid = $set->id;
  unless($set->is_internal) {
    $id_col = "obj_rep";
    $member_table = "setmembers_external";
  }
  my $remove_sth = $self->write_dbh->prepare_cached
   ("delete from $member_table where $id_col=? and set_id=?",
     {dbi_dummy=>"HAccessor.remove_from_set"});
  foreach my $oid (@mlist) {
    eval {$remove_sth->execute($oid,$sid);};
    if (my $e = $@) {
      # unhandled
      $remove_sth->finish;
      $self->write_dbh->rollback;
      die $e;
    }
  }
}

=item B<op_add_valid_condition_op>

=item B<add_valid_condition_op>

$ha->add_valid_condition_op($op)

=cut

sub add_valid_condition_op {
	my $self = shift;
	$self->do_op("add_valid_condition_op",@_);
}
sub op_add_valid_condition_op {
	my ($self,$actor,$rev,$op) = @_;
  $self->write_dbh->do
    ("insert into valid_condition_ops (op,rev_id) values (?,?)",{},$op,$rev);
}

=item B<op_add_set_direct_condition>

=item B<add_set_direct_condition>

$ha->add_set_direct_condition($set,$col,$op,$val)

=cut

sub add_set_direct_condition {
	my $self = shift;
	$self->do_op("add_set_direct_condition",@_);
}
sub op_add_set_direct_condition {
	my ($self,$actor,$rev,$set,$col,$op,$val) = @_;

  my $set_obj = Machination::HSet->new($self,$set);
  my $search_table;
  if ($set_obj->is_internal) {
    $search_table = "objs_" . $set_obj->member_type;
  } else {
    $search_table = "setmembers_external";
  }
  if (! exists $self->dbc->dbconfig->table_info($search_table)->{atts}->{$col}) {
    die "can only set a condition on a column that exists in the object table";
  }

  my $sth = $self->write_dbh->prepare_cached
    ("insert into direct_conditions (set_id,col,op,val,rev_id) " .
     "values (?,?,?,?,?)");
  $sth->execute($set,$col,$op,$val,$rev);
}

=item B<op_remove_set_direct_condition>

=item B<add_remove_direct_condition>

$ha->add_remove_direct_condition($condition_id)

=cut

sub remove_set_direct_condition {
	my $self = shift;
	$self->do_op("remove_set_direct_condition",@_);
}
sub op_remove_set_direct_condition {
	my ($self,$actor,$rev,$id) = @_;

  $self->write_dbh->do
    ("delete from direct_conditions where id=?",{},$id);
}

sub add_valid_os {
  my $self = shift;
  $self->do_op("add_valid_os",@_);
}
sub op_add_valid_os {
  my ($self,$actor,$rev,$name,$majv,$minv,$bit) = @_;
  $self->write_dbh->do
    ("insert into valid_oses " .
     "(name,major_version,minor_version,bitness,rev_id) " .
     "values (?,?,?,?,?)",{},$name,$majv,$minv,$bit,$rev);
}
sub delete_valid_os {
  my $self = shift;
  $self->do_op("delete_valid_os",@_);
}
sub op_delete_valid_os {
  my ($self,$actor,$rev,$id) = @_;
  $self->write_dbh->do
    ("delete from valid_oses where id=?",{},$id);
}

sub add_valid_action_op {
  my $self = shift;
  $self->do_op("add_valid_action_op",@_);
}
sub op_add_valid_action_op {
  my ($self,$actor,$rev,$op,$complete,$overlay,$arg_meaning,$desc) = @_;
  $self->write_dbh->do
    ("insert into valid_action_ops " .
     "(op,complete,overlay,arg_meaning,description,rev_id) " .
     "values (?,?,?,?,?,?)",{},
     $op,$complete,$overlay,$arg_meaning,$desc,$rev);
}
sub delete_valid_action_op {
  my $self = shift;
  $self->do_op("delete_valid_action_op",@_);
}
sub op_delete_valid_action_op {
  my ($self,$actor,$rev,$op) = @_;
  $self->write_dbh->do
    ("delete from action_ops where op=?",{},$op);
}

sub add_valid_assertion_op {
  my $self = shift;
  $self->do_op("add_valid_assertion_op",@_);
}
sub op_add_valid_assertion_op {
  my ($self,$actor,$rev,$op,$arg_meaning) = @_;
  $self->write_dbh->do
    ("insert into valid_assertion_ops (op,arg_meaning,rev_id) values (?,?,?)",
     {},$op,$arg_meaning,$rev);
}
sub delete_valid_assertion_op {
  my $self = shift;
  $self->do_op("delete_valid_assertion_op",@_);
}
sub op_delete_valid_assertion_op {
  my ($self,$actor,$rev,$op) = @_;
  $self->write_dbh->do
    ("delete from assertion_ops where op=?",{},$op);
}

sub create_action {
  my $self = shift;
  $self->do_op("create_action",@_);
}
sub op_create_action {
  my ($self,$actor,$rev,$op,@args) = @_;
  $self->write_dbh->do
    ("insert into assertion_actions (op,rev_id) values (?,?)",{},$op,$rev);
  my $row = $self->write_dbh->selectrow_hashref
    ("select currval('assertion_actions_id_seq')");
  unless($row) {
    die "could not find id of action created";
  }
  my $action_id = $row->{currval};
  while (my $name = shift @args) {
    my $value = shift @args;
    $self->write_dbh->do
      ("insert into action_args (name,value,action_id,rev_id) " .
       "values (?,?,?,?)",{},$name,$value,$action_id,$rev);
  }
  return $action_id;
}

sub modify_action {
  my $self = shift;
  $self->do_op("modify_action",@_);
}
sub op_modify_action {
  my ($self,$actor,$rev,$id,$op,@args) = @_;
  $self->write_dbh->do
    ("update assertion_actions set (op,rev_id) = (?,?) where id=?",{},
     $op,$rev,$id);
  $self->write_dbh->do
    ("delete from action_args where action_id=?",{},$id);
  while (my $name = shift @args) {
    my $value = shift @args;
    $self->write_dbh->do
      ("insert into action_args (name,value,action_id,rev_id) " .
       "values (?,?,?,?)",{},$name,$value,$id,$rev);
  }
}

sub delete_action {
  my $self = shift;
  $self->do_op("delete_action",@_);
}
sub op_delete_action {
  my ($self,$actor,$rev,$id) = @_;
  my $sql;
  my @vars;

  $self->write_dbh->do
    ("delete from action_args where action_id=?",{},$id);
  $self->write_dbh->do
    ("delete from assertion_actions where id=?",{},$id);
}

sub tag_action {
  my $self = shift;
  $self->do_op("tag_action",@_);
}
sub op_tag_action {
  my ($self,$actor,$rev,$id,$ref,$description) = @_;
  $self->write_dbh->do
    ("update assertion_actions set (ref,description,rev_id) = (?,?,?) " .
     "where id=?",{},$ref,$description,$rev,$id);
}

sub create_assertion {
  my $self = shift;
  $self->do_op("create_assertion",@_);
}
sub op_create_assertion {
  my ($self,$actor,$rev,$op,$mpath,$arg,$action_id) = @_;
}

#sub add_valid_lib_assertion_op {
#  my $self = shift;
#  $self->do_op("add_valid_lib_assertion_op",@_);
#}
#sub op_add_valid_lib_assertion_op {
#  my ($self,$actor,$rev,$op) = @_;
#  $self->write_dbh->do
#    ("insert into lib_assertion_ops (op,rev_id) values (?,?)",{},$op,$rev);
#}
#sub delete_valid_lib_assertion_op {
#  my $self = shift;
#  $self->do_op("delete_valid_lib_assertion_op",@_);
#}
#sub op_delete_valid_lib_assertion_op {
#  my ($self,$actor,$rev,$op) = @_;
#  $self->write_dbh->do
#    ("delete from lib_assertion_ops where op=?",{},$op);
#}


=item B<op_assertion_group_from_xml>

=item B<assertion_group_from_xml>

$ha->assertion_group_from_xml($op_opts, $hcid, $name, $channel_id,
                              $xml, $opts)
$ha->op_assertion_group_from_xml($actor,$rev, $hcid, $name, $channel_id,
                                 $xml, $opts)

=cut
sub assertion_group_from_xml {
  my $self = shift;
  $self->do_op('assertion_group_from_xml', @_);
}
sub op_assertion_group_from_xml {
  my $self = shift;
  my ($actor, $rev, $hcid, $name, $channel_id, $xml, $opts) = @_;

  $opts->{'x2a:replace'} = 0 unless exists $opts->{'x2a:replace'};

  # Convert XML to a list of assertions before we start mucking with
  # the hierarchy.
  my $a2s = Machination::XML2Assertions->new(doc=>$xml);
  my $alist = $a2s->to_assertions;

  # Check for the an existing agroup
  my $ag_tid = $self->type_id("agroup_assertion");
  my $ag_id = $self->fetch_id($ag_tid,$name,$hcid);
  if ($ag_id) {
    unless($opts->{'x2a:replace'}) {
      HierarchyNameExistsException->
        throw("Not replacing agroup_assertion:$name in " .
              Machination::HPath->new($self, $hcid)->to_string);
    }
    # need to delete the agroup and the member assertions
    $self->do_op('delete_obj', {actor=>$actor, parent=>$rev},
                 $ag_tid, $ag_id);
  }

  # now create an agroup and the associated assertions
  $ag_id = $self->do_op('create_obj', {actor=>$actor, parent=>$rev},
                        $ag_tid, $name, $hcid, {channel_id=>$channel_id});
  my $i = 0;
  for my $a (@$alist) {
    $a->{agroup} = $ag_id;
    $self->do_op('create_obj', {actor=>$actor, parent=>$rev},
                $self->type_id('assertion'), "${name}__${i}__", $hcid, $a);
    $i++;
  }
}



=back

=cut

package Machination::HFetcher;

=head2 Machination::HFetcher

=head3 Methods:

=over

=item * $hf = Machination::HFetcher->new($dbh,$log,$table,$opts)

Create a new Machination::HFetcher

=cut

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $dbh = shift;
  my $log = shift;
  my $tables = shift;
  my $opts = shift;
  my $self = {};
  bless $self,$class;

  $self->dbh($dbh);
  $self->_tables($tables);
  $self->opts($opts);
  $self->log($log);

  return $self;
}

sub _tables {
  my $self = shift;
  if (@_) {
    $self->{_tables} = shift;
    delete $self->{tables};
  }
  return $self->{_tables};
}

sub tables {
  my $self = shift;
  unless (defined $self->{tables}) {
    my $arg = $self->{_tables};
    my @tlist;
    my %taliases;
    if (ref $arg) {
      my @tbls;
      foreach my $t (@$arg) {
        if (ref $t) {
          if (defined $self->opts->{revision}) {
            my $name = "zzh_" . $t->[0];
            my $alias = $t->[1];
            push @tbls,  "$name as $alias";
            push @tlist, $name;
            $taliases{$name} = $alias;
          } else {
            my $name = $t->[0];
            my $alias = $t->[1];
            push @tbls, "$name as $alias";
            push @tlist, $name;
            $taliases{$name}=$alias;
          }
        } else {
          if (defined $self->opts->{revision}) {
            my $name = "zzh_$t";
            push @tbls, $name;
            push @tlist, $name;
            $taliases{$name}=$name;
          } else {
            push @tbls, $t;
            push @tlist, $t;
            $taliases{$t}=$t;
          }
        }
      }
      $self->{tables} = join(",",@tbls);
    } else {
      if (defined $self->opts->{revision}) {
        my $name = "zzh_$arg";
        $self->{tables} = $name;
        push @tlist, $name;
        $taliases{$name}=$name;
      } else {
        $self->{tables} = $arg;
        push @tlist, $arg;
        $taliases{$arg}=$arg;
      }
    }
    $self->{tlist} = \@tlist;
    $self->{taliases} = \%taliases;
  }
  return $self->{tables};
}

=item * $hf->opts($opts)

Get/set options. $opts is hashref with the following fields:

    type: type of query, one of:
      unique (default): query will produce only one result.
      multi: query may produce more than one result.


=cut

sub opts {
	my $self = shift;
	if (@_) {
		my $opts = shift;

		# defaults
		$opts->{type} = "unique" unless(defined $opts->{type});
		$opts->{fields} = ["*"] unless(defined $opts->{fields});
		$opts->{condition} = "id=?" unless(defined $opts->{condition});
		$opts->{keys} = ["id"] unless(defined $opts->{keys});

		#       if(defined $opts->{revision}) {
		#           my $table = $self->table;
		#           $table = "zzh_$table" unless($table=~/^zzh_/);
		#           $self->table($table);
		#           $opts->{limit} = 1 unless(defined $opts->{limit});
		#       }

		delete $self->{query};

		$self->{opts} = $opts;
	}
	return $self->{opts};
}

sub dbh {
	my $self = shift;
	$self->{dbh} = shift if(@_);
	return $self->{dbh};
}

sub log {
	my $self = shift;
	$self->{log} = shift if(@_);
	return $self->{log};
}

sub sth {
	my $self = shift;
	$self->{sth} = shift if(@_);
	return $self->{sth};
}

sub _extra_fields {
	my $self = shift;
	$self->{_extra_fields} = shift if(@_);
	return $self->{_extra_fields};
}

sub _params {
	my $self = shift;
	$self->{_params} = shift if(@_);
	return $self->{_params};
}

sub prepare {
	my $self = shift;
	$self->sth($self->dbh->prepare($self->query));
}

sub prepare_cached {
	my $self = shift;
	$self->sth($self->dbh->
						 prepare_cached($self->query,
														{
														 dbi_dummy=>$self->opts->{qid}}));
}

sub execute {
	my $self = shift;
	$self->sth->execute(@{$self->_params});
}

sub finish {
	my $self = shift;
	$self->sth->finish;
	$self->{sth} = undef;
}

#sub fetchrow_array {
#    my $self = shift;
#    return $self->sth->fetchrow_array;
#}

sub fetchrow {
	my $self = shift;
	my $row = $self->sth->fetchrow_hashref;
	return unless defined $row;

	if (defined $self->opts->{revision}) {
		while ($row->{history_deletes}) {
			$row = $self->sth->fetchrow_hashref;
			return unless defined $row;
		}
	}

#  if ($opts->{add_info}) {
#    foreach (@{$opts->{add_info}}) {
#      $row->{$_->[0]} = $_->[1];
#    }
#  }

	#    if(defined $opts->{transform}) {
	#       foreach my $tr (@{$opts->{transform}}) {
	#           $row->{$tr->[1]} = $row->{$tr->[0]};
	#           delete $row->{$tr->[0]};
	#       }
	#    }

	delete @$row{@{$self->_extra_fields}};
	return $row;
}

sub fetch_some {
	my $self = shift;
	my ($limit,$opts) = @_;
	my @rows;

	my $i = 0;
	while ((($i++) < $limit) && (my $row = $self->fetchrow($opts))) {
		push @rows, $row;
	}
	return @rows;
}

sub fetch_all {
	my $self = shift;
	my $opts = shift;
	my @rows;
	while (my $row = $self->fetchrow($opts)) {
		push @rows, $row;
	}
	return @rows;
}

sub query {
	my $self = shift;
	return $self->{query} if(exists $self->{query});
  my $cat = "HAccessor.query";

	my $q;
	my $opts = $self->opts;
	my @params;
	@params = @{$opts->{params}} if(defined $opts->{params});
	my @fields;
	my @field_texts;
	if (defined $opts->{fields}) {
		foreach my $fe (@{$opts->{fields}}) {
			if (ref $fe) {
				push @fields, $fe->[0];
				push @field_texts, $fe->[0] . " as " . $fe->[1];
			} else {
				push @fields, $fe;
				push @field_texts, $fe;
			}
		}
	}
	my %fields;
	@fields{@fields} = (undef);

	my @order;
	my %order;
	if (defined $opts->{order}) {
		foreach my $o (@{$opts->{order}}) {
			$order{$o->[0]} = undef;
			my $ostr = $o->[0];
			$ostr .= " " . $o->[1] if(defined $o->[1]);
			push @order, $ostr;
		}
	}

	$self->tables;

	my @extra_fields;
	my $added;
	if (defined $opts->{revision} &&
			! exists $fields{"*"}) {
		foreach my $t (keys %{$self->{taliases}}) {
			my $a = $self->{taliases}->{$t};
			unless (exists $fields{"$a.history_deletes"} ||
							exists $fields{"history_deletes"}) {
				push @extra_fields, "$a.history_deletes";
				$added = 1;
			}
		}
	}
	push @fields, @extra_fields;
	push @field_texts, @extra_fields;
	$self->_extra_fields(\@extra_fields);
	push @{$self->_extra_fields}, "history_deletes" if($added);

	my $q;
	my $condition="";
	my $limit="";
	if ($opts->{type} eq "unique") {
		$q = "select " . join(",",@field_texts) . " from " . $self->tables . " ";
		$condition = $opts->{condition};
		my @ccs;
		push @ccs, $condition if($condition ne "");
		if (defined $opts->{revision}) {
			#           my @order;
			foreach my $t (@{$self->{tlist}}) {
				my $a = $self->{taliases}->{$t};
				push @ccs, "$a.rev_id<=?";
				push @order, "$a.history_id desc";
				push @params, $opts->{revision};
			}
			$condition = join(" and ", @ccs);
			$limit = "limit 1";
		}
	} elsif ($opts->{type} eq "multi") {
		if (defined $opts->{revision}) {
			$q = "select distinct on (" . join(",",@{$opts->{keys}}) . ")";
			$q .= " " . join(",",@fields) . " from " . $self->tables . " ";
			$condition = $opts->{condition};
			my @ccs;
			push @ccs, $condition if($condition ne "");
			#           my @order;
			foreach my $t (@{$self->{tlist}}) {
				my $a = $self->{taliases}->{$t};
				push @ccs, "$a.rev_id<=?";
				push @order, "$a.history_id desc";
				push @params, $opts->{revision};
			}
			foreach my $key (@{$opts->{keys}}) {
				push @order, $key unless(exists $order{$key});
			}
			$condition = join(" and ", @ccs);
			#           $condition .= " order by " . join(",",@{$opts->{keys}},@order);
		} else {
			$q = "select " . join(",",@fields) .
				" from " . $self->tables . " ";
			$condition = $opts->{condition};
		}
	}
	$self->_params(\@params);
	$q .= "where $condition" if($condition ne "");
	$q .= " order by " . join(",",@order) if(@order);
	$q .= " $limit" if($limit ne "");
	$self->{query} = $q;

	$self->log->dmsg($cat,$self->{query} . " (" . join(",",@params) . ")",4);
	return $self->{query};
}

=back

=cut

1;
