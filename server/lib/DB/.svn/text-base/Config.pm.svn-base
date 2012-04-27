use strict;
package DB::Config;

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

use XML::LibXML;
use Data::Dumper;
use Carp;
our $AUTOLOAD;

my %fields = (
              dbh => undef,
              prepared_queries => {},
              test_table => "test_table",
              types => {},
              verbosity => 1,
             );

sub new {
  my $class = shift;
  my ($dbh) = @_;
  my $self = {
              _permitted => \%fields,
              %fields,
             };
  bless $self,$class;
  $self->dbh($dbh) if(defined $dbh);
  return $self;
}

sub AUTOLOAD {
  my $self = shift;
  my $type = ref($self)
    or croak "$self is not an object";

  my $name = $AUTOLOAD;
  $name =~ s/.*://;   # strip fully-qualified portion

  unless (exists $self->{_permitted}->{$name} ) {
    croak "Can't access `$name' field in class $type";
  }

  if (@_) {
    return $self->{$name} = shift;
  } else {
    return $self->{$name};
  }
}

sub parser {
    my $self = shift;
    $self->{parser} = XML::LibXML->new unless($self->{parser});
    return $self->{parser};
}

sub generate_array {
    my $self = shift;
    my ($entry,$size) = @_;
    my @arr;
    foreach (1..$size) {
	push @arr, $entry;
    }
    return @arr;
}

sub find_type_ids {
    my $self = shift;
    my ($str) = @_;
    my $major; my $minor;
    my $table = $self->test_table;
    my $test_col = "type_test";
    my $dbh = $self->dbh;

    if(exists $self->types->{$str}) {
	return @{$self->types->{$str}};
    }

    my $save_auto_commit = $dbh->{AutoCommit};
    $dbh->begin_work if($save_auto_commit);
    $dbh->pg_savepoint("find_type_ids");
    my $abort = sub {
	$dbh->pg_rollback_to("find_type_ids");
	$dbh->pg_release("find_type_ids");
	croak(@_);
    };
    
    unless($self->table_exists($table)) {
	eval {$dbh->do("create table $table ();")};
	if($@) {
	    &$abort("find_type_ids could not create" .
		  "test table $table:\n$@");
	}
    }
    my $info = $self->table_info($table);
    if(exists $info->{"atts"}->{$test_col}) {
	eval {
	    $dbh->do("alter table $table drop $test_col;");
	};
	if($@) {
	    &$abort("could not drop test column $test_col:\n$@");
	}
    }
    eval {
	$dbh->do("alter table $table add $test_col $str;");
    };
    if($@) {
	&$abort("Could not add test column $test_col:\n$@");
    }
    $info = $self->table_info($table);
    
    $dbh->pg_rollback_to("find_type_ids");
    $dbh->pg_release("find_type_ids");
    $dbh->{AutoCommit} = $save_auto_commit;

    $self->types->{$str} = \@{$info->{"atts"}->{$test_col}->{"typeids"}};

    return @{$self->types->{$str}};
}

