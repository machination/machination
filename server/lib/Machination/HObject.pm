package Machination::HObject;
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
#use Machination::HAccessor;
use Machination::Exceptions;
use Data::Dumper;

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $self = {};
  bless $self,$class;

  $self->ha(shift);
  $self->type(shift);
  $self->id(shift);

  return $self;
}

sub ha {
	my $self = shift;
	$self->{ha} = shift if(@_);
	return $self->{ha};
}
sub read_dbh {
	my $self = shift;
	return $self->ha->read_dbh;
}
sub write_dbh {
	my $self = shift;
	return $self->ha->write_dbh;
}
sub id {
	my $self = shift;
  if(@_) {
    $self->{id} = shift;
    delete $self->{data};
  }
	return $self->{id};
}
sub type {
	my $self = shift;
  if(@_) {
    my $type = shift;
    $type = "machination:hc" if(! defined $type);
    $self->{type} = $type;
    delete $self->{data};
  }
	return $self->{type};
}

sub fetch_data {
  my $self = shift;
  my @fields = @_;
  my $opts = pop @fields
    if(ref($fields[$#fields]) || ! defined $fields[$#fields]);
  @fields = ("*") unless(@fields);

  my $table;
  if($self->type eq "machination:hc") {
    $table = "hcs";
  } else {
    $table = "objs_" . $self->type;
  }
  $self->{data} = $self->ha->fetch($table,{fields=>\@fields,
                                           params=>[$self->id],
                                           revision=>$opts->{revision}});
  return $self->{data};
}

sub modify_data {
  my $self = shift;
  my $opts = shift;
  my %fields = @_;

  $self->ha->modify_obj($opts,$self->type,$self->id,\%fields);
}

sub fetch_action_list {
  my ($self,$channel,$opts) = @_;
}

1;
