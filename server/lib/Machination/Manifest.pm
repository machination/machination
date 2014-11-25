package Machination::Manifest;
# Copyright 2014 Colin Higgs
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
use XML::LibXML;
use File::Path qw(make_path remove_tree);
use File::Copy::Recursive(qw(fcopy dircopy));
use File::Spec;

=pod

=head1 Machination::Manifest

=head2 Create/Copy files and directories from a manifest

=head2 Synopsis

$man = Machination::Manifest->new(location=>$file);

=head2 Machination::Manifest

=head3 Methods:

=over

=item B<new>

$hp = Machination::Manifest->new(location=>"manifest.xml");

=cut

has 'location' => (
  is=>'ro',
  required=>1
);

has 'doc' => (
  is=>'ro',
  writer=>'_set_doc'
);

has 'verbose' => (
  is => 'rw',
  isa => 'Bool',
  default => 1,
);

has 'src_root' => (
  is => 'rw',
  predicate => 'has_src_root',
  clearer => 'clear_src_root'
);

has 'tgt_root' => (
  is => 'rw',
  predicate => 'has_tgt_root',
  clearer => 'clear_tgt_root',
);

sub BUILD {
  my $self = shift;
  my $args = shift;

  $self->_set_doc(XML::LibXML->load_xml(location=>$self->location));
}

sub install {
  my $self = shift;
  foreach my $node ($self->doc->findnodes('/manifest/*')) {
    $self->install_node($node);
  }
}

sub install_node {
  my $self = shift;
  my $node = shift;
  if($node->nodeName eq "file") {
    $self->install_file($node);
  } elsif($node->nodeName eq "dir") {
    $self->install_dir($node);
  }
}

sub install_file {
  my $self = shift;
  my $node = shift;

  my $src = $self->rootify($node->getAttribute('src'),'src');
  my $tgt = $self->rootify($node->getAttribute('tgt'),'tgt');
  $self->msg("FILE: copying $src to $tgt");
  fcopy($src,$tgt);
}

sub install_dir {
  my $self = shift;
  my $node = shift;

  my $src = $self->rootify($node->getAttribute('src'),'src');
  my $tgt = $self->rootify($node->getAttribute('tgt'),'tgt');

  if($node->hasAttribute('src')) {
    # a directory to be copied
    $self->msg("DIR: copying $src to $tgt");
    dircopy($src,$tgt);
  } else {
    # make sure directory exists
    $self->msg("DIR: ensure $tgt exists");
    make_path($tgt);
  }
}

sub rootify {
  my $self = shift;
  my $path = shift;
  my $kind = shift;
  $kind = 'tgt' unless defined $kind;

  my $root = "${kind}_root";
  my $has = "has_${kind}_root";
  if($self->$has) {
    return File::Spec->canonpath(
      File::Spec->catfile($self->$root,$path)
    );
  }
  return $path;
}

sub msg {
  my $self = shift;
  my $msg = shift;

  print "$msg\n" if $self->verbose;
}

__PACKAGE__->meta->make_immutable;

1;