sub config_sequence {
    my $self = shift;
    my ($seq_elt,$opts) = @_;
    unless(ref($seq_elt)) {
	$seq_elt = $self->parser->parse_string($seq_elt)->documentElement;
    }
    my $dbh = $self->dbh;

    my $delete;
    if(exists $opts->{"delete"}) {
	$delete = $opts->{"delete"};
    }

    my $sname = $seq_elt->getAttribute("name");
    print "Checking sequence \"$sname\"\n";
    my $start = $seq_elt->getAttribute("start");
    my $increment = $seq_elt->getAttribute("increment");
    my $minvalue = $seq_elt->getAttribute("minvalue");
    my $maxvalue = $seq_elt->getAttribute("maxvalue");
    my $cache = $seq_elt->getAttribute("cache");
    my $cycle = $seq_elt->getAttribute("cycle");
    $increment = undef if($increment eq "");
    $minvalue = undef if($minvalue eq "");
    $maxvalue = undef if($maxvalue eq "");
    $start = undef if($start eq "");
    $cache = undef if($cache eq "");
    $cycle = undef if($cycle eq "");

    unless($self->sequence_exists($sname)) {
	# no such sequence exists - create one
	my $sql = "create sequence $sname";
	print "  creating sequence \"$sname\"\n";
	$sql .= " start $start" if(defined $start); 
	$sql .= " increment $increment" if(defined $increment);
	$sql .= " minvalue $minvalue" if(defined $minvalue);
	$sql .= " maxvalue $maxvalue" if(defined $maxvalue);
	$sql .= " cache $cache" if(defined $cache);
	$sql .= " cycle" if($cycle);
	$sql .= ";";
	eval {
	    $dbh->do($sql);
	};
	if($@) {
	    croak("could not create sequence $sname:\n$@");
	}
    }

    # the sequence should now exist - make any alterations necessary
    my $info = $self->sequence_info($sname);
    my $changes;
    if($seq_elt) {
	if (defined $increment && $increment != $info->{'increment_by'}) {
	    $changes .= " increment $increment";
	}
	
	$changes .= " minvalue $minvalue" 
	    if(defined $minvalue && $minvalue != $info->{'min_value'});
	
	$changes .= " maxvalue $maxvalue"
	    if(defined $maxvalue && $maxvalue != $info->{'max_value'});
	
	$changes .= " cache $cache"
	    if(defined $cache && $cache != $info->{'cache_value'});

	$cycle = 0 if(lc($cycle) eq "false");
	$cycle = 1 if($cycle);
	if(defined $cycle && $cycle != $info->{'is_cycled'}) {
	    if($cycle) {
		$changes .= " cycle";
	    } else {
		$changes .= " no cycle";
	    }
	}
	
    }

    if($changes) {
	my $sql = "alter sequence $sname$changes;";
	print "  $sql\n";
	$dbh->do($sql);
    }
}

sub config_table_cols {
  my $self = shift;
  my ($table_elt,$opts) = @_;
  unless(ref($table_elt)) {
    $table_elt = $self->parser->parse_string($table_elt)->documentElement;
  }
  my $dbh = $self->dbh;

  my $do_types = 1;
  if(exists $opts->{"types"} && ! $opts->{"types"}) {
    $do_types = 0;
  }
  my $commit = 0;
  if(exists $opts->{"commit"}) {
    $commit = $opts->{commit};
  }
  my $delete = "error";
  if(exists $opts->{"delete"}) {
    $delete = $opts->{"delete"};
  }

  # first find out if the table exists

  my $tname = $table_elt->getAttribute("name");
  print "Checking table $tname\n";

  my $changed = $self->ensure_table_exists($table_elt);
  #    unless($self->table_exists($tname)) {
  #	print "creating table $tname\n";
  #	# this can throw an exception, but we'll not handle it here
  #	$self->create_table($table_elt);
  #    }

  # now the table must exist, make sure it has the right columns
  # and data types

  my $info = $self->table_info($tname,{types=>$do_types});
  #    print Dumper($info);

  my %db_cols_set;
  @db_cols_set{keys %{$info->{"atts"}}} = (undef);
  my %xml_cols_set;
  foreach my $xml_col ($table_elt->findnodes("col")) {
    $xml_cols_set{$xml_col->getAttribute("name")} = undef;
  }
  my %union_set;
  @union_set{keys %db_cols_set} = (undef);
  @union_set{keys %xml_cols_set} = (undef);
  my %dbonly_set = %db_cols_set;
  foreach (keys %xml_cols_set){
    delete($dbonly_set{$_});
  }
  my %xmlonly_set = %xml_cols_set;
  foreach (keys %db_cols_set){
    delete($xmlonly_set{$_});
  }

  #    print "db: " . Dumper(\%db_cols_set);
  #    print "xml: " . Dumper(\%xml_cols_set);
  #    print "union: " . Dumper(\%union_set);
  #    print "dbonly: " . Dumper(\%dbonly_set);
  #    print "xmlonly: " . Dumper(\%xmlonly_set);

  my $changed = 0;

  # delete columns which are only in the db (not yet implemented)
  if(keys %dbonly_set) {
    if($delete eq "ignore") {

    } else {
	    croak("The following columns need deleted: " .
            join(", ",keys(%dbonly_set)));
    }
  }

  # add columns which are only in the XML.
  if(keys %xmlonly_set) {
    $changed = 1;
    foreach my $col (keys %xmlonly_set) {
	    my $col_elt = ($table_elt->
                     findnodes("col[\@name=\"$col\"]"))[0];
	    my $type = $col_elt->getAttribute("type");
	    my $null = $col_elt->getAttribute("nullAllowed");
	    (defined $null && !$null) ? $null = " not null" : $null="";
      my $default = $col_elt->getAttribute("default");
      (defined $default) ? $default = " default $default" : $default="";
	    print "  Adding $col, $type\n";
	    eval {
        $dbh->do("alter table $tname add $col ${type}${null}${default};");
	    };
	    if($@) {
        croak("could not add column $col:\n$@");
	    }
    }
  }

  foreach my $col (keys %union_set) {
    if(exists $xml_cols_set{$col} && exists $db_cols_set{$col}) {
	    # now in the intersection set
	    my $sth = $dbh->column_info(undef,undef,$tname,$col);
	    my $cinfo = $sth->fetchall_hashref("COLUMN_NAME")->{$col};
	    my %pks;
	    foreach ($dbh->primary_key(undef,undef,$tname)) {
        s/\"//g;
        $pks{$_} = undef;
	    }

	    my $celt = ($table_elt->
                  findnodes("col[\@name=\"$col\"]"))[0];
	    my $type = $celt->getAttribute("type");
	    my $nullable = 1;
	    $nullable = $celt->getAttribute("nullAllowed")
        if(defined $celt->getAttribute("nullAllowed"));
	    my ($xml_major,$xml_minor) =
        $self->find_type_ids($type);
	    my ($db_major, $db_minor) =
        @{$info->{"atts"}->{$col}->{"typeids"}};
	    croak("Column $col of table $tname " .
            "has different type from XML\n")
        unless($xml_major == $db_major &&
               $xml_minor == $db_minor);

	    unless(exists $pks{$col}) {
        if($cinfo->{'NULLABLE'} && ! $nullable) {
          print "  setting col $col in table $tname " .
            "to dissallow NULL\n";
          $dbh->do("alter table $tname alter column $col " .
                   "set not null");
        }
        if((! $cinfo->{'NULLABLE'}) && $nullable) {
          #		    print Dumper(\%pks);
          #		    print Dumper($cinfo);
          #		    print !$cinfo->{'NULLABLE'} . ":$nullable\n";
          print "  setting col $col in table $tname to allow NULL\n";
          $dbh->do("alter table $tname alter column $col " .
                   "drop not null");
        }
	    }

      # set column default if any
      my $default = $celt->getAttribute("default");
      if(defined $default) {
        $dbh->do("alter table $tname alter column $col set default ?",
                {},$default);
      }
    }
  }

  print "table $tname done\n";
  return $changed;
}

