use strict;
package Machination::XMLConstructor;

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
use Exception::Class;
use Machination::Exceptions;
use Machination::MPath;
use XML::LibXML;
use Data::Dumper;
=pod

=head1 Machination::XMLConstructor

=head2 Construct XML from Machination assertion actions

=head2 Synopsis

 $xcon = Machination::XMLConstructor->new($root_name);

=head2 Machination::XMLConstructor

=head3 Methods:

=over

=item B<new>

 $xcon = Machination::XMLConstructor->new($webclient);

Create a new Machination::XMLConstructor

=cut

sub new {
  my $class = shift;
  my ($wc) = @_;
  my $self = {};
  bless $self,$class;

  $self->parser(XML::LibXML->new);
  my $doc = XML::LibXML::Document->new;
  $self->doc($doc);
  $self->wc($wc);

  return $self;
}

=item B<parser>

 $parser = $con->parser or $parser = $con->parser(XML::LibXML->new)

=cut

sub parser {
  my $self = shift;

  if(@_) {
    $self->{parser} = shift;
  }
  return $self->{parser};
}

=item B<doc>

 $r = $con->doc or $r = $con->root($document_node)

document node should be an XML::LibXML::Document object

=cut

sub doc {
  my $self = shift;
  if(@_) {
    $self->{doc} = shift;
  }
  return $self->{doc};
}

=item B<wc>

 $webclient = $con->wc or $webclient = $con->wc($webclient)

$webclient should be an Machination::WebClient object

=cut

sub wc {
  my $self = shift;
  if(@_) {
    $self->{wc} = shift;
  }
  return $self->{wc};
}

=item B<compile>

$doc = $con->compile($data);

=cut

sub compile {
  my $self = shift;
  my $data = shift;
  my $mpolicies={};

  # $res_idx = { /mpath => $data, ... , mandatory => {/mpath=>$data,...}}
  my $res_idx = {};

  my %mp_map;
  my %mps;
  foreach my $mp (@{$data->{mps}}) {
    $mps{$mp->[-1]} = undef;
  }
  foreach my $hcp (@{$data->{hcs}}) {
    my $hc = $hcp->[-1];
    my @list;
    foreach my $hid (@$hcp) {
      if(exists $mps{$hid}) {
        push @list, $hid;
      }
    }
    $mp_map{$hc} = \@list;
  }
  $mpolicies->{mp_map} = \%mp_map;
  $mpolicies->{data} = $data;

#  # TODO: calculate mpolicies
#  foreach my $path (@{$data->{hcs}}) {
#    $self->get_mpolicy($path,$mpolicies);
#  }

#  delete $mpolicies->{data};
#  print Dumper($mpolicies); return;

  my @stack = @{$data->{attachments}};
  while(@stack) {
    my $a = shift @stack;
    if(! $self->assert($a)) {
      $self->act($a,$res_idx,$self->get_poldir($a,$mpolicies),\@stack);
    }
  }

  return ($self->doc,$res_idx);
}

sub get_poldir {
  my $self = shift;
  my $a = shift;
  my $mpolicies = shift;

  my @pol = reverse $self->get_mpolicy($a->{hc_id},$mpolicies);
  my $direction = 0;
  foreach my $pol (@pol) {
    my $pol_obj = Machination::MPath->new($pol->{mpath});
    if($pol_obj->could_be_parent_of($a->{mpath})) {
      $direction = $pol->{policy_direction};
      last;
    }
  }
  return $direction;
}

sub get_mpolicy {
  my $self = shift;
  my $hc = shift;
  my $mpolicies = shift;
  my $data = $mpolicies->{data};
  my $mp_map = $mpolicies->{mp_map};

  my $mplist = $mp_map->{$hc};
  my @pols;
  foreach my $mp (@$mplist) {
    push @pols, @{$data->{mpolicy_attachments}->{$mp}};
  }
  return @pols;
}

=item B<assert>

 $bool = $con->assert($mpath,$op,$arg);

=cut

