use strict;
package Machination::XML::Element;

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
use XML::LibXML;

@Machination::XML::Element::ISA = qw(XML::LibXML::Element);

=pod

=head1 Machination::XML::Element

=head2 Inherits XML::LibXML::Element and provides extra convenience methods

=head2 Synopsis

    my $elt = Machination::XML::Element->new($name);

=head2 Machination::XML::Element

=head3 Methods:

=over

=item * $elt = Machination::XML::Element->new($name);

Create a new Machination::XML::Element

=cut

sub new {
    my $class = shift;
    my $self = $class->SUPER::new(@_);
    bless $self,$class;
    return $self;
}

=item * $newelt = $elt->insertNewChild($name,$atts,$opts);

Create a new child element of $elt.

args:
  $name = name of new element
  $atts = hashref of attributes for new element. e.g. {attrib=>"value"}
  $opts = hashref of options:
    pos: "first" or "last" - controls position of inserted element
    
return:
  new element
    
=cut

sub insertNewChild {
    my $self = shift;
    my ($name,$atts,$opts) = @_;

    $opts->{pos} = "last" unless $opts->{pos};

    my $newelt = ref($self)->new($name);
    foreach (keys %$atts) {
	$newelt->setAttribute($_, $atts->{$_});
    }
    if($opts->{pos} eq "last") {
	$self->appendChild($newelt);
    } elsif ($opts->{pos} eq "first") {
	my $first = $self->firstChild;
	if($first) {
	    $self->insertBefore($newelt,$first);
	} else {
	    $self->appendChild($newelt);
	}
    } else {
	croak "insertNewChild does not understand position \"" .
	    $opts->{pos} . "\"";
    }
    return $newelt;
}

sub blessElement {
    my $self = shift;
    my $elt = shift;

    my $class = ref($self) ? ref($self) : $self;
    bless $elt, $class;
}

=back

=cut

1;
