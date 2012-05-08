use strict;
package Machination::HPath;
# Copyright 2012 Colin Higgs
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
use Data::Dumper;
use Text::ParseWords;

=pod

=head1 Machination::HPath

=head2 Class to manipulate Machination Hierarchy paths.

=head2 Synopsis

 $hp = Machination::HPath->new($ha,"/system/sets/set:some_set");

 or

 $hp = Machination::HPath->new($ha,$other_hpath_object_to_copy);
 print Dumper($hp->id_path);
 $object_id = $hp->id;

 The path need not exist in the hierarchy yet, though if it does not
 any attempts to look up hierarchy information like id_path() or id()
 will fail.

 $ha should be a Machination::HAccessor object and is used to look up
 information in the hierachy.

=head2 Machination::MPath

=head3 Methods:

=over

=item B<new>

 $hp = Machination::HPath->new($ha,"/system/sets/set:some_set");

 or

 $hp = Machination::HPath->new($ha,$other_hpath_object_to_copy);

Create a new Machination::HPath

=cut

sub new {
  my $class = shift;
  my ($ha,$path,$revision) = @_;
  my $self = {};
  bless $self,$class;

  $self->ha($ha);
  $self->set_path($path) if(defined $path);
  $self->revision($revision) if(defined $revision);

  return $self;
}

=item B<ha>

=cut

sub ha {
  my ($self,$in) = @_;

  if($in) {
    MachinationException->
	    throw("ha must be a Machination::HAccessor\n")
        unless(eval {$in->isa('Machination::HAccessor')});
    $self->{'ha'} = $in;
  }
  return $self->{'ha'};
}

=item B<set_path>

 $hp->set_path("/some/path");
 $hp->set_path($another_hpath_obj);
 $hp->set_path($numerical_id);

=cut

sub set_path {
  my $self = shift;
  my ($path) = @_;
  my $cat = "HAccessor.set_path";

  if($path) {
    if(eval {$path->isa('Machination::HPath')}) {
	    # clone an existing object
	    $self->{rep} = $path->clone_rep;
    } elsif(ref $path eq "ARRAY") {
      # ARRAY ref - should be an hpath rep
      $self->{rep} = $self->clone_rep($path);
    } elsif($path =~ /^\d+$/) {
      # numerical arg, assume an hc which must already exist in hierarchy
      my $cur_id = $path;
      my $root_id = $self->ha->fetch_root_id;
      my $name;
      if($cur_id == $root_id) {
        $name = '';
      } else {
        $name = $self->ha->fetch_name(undef,$cur_id,
                                      {revision=>$self->revision});
      }
      my @rep = (['contents',undef,$name]);
      while($cur_id) {
        $cur_id = $self->ha->fetch_parent($cur_id,{revision=>$self->revision});
        $self->ha->log->dmsg($cat,"cur id is : $cur_id",8);
        if($cur_id == $root_id) {
          $name = '';
        } else {
          $name = $self->ha->fetch_name(undef,$cur_id,
                                        {revision=>$self->revision});
        }
        unshift @rep, $name if($cur_id);
      }
      $self->{rep} = \@rep;
    } elsif(my ($type,$id) = $path =~ /^([^\/].*):(\d+)$/) {
      # a string in the form "type:12" or "1:12"
      my $type_id;
      $type =~ /^\d+$/ ?
        $type_id = $type : $type_id = $self->ha->type_id($type);

      # Make sure the object exists
      MalformedPathException->
        throw("object referred to by id in $path does not exist")
          unless $self->ha->object_exists($type_id,$id);

      if($type_id eq "machination:hc") {
        $self->{rep} = Machination::HPath->new($self->ha,$id)->clone_rep;
      } else {
        # Anything that's not an hc could have multiple parents.
        # We need to pick one.

        # Try /system/$type_name first
        my $type_name = $self->ha->type_name($type_id);
        my $hp = Machination::HPath->new
          ($self->ha,"/system/$type_name/$type_name:$id");
        if ($hp->id_path) {
          print "cloning " . $hp->to_string . "\n";
          $self->{rep} = $hp->clone_rep;
        } else {
          # Not in /system/$type_name - try picking first entry of @parents
          my @parents = $self->ha->fetch_parents($type_id,$id);
          if(@parents) {
            my $php = Machination::HPath->new($self->ha, $parents[0]);
            my $last = pop @{$php->{rep}};
            push @{$php->{rep}}, $last->[2];
            my $rep = [@{$php->{rep}},
                       ['contents',
                        $type_name,
                        $self->ha->fetch_name($type_id, $id)
                       ]
                      ];
            $self->{rep} = Machination::HPath->new($self->ha, $rep)->clone_rep;
          } else {
            # orphaned object
            $self->{rep} = $self->string_to_rep("/::orphaned::$type_id:$id");
          }
        }
      }
    } else {
      $self->{rep} = $self->string_to_rep($path);
    }
    croak "Machination::HPath not yet safe for branches other than contents"
      if $self->branch ne "contents";
  }
}