sub config_table_triggers {
    my $self = shift;
    my ($table_elt) = @_;
    unless(ref($table_elt)) {
	$table_elt = $self->parser->parse_string($table_elt)->documentElement;
    }
    my $dbh = $self->dbh;
    my $tname = $table_elt->getAttribute("name");
    my $info = $self->table_info($tname);
    my $changed = $self->ensure_table_exists($table_elt);

    # Deal with triggers.
    # There doesn't seem to be any way to tell the difference between
    # triggers automatically added by postgres and those added
    # explicitly. We'll only add and modify triggers listed in the XML
    foreach my $trig_elt ($table_elt->findnodes("trigger")) {
	eval {
	    $dbh->do("drop trigger if exists " .
		     $trig_elt->getAttribute("name") .
		     " on $tname");
	    $dbh->do("create trigger " .
		$trig_elt->getAttribute("name") . " " .
		$trig_elt->getAttribute("when") . " on $tname for each " .
		$trig_elt->getAttribute("each") . " execute procedure " .
		$trig_elt->getAttribute("execute") . "()");
	    $changed = 1;
	}
    }

    return $changed;
}

sub config_table_constraints {
    my $self = shift;
    my ($table_elt,$opts) = @_;
    unless(ref($table_elt)) {
	$table_elt = $self->parser->parse_string($table_elt)->documentElement;
    }
    my $dbh = $self->dbh;
    my $tname = $table_elt->getAttribute("name");
    my $info = $self->table_info($tname);
    my $changed = $self->ensure_table_exists($table_elt);

    # make sure the constraints are correct, apart from foreign
    # key constraints, which must be dealt with seperately because
    # they touch multiple tables (the target table/key may not exist
    # yet)

#    print Dumper($info);
#    print "constraints found:\n" . Dumper($info->{"constraints"});

    my %xml_cons;
    foreach my $celt ($table_elt->findnodes("constraint")) {
	$xml_cons{lc($celt->getAttribute('id'))} = $celt;
    }

    # make sure any constraints *not* in the XML file are removed
    foreach my $con (keys %{$info->{"constraints"}}) {
	$con = lc $con;
	next if(exists $xml_cons{$con});
	# remove db constraint
	print "  remove constraint $con\n";
	eval {
	    $dbh->do("alter table $tname drop constraint $con;");
	};
	if($@) {
	    croak("could not drop constraint $con:\n$@");
	}
	$changed = 1;
    }

    # make sure all constraints specified in XML are present and
    # correct (except foreign keys).
    foreach my $con_elt ($table_elt->findnodes("constraint")) {
	my $type = $con_elt->getAttribute("type");
	my $id = lc($con_elt->getAttribute("id"));

	# check to see if constraint is there
	my $addcon = 1;
	if(exists $info->{"constraints"}->{$id}) {
	    $addcon = 0;
	    if($type ne $info->{"constraints"}->{$id}) {
		print "  constraint $id is different from XML - removing\n";
		eval {
		    $dbh->do("alter table $tname drop constraint $id;");
		};
		if($@) {
		    croak("could not drop constraint $id:\n$@");
		}
		$addcon = 1;
		$changed=1;
	    }
	    print "  constraint $id exists\n" unless($addcon);
	}

	# deal with foreign keys later
	if($type eq "FOREIGN KEY") {
	    print "  deferring foreign key constraint $id till later\n";
	    next;
	}

	if($addcon) {
    print "  add constraint $id\n";
    if($type eq "PRIMARY KEY") {
      my @cols;
      foreach my $col ($con_elt->findnodes("col")) {
		    push @cols, $col->getAttribute("name");
      }
      croak("no \"col\" elements found in " .
            "$type constraint $id")
		    unless @cols;
      eval {
		    $dbh->do("alter table $tname add constraint $id $type (" .
                 join(",",@cols) .
                 ");");
      };
      if($@) {
		    croak("could not add constraint $id:\n$@");
      }
      $changed=1;
    } elsif ($type eq "UNIQUE") {
      my @cols;
      foreach my $col ($con_elt->findnodes("col")) {
		    push @cols, $col->getAttribute("name");
      }
      croak("no \"col\" elements found in " .
            "$type constraint $id")
		    unless @cols;
      eval {
		    $dbh->do("alter table $tname add constraint $id $type (" .
                 join(",",@cols) .
                 ");");
      };
      if($@) {
		    croak("could not add constraint $id:\n$@");
      }
      $changed=1;
    } elsif ($type eq "general") {
      my $sql = "alter table $tname add constraint $id " .
		    $con_elt->textContent;
      eval {
		    $dbh->do($sql);
      };
      if($@) {
		    croak("could not add constraint $id " .
              "with SQL:\n$sql\n$@\n");
      }
      $changed=1;
    } else {
      croak("unknown constraint type \"$type\"\n");
    }
	}
}

    return $changed;
}

