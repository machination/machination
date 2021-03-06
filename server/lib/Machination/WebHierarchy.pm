package Machination::WebHierarchy;

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

use strict;
no strict "refs";
use warnings;

=head1 Machination::WebHierarchy

=cut
BEGIN {
  use threads;
}

use Apache::DBI;
use APR::Table;
use Apache2::RequestRec ();
use Apache2::RequestIO ();
use Apache2::Const -compile => qw(:common);
#use Apache2::Directive ();
#use Apache2::Module ();
use Apache2::MPM;
use DBI;
use Data::Dumper;
$Data::Dumper::Indent=1;
use XML::LibXML;
use File::Path qw(make_path);
use URI;

use Machination::HAccessor;
use Machination::XMLDumper;
use Machination::Exceptions;
use Machination::ConfigFile;

use Apache::DataIterator::Reader;
use Apache::DataIterator::Writer;
use Machination::WebIterator::HCContents;

use Thread::Queue;

Exception::Class::Base->Trace(1);

my $machination_config_default = "/etc/machination/config.xml";

my %calls =
  (
   ########################################
   # Getting information
   ########################################
   Help => undef,
   CertInfo => undef,
   OsId => undef,
   ServiceInfo => undef,
   ServiceConfig => undef,

   # types
   TypeInfo => undef,
   AllTypesInfo => undef,
   TypeId => undef,

   # authorisation
   ActionAllowed => undef,

   # hcs
   Exists => undef,
   ListContents => undef,
   GetListContentsIterator => undef,
   IteratorNext => undef,
   IteratorFinish => undef,
   ListAttachments => undef,

   # agroups
   AgroupMembers => undef,

   # sets
   SetMembers => undef,

   # objects
   FetchObject => undef,
   ModifyObject => undef,
   IdPair => undef,
   EntityId => undef,

   # channels
   ProfChannel => undef,
   HierarchyChannel => undef,
   ChannelInfo => undef,

   # assertions/instructions/profiles
   GetAssertionList => undef,
   GetLibraryItem => undef,


   ########################################
   # signing up...
   ########################################
   SignIdentityCert => undef,
#   RevokeIdentity => undef,
#   RemoveIdentity => undef,

   ########################################
   # Manipulating the hierarchy and objects
   ########################################
   Create => undef,
   AddValidOs => undef,

    Link => undef,
    Unlink => undef,
    LinkCount => undef,
    ContentsCount => undef,
    Fetch => undef,
    AddToAgroup => undef,
    Attach => undef,
    ListAttachments => undef,
    AttachmentsCount => undef,
    FetchAttachmentInfo => undef,
    CreateLibItem => undef,
    GetSpecialSet => undef,
    );
our $log;
our $ha;
our $debug;
our $hierarchy_channel;
our $shared_memory_dir;

my $xmld = Machination::XMLDumper->new;
my $orig_rem_user;

=head3 Functions:

=over

=cut

=item * B<handler>

The handler is called by mod_perl whenever WebHierarchy is invoked.

=cut

