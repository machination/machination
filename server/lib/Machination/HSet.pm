package Machination::HSet;
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
#use Class::Interface;
#implements("Machination::IReadableSet");
#implements("Machination::IWriteableSet");
use Machination::Exceptions;
use Machination::HObject;
use Data::Dumper;

push @ISA, "Machination::HObject";

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $ha = shift;
  my $id = shift;
  my $self = $this->SUPER::new($ha,$ha->type_id("set"),$id);
  bless $self,$class;
  return $self;
}

sub id {
	my $self = shift;
  if(@_) {
    $self->SUPER::id(shift);
    delete $self->{set_type};
  }
	return $self->SUPER::id;
}

sub is_internal {
	my $self = shift;
  return $self->fetch_data("is_internal")->{is_internal};
}

sub direct {
	my $self = shift;
  if(@_) {
    $self->modify_data($_[0],direct=>$_[1]);
  }
  return $self->fetch_data("direct")->{direct};
}

sub expression {
	my $self = shift;
  if(@_) {
    $self->modify_data($_[0],expression=>$_[1]);
  }
  return $self->fetch_data("expression")->{expression};
}

sub member_type {
	my $self = shift;
  # cache the member_type since it shouldn't change
  return $self->{member_type} if (exists $self->{member_type});

  $self->{member_type} = $self->fetch_data("member_type")->{member_type};
  return $self->{member_type};
}

sub member_allowed {
#  my $self = shift;
#  my $member = shift;

  return 1;
}

sub add_members {
    my $self = shift;
    my $opts = shift;

#    SetException->
#      throw("Member $mid is not allowed in set " . $self->id . "\n")
#        unless($self->member_allowed($mid));

    $self->ha->add_to_set($opts,$self->id,@_);
}

sub remove_members {
    my $self = shift;
    my $opts = shift;

    $self->ha->remove_from_set($opts,$self->id,@_);
}

sub get_direct_query {
  my $self = shift;
  my $opts = shift;

  my $revision = $opts->{revision};
  my $aspart = $opts->{query_as_part};
#  $opts->{qn} = 1 unless($opts->{qn});
  my $data = $self->fetch_data($opts);
  unless(defined $data) {
    die "set " . $self->id . " doesn't exist in revision $revision";
  }
  my $direct = $data->{direct};
  my $id_field = "obj_id";
  my $smtable = "setmembers_";
  my $internal_bool;
  if($data->{is_internal}) {
    $internal_bool = "true";
    $smtable .= $data->{member_type};
  } else {
    $id_field = "obj_rep";
    $smtable .= "external";
    $internal_bool = "false";
  }
  return ("select $internal_bool as is_internal," .
          "?::text as type," .
          "'0' as id where true = false",[$data->{member_type}])
    if($direct eq "EMPTY");
  if(defined $direct) {
    my @svals;
    my @cvals;
    $direct=~s/\s*\&\s*/ and /g;
    $direct=~s/\s*\|\s*/ or /g;
    $direct=~s/\s*!\s*/ not /g;
    my $condition_query =
      "select col,op,val from direct_conditions where id=?";
    if($revision) {
      $condition_query = "select col,op,val from " .
        "(select distinct on (id) id,history_deletes,history_id,col,op,val" .
          " from zzh_direct_conditions where id=?) as q1 " .
            "where history_deletes=false";
    }
    $direct =~ s/(\d+)/
      my $sth = $self->ha->read_dbh->prepare_cached
        ($condition_query,{dbi_dummy=>"HSet.get_direct_query"});
    $sth->execute($1);
    my ($col,$op,$val) = $sth->fetchrow_array;
    $sth->finish;
    $col = "sme.obj_rep" unless($data->{is_internal});
    push @cvals, $val;
    "$col $op ?";
    /ge;
    my $join_word;
    my $search = "select $internal_bool as is_internal," .
      "?::text as type,";
    push @svals, $data->{member_type};
    my $hcols = "history_id,history_deletes";
    if($revision) {
      if($data->{is_internal}) {
        my $conditions;
        $conditions = "and $direct"
          unless($direct eq "UNIVERSAL" || $direct eq "UNIVERSAL+");
        $search=~s/^select/select distinct on (id)/;
        $search .= "id::text,$hcols " .
          "from zzh_objs_". $data->{member_type} .
            " where rev_id <=? $conditions " .
              "order by id,history_id desc";
        $search = "select is_internal,type,id from ($search) as q" .
          $self->ha->imun . " where history_deletes=false";
        push @svals, $revision;
      } else {
        $sq2 = "select member_type from " .
          "(select distinct on (id) " .
            "id,member_type,history_id,history_deletes " .
              "from zzh_objs_" . $self->ha->type_id("set") . " where " .
                "rev_id<=? and id=set_id order by id,history_id desc) " .
                  "as q" . $self->ha->imun . " where " .
                    "history_deletes=false";
        $sq1 = "select distinct on (id) " .
          "obj_rep as id,history_id,history_deletes from " .
            "zzh_setmembers_external as sme where rev_id <= ? and " .
              "($sq2)=? and $direct";
        $search .=  "id from ($sq1) as q" . $self->ha->imun .
          " where history_deletes=false";
        push @svals, $revision, $revision,$data->{member_type};
      }
      my @values = (@svals,@cvals);
      return ($search,\@values);
    } else {
      if($data->{is_internal}) {
        $search = $search . "id::text from objs_" . $data->{member_type};
        $join_word = "where";
      } else {
        $search = $search .
          "sme.obj_rep as id " .
            "from setmembers_external as sme," .
              "objs_" . $self->ha->type_id("set") . " as set "  .
                "where sme.set_id = set.id and set.member_type=?";
        push @svals,$data->{member_type};
        $join_word = "and";
      }
      my @values = (@svals,@cvals);
      return ($search,\@values)
        if($direct eq "UNIVERSAL" || $direct eq "UNIVERSAL+");
      return ("$search $join_word $direct",\@values);
    }
  } else {
    if($revision) {
      return ("select $internal_bool as is_internal," .
              "?::text as type," .
              "${id_field}::text as id from zzh_$smtable " .
              "where set_id=?",
              [$data->{member_type},$data->{id}]);
    } else {
      return ("select $internal_bool as is_internal, " .
              "?::text as type, " .
              "${id_field}::text as id from $smtable" .
              " where set_id=?", [$data->{member_type},$data->{id}]);
    }
  }
}

