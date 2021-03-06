package Machination::HPath;
# Copyright 2013 Colin Higgs
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

use Moose;
use namespace::autoclean;
use Carp;
use Exception::Class;
use Machination::Exceptions;
use Data::Dumper;
use Text::ParseWords;
use HOP::Lexer qw(string_lexer);
use Storable;
use Machination::HPathItem;

=pod

=head1 Machination::HPath

=head2 Class to manipulate Machination Hierarchy paths.

=head2 Synopsis

 $hp = Machination::HPath->new(ha=>$ha,from=>"/system/sets/set:some_set");

 or

 $hp = Machination::HPath->new(ha=>$ha,from=>$other_hpath_object_to_copy);
 $object_id = $hp->id;

 The path need not exist in the hierarchy yet, though if it does not
 any attempts to look up hierarchy information like parents() or id()
 will fail.

 $ha should be a Machination::HAccessor object and is used to look up
 information in the hierachy.

=head2 Machination::HPath

=head3 Methods:

=over

=item B<new>

 $hp = Machination::HPath->new(from=>"/system/sets/set:some_set");

 or

 $hp = Machination::HPath->new(from=>$other_hpath_object_to_copy);

Create a new Machination::HPath

=cut

# Internal Representation
#
# [
#  Machination::HPathItem,
#  ...
# ]

has 'rep' => (is=>'ro',
              required=>0,
              isa=>'ArrayRef[Machination::HPathItem]',
              writer=>'_set_rep');

has 'ha' => (is=>'rw',
             isa => 'Machination::HAccessor',
             clearer=>'clear_ha',
             predicate=>'has_ha',
             required=>0);

has 'revision' => (is=>'rw',
                   required =>0);

has 'ensure_rooted' => (is=>'ro',
                        required=>1,
                        default=>1,
                        isa=>'Bool',
                        writer=>'_set_ensure_rooted');

has '_ids_populated' => (is=>'ro',
                         required=>1,
                         default=>0,
                         isa=>'Bool',
                         writer=>'_set_ids_populated');

has '_last_id_index' => (is=>'ro',
                         required=>0,
                         default=>0,
                         isa=>'Int',
                         writer=>'_set_last_id_index');

around BUILDARGS => sub {
  my $orig  = shift;
  my $class = shift;

  my $obj;
  if ( @_ == 1 && ref($_[0]) ne 'HASH') {
    return $class->$orig( from => $_[0] );
  }
  else {
    return $class->$orig(@_);
  }

};

sub BUILD {
  my $self = shift;
  my $args = shift;

  $self->_set_rep($self->construct_rep($args->{from}));
  MalformedPathException->
    throw("HPath is not rooted and ensure_rooted is true.")
      if($self->ensure_rooted && ! $self->is_rooted);

}

=item B<construct_rep>

$rep = $hp->construct_rep($other_hp)
$rep = $hp->construct_rep($other_rep)
$rep = $hp->construct_rep("/some/path/string")

=cut

sub construct_rep {
  my $self = shift;
  my $path = shift;

  my $rep;
  if(eval {$path->isa('Machination::HPath')}) {
    # clone an existing object
    $rep = $self->clone_rep($path->rep);
  } elsif(ref $path eq "ARRAY") {
    # ARRAY ref - should be an hpath rep
    $rep = $self->clone_rep($path);
  } else {
    $rep = $self->string_to_rep($path);
  }

  # Check that the representation we just made is valid
  my $parent = undef;
  foreach my $item (@$rep) {
#    print Dumper($parent);
#    print Dumper($item);
    if($item->branch eq "contents") {
      next if ! defined $parent;
      MalformedPathException->
        throw($item->full_string . " in " . $parent->full_string .
              " should be after an hc or in another branch.\n")
          unless($parent->type eq "machination:hc");
    } elsif ($item->branch eq "attachments") {
      MalformedPathException->
        throw($item->full_string . " in " . $parent->full_string .
              " should be after an hc or in another branch.\n")
          unless($parent->type eq "machination:hc");
    } elsif ($item->branch eq "agroup_members") {
      MalformedPathException->
        throw($item->full_string . ": agroup_members must be specified with an id.\n")
          unless($item->has_id);
      MalformedPathException->
        throw($item->full_string . " in " . $parent->full_string .
              " should be after an agroup_" . $item->type . " or in another branch.\n")
          unless(
                 $self->ha->type_from_agroup_type
                 (
                  $self->ha->type_id($parent->type)
                 )
                 ==
                 $self->ha->type_id($item->type)
                );
    } elsif ($item->branch eq "set_members") {
      MalformedPathException->
        throw($item->full_string . " in " . $parent->full_string .
              " should be after a set or another branch.\n")
          unless($parent->type eq "set");
      MalformedPathException->
        throw($item->full_string . ": set_members must be specified with an id.\n")
          unless($item->has_id);
    } elsif ($item->branch eq "machination_root") {

    } else {
      die "unkown branch '" . $item->branch . "'";
    }
    $parent = $item;
  }

  return $rep;
}