sub handler {
  my $r = shift;
  my $cat = "WebHierarchy.handler";
  #    my $dbh = DBI->connect("dbi:Pg:database=$dbname;" .
  #			"host=$dbhost",$dbuser,$dbpass,
  #			{RaiseError=>1});

  tie *STDOUT, $r;

  # find config file
  $r->content_type("text/plain");

  my $machination_config = $r->dir_config('MachinationConfig');
  $machination_config = $machination_config_default
    unless(defined $machination_config);

  my $conf = Machination::ConfigFile->new($machination_config);
  $debug = $conf->root->
    findvalue('//subconfig[@xml:id="subconfig.haccess"]/@debug');

  if(! defined $ha) {
    eval {
      $ha = Machination::HAccessor->new($conf);
    };
    if($@) {
      if($@ =~ /authentication failed/) {
        error("Authentication to database failed.");
      } else {
        error($@);
      }
      return Apache2::Const::OK;
    }
    $log = $ha->log;
    $log->dmsg($cat,"handler called",1);
    $shared_memory_dir = $ha->conf->get_dir("dir.SHM");
    -d $shared_memory_dir || make_path($shared_memory_dir);
  }

  # sort out authentication and set up remote user
  my $uri = $ha->conf->get_value("subconfig.haccess", "\@URI");
  my $uri_base = URI->new($uri)->path;
  my $ruri = substr($r->uri,length($uri_base));
  $ruri =~ s/^\///;
  my ($authen_type, $rem_user) = split(/\//, $ruri);
  # For $authen_type 'debug' the remote user is in the uri so we are done.
  if($authen_type ne "debug") {
    if($authen_type eq "public") {
      $rem_user = "person:__MACHINATION_PUBLIC__";
    } else {
      # For all other authentication types Apache should tell us.
      $rem_user = $r->user unless $authen_type eq "debug";
    }
  }
  my $haccess_conf_node = ($ha->conf->doc->findnodes(
    '//subconfig[@id="subconfig.haccess"]')
  )[0];
  my @authen_nodes = $haccess_conf_node->findnodes(
    "authentication/type[\@id='$authen_type']"
  );
  unless(@authen_nodes) {
    error("Unsupported authentication type '$authen_type'");
    return Apache2::Const::OK;
  }
  $log->dmsg($cat, "original remote user: $rem_user", 4);
  $orig_rem_user = $rem_user;

  my $entity_pattern =
    '
    (?(?=:)) # does entity have a : in it?
      # yes: interpret as type:name
      ^(?<type>.*?):(?<name>.*)$ |
      # no: interpret as just name
      ^(?<name>.*)$
    ';
  $entity_pattern = $authen_nodes[0]->getAttribute("entityPattern")
    if($authen_nodes[0]->hasAttribute("entityPattern"));
  # set type and name from named groups
  $rem_user =~ /$entity_pattern/x;
  my $obj_type = $+{type};
  my $obj_name = $+{name};
  # get defaults if name or type not set
  $obj_type = $authen_nodes[0]->getAttribute("defaultObjType")
    if ($authen_nodes[0]->hasAttribute("defaultObjType")  &&
        (!defined $obj_type || $obj_type eq ""));
  $obj_name = $authen_nodes[0]->getAttribute("defaultName")
    if ($authen_nodes[0]->hasAttribute("defaultName")  &&
        (!defined $obj_name || $obj_name eq ""));
  # check that $obj_type can use this auth method
  unless($authen_nodes[0]->findnodes("objType\[\@id='$obj_type'\]")) {
    error("Object type '$obj_type' may not use authentication type '$authen_type'");
    return Apache2::Const::OK;
  }
  $rem_user = $obj_type . ":" . $obj_name;

  unless($r->method eq "POST") {
    error("HTTP method must be POST");
    return Apache2::Const::OK;
  }
  unless($r->headers_in->{'Content-length'} > 0) {
    error("Got a content-length of " .
          $r->headers_in->{'Content-length'} .
          " it should be positive");
    return Apache2::Const::OK;
  }
  my $inputText;
  $r->read($inputText,$r->headers_in->{'Content-length'});
  $log->dmsg($cat,"raw request:\n" . $inputText,4);

  my $req;
  eval {
    $req = XML::LibXML->new->parse_string($inputText)->documentElement;
  };
  if($@) {
    error("could not parse input " . $@);
    return Apache2::Const::OK;
  }

  my $call = $req->getAttribute("call");

  unless(exists $calls{$call}) {
    error("no such call \"$call\"");
    return Apache2::Const::OK;
  }
  $call = "call_" . $call;

  my @approval_nodes = $req->findnodes("approval");
  my @approval;
  foreach (@approval_nodes) {
    push @approval, $_->textContent;
    $_->parentNode->removeChild($_);
  }

  my $args;
  eval {
    $args = $xmld->to_perl($req);
  };
  if($@) {
    error($@);
    return Apache2::Const::OK;
  }

#    if($call eq "call_CreateLibItem") {
#	my $err = $req->sprint;
#	$err .= "\n" . Dumper($args);
#	error($err);
#	return Apache2::Const::OK;
#    }

#    print Dumper($args);

  my $call_args = $xmld->to_perl($req);
  $log->dmsg($cat,"calling:\n$call($rem_user,[" .
             join(",",@approval) . "],\n" . Dumper($call_args) . ")",4);
  my $ret;
  eval {
    $ret = &$call($rem_user,\@approval,@$call_args);
  };
  if($@) {
    &error("your call didn't work because:\n$@");
    return Apache2::Const::OK;
  }
  $log->dmsg($cat, "call worked - answer:\n" . Dumper($ret), 4);
  $log->dmsg($cat, $xmld->to_xml($ret)->toString , 9);
#  my $rep = &perl_to_xrep($ret);

  print $xmld->to_xml($ret)->toString . "\n";

  return Apache2::Const::OK;
}

=item B<hierarchy_channel>

=cut

sub hierarchy_channel {
  unless(defined $hierarchy_channel) {
    $hierarchy_channel = $ha->channel_id("machination:hierarchy");
  }
  return $hierarchy_channel;
}

=item B<HierarchyChannel>

=cut
#hp
sub call_HierarchyChannel {
  return hierarchy_channel();
}

=item B<CertInfo>

=cut
#hp
sub call_CertInfo {
  my $info = {};
  $info->{serverdn_string_rfc} = $ha->ssl_server_dn;
  $info->{serverdn_list} = $ha->ssl_split_dn($info->{serverdn_string_rfc});
  $info->{serverdn_string_slash} =
    $ha->ssl_dnlist_to_string($info->{serverdn_list}, "slash");


  my @dnbase = @{$info->{serverdn_list}};
  shift @dnbase;
  $info->{basedn_list} = \@dnbase;
  $info->{basedn_string_slash} =
    $ha->ssl_dnlist_to_string($info->{basedn_list}, "slash");
  $info->{basedn_string_rfc} =
    $ha->ssl_dnlist_to_string($info->{basedn_list});
#    join(",", map {$_->[0] . "=" . $_->[1]} @dnbase);

  return $info;
}

=item B<OsId>

=cut
#hp
sub call_OsId {
  shift;
  shift;
  return $ha->os_id(@_)
}

=item B<AddValidOs>

=cut

sub call_AddValidOs {
  my $caller = shift;
  my $approval = shift;

  my $hp = Machination::HPath->
    new(ha=>$ha,from=>"/system/special/authz/valid_oses");

  my $req = {channel_id=>hierarchy_channel(),
             op=>"create",
             mpath=>"/contents",
             owner=>$caller,
             approval=>$approval};

  AuthzDeniedException->
    throw("could not get create permission for " . $hp->to_string)
      unless $ha->action_allowed($req,$hp);

  $ha->add_valid_os({actor=>$caller}, @_);
}

=item B<ServiceInfo>

Return old style service config element.

=cut
#hp
sub call_ServiceInfo {
  my $haccess_node = ($ha->conf->doc->findnodes(
    '//subconfig[@id="subconfig.haccess"]')
  )[0];

  # Start with a brand new service element
  my $service_elt = XML::LibXML::Element->new('service');

  # Add some stuff directle from server config
  $service_elt->setAttribute('id', $haccess_node->getAttribute('serviceId'));
  my $helt = XML::LibXML::Element->new('hierarchy');
  $helt->setAttribute('id', $haccess_node->getAttribute('URI'));
  $service_elt->appendChild($helt);

  # Transform new style authentication type definitions to old client side ones
  foreach my $aelt ($haccess_node->findnodes("authentication/objType")) {
#    my $newa = $aelt->cloneNode(1);
#    $newa->setNodeName('authentication');
    my $newa = XML::LibXML::Element->new('authentication');
    my $obj_type = $aelt->getAttribute('id');
    my $auth_type = $aelt->getAttribute('defaultAuth');
    $newa->setAttribute('id', $obj_type);
    $newa->setAttribute('type', $auth_type);
    if($aelt->getAttribute('defaultAuth') eq 'debug') {
      my @nodes = $haccess_node->
        findnodes("authentication/type\[\@id='debug']/objType\[\@id='$obj_type'\]");
      if(@nodes) {
        $newa->setAttribute('username', $nodes[0]->getAttribute('defaultName'));
      }
    }
    $service_elt->appendChild($newa);
  }
  return $service_elt->toString(1);
}

=item B<ServiceConfig>

Return service info in the form of the server's config file. Not all
information is transferred.

=cut
#hp
sub call_ServiceConfig {
  my $han = ($ha->conf->doc->findnodes(
    '//subconfig[@id="subconfig.haccess"]')
  )[0];
  my $ret = XML::LibXML::Element->new('subconfig');
  my $auth = $ret->appendChild(XML::LibXML::Element->new("authentication"));
  $ret->setAttribute('xml:id', "subconfig.haccess");
  $ret->setAttribute('serviceId', $han->getAttribute('serviceId'));
  $ret->setAttribute('URI', $han->getAttribute('URI'));
  foreach my $elt ($han->findnodes('authentication/objType')) {
    $auth->appendChild($elt->cloneNode(1));
  }
  foreach my $elt ($han->findnodes('authentication/type')) {
    $auth->appendChild($elt->cloneNode(1));
  }
  foreach my $elt ($han->findnodes('authentication/certSign')) {
    $auth->appendChild($elt->cloneNode(1));
  }
  return $ret->toString(1);
}


=item B<Help>

=cut
#hp
sub call_Help {
  my $user = shift;
  my $info;

  $info .= "Machination WebHierarchy\n";
  $info .= "Hello $user (originally $orig_rem_user)\n\n";
  $info .= "MPM: " . Apache2::MPM->show() . "\n";
  $info .= "threaded: " . Apache2::MPM->is_threaded() . "\n";

#  my $t = threads->create(\&splat);
  return $info;
}

sub splat {
  return 1;
}

=item B<TypeInfo>

TypeInfo($type)

=cut
#hp
sub call_TypeInfo {
  my ($owner,$approval,$type) = @_;

  return $ha->type_info($type);
}

=item B<AllTypesInfo>

AllTypesInfo($opts)

=cut
#hp
sub call_AllTypesInfo {
  my ($owner,$approval,$opts) = @_;

  return $ha->all_types_info($opts);
}

=item B<TypeId>

TypeId($type_name)

=cut
#hp
sub call_TypeId {
  my ($owner,$approval,$type) = @_;

  return $ha->type_id($type);
}

=item B<ActionAllowed>

ActionAllowed($req, $hc_id)

$req =
 {
  channel_id=>$channel_id
  op=>$op,
  mpath=>$mpath,
  arg=>$arg,
  owner=>$authen_string,
  approval=>[$authen_string,$authen_string,...],
 }

=cut
#hp
sub call_ActionAllowed {
  my ($owner, $approval, $req, $path) = @_;
  my $hp = Machination::HPath->new(ha=>$ha, from=>$path);

  return $ha->action_allowed($req, $hp);
}

=item B<Exists>

Exists($path)

Permission required:
- readtext on $path or listchildren on parent.

=cut
#
sub call_Exists {
  my ($owner,$approval,$path) = @_;

  my $hp;
  $hp = Machination::HPath->new(ha=>$ha,from=>$path);
  my $mpath = "/contents/" . $hp->type;
  $mpath .= "[" . $hp->id . "]" if $hp->exists;

  my $req = {channel_id=>hierarchy_channel(),
             op=>"listchildren",
             mpath=>$mpath,
             owner=>$owner,
             approval=>$approval};
  return $hp->id if $ha->action_allowed($req,$hp->parent);
  $req->{op} = "readtext";
  return $hp->id
    if($hp->exists and $ha->action_allowed($req,$hp->parent->id));

  AuthzDeniedException->
    throw("could not get read or exists permission for $path");
}

=item B<ListContents($hcpath,$opts)>

List the contents of $hcpath.

 $hcpath = path string denoting an hc
 $opts = hash of options {
    types => [types,to,list], # (all types if this is not specified)
    fetch_names => 0 or 1 (whether to fetch object names as well)
    max_objects => max number of objects to return
 }

returns:

{
  type1 => [ $item1, $item2, ... ],
  type2 => [ ... ],
}

items are of the form:

{
    id => $id, name => $name
}

you always get the ids, names are optional.

=cut
#
sub call_ListContents {
  my ($owner,$approval,$path,$opts) = @_;

  $opts->{max_objects} = undef unless exists $opts->{max_objects};
  $ha->log->dmsg("WebHierarchy.ListContents",
                 "owner: $owner, approval: $approval, hc: $path, " .
                 "opts: " . Data::Dumper->Dump([$opts],[qw(opts)]),9);

  my $hp = Machination::HPath->new(ha=>$ha,from=>$path);
  die "$path is not an hc, it is a " . $hp->type
    unless($hp->type eq "machination:hc");

  $ha->log->dmsg("WebHierarchy.ListContents","hp: " . $hp->id,9);
  my $req = {channel_id=>hierarchy_channel(),
             op=>"listchildren",
             mpath=>"/contents",
             owner=>$owner,
             approval=>$approval};
#  $ha->log->dmsg("WebHierarchy.ListContents", Dumper($hp->{rep}),9);

  die "could not get listchildren permission for " . $req->{mpath}
    unless($ha->action_allowed($req,$hp));

  die "hc $path does not exist" unless($hp->exists);

  my $pass_opts = {};
  $pass_opts->{fields} = ["name"] if($opts->{fetch_names});

  my $types = $opts->{types};
  $types = ['machination:hc', keys %{$ha->all_types_info}]
    unless defined($types);
  my $contents = $ha->get_contents_handle($hp->id, $types)->
    fetchall_arrayref({}, $opts->{max_objects});


  return $contents;
}

=item B<GetListContentsIterator>

$fetcher_info = GetListContentsIterator($hcpath,$opts)

See B<GetIteratorInfo> for $fetcher_info format

=cut

sub call_GetListContentsIterator {
  my ($owner,$approval,$hc,$types,$opts) = @_;

  my $hp = Machination::HPath->new(ha=>$ha,from=>$hc);
  die "$hc is not an hc, it is a " . $hp->type
    unless($hp->type eq "machination:hc");
  die "hc $hc does not exist" unless($hp->exists);

  my $req = {channel_id=>hierarchy_channel(),
             op=>"listchildren",
             mpath=>"/contents",
             owner=>$owner,
             approval=>$approval};
  die "could not get listchildren permission for " . $req->{mpath}
    unless($ha->action_allowed($req,$hp->id));

  my $q = Thread::Queue->new();
  $ha->log->dmsg("WebHierarchy.GetListContentsIterator",
                 "starting _writer_thread. hc: " . $hp->id .
                 " types: $types",
                9);
  my $thr = threads->create(\&_writer_thread,$q,$ha->conf->file,
                           $hp->id,$types,$owner);
  $ha->log->dmsg("WebHierarchy.GetListContentsIterator",
                 "thread created",
                 9);
  my $handle = $q->dequeue;
  $ha->log->dmsg("WebHierarchy.GetListContentsIterator",
                 "sending back $handle",
                 9);
  $thr->detach;
  return $handle;
}

sub _writer_thread {
  my $q = shift;
  my $config = shift;
  my $hc = shift;
  my $types = shift;
  my $owner = shift;

  my $ha = Machination::HAccessor->new($config);
  $ha->log->dmsg("WebHierarchy._writer_thread",
                "hc: $hc, types: " . Dumper($types),9);
  my $hcit = Machination::WebIterator::HCContents->
    new($ha,$hc);
  $hcit->types($types);
  my $itw = Apache::DataIterator::Writer->
    new($hcit,dir=>$shared_memory_dir,template=>"it-XXXXXXXX");
  $itw->store_info("server","owner",$owner);
  $itw->nfetch(2);
  $ha->log->dmsg("WebHierarchy._writer_thread",
                 "sending back " . $itw->id,
                 9);
  $q->enqueue($itw->id);
  $itw->start;
}

=item B<ListAttachments>

$attachments = ListAttachments($hc, $opts)

=cut
#hp
sub call_ListAttachments {
  my ($owner,$approval,$hc,$opts) = @_;

  $opts->{max_objects} = undef unless exists $opts->{max_objects};
  $opts->{get_members} = 1 unless exists $opts->{get_members};
  $ha->log->dmsg("WebHierarchy.ListAttachments",
                 "owner: $owner, approval: $approval, hc: $hc, " .
                 "opts: " . Data::Dumper->Dump([$opts],[qw(opts)]),9);

  my $hp = Machination::HPath->new(ha=>$ha,from=>$hc);
  die "$hc is not an hc, it is a " . $hp->type
    unless($hp->type eq "machination:hc");

  $ha->log->dmsg("WebHierarchy.ListAttachments","hp: " . $hp->id,9);
  my $req = {channel_id=>hierarchy_channel(),
             op=>"listchildren",
             mpath=>"/attachments",
             owner=>$owner,
             approval=>$approval};
#  $ha->log->dmsg("WebHierarchy.ListContents", Dumper($hp->{rep}),9);

  die "could not get listchildren permission for " . $req->{mpath}
    unless($ha->action_allowed($req,$hp));

  die "hc $hc does not exist" unless($hp->exists);

  my $types = $opts->{types};
  unless (defined $types) {
    $types = [];
    my $type_info = $ha->all_types_info;
    foreach my $tid (keys %$type_info) {
      push @$types, $tid if($type_info->{$tid}->{is_attachable});
    }
  }
  my @channels = keys %{$ha->channels_info(undef)};
  my $direct = $ha->get_attached_handle($hp->id, \@channels, $types)->
    fetchall_arrayref({}, $opts->{max_objects});

  my @attachments;
  foreach my $att (@$direct) {
    push @attachments, $att;
    if($ha->is_agroup($att->{type_id}) && $opts->{get_members}) {
      my $members = $ha->
        get_ag_member_handle($att->{type_id}, $att->{obj_id})->
          fetchall_arrayref({});
      push @attachments, @$members;
    }
  }

  return \@attachments;
}

=item B<AgroupMembers>

$members = AgroupMembers($path_or_spec, $opts)

If $path_or_spec starts with '/' then it is interpreted as a path to
an agroup object (/path/to/agroup_something:blah). Otherwise it is
interpreted as a constructor string for a MooseHObject
(e.g. 'type_name:id').

=cut
#hp
sub call_AgroupMembers {
  my ($owner,$approval,$path_or_spec,$opts) = @_;
  $opts->{max_objects} = undef unless exists $opts->{max_objects};

  my $type_id;
  my $id;
  my $parent_hpath;
  if($path_or_spec =~ /^\//) {
    # Starts with '/', assume path.
    my $hp = Machination::HPath->new(ha=>$ha,from=>$path_or_spec);
    if($hp->exists) {
      $type_id = $hp->type_id;
      $id = $hp->id;
      $parent_hpath = $hp->parent;
    }
  } else {
    # Assume object spec.
    my $o = Machination::MooseHObject->new(ha=>$ha, from=>$path_or_spec);
    if($o->exists) {
      $type_id = $o->type_id;
      $id = $o->id;
      $parent_hpath = Machination::HPath->
        new(ha=>$ha, from=>'/system/special/authz/objects');
    } else {
      die "object " . $o->type_id . "," . $o->id . " doesn't exist";
    }
  }

  my $type_name = $ha->type_name($type_id);
  my $req = {channel_id=>hierarchy_channel(),
             op=>"listchildren",
             mpath=>"/contents/$type_name\[$id\]/members",
             owner=>$owner,
             approval=>$approval};

  die "could not get listchildren permission for " . $req->{mpath}
    unless($ha->action_allowed($req,$parent_hpath->id));

  return $ha->
    get_ag_member_handle($type_id, $id)->
      fetchall_arrayref({}, $opts->{max_objects});
}

=item B<SetMembers>

$members = SetMembers($path_or_spec, $opts)

If $path_or_spec starts with '/' then it is interpreted as a path to
an set object (/path/to/set:blah). Otherwise it is interpreted as a
constructor string for a MooseHObject (e.g. 'set:id').

=cut

sub call_SetMembers {
  my ($owner,$approval,$path_or_spec,$opts) = @_;
  $opts->{max_objects} = undef unless exists $opts->{max_objects};

#  my $type_id;
  my $id;
  my $parent_hpath;
  if($path_or_spec =~ /^\//) {
    # Starts with '/', assume path.
    my $hp = Machination::HPath->new(ha=>$ha,from=>$path_or_spec);
    die "$path_or_spec must be a set. This looks like a " . $hp->type
      unless($hp->type eq "set");
    if($hp->exists) {
#      $type_id = $hp->type_id;
      $id = $hp->id;
      $parent_hpath = $hp->parent;
    }
  } else {
    # Assume object spec.
    my $o = Machination::MooseHObject->new(ha=>$ha, from=>$path_or_spec);
    my $type_name = $ha->type_name($o->type_id);
    die "$path_or_spec must be a set. This looks like a $type_name"
      unless($type_name eq "set");
    if($o->exists) {
#      $type_id = $o->type_id;
      $id = $o->id;
      $parent_hpath = Machination::HPath->
        new(ha=>$ha, from=>'/system/special/authz/objects');
    } else {
      die "object " . $o->type_id . "," . $o->id . " doesn't exist";
    }
  }

#  my $type_name = $ha->type_name($type_id);
  my $req = {channel_id=>hierarchy_channel(),
             op=>"listchildren",
             mpath=>"/contents/set\[$id\]/members",
             owner=>$owner,
             approval=>$approval};

  die "could not get listchildren permission for " . $req->{mpath}
    unless($ha->action_allowed($req,$parent_hpath->id));

  my $set = Machination::HSet->new($ha, $id);

  my @members;
  if($opts->{max_objects}) {
    my $fetcher = $set->fetcher("all");
    $fetcher->prepare_cached;
    $fetcher->execute;
    @members = $fetcher->fetch_some($opts->{max_objects})
  } else {
    @members = $set->fetch_members("all");
  }
  return \@members;

}

=item B<FetchObject>

$members = FetchObject($path_or_spec, $opts)

If $path_or_spec starts with '/' then it is interpreted as a path to
an object in the hierarchy (/path/to/type_name:blah). Otherwise it is
interpreted as a constructor string for a MooseHObject
(e.g. 'type_name:id').

=cut

sub call_FetchObject {
  my ($owner,$approval,$path_or_spec,$opts) = @_;

  my $type_id;
  my $id;
  my $parent_hpath;
  my $obj;
  if($path_or_spec =~ /^\//) {
    # Starts with '/', assume path.
    my $hp = Machination::HPath->new(ha=>$ha,from=>$path_or_spec);
    if($hp->exists) {
      $type_id = $hp->type_id;
      $id = $hp->id;
      $parent_hpath = $hp->parent;
    }
    $obj = Machination::MooseHObject->
      new(ha=>$ha, id=>$hp->id, type_id=>$hp->type_id)
  } else {
    # Assume object spec.
    my $o = Machination::MooseHObject->new(ha=>$ha, from=>$path_or_spec);
    if($o->exists) {
      $type_id = $o->type_id;
      $id = $o->id;
      $parent_hpath = Machination::HPath->
        new(ha=>$ha, from=>'/system/special/authz/objects');
    } else {
      die "object " . $o->type_id . "," . $o->id . " doesn't exist";
    }
    $obj = $o;
  }

  my $type_name = $ha->type_name($type_id);
  my $req = {channel_id=>hierarchy_channel(),
             op=>"readtext",
             mpath=>"/contents/$type_name\[$id\]",
             owner=>$owner,
             approval=>$approval};

  die "could not get readtext permission for " . $req->{mpath}
    unless($ha->action_allowed($req,$parent_hpath->id));

  return $obj->fetch_data;
}

=item B<ModifyObject>

$members = ModifyObject($path_or_spec, $newfields, $opts)

If $path_or_spec starts with '/' then it is interpreted as a path to
an object in the hierarchy (/path/to/type_name:blah). Otherwise it is
interpreted as a constructor string for a MooseHObject
(e.g. 'type_name:id').

=cut

sub call_ModifyObject {
  my ($owner,$approval,$path_or_spec, $newfields, $opts) = @_;

  my $type_id;
  my $id;
  my $parent_hpath;
  my $obj;
  if($path_or_spec =~ /^\//) {
    # Starts with '/', assume path.
    my $hp = Machination::HPath->new(ha=>$ha,from=>$path_or_spec);
    if($hp->exists) {
      $type_id = $hp->type_id;
      $id = $hp->id;
      $parent_hpath = $hp->parent;
    }
    $obj = Machination::MooseHObject->
      new(ha=>$ha, id=>$hp->id, type_id=>$hp->type_id)
  } else {
    # Assume object spec.
    my $o = Machination::MooseHObject->new(ha=>$ha, from=>$path_or_spec);
    if($o->exists) {
      $type_id = $o->type_id;
      $id = $o->id;
      $parent_hpath = Machination::HPath->
        new(ha=>$ha, from=>'/system/special/authz/objects');
    } else {
      die "object " . $o->type_id . "," . $o->id . " doesn't exist";
    }
    $obj = $o;
  }

  my $type_name = $ha->type_name($type_id);
  my $allowed = 0;

  # First try to get settext permission for the whole object
  my $req = {channel_id=>hierarchy_channel(),
             op=>"settext",
             mpath=>"/contents/$type_name\[$id\]",
             owner=>$owner,
             approval=>$approval};

  # If that didn't work try to get permission for the fields individually
  if(!$ha->action_allowed($req,$parent_hpath->id)) {
    foreach my $field (keys %$newfields) {
      my $req = {channel_id=>hierarchy_channel(),
                 op=>"settext",
                 mpath=>"/contents/$type_name\[$id\]/field[$field]",
                 owner=>$owner,
                 approval=>$approval};
      die "could not get settext permission for " . $req->{mpath}
        unless($ha->action_allowed($req,$parent_hpath->id));
    }
  }

  # now we're allowed to try to change the object
  $ha->modify_obj({actor=>$owner}, $obj->type_id, $obj->id, $newfields);
}


=item B<IteratorNext>

$items = IteratorNext($handle)

=cut

sub call_IteratorNext {
  my ($owner,$approval,$handle) = @_;

  my $it_owner = Apache::DataIterator::Reader::retrieve_info
    ($handle,"server","owner");
  die "$owner not the owner of iterator $handle"
    unless($owner eq $it_owner);

  return Apache::DataIterator::Reader::next($handle);
}


=item B<IteratorFinish>

IteratorFinish($handle);

=cut

sub call_IteratorFinish {
  my ($owner,$approval,$handle) = @_;

  my $it_owner = Apache::DataIterator::Reader::retrieve_info
    ($handle,"server","owner");
  die "$owner not the owner of iterator $handle"
    unless($owner eq $it_owner);

  return Apache::DataIterator::Reader::finish($handle);
}


=item B<IteratorInfo>

$it_info = IteratorInfo($handle)

$it_info = {
  handle=>$handle,
  expires=>$time,
  time_to_live=>$time_left,
}

=cut


=item B<ExtendIteratorLife>

$success = ExtendIteratorLife($handle)

=cut


=item B<GetAssertionList>

$list = GetAssertionList($type_name, $obj_name, $channel)

=cut
#hp
sub call_GetAssertionList {
  my ($owner,$approval,$type_name, $obj_name) = @_;
  my $info;

  my $obj_type_id = $ha->type_id($type_name);
  my $obj_id = $ha->entity_id($obj_type_id, $obj_name);
  my $channel = call_ProfChannel($owner, $approval, $type_name);

  my $authorised = 0;
  my ($own_type_id,$own_id) = $ha->authen_str_to_object($owner);
  $authorised = 1 if($own_type_id == $obj_type_id &&
                     $own_id == $obj_id);

  die "$owner is not allowed to view the assertion list for $type_name:$obj_name"
    unless $authorised;

  my @parents = $ha->fetch_parents($obj_type_id,$obj_id);
  my @lineages;
  foreach my $p (@parents) {
    my @l = $ha->fetch_lineage($p);
    push @lineages, \@l;
  }
  @lineages = sort lineage_sort @lineages;

  # build a list of unique in-order hcs
  my %seen = ();
  my @hc_info;
  my @hc_ids;
  my @hc_path;
  my @hc_mp_path;
  my @hc_mps;
  foreach my $l (@lineages) {
    foreach my $hc (@$l) {
      unless ($seen{$hc->{id}}++)
        {
          push @hc_info, $hc;
          push @hc_ids, $hc->{id};
#          my $lin = $ha->fetch_lineage($hc->{id});
          my $hc_obj = Machination::MooseHC->new(ha=>$ha, id=>$hc->{id});
          my $hp = $hc_obj->path;
          my $id_path = $hc_obj->id_path;
          push @hc_path, $id_path;
          if($hc->{is_mp}) {
            push @hc_mp_path, $id_path;
            push @hc_mps, $hc->{id};
          }
        }
    }
  }

  my $stelt = XML::LibXML::Element->new('status');
  my $welt = $stelt->appendChild(XML::LibXML::Element->new('worker'));
  $welt->setAttribute('id', '__machination__');
  my $svselt = $welt->appendChild(XML::LibXML::Element->new('services'));
  $svselt->appendChild
    (XML::LibXML->load_xml(string=>call_ServiceInfo())->documentElement);
  my $a2s = Machination::XML2Assertions->new(doc=>$stelt);
  my $alist = $a2s->to_assertions;

  my $root_hc = $ha->fetch_root_id();
  foreach my $ass (@$alist) {
    $ass->{ass_arg} = undef unless(exists $ass->{ass_arg});
    $ass->{hc_id} = $root_hc;
  }

  $info->{hcs} = \@hc_path;
#  $info->{attachments} =
#    $ha->fetch_attachment_list
  my $sth = $ha->get_attachments_handle
    ($channel,\@hc_ids,"assertion",
     {obj_fields=>["mpath","ass_op","ass_arg","action_op","action_arg"]});
  $info->{attachments} = [@$alist, @{$sth->fetchall_arrayref({})}];
#  $info->{mps} = $ha->mps(\@hc_ids);
  $info->{mps} = \@hc_mp_path;
  $sth = $ha->get_attachments_handle
    ($channel,\@hc_mps,"mpolicy",
     {obj_fields=>["mpath","policy_direction"]});
  my $policies = $sth->fetchall_arrayref({});
  $info->{mpolicy_attachments} = {};
  foreach my $pol (@$policies) {
    $info->{mpolicy_attachments}->{$pol->{hc_id}} = [] unless
      exists($info->{mpolicy_attachments}->{$pol->{hc_id}});
    push @{$info->{mpolicy_attachments}->{$pol->{hc_id}}}, $pol;
  }

  return $info;
}

# sorting function used by GetAssertionList
sub lineage_sort {
  my $i = 0;
  while(1) {
    return 0 if(!exists $a->[$i] && !exists $b->[$i]);
    return 1 if(!exists $b->[$i]);
    return -1 if(!exists $a->[$i]);
    return $a->[$i]->{ordinal} <=> $b->[$i]->{ordinal}
      if($a->[$i]->{ordinal} <=> $b->[$i]->{ordinal});
    $i++;
  }
}

=item B<GetLibraryItem>

$list = GetLibraryItem($assertion,$lib_path)

=cut

sub call_GetLibraryItem {
  my ($owner,$approval,$ass,$lpath) = @_;
  my $hp;
  foreach my $l (@$lpath) {
    my $lhp = Machination::HPath($ha, $l);
    # recursively search for a libitem providing $mpath $op $arg
    $hp = $ha->get_library_item($ass, $lhp->id);
    if(defined $hp) {
      last;
    }
  }
  return {found=>undef, assertions=>[]} unless defined $hp;

  # now fetch the assertions from the item
  my @ass = $ha->fetch_from_agroup($hp->type_id, $hp->id);
  return {found=>$hp->to_string(), assertions=>\@ass};
}

=item B<SignIdentityCert>

$signed_cert = SignIdentityCert($obj_type,$obj_name,$csr,$force)

permissions required:

- settext /system/special/authz/objects
  /contents/$obj_type[$obj_id]/field[reset_trust]

=cut

sub call_SignIdentityCert {
  my ($caller,$approval,$csr,$force) = @_;

  my $cn = $ha->ssl_split_dn($ha->ssl_dn_from_string($csr,"req"))->[0]->[1];
  my ($obj_type, $obj_name) = $ha->ssl_entity_from_cn($cn);
  my $obj_id = $ha->entity_id($ha->type_id($obj_type), $obj_name);
  my $mpath_obj_id="";
  if($obj_id) {
    $mpath_obj_id = "[$obj_id]";
  }
  my $req = {
         channel_id => hierarchy_channel(),
         op=>'settext',
         mpath => "/contents/${obj_type}${mpath_obj_id}/fields[reset_trust]",
         owner => $caller,
         approval => $approval
        };
  AuthzDeniedException->
    throw("Could not get permission to reset trust for $obj_type $obj_name")
      unless $ha->action_allowed
        (
         $req,
         Machination::HPath->new(ha=>$ha,
                                 from=>'/system/special/authz/objects')->id
        );

  die "Object ${obj_type}:${obj_name} does not exist" unless($obj_id);

  return $ha->sign_csr($csr, $force);
}

=item B<RevokeIdentity>

$success = RevokeIdentity($id)

=cut

sub call_RevokeIdentity {
  my ($owner,$approval,$id) = @_;

}

=item B<FetchObject>

=cut

=item B<IdPair>

=cut

sub call_IdPair {
  my ($owner, $approval, $path) = @_;

  my $hp = Machination::HPath->new(ha=>$ha, from=>$path);
  my $mpath = "/contents/" . $hp->type;
  $mpath .= "[" . $hp->id . "]" if $hp->exists;
  my ($own_type_id,$own_id) = $ha->authen_str_to_object($owner);

  my $req = {channel_id=>hierarchy_channel(),
             op=>"exists",
             mpath=>$mpath,
             owner=>$owner,
             approval=>$approval};
  if(($own_type_id == $hp->type_id and $own_id == $hp->id) or
     $ha->action_allowed($req, $hp->id)) {
    return {type_id=>$hp->type_id, id=>$hp->id};
  }
  AuthzDeniedException->
    throw("could not get exists permission for $path");
}

=item B<EntityId>

=cut

sub call_EntityId {
  my ($owner, $approval, $type_name, $name) = @_;

  my $id = $ha->entity_id($ha->type_id($type_name), $name);

  my $req = {channel_id=>hierarchy_channel(),
             op=>"exists",
             mpath=>"/contents/$type_name\[$id\]",
             owner=>$owner,
             approval=>$approval};
  AuthzDeniedException->
    throw("could not get exists permission for $type_name:$id in " .
          "/system/special/authz/objects")
      unless $ha->action_allowed
        ($req, Machination::HPath->new(ha=>$ha, from=>"/system/special/authz/objects")->id);

  return $id
}

=item B<ProfChannel>

=cut

sub call_ProfChannel {
  my ($caller, $approval, $type) = @_;

  my $type_id = $type;
  $type_id = $ha->type_id($type) unless($type =~ /^\d+$/);

  return $ha->profchannel($type_id);
}

=item B<ChannelInfo>

=cut

sub call_ChannelInfo {
  my ($caller, $approval, $cid) = @_;

  return $ha->channel_info($cid);
}


=item B<call_Create($caller, $approval ,$path,$fields)>

=cut

sub call_Create {
  my ($caller, $approval, $path, $fields) = @_;

  my $hp;
  $hp = Machination::HPath->new(ha=>$ha,from=>$path);
  $hp->populate_ids;
  my $type = $hp->type;
  $type = "machination:hc" unless defined $type;
  my $mpath = "/contents/$type/fields[name]/" . $hp->name;

  my $req = {channel_id=>hierarchy_channel(),
             op=>"create",
             mpath=>$mpath,
             owner=>$caller,
             approval=>$approval};
  AuthzDeniedException->
    throw("Could not get create permission for $mpath on " . $hp->parent->to_string)
      unless $ha->action_allowed($req,$hp->parent->id);

  return $ha->create_obj({actor=>$caller}, $hp->type_id, $hp->name, $hp->parent->id, $fields);
}

=item * call_LinkCount($ent,$item)

$item = path_string or type:id

=cut

sub call_LinkCount {
  my ($owner,$approval,$item) = @_;

  my ($type,$id);
  if($item =~ /^\//) {
    my $hp = Machination::HPath->new(ha=>$ha,from=>$item);
    $type = $hp->type;
    $id = $hp->id;
  } else {
    ($type,$id) = split(/:/,$item);
  }
  $log->dmsg("WebHierarchy.LinkCount","$type,$id",8);

  return $ha->hobject->contained_count($type,$id);
}

=item * call_Link($ent,$item_path,$hc)

$item_path = path string
$hc = path string or id

=cut

sub call_Link {
  my ($ent,$item,$hc) = @_;

  my $item_hp = Machination::HPath->new(ha=>$ha,from=>$item);

  my $hc_id;
  if($hc=~/^\//) {
    my $hp = Machination::HPath->new(ha=>$ha,from=>$hc);
    $hc_id = $hp->id;
  } else {
    $hc_id = $hc;
  }

  # need read_elt permission on the item from the point of view
  # of the $item_path's parent
  authz(
        {
         svc_id=>"machination:hierarchy",
         to=>{type=>$item_hp->type,
              id=>$item_hp->id},
         owner=>$ent,
         op=>"read_elt",
         elt_path=>"/",
        },
        $item_hp->parent->id
       );
  # need add_elt permission to the path where the link is to be added
  authz(
        {
         svc_id=>"machination:hierarchy",
         to=>{type=>"machination:hc",
              id=>$hc_id},
         owner=>$ent,
         op=>"add_elt",
         elt_path=>"/hc/contents",
        },
        $hc_id
       );

  $ha->hcontainer->add_object($item_hp->type,$item_hp->id,$hc_id);

  return $ha->hobject->contained_count($item_hp->type,$item_hp->id);
}

=item * call_Unlink($ent,$item_path)

$item_path = path string

=cut

sub call_Unlink {
  my ($ent,$item) = @_;

  my $item_hp = Machination::HPath->new(ha=>$ha,from=>$item);

  # need del_elt permission to the path where the link is to be removed
  authz(
        {
         svc_id=>"machination:hierarchy",
         to=>{type=>"machination:hc",
              id=>$item_hp->parent->id},
         owner=>$ent,
         op=>"del_elt",
         elt_path=>"/hc/contents",
        },
        $item_hp->parent->id,
       );

    $ha->hcontainer->
	remove_object($item_hp->type,$item_hp->id,$item_hp->parent);

    return $ha->hobject->contained_count($item_hp->type,$item_hp->id);
}


=item * call_ContentsCount($ent,$hc,$opts)

=cut

sub call_ContentsCount {
    my ($ent,$hc,$opts) = @_;

    if($hc =~ /^\//) {
	# $hc is a path
	my $hp = Machination::HPath->new($ha,$hc);
	$hc = $hp->id;
    }

    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",id=>$hc},
	    owner=>$ent,
	    op=>"read_elt",
	    elt_path=>"/hc/contents",
	},
	$hc
	);


    my $types = $opts->{types};
    unless($types) {
	my @types = $ha->object_types;
	$types = \@types;
    }

    my $contents = {total=>0,types=>{}};
    foreach my $type (@$types) {
	my $num = $ha->hcontainer->list_contents_of_type($type,$hc);
	$contents->{types}->{$type} = $num;
	$contents->{total}+=$num;
    }

    return $contents;
}

