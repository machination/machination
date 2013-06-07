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

 $hp = Machination::HPath->new($ha,"/system/sets/set:some_set");

 or

 $hp = Machination::HPath->new($ha,$other_hpath_object_to_copy);
 print Dumper($hp->id_path);
 $object_id = $hp->id;

 The path need not exist in the hierarchy yet, though if it does not
 any attempts to look up hierarchy information like id_path() or id()
 will fail.

 $ha should be a Machination::HAccessor object and is used to look up
 information in the hierachy.

=head2 Machination::HPath

=head3 Methods:

=over

=item B<new>

 $hp = Machination::HPath->new("/system/sets/set:some_set");

 or

 $hp = Machination::HPath->new($other_hpath_object_to_copy);

Create a new Machination::HPath

=cut

# Internal Representation
#
# [
#  [ $branch,
#   [ $type_name, $type_id, $which_specifed],
#   [ $obj_name, $obj_id, $which_specified]
#  ],
#  ...
# ]

has 'rep' => (is=>'ro',
              required=>0,
              isa=>'ArrayRef[Machination::HPathItem]',
              writer=>'_set_rep');

has 'ha' => (is=>'rw',
             isa => 'Machination::HAccessor',
             required=>0);

has 'revision' => (is=>'rw',
                   required =>0);

around BUILDARGS => sub {
  my $orig  = shift;
  my $class = shift;

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
}

=item B<construct_rep>

$rep = $hp->construct_rep($other_hp)
$rep = $hp->construct_rep($other_rep)
$rep = $hp->construct_rep("/some/path/string")

=cut

sub construct_rep {
  my $self = shift;
  my $path = shift;

  if(eval {$path->isa('Machination::HPath')}) {
    # clone an existing object
    return $self->clone_rep($path->rep);
  } elsif(ref $path eq "ARRAY") {
    # ARRAY ref - should be an hpath rep
    return $self->clone_rep($path);
  } else {
    return $self->string_to_rep($path);
  }
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

=item B<string_to_rep>

 $rep = $hp->string_to_rep("/some/path/to/type:name");

 Used by new to construct the object representation when given a
 string argument.

=cut

sub _path_item {
  my $self = shift;
  my $tracking = shift;

  my %args = (path=>$self);
  $args{branch} = $tracking->{branch} if (exists $tracking->{branch});
  if($tracking->{type_is_id}) {
    $args{type_id} = $tracking->{type};
  } else {
    $args{type_name} = $tracking->{type};
  }
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
    push @path, Machination::HPathItem->new(path=>$self, special=>"root");
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
  my $tracking = {is_id=>0, type_is_id=>0};
  while (my $token = $lexer->()) {
    if($token->[0] eq 'PATH_SEP') {
      push @path, $self->_path_item($tracking);
      $tracking = {is_id=>0, type_is_id=>0};
    } elsif ($token->[0] eq 'NAME') {
      die "attempting to add non digits to an ID" if($tracking->{is_id});
      $tracking->{name} .= $token->[1];
    } elsif ($token->[0] eq 'BRANCH_SEP') {
      die "adding a second branch" if(exists $tracking->{branch});
      $tracking->{branch} = $tracking->{name};
      delete $tracking->{name};
    } elsif ($token->[0] eq 'TYPENAME_SEP') {
      die "second type/name seperator"
        if(exists $tracking->{type});
      $tracking->{type} = $tracking->{name};
      delete $tracking->{name};
    } elsif ($token->[0] eq 'ID') {
      $tracking->{name} = $token->[1];
      if(exists $tracking->{type}) {
        # object specifier is an id
        $tracking->{is_id} = 1;
      } else {
        # type specifier is an id
        $tracking->{type_is_id} = 1;
      }
    } else {
      die "Unrecognised token $token->[0] parsing HPath $path";
    }
  }
  push @path, $self->_path_item($tracking);

  return \@path;
}

sub is_rooted {
  my $self = shift;
  return $self->rep->[0]->is_root;
}

sub to_string {
  my $self = shift;
  my @path = map {$_->to_string} @{$self->rep};
  return join("/",@path)
}

sub slice {
  my $self = shift;
  my $slice = shift;
  my ($from, $to) = split(/:/, $slice);
  $from = 0 if($from eq '');
  my @rep;
  my $len = @{$self->rep};
  if(defined $to) {
    $to = $len - 1 if($to eq "");
    $to = $len - 1 + $to if($to < 0);
    @rep = @{$self->rep}[$from .. $to];
  } else {
    @rep = ($self->rep->[$from]);
  }
  return __PACKAGE__->new(\@rep)
}

__PACKAGE__->meta->make_immutable;

1;