=item B<clone_rep>

 $copy_of_hp_rep = $hp->clone_rep;
 $newrep = $hp->clone_rep($other_rep);

=cut

sub clone_rep {
  my ($self,$rep) = @_;
  $rep = $self->rep unless defined $rep;

  return Storable::dclone($rep);
}

=item B<copy_attribs>

=cut

sub copy_attribs {
  my $self = shift;
  my $from = shift;
  my $to = shift;

  $to->ha($from->ha) if($from->has_ha);
  $to->revision($from->revision);
  $to->_set_ensure_rooted($from->ensure_rooted);
}

=item B<clone_attribs>

=cut

sub clone_attribs {
  my $self = shift;
  # Construct the simplest HPath object we can so we can copy attribs
  # to it.
  my $hp = Machination::HPath->new(ensure_rooted=>0, from=>[]);
  $self->copy_attribs($self, $hp);
  return $hp;
}

=item B<clone>

=cut

sub clone {
  my $self = shift;
  my $hp = $self->clone_attribs;
  $hp->_set_rep($self->clone_rep($self->rep));
  return $hp;
}

=item B<string_to_rep>

 $rep = $hp->string_to_rep("/some/path/to/type:name");

 Used by new to construct the object representation when given a
 string argument.

=cut

sub _path_item {
  my $self = shift;
  my $tracking = shift;

#  my %args = (path=>$self);
  my %args;
  $args{branch} = $tracking->{branch} if (exists $tracking->{branch});
  $args{type} = $tracking->{type};
  if($tracking->{is_id}) {
    $args{id} = $tracking->{name};
  } else {
    $args{name} = $tracking->{name};
  }

  return Machination::HPathItem->new(%args);
}

sub string_to_rep {
  my $self = shift;
  my ($path) = @_;
  my @path;
  my $cat = "HPath.string_to_rep";

  # Treat root differently
  if($path =~ s/\///) {
    push @path, Machination::HPathItem->new(special=>"root");
  }

  my @input_tokens =
    (
     ['QSTRING', qr/'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"/, sub {
        $_[1] =~ s/\\(.)/$1/g;
        return ['NAME', substr($_[1],1,-1)]
      }],
     ['QCHAR', qr/\\./, sub {
        return ['NAME', substr($_[1],1,1)]
      }],
     ['PATH_SEP', qr/\//],
     ['BRANCH_SEP', qr/::/],
     ['TYPENAME_SEP', qr/:/],
     ['ID', qr/\#\d+/, sub {
        return ['ID', substr($_[1],1)]
      }],
     ['NAME', qr/.*/],
     );
  my $lexer = string_lexer($path, @input_tokens);