=item * call_Fetch($ent,$path)

=cut

sub call_Fetch {
    my ($ent,$path) = @_;

    my $hp = Machination::HPath->new($ha,$path);

    my $elt_path;
    my $att_hc;
    if($hp->type eq "machination:hc") {
	$elt_path = "/hc/fields";
	$att_hc = $hp->id;
    } else {
	$elt_path = "/" . $hp->type;
	$att_hc = $hp->parent;
    }
    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>$hp->type,id=>$hp->id},
	    owner=>$ent,
	    op=>"read_elt",
	    elt_path=>$elt_path,
	},
	$att_hc
	);

    my $obj = $ha->fetch_object($hp->type,$hp->id);
    my $ret = {};
    $ret->{type} = $obj->type;
    $ret->{id} = $obj->id;
    $ret->{name} = $obj->name;
    $ret->{fields} = $obj->fields;

    return $ret;
}

=item * call_AddToAgroup($ent,$group,$item[,$item,...])

$group = path_string of agroup
$item = path_string of item(s) to add

=cut

sub call_AddToAgroup {
    my ($ent,$group,@items) = @_;

    my $ag_hp = Machination::HPath->new($ha,$group);

    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>$ag_hp->type,id=>$ag_hp->id},
	    owner=>$ent,
	    op=>"add_elt",
	    elt_path=>"/agroup/members",
	},
	$ag_hp->parent
	);

    my @oids;
    my $atype = $ag_hp->type;
    $atype=~s/^agroup_//;
    foreach my $item (@items) {
	my $hp = Machination::HPath->new($ha,$item);
	MachinationException->
	    throw("$item isn't the same type ($atype) as $group")
	    unless($hp->type eq $atype);
	push @oids,$hp->id;
    }
    $ha->add_to_agroup($atype,$ag_hp->id,\@oids);
}

