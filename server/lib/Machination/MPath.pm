use strict;
package Machination::MPath;

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
use Text::ParseWords;
use XML::LibXML;
use Data::Dumper;
=pod

=head1 Machination::MPath

=head2 Class to manipulate "Machination paths" - a restricted version of
xpaths.

=head2 Synopsis

 $mp = Machination::MPath->new("/machination/path[description]");

 or

 $mp = Machination::MPath->new($other_mpath_object_to_copy);

=head2 Machination::MPath

=head3 Methods:

=over

=item B<new>

 $mp = Machination::MPath->new("/machination/path[description]");

 or

 $mp = Machination::MPath->new($other_mpath_object_to_copy);

Create a new Machination::MPath

=cut

sub new {
  my $class = shift;
  my ($mpath) = @_;
  my $self = {};
  bless $self,$class;

  $self->set_path($mpath) if(defined $mpath);

  return $self;
}

=item B<set_path>

$mp->set_path($string) or $mp->set_path($mpath_object)

Set the path represented by this object to $string or clone it from
another MPath object.

This method is called once during the constructor.

=cut

sub set_path {
  my $self = shift;
  my $mpath = shift;

  $self->{is_attribute} = 0;
  $self->{is_element} = 0;
  if(eval {$mpath->isa("Machination::MPath")}) {
    $self->{rep} = $mpath->clone_rep;
  } elsif(eval {$mpath->isa("XML::LibXML::Node")}) {
    my $node = $mpath;
    my @rep;
    while($node->nodeType != XML_DOCUMENT_NODE &&
         $node->nodeType != XML_DOCUMENT_FRAG_NODE) {
      my $name = $node->nodeName;
      if($node->nodeType == XML_ATTRIBUTE_NODE) {
        $name = "\@$name";
      }
      if($node->nodeType == XML_ELEMENT_NODE && $node->hasAttribute("id")) {
#        $name .= "[" . $node->getAttribute("id") . "]";
        $name = [$name, $node->getAttribute("id")];
      }
      unshift @rep, $name;
      $node = $node->parentNode;
    }
    unshift @rep, '';
    $self->{rep} = \@rep;
  } else {
    my @path;
    my @rep;
    $mpath eq "/" ? {@path = ("")} : {@path = parse_line("/",0,$mpath)};
    foreach my $elt (@path) {
      die "can't add mpath elements after specifying an attribute"
        if($self->is_attribute(\@rep));
      if($elt =~ /\[/) {
        my ($tag,$id) = $elt =~ /^(.+?)\[(.*)\]$/;
        croak "$elt specified incorrectly" if (!defined $tag || ! defined $id);
        push @rep, [$tag,$id];
      } else {
        push @rep, $elt;
      }
    }
    $self->{rep} = \@rep;
  }
}

=item B<clone_rep>

$rep = $mp->clone_rep

Return a deep copy of the representation of this object. Primarily used
to initialise a new copy of this object.

=cut

sub clone_rep {
  my $self = shift;

  my @new;
  foreach my $elt (@{$self->{rep}}) {
    if(ref $elt) {
      push @new, [$elt->[0],$elt->[1]];
    } else {
      push @new, $elt;
    }
  }

  return \@new;
}

=item B<to_string>

=cut

sub to_string {
  my $self = shift;
  my %opts = @_;
  my $rep = $opts{rep};
  $rep = $self->{rep} unless $rep;

  my @path;
  foreach my $node (@$rep) {
    if (ref $node) {
      my $id = $node->[1];
      $id = "\@id=\"$id\"" if($opts{to_xpath});
      push @path, $node->[0] . "[$id]";
    } else {
      push @path, $node;
    }
  }
  return "/" if(@path == 1);
  return join("/",@path);
}

=item B<construct_elt>

=cut

sub construct_elt {
  my $self = shift;

  my $doc = XML::LibXML::Element->new('doc');
  my $p = $doc;
  foreach my $node (@{$self->{rep}}) {
    next if $node eq "";
    my $e;
    if(ref $node) {
      $e = XML::LibXML::Element->new($node->[0]);
      $e->setAttribute("id",$node->[1]);
    } else {
      if(my ($name) = $node =~ /^\@(.+)/) {
        # an attribute
        $p->setAttribute($name, "");
        last;
      } else {
        # an element
        $e = XML::LibXML::Element->new($node);
      }
    }
    $p->appendChild($e);
    $p = $e;
  }
  return $doc->firstChild;
}

=item B<to_xpath>

=cut

sub to_xpath {
  my $self = shift;

  return $self->to_string(to_xpath=>1);
}

=item B<name>

$name = $mp->name

=cut

sub name {
  my $self = shift;

  my $name = $self->{rep}->[-1];
  $name = $name->[0] if ref $name;
  $name =~ s/^@//;
  return $name;
}

=item B<id>

$id = $mp->id

or

$newid = $mp->id($newid)

=cut

sub id {
  my $self = shift;

  if(@_) {
    print Dumper($self->{rep});
    $self->{rep}->[-1] = [$self->name, $_[0]];
    print Dumper($self->{rep});
  }
  my $last = $self->{rep}->[-1];
  ref $last ? return $last->[1] : return;
}

=item B<parent>

$parent = $mp->parent

return parent as a Machination::MPath object

=cut

sub parent {
  my $self = shift;

  my $p = Machination::MPath->new($self);
  pop @{$p->{rep}};

  return $p;
}

=item B<parents>

@parents = $mp->parent

return @parents as a list of Machination::MPath objects

=cut

sub parents {
  my $self = shift;
  my @p;

  my $p = $self->parent;
  while(@{$p->{rep}} >= 1) {
    push @p, $p;
    $p = $p->parent;
  }
  return @p;
}

=item B<could_be_parent_of>

$bool = $mp->could_be_parent_of($other_mpath)

Test whether this mpath could represent the (XML-wise) parent element
of $other_mpath. $other_mpath may be a string or another MPath object.

=cut

sub could_be_parent_of {
  my $self = shift;
  my $mpath = shift;

  $mpath = Machination::MPath->new($mpath)
    unless(eval {$mpath->isa("Machination::MPath")});

  my $i = 0;
  foreach my $pelt (@{$self->{rep}}) {
    my $elt = $mpath->{rep}->[$i];
    return 0 unless defined $elt;
    my ($ptag,$pid);
    if(ref $pelt) {
      ($ptag,$pid) = @$pelt;
    } else {
      $ptag = $pelt;
    }
    my ($tag,$id);
    if(ref $elt) {
      ($tag,$id) = @$elt;
    } else {
      $tag = $elt;
    }
#    print "compare '$tag($id)' with '$ptag($pid)'\n";
    return 0 unless($tag eq $ptag || $ptag eq "*");
    if(defined $pid) {
	    return 0 unless($id eq $pid || $pid eq "*");
    }
    $i++;
  }
  return 1;
}

=item B<is_element>

$bool = $mp->is_element

true if this mpath represents an XML element

=cut

sub is_element {
  my $self = shift;

  return ! $self->is_attribute;
}

=item B<is_attribute>

$bool = $mp->is_attribute

true if this mpath represents an XML attribute

=cut

sub is_attribute {
  my $self = shift;
  my $path = shift;
  $path = $self->{rep} unless $path;

  $path->[-1] =~ /^@/ ? return 1 : return 0;
}

=item B<depth>

$d = $mp->depth

return XML 'depth' =def number of elements deep in the tree, including
the final attribute node if this is an attribute

=cut

sub depth {
  my $self = shift;

  return scalar(@{$self->{rep}});
}

=item B<most_specific>

$more_specific_mpath = $mp->most_specific($mpath1,$mpath2)

=cut

sub most_specific {
  my $self = shift;
  my $mpath1 = shift;
  my $mpath2 = shift;

  $mpath1 = Machination::MPath->new($mpath1)
    unless(eval {$mpath1->isa("Machination::MPath")});
  $mpath2 = Machination::MPath->new($mpath2)
    unless(eval {$mpath2->isa("Machination::MPath")});

  return $mpath1 if $mpath1->depth > $mpath2->depth;
  return $mpath2 if $mpath2->depth > $mpath1->depth;

  # equal depths: more work required
}


=item B<quote_id>

$quoted_string = $mp->quote_id($unquoted_string)

=cut

sub quote_id {
  my $self = shift;
  my $str = shift;

  $str =~ s/\//\\\//g;
  return $str;
}

=back

=cut

1;
