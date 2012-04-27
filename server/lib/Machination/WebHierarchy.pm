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

use Machination::HAccessor;
use Machination::HashXML;
use Machination::Exceptions;

use Apache::DataIterator::Reader;
use Apache::DataIterator::Writer;
use Machination::WebIterator::HCContents;

use threads;
use Thread::Queue;

Exception::Class::Base->Trace(1);

my $machination_config_default = "/etc/machination/config.xml";

my %calls =
  (
   ########################################
   # Getting information
   ########################################
   Help => undef,

   # types
   TypeInfo => undef,
   AllTypesInfo => undef,
   TypeId => undef,

   # hcs
   Exists => undef,
   ListContents => undef,
   GetListContentsIterator => undef,
   IteratorNext => undef,
   IteratorFinish => undef,

   # objects
   FetchObject => undef,

   # assertions/instructions/profiles
   GetAssertionList => undef,
   FetchFromLibrary => undef,


   ########################################
   # signing up...
   ########################################
   RegisterIdentity => undef,
   RevokeIdentity => undef,
   RemoveIdentity => undef,

   ########################################
   # Manipulating the hierarchy and objects
   ########################################
   Create => undef,

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
    ActionAllowed => undef,
    CreateLibItem => undef,
    GetSpecialSet => undef,
    );
our $log;
our $ha;
our $hierarchy_channel;
our $shared_memory_dir;

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

  if(! defined $ha) {
    $ha = Machination::HAccessor->new($machination_config);
    $log = $ha->log;
    $log->dmsg($cat,"handler called",1);
    $shared_memory_dir = $ha->conf->get_dir("dir.SHM");
    -d $shared_memory_dir || make_path($shared_memory_dir);
  }

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
  my $rem_user = $req->getAttribute("user");

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
    $args = &xml_to_perl($req);
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

  my $call_args = &xml_to_perl($req);
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
  my $rep = &perl_to_xrep($ret);

  print to_xml($rep) . "\n";

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

=item * B<Help>

=cut

sub call_Help {
  my $info;

  $info .= "Machination WebHierarchy\n";
  $info .= "MPM: " . Apache2::MPM->show() . "\n";
  $info .= "threaded: " . Apache2::MPM->is_threaded() . "\n";

  my $t = threads->create(\&splat);
  return $info;
}

sub splat {
  return 1;
}

=item * B<TypeInfo>

TypeInfo($type)

=cut

sub call_TypeInfo {
  my ($owner,$approval,$type) = @_;

  return $ha->type_info($type);
}

=item * B<AllTypesInfo>

AllTypesInfo($opts)

=cut

sub call_AllTypesInfo {
  my ($owner,$approval,$opts) = @_;

  return $ha->all_types_info($opts);
}

=item * B<TypeId>

TypeId($type_name)

=cut

sub call_TypeId {
  my ($owner,$approval,$type) = @_;

  return $ha->type_id($type);
}

=item B<Exists>

Exists($path)

need readtext or exists permission on /hc[machination:root]/hc[path1]...

=cut

sub call_Exists {
  my ($owner,$approval,$path) = @_;

  my $hp;
  $hp = Machination::HPath->new($ha,$path);

  my $req = {channel_id=>hierarchy_channel(),
             op=>"exists",
             mpath=>$hp->to_mpath,
             owner=>$owner,
             approval=>$approval};
  return $hp->id if $ha->action_allowed($req,$hp->parent);
  $req->{op} = "readtext";
  return $hp->id if $ha->action_allowed($req,$hp->parent);

  AuthzDeniedException->
    throw("could not get read or exists permission for $path");
}

=item B<ListContents($hc,$opts)>