=item * call_Attach($ent,$attachable,$hc,$mandatory,$set)

$attachable = path_string or type:id of an attachable type
$hc = path string or id of hc to attach to

=cut

sub call_Attach {
    my ($ent,$attachable,$hc,$mandatory,$set) = @_;

    my ($atype,$aid);
    if($attachable =~ /^\//) {
	my $hp = Machination::HPath->new($ha,$attachable);
	$atype = $hp->type;
	$aid = $hp->id;
    } else {
	($atype,$aid) = split(/:/,$attachable);
    }
    if($hc =~ /^\//) {
	# $hc is a path
	my $hp = Machination::HPath->new($ha,$hc);
	$hc = $hp->id;
    }
    if($set =~ /^\//) {
	# $set is a path
	my $hp = Machination::HPath->new($ha,$set);
	$set = $hp->id;
    }

    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",id=>$hc},
	    owner=>$ent,
	    op=>"add_elt",
	    elt_path=>"/hc/attachments/",
	},
	$hc
	);

    $ha->hobject->attach_to_hc($hc,$ent,$set,$mandatory,$atype,$aid);

    return 1;
}

=item * call_ListAttachments($ent,$hc,$opts)

=cut

sub call_ListAttachmentsOld {
    my ($ent,$hc,$opts) = @_;

    if($hc =~ /^\//) {
	# $hc is a path
	my $hp = Machination::HPath->new($ha,$hc);
	$hc = $hp->id;
    }

    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",id=>$hc},
	    owner=>$ent,
	    op=>"read_elt",
	    elt_path=>"/hc/attachments",
	},
	$hc
	);

    my @types = @{$opts->{types}} if(defined $opts->{types});
    my @svcs = @{$opts->{svcs}} if(defined $opts->{svcs});

