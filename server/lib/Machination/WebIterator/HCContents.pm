package Machination::WebIterator::HCContents;

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

use strict;
use warnings;

use Machination::WebIterator;

our @ISA;
push @ISA, "Machination::WebIterator";

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $self = $this->SUPER::new(shift);
  bless $self,$class;

  $self->hc(shift);

  return $self;
}

sub hc {
  my $self = shift;
  if(@_) {
    $self->{hc} = shift;
  }
  return $self->{hc};
}

sub types {
  my $self = shift;
  if(@_) {
    $self->{types} = shift;
  }
  return $self->{types};
}

sub current_type_index {
  my $self = shift;
  if(@_) {
    $self->{current_type_index} = shift;
  }
  return $self->{current_type_index};
}

sub fetcher {
  my $self = shift;
  if(@_) {
    $self->{fetcher} = shift;
  }
  return $self->{fetcher};
}

sub next_fetcher {
  my $self = shift;

  $self->current_type_index($self->current_type_index + 1);
  if ($self->current_type_index >= @{$self->types}) {
    # off the end of the list of types
    $self->fetcher(undef);
  } else {
    $self->fetcher
      (
       $self->ha->get_typed_contents_handle
       (
        $self->types->[$self->current_type_index],
        $self->hc,
        {fields=>["name"],show_type_id=>1}
       )
      );
  }

}

sub ITERATOR_INIT {
  my $self = shift;

#  print "calling $self->ITERATOR_INIT\n";
  $self->SUPER::ITERATOR_INIT;
  $self->current_type_index(-1);
  $self->next_fetcher;
}

sub ITERATOR_NEXT {
  my $self = shift;
  my $n = shift;
  my $id = shift;

#  print "calling $self->ITERATOR_NEXT\n";
  return unless $self->fetcher;
  my @rows;
#  my $continue = 1;
  while (@rows < $n) {
    my $need = $n - @rows;
    my @newrows = $self->fetcher->fetch_some($need);
    foreach my $row (@newrows) {
      $row->{type_id} = $self->types->[$self->current_type_index];
    }
    push @rows, @newrows;
    if (@rows < $n) {
      # not enough objects of the current type left to fetch $n: start
      # on the next type
      $self->fetcher->finish;
      $self->next_fetcher;
      if(! defined $self->fetcher) {
        # gone off the end of the list of types
        return @rows;
      }
    }
  }
  $self->ha->log->dmsg("HCContents.ITERATOR_NEXT","NEXT on iterator $id",4);
  return @rows;
}

1;
