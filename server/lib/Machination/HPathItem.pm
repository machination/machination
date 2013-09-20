package Machination::HPathItem;
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
use Data::Dumper;

=pod

=head1 Machination::HPathItem

=head2 Encapsulate properties of items in Machination Hierarchy paths.

=head2 Synopsis

 $root_item = Machination::HPathItem->new(special=>'root');
 $hc_item = Machination::HPathItem->new(name=>'system');
 $obj_item = Machination::HPathItem->new(
  type=>'set',
  name=>'global_admins'
 );
 $in_attachments_branch = Machination::HPathItem->new(
  branch=>'attachments',
  type=>'agroup_assertion',
  name=>'microsoft-office-v1234'
 );

=head2 Machination::HPathItem

=head3 Attributes:

=cut

#has 'path' => (is=>'ro',
#               required=>0,
#               isa=>'Machination::HPath');

has 'branch' => (is=>'ro',
                 required=>0,
                 isa=>'Str',
                 default=>'contents',
                 writer=>'_set_branch');

has 'name' => (is=>'rw',
               required=>1,
               isa=>'Str',
               clearer=>'clear_name',
               predicate=>'has_name');

has 'id' => (is=>'rw',
             required=>0,
             isa=>'Int',
             clearer=>'clear_id',
             predicate=>'has_id');

has 'type' => (is=>'rw',
               isa=>'Maybe[Str]',
               required=>1,
               default=>"machination:hc",
               clearer=>'clear_type_name',
               predicate=>'has_type_name');

=head3 Methods:

=over

=item B<new>

Create a new Machination::HPathItem

=cut

around BUILDARGS => sub {
  my $orig = shift;
  my $class = shift;

  my $args;
  if(ref($_[0]) eq 'HASH') {
    $args = $_[0];
  } else {
    my %args = @_;
    $args = \%args;
  }
  if(exists $args->{special}) {
    if($args->{special} eq "root") {
      $args->{name} = "machination:root"
        unless defined $args->{name};
      $args->{type} = "machination:hc"
        unless defined $args->{type};
    }
  }
  return $class->$orig($args);
};

sub BUILD {
  my $self = shift;
  my $args = shift;

  if(exists $args->{special}) {
    if($args->{special} eq "root") {
      $self->_set_branch('machination_root');
    }
  }

}

=item B<to_string>


=cut

sub to_string {
  my $self = shift;

  return '' if $self->is_root;
  my $str = "";
  $str .= $self->quote_name($self->branch) . "::"
    if($self->branch ne 'contents');
  $str .= $self->quote_name($self->type) . ":"
    if(! $self->is_hc);
  $str .= $self->quote_name($self->name);
  return $str;
}

=item B<quote_name>

=cut

sub quote_name {
  my $self = shift;
  my $name = shift;

  $name =~ s/([\\:'"])/\\$1/g;

  return $name;
}

=item B<is_root>

True if this item is the root hc.

=cut

sub is_root {
  my $self = shift;
  $self->branch eq "machination_root" ? return 1 : return 0;
}

=item B<is_hc>

True if this item is an hc.

=cut

sub is_hc {
  my $self = shift;
  if(!defined $self->type || $self->type eq "machination:hc") {
    return 1;
  } else {
    return 0;
  }
}

__PACKAGE__->meta->make_immutable;

1;