#    my @info;
    my $contents = {};
    unless(@types) {
	foreach my $type ($ha->object_types) {
#	    push @info, "checking type $type";
	    push @types, $type if($ha->type_info($type)->{is_attachable});
	}
    }
    unless(@svcs) {
#	push @info, "finding allowed services";
	@svcs = $ha->allowed_services;
    }

#    my $contents = $ha->hcontainer->list_att($opts,$hc);
    foreach my $svc (@svcs) {
#	$contents->{svc} = undef;
	foreach my $type (@types) {
	    my $list = $ha->hcontainer->fetch_ordered_att($type,$svc,$hc);
	    $contents->{$svc}->{$type} = $list if(@$list);
	}
    }

    return $contents;
}

=item * call_AttachmentsCount($ent,$hc,$opts)

=cut

sub call_AttachmentsCount {
    my ($ent,$hc,$opts) = @_;

    if($hc =~ /^\//) {
	# $hc is a path
	my $hp = Machination::HPath->new($ha,$hc);
	$hc = $hp->id;
    }

    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",id=>$hc},
	    owner=>$ent,
	    op=>"read_elt",
	    elt_path=>"/hc/attachments",
	},
	$hc
	);

    my @types = @{$opts->{types}} if(defined $opts->{types});
    my @svcs = @{$opts->{svcs}} if(defined $opts->{svcs});