sub assert {
  my $self = shift;
  my $a = shift;
  my ($mpath,$op,$arg) = ($a->{mpath},$a->{ass_op},$a->{ass_arg});

  $mpath = Machination::MPath->new($mpath) if(! ref $mpath);
  $self->wc->log->dmsg
    ("XMLConstructor.assert","asserting " . $mpath->to_string . " $op($arg)",
     9);
  if ($op eq "exists") {
    if($self->doc->findnodes($mpath->to_xpath)) {
      $self->wc->log->dmsg
        ("XMLConstructor.assert", "  TRUE",9);
      return 1;
    } else {
      $self->wc->log->dmsg
        ("XMLConstructor.assert", "  FALSE",9);
      return 0;
    }
  } elsif($op eq "hastext") {
    my @nodes = $self->doc->findnodes($mpath->to_xpath);
    return unless @nodes;
    my $content;
    if($nodes[0]->nodeType == XML_ELEMENT_NODE) {
      # element
      $content = $nodes[0]->textContent;
    } else {
      # attribute
      $content = $nodes[0]->getValue;
    }
    if($content eq $arg) {
      return 1;
    } else {
      return 0;
    }
  } elsif($op eq "notexists") {
    if($self->doc->findnodes($mpath->to_xpath)) {
      $self->wc->log->dmsg
        ("XMLConstructor.assert", "  FALSE",9);
      return 0;
    } else {
      $self->wc->log->dmsg
        ("XMLConstructor.assert", "  TRUE",9);
      return 1;
    }
  } else {
    die "Assertion op unknown: \"$op\"";
  }
}

=item B<act>

 $bool = $con->act($mpath,$op,$arg);

=cut

sub act {
  my $self = shift;
  my ($a,$res_idx,$poldir,$stack) = @_;
  my ($mpath,$op,$arg) = ($a->{mpath},$a->{action_op},$a->{action_arg});

  my $mpath = Machination::MPath->new($mpath) unless ref $mpath;
  $self->wc->log->dmsg
    ("XMLConstructor.act","performing action $op($arg) on " .
     $mpath->to_string,9);

  my $action = "action_$op";
  $self->$action($mpath,$a,$res_idx,$poldir,$stack);

#  if($a->{is_mandatory}) {
#    $res_idx->{mandatory}->{$mpath->to_string} = $a;
#  }

  return;
}

sub action_create {
  my $self = shift;
  my $mpath = shift;
  my $a = shift;
  my $res_idx = shift;
  my $poldir = shift;
  my %opts = @_;
  $opts{auto_viv} = 1 unless(exists $opts{auto_viv});
  $opts{record_index} = 1 unless(exists $opts{record_index});

  $mpath = Machination::MPath->new($mpath) unless(ref $mpath);

  if($poldir == -1) {
    # see if the node doesn't exist because of a previous "notexists"
    # on mpath or parents
    foreach my $p ($mpath, $mpath->parents) {
      if(my $d = $res_idx->{$p->to_string}) {
        return if $d->{ass_op} eq "notexists";
      }
    }
  } elsif($poldir == 0) {
    # check there is no mandatory notextists for mpath or parents
    foreach my $p ($mpath, $mpath->parents) {
      if(my $d = $res_idx->{$p->to_string}) {
        # don't do anything if the mandatory is a notexists
        return if($d->{is_mandatory} && $d->{ass_op} eq "notexists");
      }
    }
  }

#  my $r = $self->doc;
  my $pelt = $self->doc;
  my $i = 0;
  my @sofar;
  foreach my $node (@{$mpath->{rep}}) {
    push @sofar, $node;
    if($i == 0 ) {
      $i++;
      next;
    }

    my ($name,$id,$xpath);
    if(ref $node) {
      ($name,$id) = @$node;
      $xpath = "$name\[\@id=\"$id\"\]";
    } else {
      $name = $node;
      $xpath = $name;
    }

    if (my @children = $pelt->findnodes($xpath)) {
      $i++;
      $pelt = $children[0];
      next;
    }

    die $mpath->to_string . " already exists" if $i > $#{$mpath->{rep}};

    if($i == $#{$mpath->{rep}} || $opts{auto_viv}) {
      $self->wc->log->dmsg
        ("XMLConstructor.action_create",
         "creating " . $mpath->to_string(rep=>\@sofar),9);
      my $new;
      if($name =~ s/^\@//) {
        # attribute
        $new = $pelt->setAttribute($name,"");
      } else {
        # element
        if($pelt->isa("XML::LibXML::Document")) {
          $new = $self->doc->createElement($name);
          $self->doc->setDocumentElement($new);
        } else {
          $new = $pelt->addNewChild(undef,$name);
        }
      }
      $new->setAttribute("id",$id) if(defined $id);
      $pelt = $new;
    } else {
      die "parent or parents of " . $mpath->to_string . " not yet created";
    }
    $i++;
  }
  $res_idx->{$mpath->to_string} = $a if($opts{record_index});
}

