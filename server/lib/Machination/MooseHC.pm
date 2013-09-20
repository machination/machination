package Machination::MooseHC;
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
use Machination::HPath;

extends 'Machination::MooseHObject';

use Data::Dumper;


has '+type_id' => (default=>'machination:hc');

sub parent {
  my $self = shift;
  return $self->new(ha=>$self->ha, id=>$self->ha->fetch_parent($self->id));
}

sub path {
  my $self = shift;
  return $self->_construct_path($self->parent);
}

sub id_path {
  my $self = shift;
  my @idpath;
  foreach my $item (@{$self->path->rep}) {
    push @idpath, $item->id;
  }
  return \@idpath;
}

__PACKAGE__->meta->make_immutable;

1;