#    my @info;
    my $count = {total=>0,counts=>{}};
    unless(@types) {
	foreach my $type ($ha->object_types) {
#	    push @info, "checking type $type";
	    push @types, $type if($ha->type_info($type)->{is_attachable});
	}
    }
    unless(@svcs) {
#	push @info, "finding allowed services";
	@svcs = $ha->allowed_services;
    }

#    my $contents = $ha->hcontainer->list_att($opts,$hc);
    foreach my $svc (@svcs) {
#	$contents->{svc} = undef;
	foreach my $type (@types) {
	    my $list = $ha->hcontainer->fetch_ordered_att($type,$svc,$hc);
	    $count->{counts}->{$svc}->{$type} = @$list;
	    $count->{total} += @$list;
#	    $contents->{$svc}->{$type} = $list if(@$list);
	}
    }

    return $count;
}

=item * call_FetchAttachmentInfo($ent,$otype,$oid,$hc)

=cut

sub call_FetchAttachmentInfo {
    my ($ent,$otype,$oid,$hc) = @_;

    if($hc =~ /^\//) {
	# $hc is a path
	my $hp = Machination::HPath->new($ha,$hc);
	$hc = $hp->id;
    }

    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",id=>$hc},
	    owner=>$ent,
	    op=>"read_elt",
	    elt_path=>"/hc/attachments",
	},
	$hc
	);

    return $ha->fetch_attachment_info($otype,$oid,$hc);
}