sub action_settext {
  my $self = shift;
  my $mpath = shift;
  my $a = shift;
  my $res_idx = shift;
  my $poldir = shift;
  my %opts = @_;
  $opts{auto_viv} = 1 unless(exists $opts{auto_viv});

  $mpath = Machination::MPath->new($mpath) unless(ref $mpath);
  my @nodes = $self->doc->findnodes($mpath->to_xpath);

    $self->wc->log->dmsg
      ("XMLConstructor.action_settext",
       "policy direction $poldir",9);

  if($poldir == -1) {
    # see if the node doesn't exist because of a previous "notexists"
    # on mpath or parents
    foreach my $p ($mpath, $mpath->parents) {
      if(my $d = $res_idx->{$p->to_string}) {
        return if $d->{ass_op} eq "notexists";
      }
    }
    # check if the node has some text already, abort if it does
    if(@nodes) {
      if($nodes[0]->nodeType == XML_ELEMENT_NODE) {
        return if($nodes[0]->hasChildren);
      } else {
        return if($nodes[0]->getValue ne "");
      }
    }
  } elsif($poldir == 0) {
    # check there is no mandatory notextists for mpath or parents
    foreach my $p ($mpath, $mpath->parents) {
#      $self->wc->log->dmsg
#        ("XMLConstructor.action_settext",
#         "checking mandatory for " . $p->to_string,9);

      if(my $d = $res_idx->{$p->to_string}) {
        # don't do anything if the mandatory is a notexists
#        $self->wc->log->dmsg
#          ("XMLConstructor.action_settext",
#           "found mandatory for " . $p->to_string,9);
        return if($d->{is_mandatory} && $d->{ass_op} eq "notexists");
      }
    }
    # check if the node has some mandatory text already, abort if it does
    if(@nodes) {
      if(my $d = $res_idx->{$mpath->to_string}) {
        return if($d->{is_mandatory} && $d->{ass_op} =~ /^hastext/);
      }
    }
  }
  if(! @nodes) {
    # create the element if it doesn't already exist
    $self->action_create($mpath,$a,$res_idx,$poldir,record_index=>0);
    @nodes = $self->doc->findnodes($mpath->to_xpath);
  }

  #replace any text content

  # default to the assertion argument if the action argument is missing
  my $content = $a->{action_arg};
  $content = $a->{ass_arg} unless defined $content;

  $self->wc->log->dmsg
    ("XMLConstructor.action_settext",
     "setting text of " . $mpath->to_string . " to $content",9);

  if($nodes[0]->nodeType == XML_ELEMENT_NODE) {
    $nodes[0]->removeChildNodes;
    $nodes[0]->appendText($content);
  } else {
    $nodes[0]->setValue($content);
  }
  $res_idx->{$mpath->to_string} = $a;
}

sub action_delete {
  my $self = shift;
  my $mpath = shift;
  my $a = shift;
  my $res_idx = shift;
  my $poldir = shift;
  my %opts = @_;

  $mpath = Machination::MPath->new($mpath) unless(ref $mpath);

  if($poldir == -1) {
    # never delete an existing node if remote wins
    return 0;
  } elsif($poldir == 0) {
    my $blocked = 0;
    # check to make sure there is no mandatory implying existence
    if(my $d = $res_idx->{$mpath}) {
      if($d->{is_mandatory}) {
        return 0 if($d->{ass_op} eq "exists" ||
                    $d->{ass_op} =~ /^hastext/);
      }
    }
    if($mpath->is_element) {
      # look at any existing children (including attributes)
      # and see if they can be deleted
      my $xpath = $mpath->to_xpath . "/* | " . $mpath->to_xpath . "/\@*";
      foreach my $node ($self->doc->findnodes($xpath)) {
        my $cmp = Machination::MPath->new($node);
        $self->wc->log->dmsg
          ("XMLConstructor.action_delete",
           "  deleting child " . $cmp->to_string,9);
        $blocked = 1
          unless($self->action_delete($cmp,
                                      $a,
                                      $res_idx,
                                      $poldir));
      }
    }
    $res_idx->{$mpath->to_string} = $a;
    if($blocked) {
      return 0;
    } else {
      $self->delete_mpath($mpath,$a,$res_idx);
      return 1;
    }
  } elsif($poldir == 1) {
    $self->delete_mpath($mpath,$a,$res_idx);
    $res_idx->{$mpath->to_string} = $a;
    return 1;
  }
}

