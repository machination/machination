package Machination::XMLDumper;

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

use XML::LibXML;

=pod

=head1 Machination::XMLDumper

=head2 Convert between perl data structures and a very simple XML
representation


=head2 Synopsis

$xd = Machination::XMLDumper->new;

$xml_elt = $xd->to_xml({text=>"some text",array=>[1,2,3]});

$perl_var = $xd->to_perl(XML::LibXML::Element or $xml_string);

=cut

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $self = {};
  bless $self,$class;

  return $self;
}

sub to_perl {
  my $self = shift;
  my ($elt) = @_;

  unless(ref $elt) {
    $elt = XML::LibXML->new->parse_string($elt)->documentElement;
  }

  my $obj;
  my $tag = $elt->nodeName;
  if($tag eq "r" || $tag eq "a") {
    $obj = [];
    foreach ($elt->findnodes("*")) {
	    push @$obj, $self->to_perl($_);
    }
  } elsif($tag eq "u") {
    $obj = undef;
  } elsif($tag eq "s") {
    $obj = $elt->textContent;
  } elsif($tag eq "h") {
    $obj = {};
    foreach ($elt->findnodes("k")) {
	    unless (defined $_->getAttribute("id")) {
        die "attempt to specify a hash item with no id";
	    }
	    if(my @nodes = $_->findnodes("*")) {
        $obj->{$_->getAttribute("id")} = $self->to_perl($nodes[0]);
	    } else {
        my $text = $_->textContent;
        if($text eq "") {
          $obj->{$_->getAttribute("id")} = undef;
        } else {
          $obj->{$_->getAttribute("id")} = $text;
        }
	    }
    }
  }

  return $obj;
}

sub to_xml {
  my $self = shift;
  my $obj = shift;

  if(!defined $obj) {
    return XML::LibXML::Element->new("u");
  } elsif(! ref $obj) {
    my $elt = XML::LibXML::Element->new("s");
    $elt->appendText($obj);
    return $elt;
  } elsif(ref $obj eq "HASH") {
    my $elt = XML::LibXML::Element->new("h");
    foreach my $k (keys %$obj) {
      my $item = XML::LibXML::Element->new("k");
      $item->setAttribute("id",$k);
      $item->appendChild($self->to_xml($obj->{$k}));
      $elt->appendChild($item);
    }
    return $elt;
  } elsif(ref $obj eq "ARRAY") {
    my $elt = XML::LibXML::Element->new("a");
    foreach my $item (@$obj) {
      $elt->appendChild($self->to_xml($item));
    }
    return $elt;
  } else {
    die "don't know how to turn a " . ref $obj . " into xml";
  }
}

1;