=item * call_CreateLibItem($ent,$name,$parent,$svc,$ihc,$xml)

 $ent = creating entity
 $name = the name of the library item
 $parent = path to parent hc (string path, hc id or HPath)
 $svc = svc_id
 $ihc = hc to store conf_insts (string path, hc id or HPath)
 $xml = xml in the form required for
    $ha->create_ci_agroup_from_xml

=cut

sub call_CreateLibItem {
    my ($ent,$name,$parent,$svc,$ihc,$xml) = @_;

    my $parent_id;
    if(ref $parent) {
	# $parent is a Machination::HPath
	$parent_id = $parent->id;
    } elsif($parent=~/^\//) {
	# $parent is a string path
	$parent_id = Machination::HPath->new($ha,$parent)->id;
    } else {
	# $parent should be an id
	$parent_id = $parent;
    }
    my $ihc_id;
    if(ref $ihc) {
	# $ihc is a Machination::HPath
	$ihc_id = $ihc->id;
    } elsif($ihc=~/^\//) {
	# $ihc is a string path
	$ihc_id = Machination::HPath->new($ha,$ihc)->id;
    } else {
	# $ihc should be an id
	$ihc_id = $ihc;
    }

    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",id=>$parent_id},
	    owner=>$ent,
	    op=>"add_elt",
	    elt_path=>"/hc/contents",
	},
	$parent_id
	);
    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",id=>$ihc_id},
	    owner=>$ent,
	    op=>"add_elt",
	    elt_path=>"/hc/contents",
	},
	$ihc_id
	);

    # should be authorised now

    $ha->create_ci_agroup_from_xml
	($name,$ent,$svc,$parent_id,$ihc_id,$xml);
}

=item * call_GetSpecialSet($ent,$name)

=cut

sub call_GetSpecialSet {
    my ($ent,$name) = @_;

    return $ha->get_special_set($name);
}

=item * error($r)

=cut

sub error {
    my ($error,$opts) = @_;

    $log->emsg("WebHierarchy.error",$error,1)
      if defined $log;
    my $e = XML::LibXML::Element->new('error');
    my $d = XML::LibXML::Element->new('debug');
    my $m = XML::LibXML::Element->new('message');
    $d->appendTextChild("file", __FILE__);
    $m->appendText($error);
    $e->appendChild($d) if($debug);
    $e->appendChild($m);
    $log->dmsg("WebHierarchy.error", "sending back error:\n" . $e->toString,4)
      if defined $log;
    print $e->toString . "\n";

}

=item * authz()

=cut

sub authz {
  my ($owner,$approval,$channel,$op,$mpath,$arg,$hc_id) = @_;

#  my ($rel,$allow)  = $ha->action_allowed($req,$hc);

#  die "no authorisation instruction relevant"
#    unless($rel);
#  die "permission denied for request " . Dumper($req)
#    unless($allow);
}

=back

=cut

1;