#  my $tracking = {is_id=>0, type_is_id=>0};
  my $tracking = {};
  while (my $token = $lexer->()) {
    if($token->[0] eq 'PATH_SEP') {
      $tracking->{name} = "" unless defined $tracking->{name};
      my $item = $self->_path_item($tracking);
      push @path, $item
        unless($item->is_hc and $item->name eq "");
      $tracking = {is_id=>0, type_is_id=>0};
    } elsif ($token->[0] eq 'NAME') {
      MalformedPathException->
        throw("attempting to add non digits to an ID")
          if($tracking->{is_id});
      $tracking->{name} .= $token->[1];
    } elsif ($token->[0] eq 'BRANCH_SEP') {
      MalformedPathException->
        throw("adding a second branch")
          if(exists $tracking->{branch});
      $tracking->{branch} = $tracking->{name};
      delete $tracking->{name};
    } elsif ($token->[0] eq 'TYPENAME_SEP') {
      MalformedPathException->
        throw("second type/name seperator")
          if(exists $tracking->{type});
      $tracking->{type} = $tracking->{name};
      delete $tracking->{name};
    } elsif ($token->[0] eq 'ID') {
      $tracking->{name} = $token->[1];
      if(exists $tracking->{type}) {
        # object specifier is an id
        $tracking->{is_id} = 1;
      } else {
        # type specifier is an id - not supposed to do that.
        MalformedPathException->
          throw("Type specifier must not be an id.")
      }
    } else {
      MalformedPathException->
        throw("Unrecognised token $token->[0] parsing HPath $path");
    }
  }
  $tracking->{name} = "" unless defined $tracking->{name};
  $tracking->{type} = 'machination:hc' unless defined $tracking->{type};
  my $item = $self->_path_item($tracking);
  push @path, $item
    unless($item->is_hc and $item->name eq "");

  return \@path;
}

=item B<is_rooted>

=cut

sub is_rooted {
  my $self = shift;
  return if ! @{$self->rep};
  return $self->rep->[0]->is_root;
}

=item B<to_string>

=cut

sub to_string {
  my $self = shift;
  my @path = map {$_->to_string} @{$self->rep};
  return "/" if(@path==1 && $self->is_rooted);
  return join("/",@path)
}

=item B<slice>

=cut

sub slice {
  my $self = shift;
  my $slice = shift;
  my ($from, $to) = split(/:/, $slice);
  my $ensure_rooted = 0;
  if($from eq '') {
    $from = 0;
    $ensure_rooted = $self->ensure_rooted;
  }
  my @rep;
  my $len = @{$self->rep};
  if(defined $to) {
    $to = $len - 1 if($to eq "");
    $to = $len - 1 + $to if($to < 0);
    @rep = @{$self->rep}[$from .. $to];
  } else {
    @rep = ($self->rep->[$from]);
  }
  my $hp = $self->clone_attribs;
  $hp->_set_ensure_rooted($ensure_rooted);
  $hp->_set_rep(\@rep);
  return $hp;
}

=item B<identifies_object>

An HPath identifies an object if it is one of the following:

- rooted
- an hc with an id defined
- an object with an id defined

Note that the object may not exist in the hierarchy, but if it does,
the above is enough information to find it.

=cut

sub identifies_object {
  my $self = shift;

  return 0 if(! defined $self->leaf_node);
  ($self->is_rooted or $self->leaf_node->has_id) ? return 1 : return 0;
}

=item B<leaf_node>

=cut