=item B<id_path>

 $idpath = $self->id_path
 $idpath = $self->id_path("/some/other/path");

Return an array ref with a list of object ids down the path
representation. If the path represents a non-hc object the last entry
will be an array ref like [$type_id,$obj_id].

For example, "/path/to/hc" might turn into [1,3,6,7] (1=='/'), while
"/path/to/set:some_set" might become [1,3,6,[1,5]].

=cut

sub id_path {
  my ($self,$rep) = @_;

  my ($idpath,$remainder) = $self->defined_id_path($rep);
  return undef if @$remainder;
  return $idpath;
}

sub defined_id_path {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = $self->{rep};
  }

  $rep = $self->clone_rep($rep);
  my $type_id = $self->type_id($rep);
  my @path;
  while(@$rep) {
    my $elt = shift @$rep;
    my $id;
    if(!@path) {
      $id = $self->ha->fetch_root_id;
#      $id = ["machination:hc",$id] if(!@$rep);
    } else {
      if(ref $elt) {
        # last entry
        my ($branch,$type,$name) = @$elt;

        $id = $self->ha->
          fetch_id(
                   $type_id,
                   $name,
                   $path[-1]
                  );
#        $id = [$type_id,$obj_id];
#        $id = undef if(!defined $obj_id);
      } else {
        $id = $self->ha->fetch_id(undef,$elt,$path[-1]);
      }
    }
    if(defined $id) {
      push @path, $id;
    } else {
      unshift @$rep, $elt;
      last;
    }
  }
  wantarray ? return (\@path,$rep) : return \@path;
}

=item B<id>

 $id = $hp->id;
 $id = $hp->id("/other/path");

=cut

sub id {
  my ($self,$rep) = @_;

  my $idpath = $self->id_path($rep);
  return undef unless defined $idpath;
  return $idpath->[-1];
}

=item B<type>

 $type_name = $hp->type
 $type_name = $hp->type("/other/path")

=cut

sub type {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = $self->{rep};
  }

  return $rep->[-1]->[1];
}

=item B<type_id>

 $type_id = $hp->type_id
 $type_id = $hp->type_id("/other/path")

=cut

sub type_id {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = $self->{rep};
  }

  defined $self->type($rep) ?
    return $self->ha->type_id($self->type($rep),{revision=>$self->revision})
      : return "machination:hc";
}

=item B<name>

 $obj_name = $hp->name
 $obj_name = $hp->name("/other/path")

=cut

sub name {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = $self->{rep};
  }

  return $rep->[-1]->[2];
}

sub revision {
  my $self = shift;
  $self->{revision} = shift if(@_);
  return $self->{revision};
}

=item B<parent>

 $parent = $hp->parent;
 $parent = $hp->parent("/other/path");

=cut

sub parent {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = $self->{rep};
  }
  my $p = Machination::HPath->new($self->ha,$rep);
  pop @{$p->{rep}};
  return $p unless(@{$p->{rep}}); # at root - no parent

  # last entry in $p->{rep} should be an arrayref [$branch,$type,$name]
  # and will currently be just the name of an hc
  my $name = pop @{$p->{rep}};
  push @{$p->{rep}}, ['contents',undef,$name];
  return $p;
}

=item B<parent_id>

=cut