sub get_expression_query {
  my $self = shift;
  my $opts = shift;

  my $data = $self->fetch_data($opts);
  my $expression = $data->{expression};
  my %seen = ($self->id => undef);
  my %cache = ($self->id => [$expression,$self->get_direct_query($opts)]);
  my @stack = ([$self->id,$expression,undef,""]);
  my @vars;

#  print "expression is $expression\n";

  unless(defined $expression) {
    my $internal_bool = $data->{is_internal} ? "true" : "false";
    return ("select $internal_bool as is_internal," .
            "?::text as type," .
            "'0' as id where true = false",[$data->{member_type}]);
  }

  while(my $a = pop @stack) {
    my ($sid,$e,$pos,$sofar) = @$a;
    pos $e = $pos;
    EXPRESSION_LOOP:
    {
      if($e =~ /\G\s*$/) {
        # end of the expression: $sid is now defined
        delete $seen{$sid};
#        print "$sid is now defined\n";
        if(@stack) {
          $stack[-1]->[3] .= "$sofar)";
        }
        $expression = $sofar;
      }
      $sofar .= " UNION ", redo EXPRESSION_LOOP if($e =~ /\G\s*\+\s*/gc);
      $sofar .= " INTERSECT ", redo EXPRESSION_LOOP if($e =~ /\G\s*\^\s*/gc);
      $sofar .= " EXCEPT ", redo EXPRESSION_LOOP if($e =~ /\G\s*-\s*/gc);
      $sofar .= "(", redo EXPRESSION_LOOP if($e=~/\G\(/gc);
      $sofar .= ")", redo EXPRESSION_LOOP if($e=~/\G\)/gc);
      if(my ($subid) = $e =~ /\G(\d+)/gc) {
        if(exists $seen{$subid}) {
          $sofar .= $cache{$subid}->[1];
          redo EXPRESSION_LOOP;
        }
        $seen{$subid} = undef;
        my $sube;
        my $subd;
        my $subv;
        unless(exists $cache{$subid}) {
          my $set = Machination::HSet->new($self->ha,$subid);
          my $sdata = $set->fetch_data($opts);
          $sube = $cache{$subid}->[0] = $sdata->{expression};
          ($subd,$subv) =  $set->get_direct_query($opts);
          $cache{$subid}->[1] = $subd;
          $cache{$subid}->[2] = $subv;
        }
        my $parent = [$sid,$e,pos $e,$sofar];
        push @stack, $parent;
        if($sube) {
          push @stack, [$subid,$sube,undef,"($subd UNION "];
          push @vars, @$subv;
        } else {
          $parent->[3] .= "$subd";
          push @vars, @$subv;
        }
      }
    }
  }
  return ($expression,\@vars);
}

sub get_all_query {
  my $self = shift;
  my $opts = shift;

  my ($dq,$dv) = $self->get_direct_query($opts);
  my ($eq,$ev) = $self->get_expression_query($opts);
  my $query = "$dq";
  $query .= " UNION ($eq)" if($eq);
  my @vars = (@$dv,@$ev);

  return ($query, \@vars);
}

sub get_query {
  my $self = shift;
  my ($ftype,$opts) = @_;

  my ($q,$p);
  ($q,$p) = $self->get_direct_query($opts) if($ftype eq "direct");
  ($q,$p) = $self->get_expression_query($opts) if($ftype eq "expression");
  ($q,$p) = $self->get_all_query($opts) if($ftype eq "all");
#  $q = "select is_internal,type,id from ($q) as q1 " .
#      "where history_deletes=false" if($opts->{revision});
  return ($q,$p);
}

sub fetcher {
  my $self = shift;
  my ($ftype,$opts) = @_;

  return Machination::HSet::MemberFetcher->new($self,$ftype,$opts);
}

