package Apache::DataIterator::ExampleDirLister;
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

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $self = {};
  bless $self,$class;

  $self->path(shift);
  $self->names([]);

  return $self;
}

sub path {
  my $self = shift;
  if(@_) {
    $self->{path} = shift;
  }
  return $self->{path};
}

sub names {
  my $self = shift;
  if(@_) {
    $self->{names} = shift;
  }
  return $self->{names};
}

sub ITERATOR_INIT {
  my $self = shift;
  my @names = glob($self->path . "/*");
  $self->names(\@names);
}

sub ITERATOR_NEXT {
  my $self = shift;
  my $n = shift;

  my @tmp;
  foreach (1 .. $n) {
    my $val = pop @{$self->names};
    if(defined $val) {
      push @tmp, $val;
    } else {
      last;
    }
  }

  return @tmp;
}

sub SERIALISE {
  my $self = shift;

  my $dirs = shift;
  return join("\n",@$dirs) . "\n";
}

1;