sub parent_id {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = $self->{rep};
  }
  return undef if @$rep == 1; # the root
  if (@$rep == 0) {
    IndexException->
      throw("Cannot access the parent of a zero length HPath");
  }
  my ($def, $rem) = $self->defined_id_path($rep);
  if(@$rem > 1) {
    HierarchyException->
      throw("Cannot get parent id: there is more than one undefined id in ancestry");
  }
  if(@$rem) {
    # a remainder - $def goes up to parent
    return $def->[-1];
  } else {
    # no remainder - whole path in $def
    return $self->id_path($rep)->[-2];
  }
}

=item B<string_to_rep>

 $rep = $hp->string_to_rep("/some/path/to/type:name");

 $rep will be ['','some','path','to',['contents','type','name']]

 Used by new to construct the object representation when given a
 string argument.

=cut

sub string_to_rep {
  my $self = shift;
  my $path = shift;
  my @path;

  die "HPath string must begin with \"/\"" unless($path=~/^\//);
  $path eq "/" ? {@path = ("")} : {@path = parse_line("/",0,$path)};
  my $lastelt = pop @path;

  $lastelt =~ s/^::(.*?):://;
  my $branch = $1;
  $branch = 'contents' if(! defined $branch || $branch eq "");
#  $branch = "machination:root" if !@path;
  my ($type,$id);
  if(($type,$id) = $lastelt =~ /^(.*?):(.*)$/) {
    $type = undef if ($type eq "");
    $type = $self->ha->type_name($type) if($type =~ /^\d+$/);
  } else {
    $type = undef; $id = $lastelt;
  }
  push @path, [$branch,$type,$id];
  return \@path;
}

=item B<clone_rep>

 $newrep = $hp->clone_rep;
 $newrep = $hp->clone_rep("/other/path");

=cut

sub clone_rep {
  my ($self,$rep) = @_;
  $rep = $self->{rep} unless defined $rep;

  my @new;
  foreach my $elt (@$rep) {
    if(ref $elt) {
      push @new, [@$elt];
    } else {
      push @new, $elt;
    }
  }

  return \@new;
}

=item B<is_object>

 $bool = $hp->is_object;
 $bool = $hp->is_object("/other/path");

 Return 1 if the path represents an object, 0 if it represents an hc.

=cut

sub is_object {
  my $self = shift;
  my $rep = shift;

  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = $self->{rep};
  }
  defined $rep->[-1]->[1] ? return 1 : return 0;
}

=item B<to_string>

 $strpath = $hp->to_string;

=cut

sub to_string {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
#      $rep = $self->string_to_rep($rep);
      return $rep;
    }
  } else {
    $rep = $self->{rep};
  }

  return "/" if(@$rep == 1);
  my $type;
  if($self->is_object($rep)) {
    $type = $self->type($rep) . ":";
  }
  return "/" . $self->branch_str . $type . $self->name($rep)
    if(@$rep == 2);
  return $self->parent($rep)->to_string . "/" . $self->branch_str .
    $type . $self->name($rep);
}

sub branch {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = $self->{rep};
  }
  return $rep->[-1]->[0];
}
sub branch_str {
  my ($self) = @_;
  $self->branch eq "contents" ? return "" :
    return "::" . $self->branch . "::";
}

=item B<to_mpath>

=cut

sub to_mpath {
  my ($self,$rep) = @_;
  if(defined $rep) {
    if(!ref $rep) {
      $rep = $self->string_to_rep($rep);
    }
  } else {
    $rep = [@{$self->{rep}}];
  }

  shift @$rep; # remove the root entry
  my $mpath = "/hc[machination:root]";

  my ($tag,$branch,$type,$name);
  foreach my $elt (@$rep) {
    if(ref $elt) {
      $branch = $elt->[0];
      if(defined $elt->[1]) {
        $tag = "obj";
        $type = $elt->[1] . ":";
        $name = $elt->[2];
      } else {
        $tag = "hc";
        $type = "";
        $name = $elt->[2];
      }
    } else {
      $tag = "hc";
      $branch = "contents";
      $type = "";
      $name = $elt;
    }
    $mpath .= "/$branch/$tag\[$type$name\]";
  }
  return $mpath;
}

1;