sub leaf_node {
  my $self = shift;
  return $self->rep->[$#{$self->rep}];
}

=item B<parent>

=cut

sub parent {
  my $self = shift;
  return $self->slice(":-1");
}

=item B<populate_ids>

=cut

sub populate_ids {
  my $self = shift;

#  die "Cannot populate_ids unless path identifies an object"
  return
    unless $self->identifies_object;

  # If path is non rooted and still identifies an object then it has
  # an id already.
  return unless $self->is_rooted;

  croak "An ha is required to populate_ids"
    unless $self->has_ha;

  # initialise loop
  my $last_id_index = -1;
  my $parent_id;
  foreach my $item (@{$self->rep}) {
    if(!defined $item->id) {
      if($item->branch eq "machination_root") {
        $item->id($self->ha->fetch_root_id);
      } elsif($item->branch eq "contents") {
        # Try to fetch an id if we don't have one.
        $item->id($self->ha->fetch_id
                  (
                   $self->ha->type_id($item->type),
                   $item->name,
                   $parent_id
                  )
                 );
      } elsif($item->branch eq "set_members") {
        # Make sure that $item->id is a member of the parent set
      }
    }
    if(defined $item->id) {
      # We got an ID from the hierarchy.
      $last_id_index++;
    } else {
      # We didn't get one.
      last;
    }
    $parent_id = $item->id;
  }
  $self->_set_last_id_index($last_id_index);
  $self->_set_ids_populated(1);
  return;
}

=item B<existing_pos>

=cut

sub existing_pos {
  my $self = shift;
  my $recheck = 0;
  $recheck = shift if @_;

  croak "An ha is required to check existing_pos"
    unless $self->has_ha;

  if(!exists $self->{_existing_pos} || $recheck) {
    # initialise loop
    my $pos = -1;
    my $parent;
    foreach my $item (@{$self->rep}) {
      if($item->branch eq "machination_root") {
        my $root_id = $self->ha->fetch_root_id;
        last unless defined $root_id;
        $item->id($root_id);
      } elsif($item->branch eq "contents") {
        if($item->has_id) {
          # Check if id exists in parent
          my $inhc = $self->ha->object_in_hc
            (
             $self->ha->type_id($item->type),
             $item->id,
             $parent->id
            );
          last unless defined $inhc;
        } else {
          # Fetch id of name
          my $id = $self->ha->fetch_id
            (
             $self->ha->type_id($item->type),
             $item->name,
             $parent->id
            );
          # exit loop if no id was found
          last unless defined $id;
          $item->id($id);
        }
      } elsif($item->branch eq "attachments") {
        # Check if id is really attached to parent
        my $is_attached = $self->ha->is_attached
          (
           $self->ha->type_id($item->type),
           $item->id,
           $parent->id
          );
        last unless $is_attached;
      } elsif($item->branch eq "set_members") {
        # Make sure that $item->id is a member of the parent set
        my $set = Machination::HSet->new($self->ha, $parent->id);
        last unless $set->member_type == $self->ha->type_id($item->type) &&
          $set->has_member("all", $item->id);
      } elsif($item->branch eq "agroup_members") {
        # Make sure that $item->id is in agroup $parent->id
        last unless $self->ha->is_ag_member
          (
           $self->ha->type_id($parent->type),
           $parent->id,
           $item->id
          )
      }
      $parent = $item;
      $pos++;
    }
    $self->{_existing_pos} = $pos;
  }

  return $self->{_existing_pos};
}

=item B<existing>

=cut

sub existing {
  my $self = shift;
  my $pos = $self->existing_pos;
  return if $pos == -1;
  return $self->slice('0:' . $pos);
}

=item B<remainder>

=cut

sub remainder {
  my $self = shift;

  my $pos = $self->existing_pos;
  return if $pos == @{$self->rep};
  return $self->slice(($pos+1) . ":");
}

=item B<exists>

=cut

sub exists {
  my $self = shift;
  return 1 if ($self->existing_pos + 1) == @{$self->rep};
  return 0;
}

=item B<name>

=cut

sub name {
  my $self = shift;
  return unless defined $self->leaf_node;
  return $self->leaf_node->name;
}

=item B<id>

=cut

sub id {
  my $self = shift;
  return unless $self->exists;
  return $self->leaf_node->id;
}

=item B<type>

=cut

sub type {
  my $self = shift;
  return unless defined $self->leaf_node;
  return $self->leaf_node->type;
}

=item B<type_id>

=cut

sub type_id {
  my $self = shift;
  return unless defined $self->type;
  return $self->ha->type_id($self->type);
}

=item B<append>

=cut

sub append {
  my $self = shift;
  my $item = shift;
  MachinationException->
    throw("cannot append $item: it is not a Machination::HPathItem")
      unless(blessed($item) && $item->isa("Machination::HPathItem"));
  push(@{$self->rep},$item);
}

=item B<paths>

=cut

sub paths {
  my $self = shift;
  MachinationException->
    throw("cannot call 'parents' on " . $self->to_string .
    ": it does not exist")
      unless $self->exists;

  return Machination::MooseHObject->
    new(ha=>$self->ha, id=>$self->id, type_id=>$self->type_id)->
      paths;
}


__PACKAGE__->meta->make_immutable;

1;
