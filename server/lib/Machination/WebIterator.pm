package Machination::WebIterator;
# Copyright 2011 Colin Higgs
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

use Machination::XMLDumper;
use Data::Dumper;

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $self = {};
  bless $self,$class;

  $self->ha(shift);

  return $self;
}

sub ha {
  my $self = shift;
  if(@_) {
    $self->{ha} = shift;
  }
  return $self->{ha};
}

sub fetcher {
  my $self = shift;
  if(@_) {
    $self->{fetcher} = shift;
  }
  return $self->{fetcher};
}

sub dumper {
  my $self = shift;
  if(@_) {
    $self->{dumper} = shift;
  }
  return $self->{dumper};
}

sub ITERATOR_INIT {
  my $self = shift;
  $self->dumper(Machination::XMLDumper->new);
}

sub ITERATOR_NEXT {
  my $self = shift;
  my $n = shift;
  my $id = shift;

  return $self->fetcher->fetch_some($n);
}

sub ITERATOR_PRECLEANUP {
  my $self = shift;
  my $id = shift;

  $self->ha->log->dmsg("WebIterator.ITERATOR_PRECLEANUP",
                       "Deleting iterator $id",4);
  $self->fetcher->finish if($self->fetcher);
}

#sub SERIALISE {
#  my $self = shift;
#  my $thing = shift;
#
##  print "serialising " . Dumper($thing);
#  return $self->dumper->to_xml($thing)->toString(1);
#}

1;
