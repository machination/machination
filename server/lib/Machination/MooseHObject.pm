package Machination::MooseHObject;
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

has "ha" => (is=>"ro",
             required=>1,
             handles=>[qw(read_dbh write_dbh)]);

has 'id' => (is=>'ro',
             required=>1);

has 'type_id' => (is=>'ro',
                  required=>1);

has '_data' => (is=>'ro',
                required=>0,
                default => sub { {} });

sub fetch_data {
  my $self = shift;
  my @fields = @_;
  my $opts = pop @fields
    if(ref($fields[$#fields]) || ! defined $fields[$#fields]);
  @fields = ("*") unless(@fields);

  my $table;
  if($self->type_id eq "machination:hc") {
    $table = "hcs";
  } else {
    $table = "objs_" . $self->type_id;
  }
  my $fetched = $self->ha->fetch($table,{fields=>\@fields,
                                         params=>[$self->id],
                                         revision=>$opts->{revision}});
  foreach my $key (keys %$fetched) {
    $self->_data->{$key} = $fetched->{$key};
  }
  return $self->_data;
}

sub get_field {
  my $self = shift;
  my $fname = shift;

  $self->fetch_data($fname) unless exists $self->_data->{$fname};
  return $self->_data->{$fname};
}

sub modify_data {
  my $self = shift;
  my $opts = shift;
  my %fields = @_;

  $self->ha->modify_obj($opts,$self->type,$self->id,\%fields);
}

sub name {
  my $self = shift;
  return $self->get_field("name");
}

sub parents {
  my $self = shift;

  eval "use Machination::MooseHC";
  my @parents;
  foreach my $pid ($self->ha->fetch_parents($self->type_id, $self->id)) {
    push @parents, Machination::MooseHC->new(ha=>$self->ha, id=>$pid);
  }
  return @parents;
}

sub paths {
  my $self = shift;

  # Special case for machination root
  my $root_id = $self->ha->fetch_root_id;
  return (Machination::HPath->new(ha=>$self->ha, from=>"/"))
    if($self->type_id eq "machination:hc" &&
       $self->id == $root_id
      );

  my @paths;
  foreach my $parent ($self->parents) {
    push @paths, $self->_construct_path($parent);
  }
  return @paths;
}

sub _construct_path {
  my $self = shift;
  my $path_parent = shift;

  my $path = Machination::HPath->new(ha=>$self->ha,from=>"/");
  $path->populate_ids;
  my $data = $self->fetch_data;
  my @items = (Machination::HPathItem->
               new(name=>$self->name,
                   id=>$self->id,
                   type=>$self->ha->type_name($self->type_id),
                  ));
  my $parent = $path_parent;
  my $root_id = $self->ha->fetch_root_id;
  while($parent->id != $root_id) {
    unshift @items, Machination::HPathItem->
      new(name=>$parent->name,
          id=>$parent->id,
          type=>"machination:hc");
    $parent = $parent->parent;
  }
  foreach my $item (@items) {
    $path->append($item);
  }
  return $path;
}

sub obj_table {
  my $self = shift;

  if($self->type_id eq "machination:hc" || !defined $self->type_id) {
    return "hcs";
  } else {
    return "objs_" . $self->id;
  }
}

sub exists {
  my $self = shift;

  my $sql = "select name from " . $self->obj_table .
    " where id=?";
  my @row = $self->ha->read_dbh->selectrow_array($sql, {} , $self->id);

  return scalar(@row);
}

__PACKAGE__->meta->make_immutable;

1;