sub config_table_foreign_keys {
    my $self = shift;
    my ($table_elt,$opts) = @_;
    my $dbh = $self->dbh;
    unless(ref($table_elt)) {
	$table_elt = $self->parser->parse_string($table_elt)->documentElement;
    }
    
    my $changed = 0;

    my $tname = $table_elt->getAttribute("name");
    print "Checking foreign keys for table $tname\n";
    unless($self->table_exists($tname)) {
	croak("config_table_foreign_keys: " .
	      "table \"$tname\" does not exist\n");
    }

    my $info = $self->table_info($tname);
    foreach my $con_elt
	($table_elt->findnodes("constraint[\@type=\"FOREIGN KEY\"]"))
    {
	my $id = lc $con_elt->getAttribute("id");
	print "  checking foreign key constraint $id\n";

	# check to see if constraint is there
#	my $addcon = 1;
#	print Dumper($info->{"constraints"});
	if(exists $info->{"constraints"}->{$id}) {
	    print "  constraint $id exists\n";
	} else {
	    print "  adding foreign key constraint $id\n";
	    my $ftable = $con_elt->getAttribute("refTable");
	    my @cols;
	    my @fcols;
	    foreach my $col ($con_elt->findnodes("col")) {
		push @cols, $col->getAttribute("name");
		push @fcols, $col->getAttribute("refKey");
	    }
	    croak("no \"col\" elements found " .
		  "in FOREIGN KEY constraint $id\n")
		unless @cols;
	    eval {
		$dbh->do("alter table $tname add constraint $id " .
			 "FOREIGN KEY (" .
			 join(",",@cols) .
			 ") references $ftable (" .
			 join(",",@fcols) . ");");
	    };
	    if($@) {
		croak("Could not add FOREIGN KEY to $tname:\n$@");
	    }
	    $changed=1;
	}
    }
    print "table $tname done\n";
    return $changed;
}