sub delete_mpath {
  my $self = shift;
  my $mpath = shift;
  my $a = shift;
  my $res_idx = shift;

  print "delete_mpath: deleting " . $mpath->to_string . "\n";
  print Dumper($res_idx);
  if($mpath->is_element) {
    # removing an element
    my $elt = ($self->doc->findnodes($mpath->to_xpath))[0];
    $elt->parentNode->removeChild($elt);
  } else {
    # removing an attribute
    my $pelt = ($self->doc->findnodes($mpath->parent->to_xpath))[0];
    $pelt->removeAttribute($mpath->name);
  }
}

sub action_addlib {
  my $self = shift;
  my $mpath = shift;
  my $a = shift;
  my $res_idx = shift;
  my $poldir = shift;
  my $stack = shift;
  my %opts = @_;
  $opts{auto_viv} = 1 unless(exists $opts{auto_viv});
  $opts{record_index} = 1 unless(exists $opts{record_index});

  $mpath = Machination::MPath->new($mpath) unless(ref $mpath);

  if($poldir == -1) {
    # see if the node doesn't exist because of a previous "notexists"
    # on mpath or parents
    foreach my $p ($mpath, $mpath->parents) {
      if(my $d = $res_idx->{$p->to_string}) {
        return if $d->{ass_op} eq "notexists";
      }
    }
  } elsif($poldir == 0) {
    # check there is no mandatory notextists for mpath or parents
    foreach my $p ($mpath, $mpath->parents) {
      if(my $d = $res_idx->{$p->to_string}) {
        # don't do anything if the mandatory is a notexists
        return if($d->{is_mandatory} && $d->{ass_op} eq "notexists");
      }
    }
  }

  my @lib_elts = $self->doc->findnodes("/top/machination/lib-path/item");
  my @lib_path;
  foreach my $item (@lib_elts) {
    push @lib_path, $item->getAttribute("id");
  }

  my $mpath = "/top/machination/lib-added/item[" . $mpath->quote_id($a->{mpath}) . "]";
  unshift @$stack, {hc_id=>$a->{hc_id},
                   is_mandatory=>$a->{is_mandatory},
                   mpath=>$mpath,
                   ass_op=>"exists",
                   action_op=>"create"};
}


=item B<create_elt>

 $elt = $con->create_elt($mpath,%opts)

%opts:

 root=>$root_elt   (default $con->root)
 auto_viv=>$bool   (default 0)

=cut

sub create {
  my $self = shift;
  my $mpath = shift;
  my %opts = @_;
  $mpath = Machination::MPath->new($mpath) unless ref $mpath;
  my $r = $self->doc->documentElement;
  $r = $opts{root} if exists $opts{root};


  my @mrep_copy = @{$mpath->{rep}};
  if($mrep_copy[0] eq "") { # rooted mpath
    # check to make sure root node has the same name
    shift @mrep_copy;
    my $node = shift @mrep_copy;
    my ($name,$id);
    if(ref $node) {
      ($name,$id) = @$node;
    } else {
      $name = $node;
    }
    my $rname = $r->nodeName;
    my $rid = $r->getAttribute("id");
    die "Root node of mpath \"" . $mpath->to_string . "\" " .
      "does not have the same name as " .
        "the document being constructed ($rname)." unless($name eq $rname);
  }

  my $ctx = $r;
  my $i = 0;
  foreach my $node (@mrep_copy) {
    my ($name,$id);
    if(ref $node) {
      ($name,$id) = @$node;
    } else {
      $name = $node;
    }

    if($i == $#mrep_copy || $opts{auto_viv}) {
      my $new = $ctx->addNewChild(undef,$name);
      $new->setAttribute("id",$id) if(defined $id);
      $ctx = $new;
    } else {
      die "parent or parents of " . $mpath->to_string . " not yet created";
    }
    $i++;
  }

  return $r;
}

=item B<order_assertion_list>

$ordered_list = $con->order_assertion_list($assertions);

=cut

