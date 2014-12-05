use strict;
package Machination::ConfigFile;

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
use Exception::Class;
use Machination::Exceptions;
use XML::LibXML;
use File::Spec;

use Data::Dumper;

my $defaults =
  {
   "dir.VAR" => "/var/machination",
   "dir.SECRETS" => "secrets",
   "dir.TEST" => "splat",
   "dir.DATABASE" => "database",
   "file.database.CREDENTIALS" => ["dir.SECRETS","dbcred.xml"],
   "file.database.VALID_OPS" => ["dir.DATABASE","valid_ops.xml"],
};

=pod

=head1 Machination::ConfigFile

=head2 Read and manipulate Machination configuration info

=head2 Synopsis

    my $conf = Machination::ConfigFile->
      new(conf_file=>"/path/to/config/file")

=head2 Machination::ConfigFile

=head3 Methods:

=over

=item * $conf = Machination::ConfigFile->new('/path/to/config/file')

    Create a new Machination::ConfigFile

=cut

sub new {
  my $class = shift;
  my ($file) = @_;
  my $self = {};
  bless $self,$class;
  $self->file($file) if(defined $file);
  $self->root("");
  $self->defaults($defaults);

  return $self;
}

=item * $conf->defaults

=cut

sub defaults {
  my $self = shift;
  my $name = "defaults";
  $self->{$name} = shift unless($self->{$name});
  return $self->{$name};
}

=item * $conf->file of $conf->file($new_file)

    accessor for file attribute

=cut

sub file {
  my $self = shift;
  my ($in) = @_;
  my $name = "file";
  unless(exists $self->{$name}) {
    $self->{$name} = $in;
    delete $self->{doc};
    #	delete $self->{mpath};
  }
  return $self->{$name};
}

=item * $conf->mpath

    return machination path based on config file ($conf->file)
    location

=cut

sub mpath {
  my $self = shift;
  my (undef,$mpath,$file) =
    File::Spec->splitpath(File::Spec->rel2abs($self->file));
  return File::Spec->canonpath($mpath);
}

=item * $conf->root_path

  All paths are calculated relative to this. Default is "".

=cut

sub root_path {
  my $self = shift;
  my ($in) = @_;

  if(defined $in) {
    $self->{root_path} = $in;
  }
  return $self->{root_path};
}

=item * $conf->parser

=cut

sub parser {
  my $self = shift;
  my $name = "parser";
  $self->{$name} = XML::LibXML->new unless($self->{$name});
  return $self->{$name};
}

=item * $conf->doc

=cut

sub doc {
  my $self = shift;

  unless($self->file) {
    MachinationException->
	    throw("tried to get doc with no file set");
  }
  unless($self->{doc}) {
#    print "loading from " . $self->file . "\n";
    $self->{doc} = $self->parser->parse_file($self->file);
  }

# carp "returning " . (0 + $self->{doc});
  return $self->{doc};
}

=item * $conf->root

=cut

sub root {
    my $self = shift;
    return $self->doc->documentElement;
}

=item * $dir_path = $conf->get_dir($id)

=cut

sub get_dir {
  my $self = shift;
  my ($id,$recursing) = @_;

  my $dir;
  my $found = ($self->doc->findnodes("//dir\[\@xml:id='$id'\]"))[0];
  if($found) {
    my $sep = "";
    foreach my $c ($found->findnodes("component")) {
	    if($c->hasAttribute('value')){
        $dir .= $sep . $c->getAttribute('value');
	    } elsif($c->hasAttribute('ref')) {
        $dir .= $sep . $self->get_dir($c->getAttribute('ref'),1);
	    } else {
        MachinationException->
          throw("don't know how to interpret component element:\n" .
                $c->toString(1));
	    }
      # Set the seperator correctly for subsequent iterations
	    $sep = "/";
    }
  } else {
    $dir = $self->defaults->{$id};
  }

  if(substr($dir,0,1) ne "/") {
    $dir = $self->mpath . "/" . $dir;
  }

  if(!$recursing && $self->root_path ne "") {
    $dir = $self->root_path . $dir;
  }

  return $dir;
}

=item * $file_path  = $conf->get_file($file_id)

=cut

sub get_file {
  my $self = shift;
  my ($id) = @_;

  my $found = ($self->doc->findnodes("//file\[\@xml:id='$id'\]"))[0];
  if($found) {
    return $self->get_dir($found->getAttribute("dir")) . "/" .
      $found->getAttribute("name");
  } else {
    my ($dir,$fname) = @{$self->defaults->{$id}};
    return $self->get_dir($dir) . "/" . $fname;
  }
}

=item * $value = $conf->get_value($xpath)

=cut

sub get_value {
  my $self = shift;
  #    my ($xpath) = @_;

  my $id;
  my $xpath;
  my $base_node;
  if(@_ == 1) {
    $xpath = shift;
    $base_node = $self->root;
  } else {
    $id = shift;
    $xpath = shift;
    $base_node = ($self->doc->findnodes("//*\[\@xml:id='$id'\]"))[0];
  }

  my @nodes = $base_node->findnodes($xpath);
  if(@nodes) {
    return $nodes[0]->textContent;
  }
  return undef;
}

=back

=cut

1;