sub fetch_members {
  my $self = shift;
  my $ftype = shift;
  my $opts = shift;

  my $fetcher = $self->fetcher($ftype,$opts);
  $fetcher->prepare_cached;
  $fetcher->execute;
  return $fetcher->fetch_all;
}

sub has_member {
  my $self = shift;
  my ($ftype,$id,$opts) = @_;

  my $dbh = $self->ha->read_dbh;
  $dbh = $opts->{dbh} if($opts->{dbh});
  my $data = $self->fetch_data($opts);

  if (!$data->{is_internal} && $data->{direct} eq "UNIVERSAL") {
    return {is_internal=>$data->{is_internal},
            type=>$data->{type},
            id=>$id};
  }

  my ($q,$p) = $self->get_query($ftype,$opts);
  my $query = "select * from ($q) as members where " .
    "is_internal=? and type=? and id=?";


  my $sth = $dbh->prepare_cached($query,{dbi_dummy=>"HSet.has_member"});
  $sth->execute(@$p,$data->{is_internal},$data->{member_type},$id);
  my $row = $sth->fetchrow_arrayref;
  $sth->finish;

  return $row;
}

sub has_members {
  my $self = shift;
  my ($ftype,$ids,$opts) = @_;
  my $cat = "HSet.has_members";

  my $dbh = $self->ha->read_dbh;
  $dbh = $opts->{dbh} if($opts->{dbh});
  my $data = $self->fetch_data($opts);

  if (!$data->{is_internal} && $data->{direct} eq "UNIVERSAL") {
    my $ret = {};
    foreach my $id (@$ids) {
      $ret->{$id} = {is_internal=>$data->{is_internal},
                     type=>$data->{type},
                     id=>$id};
    }
    return $ret;
  }

  my @id_q;
  foreach (@$ids) {
    push @id_q, "?";
  }
  my ($q,$p) = $self->get_query($ftype,$opts);
  my $query = "select * from ($q) as members where " .
    "is_internal=? and type=? and id in (" . join(",",@id_q) .")";

  $self->ha->log->dmsg($cat,$query,8);
  my $sth = $dbh->prepare_cached($query,{dbi_dummy=>"HSet.has_member"});
  $sth->execute(@$p,$self->is_internal,$self->member_type,@$ids);
  my $rows = $sth->fetchall_hashref("id");
  $sth->finish;

  return $rows;
}

package Machination::HSet::MemberFetcher;
use Data::Dumper;

#push @ISA, "Machination::HFetcher";

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $set = shift;
  my $ftype = shift;
  my $opts = shift;
  my $self = {};
  bless $self,$class;

  $self->set($set);
  $self->ftype($ftype);
  $self->opts($opts);

  return $self;
}

sub set {
	my $self = shift;
  if(@_) {
    # finish any old statement handle if swapping sets
    $self->sth->finish if($self->sth);

    $self->{set} = shift;

    # set up the database handle
    if($self->opts && $self->opts->{dbh}) {
      $self->dbh($self->opts->{dbh});
    } else {
      $self->dbh($self->{set}->ha->read_dbh);
    }

    # invalidate query cache
    delete $self->{query};
  }
	return $self->{set};
}

sub opts {
	my $self = shift;
  if(@_) {
    $self->{opts} = shift;
  }
	return $self->{opts};
}

sub ftype {
	my $self = shift;
  if(@_) {
    my $ftype = shift;
    die "unknown fetch type $ftype"
      unless($ftype eq "direct" || $ftype eq "expression" || $ftype eq "all");
    $self->{ftype} = $ftype;
  }
	return $self->{ftype};
}

sub query {
  my $self = shift;

  return $self->{query} if($self->{query});
  return $self->set->get_query($self->ftype,$self->opts);
}

sub sth {
	my $self = shift;
	$self->{sth} = shift if(@_);
	return $self->{sth};
}

sub dbh {
	my $self = shift;
	$self->{dbh} = shift if(@_);
	return $self->{dbh};
}

sub prepare {
	my $self = shift;
	$self->sth($self->dbh->prepare(($self->query)[0]));
}

sub prepare_cached {
	my $self = shift;
	$self->sth($self->dbh->
						 prepare_cached(($self->query)[0],
														{dbi_dummy=>"HSet::MemberFetcher"}));
}

sub execute {
  my $self = shift;
  my $cat = "MemberFetcher.execute";

  $self->set->ha->log->dmsg($cat,"\n" . Dumper($self->query),8);
  $self->sth->execute(@{($self->query)[1]});
}

sub fetchrow {
  my $self = shift;

  my @row = $self->sth->fetchrow_array;
  return unless @row;

  return \@row;
}

sub fetch_some {
  my $self = shift;
	my ($limit) = @_;
	my @rows;

	my $i = 0;
	while ((($i++) < $limit) && (my $row = $self->fetchrow)) {
		push @rows, $row;
	}
	return @rows;
}

sub fetch_all {
  my $self = shift;

	my @rows;
	while (my $row = $self->fetchrow) {
		push @rows, $row;
	}
	return @rows;
}

sub finish {
  my $self = shift;
  $self->sth->finish;
  $self->{sth} = undef;
}

1;