List the contents of $hc.

 $hc = numeric id or path string
 $opts = hash of options {
    types => [types,to,list], # (all types if this is not specified)
    fetch_names => 0 or 1 (whether to fetch object names as well)
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

sub call_ListContents {
  my ($owner,$approval,$hc,$opts) = @_;

  $ha->log->dmsg("WebHierarchy.ListContents",
                 "owner: $owner, approval: $approval, hc: $hc, " .
                 "opts: " . Dumper($opts),9);

  my $hp = Machination::HPath->new($ha,$hc);

  die "hc $hc does not exist" unless(defined $hp->id);

  $ha->log->dmsg("WebHierarchy.ListContents","hp: " . $hp->id,9);

  my $req = {channel_id=>hierarchy_channel(),
             op=>"listcontents",
             mpath=>$hp->to_mpath,
             owner=>$owner,
             approval=>$approval};
  die "could not get listcontents permission for " . $req->{mpath}
    unless($ha->action_allowed($req,$hp));

  my $pass_opts = {};
  $pass_opts->{fields} = ["name"] if($opts->{fetch_names});
  my @contents;

  if($opts->{types}) {
    foreach my $type (@{$opts->{types}}) {
      my $tid = $ha->type_id($type);
      push @contents, $ha->list_all_contents_of_type($tid,$hp->id,$pass_opts);
    }
  } else {
    @contents = $ha->list_contents($hp->id,$pass_opts);
  }

  return \@contents;
}

=item B<GetListContentsIterator>

$fetcher_info = GetListContentsIterator($hc,$opts)

See B<GetIteratorInfo> for $fetcher_info format

=cut

sub call_GetListContentsIterator {
  my ($owner,$approval,$hc,$types,$opts) = @_;

  my $hp = Machination::HPath->new($ha,$hc);
  die "hc $hc does not exist" unless(defined $hp->id);

  my $req = {channel_id=>hierarchy_channel(),
             op=>"listcontents",
             mpath=>$hp->to_mpath,
             owner=>$owner,
             approval=>$approval};
  die "could not get listcontents permission for " . $req->{mpath}
    unless($ha->action_allowed($req,$hp));

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

$list = GetAssertionList($object,$channel)

=cut

sub call_GetAssertionList {
  my ($owner,$approval,$object,$channel) = @_;
  my $info;

  my ($obj_type,$obj_type_id,$obj_id);
  if($object =~ /^\//) {
    my $hp = Machination::HPath->new($ha,$object);
    $obj_type = $hp->type;
    $obj_id = $hp->id;
  } else {
    ($obj_type,$obj_id) = split(/:/,$object);
  }
  $obj_type_id = $ha->type_id($obj_type);

  my $authorised = 0;
  my ($own_type_id,$own_id) = $ha->authen_str_to_object($owner);
  $authorised = 1 if($own_type_id == $obj_type_id &&
                     $own_id == $obj_id);
  die "$owner is not allowed to view the assertion list for $object"
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
          my $id_path = Machination::HPath->new($ha,$hc->{id})->parent_path;
          push @$id_path, $hc->{id};
          push @hc_path, $id_path;
          if($hc->{is_mp}) {
            push @hc_mp_path, $id_path;
            push @hc_mps, $hc->{id};
          }
        }
    }
  }

  $info->{hcs} = \@hc_path;
  $info->{attachments} =
    $ha->fetch_attachment_list
      ($channel,\@hc_ids,"assertion",
       {obj_fields=>["mpath","ass_op","ass_arg","action_op","action_arg"]});
#  $info->{mps} = $ha->mps(\@hc_ids);
  $info->{mps} = \@hc_mp_path;
  my $policies = $ha->fetch_attachment_list
    ($channel,\@hc_mps,"mpolicy",
     {obj_fields=>["mpath","policy_direction"]});
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

=item B<FetchFromLibrary>

$list = FetchFromLibrary($mpath,$lib_path)

=cut

sub call_FetchFromLibrary {
  my ($owner,$approval,$mpath,$lpath) = @_;
  my @list;
  push @list, {mpath=>$mpath,ass_op=>"hastext",ass_arg=>join(",",@$lpath)};
  return @list;
}

=item B<RegisterIdentity>