sub config_table_all {
    my $self = shift;
    my ($t) = @_;
    $self->config_table_cols($t);
    $self->config_table_constraints($t);
    $self->config_table_foreign_keys($t);
    $self->config_table_triggers($t);
}

sub ensure_table_exists {
    my $self = shift;
    my ($table_elt) = @_;
    unless(ref($table_elt)) {
	$table_elt = $self->parser->parse_string($table_elt)->documentElement;
    }
    my $dbh = $self->dbh;
    my $tname = $table_elt->getAttribute("name");

    return undef if($self->table_exists($tname));

#    print "  Creating table " . $table_elt->getAttribute("name") . "\n";

    my $sql = "create table $tname (\n";
    my @both;
    foreach my $col ($table_elt->findnodes("col")) {
	push @both, $col->getAttribute("name") . " " .
	    $col->getAttribute("type");
    }
    $sql .= join(",\n",@both); 
    $sql .= ");";
#    print "  using sql:\n$sql\n";

    eval {
	$dbh->do($sql);
    };
    if($@) {
	croak("Error creating table $tname using sql:\n" .
	      $sql . ":\n$@");
    }

    return 1;
}

sub find_tables {

}

sub table_info {
    my $self = shift;
    my ($name,$opts) = @_;
    my $dbh = $self->dbh;
    
    my $do_types = 1;
    if(exists $opts->{"types"} && ! $opts->{"types"}) {
	$do_types = 0;
    }
    
    my $info;

    return undef unless($self->table_exists($name));

    $info->{"name"} = $name;
    
    my $sql;
    $sql = "select c.oid from pg_catalog.pg_class c where c.relname = ?;";
    my $sth = $self->prepare_query("find_oid",$sql);
    $sth->execute($name);
    my $oid;
    while(my @row = $sth->fetchrow_array) {
	$oid = $row[0];
    }
#    print "There were " . $sth->rows . " oids returned\n";
    $info->{"oid"} = $oid;

    # find attributes
    $sql = "select a.attname, " .
#	"pg_catalog.format_type(a.atttype, a.)" .
	"a.atttypid, a.atttypmod " .
	"from pg_catalog.pg_attribute a " .
	"where a.attrelid = ? and a.attnum > 0 " .
	"and not a.attisdropped;";
    $sth = $self->prepare_query("find_attributes",$sql);
    $sth->execute($oid);
    while(my @row = $sth->fetchrow_array) {
#	$info->{"atts"}->{$row[0]} = undef;
#	if($do_types) {
	$info->{"atts"}->{$row[0]}->{"typeids"} = [$row[1],$row[2]];
#	}
    }

    # find constraints
    $sql = "select constraint_name, constraint_type " .
	"from information_schema.table_constraints " .
	"where table_name = ?;";
    $sth = $self->prepare_query("find_constraints",$sql);
    $sth->execute($name);
    while(my ($cname,$ctype) = $sth->fetchrow_array) {
#	print "  Found constraint $cname ($ctype)\n";
	# postgresql seems to put it's own check constraints in from version 8
	# or so onwards. We want to ignore those. Might be a better way to do
	# this, but for now we match on the constraint name.
	next if($cname=~/^\d+_${oid}_\d+_not_null$/);
	$info->{"constraints"}->{$cname} = $ctype;
    }

    # find triggers
    $sql = "select t.tgname, t.tgfoid, p.proname " .
	"from pg_catalog.pg_trigger as t, " .
	"pg_catalog.pg_proc as p " .
	"where t.tgrelid = ? and t.tgfoid=p.oid";
    $sth = $self->prepare_query("find_triggers",$sql);
    $sth->execute($oid);
    while(my ($tname,$tfoid,$fname) = $sth->fetchrow_array) {
	$info->{"triggers"}->{$tname} = {
	    function_name=>$fname,
	    function_id=>$tfoid,
	}
    }
    return $info;
}

