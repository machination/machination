package Machination::HashXML;

# Copyright 2008 Colin Higgs and Matthew Richardson
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

BEGIN {
  use Exporter ();
  our ($VERSION, @ISA, @EXPORT, @EXPORT_OK, %EXPORT_TAGS);
  $VERSION = 0.001;
  @ISA = qw(Exporter);
  @EXPORT = qw(
                &xml_to_perl
                &perl_to_xrep
                &to_xml
             );
  @EXPORT_OK = qw(
                );
}

use XML::LibXML;

sub xml_to_perl {
  my ($elt) = @_;

  unless(ref $elt) {
    $elt = XML::LibXML->new->parse_string($elt)->documentElement;
  }

  my $obj;
  my $tag = $elt->nodeName;
  if($tag eq "r" || $tag eq "a") {
    $obj = [];
    foreach ($elt->findnodes("*")) {
	    push @$obj, &xml_to_perl($_);
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
        $obj->{$_->getAttribute("id")} = &xml_to_perl($nodes[0]);
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

sub perl_to_xrep {
  my ($obj) = @_;

#    my $xrep;
  if(!defined $obj) {
    return ["u"];
  } elsif(ref $obj eq "HASH") {
    my @items;
    foreach my $item (keys %$obj) {
	    push @items, ["k",&perl_to_xrep($obj->{$item}),{id=>$item}];
    }
    return ["h",\@items];
  } elsif(ref $obj eq "ARRAY") {
    return ["a"] unless(@$obj);
    my @items;
    foreach my $item (@$obj) {
	    push @items, &perl_to_xrep($item);
    }
    return ["a",\@items];
  } elsif(! ref $obj) {
    return ["s",$obj];
  } else {
    die "don't know how to turn a " . ref $obj . " into xml";
  }
}

sub to_xml {
  my $aref = shift;
  my $indent = shift;
  $indent = 0 unless(defined $indent);
  
  my ($tag,$content,$atts) = @$aref;
  
  my $istr = " " x $indent;
  my $str = "$istr<$tag";
  foreach my $att (keys %$atts) {
    $str .= " $att=\"" . $atts->{$att} . "\"";
  }
  unless(defined $content) {
    $str .= "/>";
    return $str;
  }
  if(ref $content) {
    if(ref $content->[0]) {
	    $str .= ">\n";
	    foreach (@{$content}) {
        $str .= to_xml($_,$indent+2) . "\n";
	    }
	    $str .= "$istr</$tag>";
    } elsif(exists $content->[0]) {
	    $content = to_xml($content,$indent+2);
	    $str .= ">\n$content\n$istr</$tag>";
    } else {
	    $str .= "/>";
    }
  } else {
    $str .= ">$content</$tag>";
  }
  return $str;
}

1;