sub order_assertion_list {
  my $self = shift;
  my $ass_list = shift;
  my $mp_idx = {mpath=>{}};
  my $ret = {};

  my %mp_map;
  my $mpi = 0;
  foreach my $hc (@{$ass_list->{hcs}}) {
    $mpi++ if($hc == $ass_list->{mps}->[$mpi+1]);
    $mp_map{$hc} = $ass_list->{mps}->[$mpi];
  }
  $ret->{mp_map} = \%mp_map;

  my %mp_ass_arrays;
  my %mp_lib_arrays;
  foreach my $mp (@{$ass_list->{mps}}) {
    $mp_ass_arrays{$mp} = [[],[],[],[],[],[]];
    $mp_lib_arrays{$mp} = [[],[],[],[],[],[]];
  }
  $ret->{mp_ass_arrays} = \%mp_ass_arrays;
  $ret->{mp_lib_arrays} = \%mp_lib_arrays;

  my @palist = @{$ass_list->{mpolicy_attachments}};
  my $pol = {};
  $ret->{pol} = $pol;
  my @alist = @{$ass_list->{attachments}};

#  my $pa_i = 0;
#  my $a_i = 0;
  foreach my $hc (@{$ass_list->{hcs}}) {

    # track policies first
    my (@pdef,@pman);
    while (@palist && $palist[0]->{hc_id} == $hc) {
      # iterate over all merge policy attachments for this hc
      my $pa = shift @palist;

      # if the current hc is a merge point, store policy attachments
      if($mp_map{$hc} == $hc) {
        if($pa->{is_mandatory}) {
          unshift @pman, $pa;
        } else {
          push @pdef, $pa;
        }
      }
    }
    if($mp_map{$hc} == $hc) {
      # $hc is a merge point
      # calculate merge policy
      foreach my $pa (@pdef,@pman) {
        $pol->{$pa->{mpath}} = {mp=>$hc,direction=>$pa->{policy_direction}};
      }
    }

    # now look at assertion attachments
    my @hc_ass;
    my @lib_ass;
    while (@alist && $alist[0]->{hc_id} == $hc) {
      # iterate over all assertion attachments for this hc and collect them
      # according to whether they affect the library path or not
      my $att = shift @alist;
      if($att->{mpath} =~ /^\/top\/machination\/lib-path\/item/) {
        push @lib_ass, $att;
      } else {
        push @hc_ass, $att;
      }
    }

    # re-order library assertions
    foreach my $att (@lib_ass) {
      # check mpath against policy
      $self->_populate_mp_arrays(\%mp_lib_arrays,$att,$pol);
    }

    # generate the library path for this hc
#    my @lib_path = $self->_generate_library_path
#      ($hc,\%mp_lib_arrays,$ass_list);
    my @lib_path;

    # re-order other assertions, inserting calls to the library as
    # necessary
    while (@hc_ass) {
      my $att = shift @hc_ass;
      if($att->{op} eq "addlib") {
        my $fetched;
        # fetch from library and add new assertions to @hc_ass
        unshift @hc_ass, $self->
          fetch_from_library($att->{mpath},\@lib_path,$fetched);
      } else {
        $self->_populate_mp_arrays(\%mp_ass_arrays,$att,$pol);
      }
    }
  }
  my (@left,@right);
  foreach my $mp (@{$ass_list->{mps}}) {
    my $arrays = $mp_ass_arrays{$mp};
    unshift @left, (@{$arrays->[0]},@{$arrays->[1]});
    push @left, @{$arrays->[2]};
    unshift @right, @{$arrays->[3]};
    push @right, (@{$arrays->[4]},@{$arrays->[5]});
  }
  $ret->{ordered} = [@left,@right];
  return $ret;
}

sub _populate_mp_arrays {
  my $self = shift;
  my ($mp_arrays,$att,$pol) = @_;

  my $controlling_mpath_obj;
  foreach my $pol_mpath (keys %$pol) {
    my $pol_mpath_obj = Machination::MPath->new($pol_mpath);
    if($pol_mpath_obj->could_be_parent_of($att->{mpath})) {
      # this policy is a candidate
      $controlling_mpath_obj = $pol_mpath_obj->
        most_specific($pol_mpath_obj,$controlling_mpath_obj);
    }
  }
  my $mp = 1;
  my $direction;
  if($controlling_mpath_obj) {
    $mp = $pol->{$controlling_mpath_obj->to_string}->{mp};
    $direction = $pol->{$controlling_mpath_obj->to_string}->{direction};
  }

  if($direction == 0) {
    # situation normal
    if($att->{is_mandatory}) {
      unshift @{$mp_arrays->{$mp}->[3]}, $att;
    } else {
      push @{$mp_arrays->{$mp}->[2]}, $att;
    }
  } elsif($direction == 1) {
    # leafward assertions win
    if($att->{is_mandatory}) {
      unshift @{$mp_arrays->{$mp}->[5]}, $att;
    } else {
      push @{$mp_arrays->{$mp}->[4]}, $att;
    }
  } elsif($direction == -1) {
    # rootward assertions win
    if($att->{is_mandatory}) {
      unshift @{$mp_arrays->{$mp}->[1]}, $att;
    } else {
      push @{$mp_arrays->{$mp}->[0]}, $att;
    }
  }
}