sub table_exists {
    my $self = shift;
    my ($name) = @_;
    my $dbh = $self->dbh;

    my $sth = $dbh->table_info(undef,"public",$name,undef);
    my $info = $sth->fetchall_hashref("TABLE_NAME");
    exists $info->{$name} ? return 1 : return 0;
}

sub sequence_info {
    my $self = shift;
    my ($name) = @_;
    my $dbh = $self->dbh;

#    my $savec = $dbh->{AutoCommit};
#    $dbh->begin_work if($savec);
#    $dbh->pg_savepoint("sequence_info");

    my $info;
    my $sql = "select * from $name where sequence_name='$name';";
    eval {
	$info = $dbh->
	    selectall_hashref($sql,"sequence_name");
    };

#    $dbh->pg_rollback_to("sequence_info");
#    $dbh->pg_release("sequence_info");
#    $dbh->{AutoCommit} = $savec;

    $info = $info->{$name} if exists $info->{$name};
    return $info;
}

sub sequence_exists {
    my $self = shift;
    my ($name) = @_;
    my $dbh = $self->dbh;

    my $info = $self->sequence_info($name);

    $info = undef unless(exists $info->{last_value});
    $info = undef unless(exists $info->{increment_by});

    $info ? return 1 : return 0;
}

sub prepare_query {
    my $self = shift;
    my ($name,$qstr,$opts) = @_;
    my $dbh = $self->dbh;
    my $prepared_queries = $self->prepared_queries;

    if($opts->{"discard"}) {
	my $sth;
	eval {
	    $sth = $dbh->prepare($qstr);
	};
	if($@) {
	    croak("could not prepare query $qstr:\n$@");
	}
	return $sth;
    }

    if(exists $prepared_queries->{$name}) {

    } else {
	eval {
	    $prepared_queries->{$name}->{"sth"} =
		$dbh->prepare($qstr);
	};
	if($@) {
	    croak("could not prepare query $qstr:\n$@");
	}
	$prepared_queries->{$name}->{"qstring"} = $qstr;
    }
    return $prepared_queries->{$name}->{"sth"};
}

sub constraint_unique {
    my ($dbh,$con_elt) = @_;
}

sub constraint_primary_key {
    my ($dbh,$con_elt) = @_;
}

sub constraint_general {

}

sub config_function {
    my $self = shift;
    my ($felt,$fdir) = @_;
    my $dbh = $self->dbh;
    unless(ref($felt)) {
	$felt = $self->parser->parse_string($felt)->documentElement;
    }

    my $name = $felt->getAttribute("name");
    my $lang = $felt->getAttribute("language");
    my $args = $felt->getAttribute("arguments");
    my $ret = $felt->getAttribute("returns");
    my $file = "$fdir/$name.pl";

    # check if language has been loaded
    my $langs = $dbh->selectall_arrayref
	("select lanname from pg_catalog.pg_language where lanname=?",{},$lang);
    unless(@$langs) {
	# $lang is not installed - try to install it
	$dbh->do("create language ?",{},$lang);
    }

    my $sql = "create or replace function $name($args)";
#    if($args) {
#	$sql .= " ($args)";
#    }
    if($ret) {
	$sql .= " returns $ret";
    }
    $sql .= " as \$$name\$\n";
    open(SCRIPT,$file) || croak "could not open $file to create function $name";
    while(<SCRIPT>) {
	$sql .= $_;
    }
    close SCRIPT;
    $sql .= "\n\$$name\$ language $lang;";

    eval {
	$dbh->do($sql);
    };
    if($@) {
	croak("Error creating function $name using sql:\n" .
	      $sql . ":\n$@");
    }
}

sub cleanup {
    my $self = shift;
    my $prepared_queries = $self->prepared_queries;
    
    foreach my $qname (keys %$prepared_queries) {
	$prepared_queries->{$qname}->{"sth"}->finish;
    }
}