$signed_cert = RegisterIdentity($obj_type,$csr,$fields)

permissions required:

- create /system/$obj_type/$obj_type:$obj_name (if the object doesn't exist)
- settext /system/$obj_type/$obj_type:$obj_name/@pubkey

=cut

sub call_RegisterIdentity {
  my ($caller,$approval,$obj_type,$csr,$fields) = @_;

  # get name from csr
  my $obj_name;

  # Try to sign the csr
  my $signed_csr = $ha->sign_csr($csr);

  my $hp_str = "/system/$obj_type/$obj_type:$obj_name";

  # create the object under /system unless it already exists.
  # This will also check we have the correct permission.
  my $obj_id;
  $obj_id = call_Create($caller,$approval,$hp_str,$fields)
    unless($obj_id = call_Exists($caller,$approval,$hp_str));

  # store the signed csr
  call_ModifyObject($caller,$approval,$hp_str,{pubkey=>$signed_csr});

  # hand the signed csr back
  return $signed_csr;
}

=item B<RevokeIdentity>

$success = RevokeIdentity($id)

=cut

sub call_RevokeIdentity {
  my ($caller,$approval,$id) = @_;

}

=item B<FetchObject>

=cut


=item * call_Create($ent,$path,$fields)

=cut

sub call_Create {
  my ($ent,$path,$fields) = @_;

  if($path eq "machination:root") {
    $ha->create_root_hc;
    return;
  }

    my $parent = $1 if($path=~s/^(.*)\///);
    my ($type,$name) = split(/:/,$path);
    if(!defined $name) {
        $name = $type;
        $type = "machination:hc";
    }
    $parent = undef if($parent eq "");
    $name = undef if($name eq "");

    die "create requires a type\n" unless $type;

    if($type eq "machination:hc" && ! exists($fields->{is_mp})){
	$fields->{is_mp}=0;
    }
    $fields->{owner} = $ent;

    $parent = "/" if(!defined $parent && $type eq "machination:hc");
    $parent = "/sys/orphaned" if(!defined $parent);
    my $id;
    my $hp = Machination::HPath->new($ha,$parent);

    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",id=>$hp->id},
	    owner=>$ent,
	    op=>"add_elt",
	    elt_path=>"/hc/contents",
	},
	$hp->id
	);

    $id = $ha->hobject->create_in($type,$name,$fields,$hp->id);

    return $id;
}

=item * call_LinkCount($ent,$item)

$item = path_string or type:id

=cut

sub call_LinkCount {
  my ($owner,$approval,$item) = @_;

  my ($type,$id);
  if($item =~ /^\//) {
    my $hp = Machination::HPath->new($ha,$item);
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
    
    my $item_hp = Machination::HPath->new($ha,$item);
    
    my $hc_id;
    if($hc=~/^\//) {
	my $hp = Machination::HPath->new($ha,$hc);
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
	$item_hp->parent
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
    
    my $item_hp = Machination::HPath->new($ha,$item);

    # need del_elt permission to the path where the link is to be removed
    authz(
	{
	    svc_id=>"machination:hierarchy",
	    to=>{type=>"machination:hc",
		 id=>$item_hp->parent},
	    owner=>$ent,
	    op=>"del_elt",
	    elt_path=>"/hc/contents",
	},
	$item_hp->parent,
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

sub call_ListAttachments {
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

=item * call_ActionAllowed($ent,$req,$thing)

$req is action request in hash ref form:
  {
    svc_id=>$svc_id,
    op=>$op,
    ...
  }

$thing can be:

=over

=item - an hc id

=item - an authz instruction in hash ref form (see 
 Machination::HInternalIface->action_allowed)

=item - a ref to an array of authz instructions as above

=back

=cut

sub call_ActionAllowed {
    my ($ent,$req,$thing) =  @_;

    return ($ha->action_allowed($req,$thing));
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

    $log->emsg("WebHierarchy.error",$error,1);
    print to_xml(['error',['message',$error]]) . "\n";

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