=item B<fetch_from_library>

 @ass_list = $con->fetch_from_library($mpath,$lib_path,$fetched);

=cut

sub fetch_from_library {
  my $self = shift;
  my ($mpath,$lpath,$fetched) = @_;

  my @list;
  if(! exists $fetched->{$mpath}) {
    @list = $self->wc->call("FetchFromLibrary",$mpath,$lpath)
  }
  $fetched->{$mpath} = undef;
  return @list;
}

=item B<try>

$con->try($elt,$channel_id,$owner,$approval,$action_list,$authz_list,$opts)

 $elt = XML::LibXML::Element object representing xml to be altered

 $channel_id = id of channel in which to try this set of instructions
 $owner = $authen_string,
 $approval = [$authen_string,$authen_string,...],

 $action_list = ref to list of hash refs with following representation:
 {
  op=>$op,
  mpath=>$mpath,
  args=>[arg1,...],
 }

 $authz_list = ref to list of authz instructions like the following:



returns:

 (0,$reason) if no authorisation tests were relevant

or

 (1,$bool) where $bool determines if action was allowed

=cut

sub try {
  my $self = shift;
  my ($elt,$act,$authz_list,$opts) = @_;
}

sub get_poldir_old {
  my $self = shift;
  my $a = shift;
  my $mpolicies = shift;

  my $pol = $self->get_mpolicy($a->{hc_id},$mpolicies);

  my $controlling_mpath_obj;
  foreach my $pol_mpath (keys %$pol) {
    print "checking against policy $pol_mpath:\n  " . $a->{mpath} . "\n";
    my $pol_mpath_obj = Machination::MPath->new($pol_mpath);
    if($pol_mpath_obj->could_be_parent_of($a->{mpath})) {
      print "  could be...\n";
      # this policy is a candidate
      if($controlling_mpath_obj) {
        $controlling_mpath_obj = $pol_mpath_obj->
          most_specific($pol_mpath_obj,$controlling_mpath_obj);
      } else {
        $controlling_mpath_obj = $pol_mpath_obj;
      }
    }
  }

  my $direction=0;
  if($controlling_mpath_obj) {
    $direction = $pol->{$controlling_mpath_obj->to_string}->{policy_direction};
    print "set direction from policy to $direction\n";
  }

  return $direction;
}

sub get_mpolicy_old {
  my $self = shift;
  my $path = shift;
  my $mpolicies = shift;
  my $data = $mpolicies->{data};
  my $mp_map = $mpolicies->{mp_map};

  if(!ref $path) {
    return $mpolicies->{$path} if (exists $mpolicies->{$path});
    foreach my $p (@{$mpolicies->{data}->{hcs}}) {
      if($p->[-1] == $path) {
        $path = $p;
        last;
      }
    }
  }

  if(exists $mpolicies->{$path->[-1]}) {
    return $mpolicies->{$path->[-1]};
  }

  # not been cached yet - work it out
  # make a local copy of path
  my @path = @$path;
  my $hcid = pop @path;
  my $prev;
  if(@path) {
    # not at root
    $prev = $self->get_mpolicy(\@path,$mpolicies);
  } else {
    # at root
    $prev = {};
  }
  if($mp_map->{$hcid} == $hcid) {
    # a new merge point - overlay new policies
    my %new;
    @new{keys %$prev} = values %$prev;
    $mpolicies->{$hcid} = \%new;
    foreach my $att (@{$data->{mpolicy_attachments}->{$hcid}}) {
      $new{$att->{mpath}} = $att;
    }
    $mpolicies->{$hcid} = \%new;
  } else {
    # policy just the same as previous
    $mpolicies->{$hcid} = $prev;
  }
}

=back

=cut

1;
