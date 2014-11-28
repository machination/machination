use strict;
package DB::Config;

# Copyright 2008, 2014 Colin Higgs and Matthew Richardson
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

=pod

=head1 DB::Config

=head2 Configure database tables based on XML definitions

=head2 Synopsis

=head2 DB::Config Moose Object

=cut

use Moose;
use namespace::autoclean;

use XML::LibXML;
use Data::Dumper;
use Carp;

=head3 Constructing

$dbc = DB::Config->new(dbh=>$dbh);

or

$dbc = DB::Config->new($dbh);

=head3 Properties

=over

=cut

=item B<dbh> (required)

Database handle.

=cut
has 'dbh' => (is=>'ro',
              required=>1);

=item B<schema_path>

Where to find relax-ng schemas. Default
/var/lib/machination/server/database/rng-schemas.

=cut
has 'schema_path' => (is=>'rw',
                      default=>'/var/lib/machination/server/database/rng-schemas');

=item B<table_schema>

Relax-ng schema for table XML.

=cut
has 'table_schema' => (is=>'rw',
                       lazy=>1,
                       builder=>'_build_table_schema');

sub _build_table_schema {
  my $self = shift;

  return XML::LibXML::RelaxNG->new
    (location=>$self->schema_path . "/table.rng");
}

=item B<type_subs>

Database type substitutions. Should be a XML::LibXML::Element
in this form:

<typeSubstitutions>
  <sub name='ID_TYPE' value='bigserial'/>
  <sub name='IDREF_TYPE' value='bigint'/>
  <sub name='OBJECT_NAME_TYPE' value="varchar"/>
  <sub name='OBJECT_NAMEREF_TYPE' value="varchar"/>
</typeSubstitutions>

=cut
has 'type_subs' => (
  is => 'rw'
);

=item B<test_table>

Name of a table where test columns can be created.

=cut
has 'test_table' => (is=>'rw',
                     default=>'test_table');

=item B<types>

Store major and minor ids of types by name. Used to memo-ise find_type_ids.

=cut
has 'types' => (is=>'rw',
                default=>sub {{}});

=item B<verbosity>



=cut
has 'verbosity' => (is=>'rw',
                    default=>0);

=item B<parser>

XML parser for re-use.

=cut
has 'parser' => (is=>'rw',
                 default=>sub {XML::LibXML->new});

=item B<prepared_queries>

=cut
has 'prepared_queries' => (is=>'rw',
                           default=>sub {{}});

around BUILDARGS => sub {
  my $orig  = shift;
  my $class = shift;

  if ( @_ == 1 && (ref($_[0]) ne "HASH")) {
    return $class->$orig( dbh => $_[0] );
  }
  else {
    return $class->$orig(@_);
  }
};

=back

=head3 Methods

=item B<type_sub>

$dbc->type_sub($type_string);

Take a string representing a database column type and
substitute anything of the form {TYPE_NAME} with the
appropriate substitution from $dbc->type_subs.

Die if there is a name in {} but no substitution.

=cut

sub type_sub {
  my $self = shift;
  my $str = shift;

  if(my ($name) = $str=~/\{(.*)\}/) {
    # need to substitute something
    my ($node) = $self->type_subs->findnodes(
      "//sub\[\@name='$name'\]"
    );
    die "There is no substitution for type $name" unless($node);
    return $node->getAttribute("value");
  }
  return $str;
}

=over

=item B<validate_table_xml>

$dbc->validate_table_xml($table_elt or $string);

Validate XMl describing a table against $dbc->table_schema.

=cut

sub validate_table_xml {
  my $self = shift;
  my $table_elt = shift;

  # We pass elements around but libxml2 can only validate documents.
  my $table_doc;
  if(ref($table_elt)) {
    # We can't just go adding elements to documents willy-nilly:
    # better make a clone.
    $table_elt = $table_elt->cloneNode(1);
    $table_doc = XML::LibXML->createDocument;
    $table_doc->setDocumentElement($table_elt);
  } else {
    $table_doc = $self->parser->parse_string($table_elt);
    $table_elt = $table_doc->documentElement;
  }
  # Check the table XML against the schema
  return $self->table_schema->validate($table_doc);
}

=item B<find_type_ids>

($major, $minor) = $dbc->find_type_ids($str);

Find the (postgresql) major and minor type ids of the type named $str

=cut
sub find_type_ids {
  my $self = shift;
  my ($str) = @_;
  my $major; my $minor;
  my $table = $self->test_table;
  my $test_col = "type_test";
  my $dbh = $self->dbh;

  # memo-isation
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

# configure a named sequence. Not used any more?
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
  $self->msg("Checking sequence \"$sname\"\n");
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
    $self->msg("  creating sequence \"$sname\"\n");
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
    $self->msg("  $sql\n");
    $dbh->do($sql);
  }
}

=item B<config_table_cols>

$cfg->config_table_cols($table_elt, $opts)

Add or modify columns as specified in XML element. $table_elt may be
an XML::LibXML::Element or a string containing the appropriate XML.

A full relax-ng schema file for tables should be in
$self->schema_path()

=cut
sub config_table_cols {
  my $self = shift;
  my ($table_elt,$opts) = @_;

  if(!ref($table_elt)) {
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
  $self->msg("Checking table $tname\n");

  my $changed = $self->ensure_table_exists($table_elt);
  #    unless($self->table_exists($tname)) {
  #	$self->msg("creating table $tname\n");
  #	# this can throw an exception, but we'll not handle it here
  #	$self->create_table($table_elt);
  #    }

  # now the table must exist, make sure it has the right columns
  # and data types

  my $info = $self->table_info($tname,{types=>$do_types});
  #    $self->msg(Dumper($info));

  my %db_cols_set;
  @db_cols_set{keys %{$info->{"atts"}}} = (undef);
  my %xml_cols_set;
  foreach my $xml_col ($table_elt->findnodes("column")) {
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

  #    $self->msg("db: " . Dumper(\%db_cols_set));
  #    $self->msg("xml: " . Dumper(\%xml_cols_set));
  #    $self->msg("union: " . Dumper(\%union_set));
  #    $self->msg("dbonly: " . Dumper(\%dbonly_set));
  #    $self->msg("xmlonly: " . Dumper(\%xmlonly_set));

#  my $changed = 0;

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
                     findnodes("column[\@name=\"$col\"]"))[0];
	    my $type = $self->type_sub(
        $col_elt->getAttribute("type")
      );
	    my $null = $col_elt->getAttribute("nullAllowed");
	    (defined $null && !$null) ? $null = " not null" : $null="";
      my $default = $col_elt->getAttribute("default");
      (defined $default) ? $default = " default $default" : $default="";
	    $self->msg("  Adding $col, $type\n");
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
                  findnodes("column[\@name=\"$col\"]"))[0];
	    my $type = $self->type_sub(
        $celt->getAttribute("type")
      );
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
          #		    $self->msg(Dumper(\%pks));
          #		    $self->msg(Dumper($cinfo));
          #		    $self->msg(!$cinfo->{'NULLABLE'} . ":$nullable\n");
          $self->msg("  setting col $col in table $tname to allow NULL\n");
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

  $self->msg("table $tname done\n");
  return $changed;
}

=item B<config_table_triggers>

$cfg->config_table_triggers($table_elt, $opts)

Add or modify triggers as specified in XML element. $table_elt may be
an XML::LibXML::Element or a string containing the appropriate XML.

A full relax-ng schema file for tables should be in
$self->schema_path()

=cut
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

=item B<config_table_constraints>

$cfg->config_table_constraints($table_elt, $opts)

Add or modify constraints as specified in XML element. $table_elt may be
an XML::LibXML::Element or a string containing the appropriate XML.

A full relax-ng schema file for tables should be in
$self->schema_path()

=cut
sub con_type_xml2db {
  my $xmltype = shift;
  return 'FOREIGN KEY' if($xmltype eq "foreignKey");
  return 'UNIQUE' if($xmltype eq "unique");
  return 'PRIMARY KEY' if($xmltype eq "primaryKey");
}
sub con_type_db2xml {
  my $dbtype = shift;
  return 'foreignKey' if($dbtype eq 'FOREIGN KEY');
  return 'unique' if($dbtype eq 'UNIQUE');
  return 'primaryKey' if($dbtype eq 'PRIMARY KEY');
  return 'generic';
}
sub config_table_constraints {
  my $self = shift;
  my ($table_elt,$opts) = @_;
  unless(ref($table_elt)) {
    $table_elt = $self->parser->
      parse_string($table_elt)->documentElement;
  }
  my $dbh = $self->dbh;
  my $tname = $table_elt->getAttribute("name");
  my $info = $self->table_info($tname);
  my $changed = $self->ensure_table_exists($table_elt);

  # make sure the constraints are correct, apart from foreign
  # key constraints, which must be dealt with seperately because
  # they touch multiple tables (the target table/key may not exist
  # yet)

  #    $self->msg(Dumper($info));
  #    $self->msg("constraints found:\n" . Dumper($info->{"constraints"}));

  my %xml_cons;
  foreach my $celt (
    $table_elt->findnodes("constraint"),
    $table_elt->findnodes("primaryKey"))
  {
    $xml_cons{lc($self->constraint_name($tname, $celt))} = $celt;
  }

  # Make sure any constraints *not* in the XML file are removed. This
  # won't check primary key constraints since they come in their own
  # 'primaryKey' elements, but we probably don't want to delete the
  # primary key anyway.
  foreach my $con (keys %{$info->{"constraints"}}) {
    $con = lc $con;
    next if(exists $xml_cons{$con});
    # remove db constraint
    $self->msg("  remove constraint $con\n");
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
  foreach my $con_elt ($table_elt->findnodes("constraint"),
                       $table_elt->findnodes("primaryKey")) {
    my $type;
    if($con_elt->nodeName eq "primaryKey") {
      $type = 'primary key';
    } else {
      $type = $con_elt->getAttribute("type");
    }
    my $id = lc $self->constraint_name($tname, $con_elt);

    # check to see if constraint is there
    my $addcon = 1;
    if(exists $info->{"constraints"}->{$id}) {
	    $addcon = 0;
	    if($type ne lc($info->{"constraints"}->{$id})) {
        $self->msg("  constraint type $type ne " .
          $info->{constraints}->{$id} . "\n");
        $self->msg("  constraint $id is different from XML" .
          " - removing\n");
        eval {
          $dbh->do("alter table $tname drop constraint $id;");
        };
        if($@) {
          croak("could not drop constraint $id:\n$@");
        }
        $addcon = 1;
        $changed=1;
	    }
	    $self->msg("  constraint $id exists\n") unless($addcon);
    }

    # deal with foreign keys later
    if($type eq "foreign key") {
	    $self->msg("  deferring foreign key constraint $id till later\n");
	    next;
    }

    if($addcon) {
      $self->msg("  add constraint $id\n");
      if($type eq "primary key") {
        my @cols;
        foreach my $col ($con_elt->findnodes("column")) {
          push @cols, $col->getAttribute("name");
        }
        croak("no \"column\" elements found in " .
              "$type constraint $id")
          unless @cols;
        eval {
          $dbh->do("alter table $tname add constraint $id PRIMARY KEY (" .
                   join(",",@cols) .
                   ");");
        };
        if($@) {
          croak("could not add constraint $id:\n$@");
        }
        $changed=1;
      } elsif ($type eq "unique") {
        my @cols;
        foreach my $col ($con_elt->findnodes("column")) {
          push @cols, $col->getAttribute("name");
        }
        croak("no \"column\" elements found in " .
              "$type constraint $id")
          unless @cols;
        eval {
          $dbh->do("alter table $tname add constraint $id UNIQUE (" .
                   join(",",@cols) .
                   ");");
        };
        if($@) {
          croak("could not add constraint $id:\n$@");
        }
        $changed=1;
      } elsif ($type eq "generic") {
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

=item B<constraint_name>

$con_name = $self->constraint_name($table_name, $con_elt);

Auto-generate a constraint name from a constraint element.

=cut
sub constraint_name {
  my $self = shift;
  my $table_name = shift;
  my $con_elt = shift;

  # If $con_elt has a name attribute, return that.
  if($con_elt->hasAttribute('name')) {
    return $con_elt->getAttribute('name');
  }

  # Autoconstruct a name.
  my @name = ('c', $table_name);
  # Primary keys are dealt with differently.
  if($con_elt->nodeName eq 'primaryKey') {
    push @name, "pk";
  } else {
    # Constraint name lengths are somewhat limited: use short versions of
    # constraint types.
    my $ctype = $con_elt->getAttribute('type');
    if($ctype eq "foreignKey") {
      push @name, "fk";
    } elsif($ctype eq 'unique') {
      push @name, "un";
    } elsif($ctype eq 'generic') {
      push @name, "gn";
    }
    # Put the columns involved in the constraint into the name.
    push @name, map {$_->nodeValue} $con_elt->findnodes('column/@name');
  }
  map {$_ =~ s/(_+)(.)/\u$2/g} @name;
  return join("_", @name);
}

=item B<config_table_foreign_keys>

$self->config_table_foreign_keys($table_elt, $opts);

Add or remove foreign key constraints for table described in $table_elt.

=cut
sub config_table_foreign_keys {
  my $self = shift;
  my ($table_elt,$opts) = @_;
  my $dbh = $self->dbh;
  unless(ref($table_elt)) {
    $table_elt = $self->parser->parse_string($table_elt)->documentElement;
  }

  my $changed = 0;

  my $tname = $table_elt->getAttribute("name");
  $self->msg("Checking foreign keys for table $tname\n");
  unless($self->table_exists($tname)) {
    croak("config_table_foreign_keys: " .
          "table \"$tname\" does not exist\n");
  }

  my $info = $self->table_info($tname);
  foreach my $con_elt
    ($table_elt->findnodes("constraint[\@type=\"foreignKey\"]"))
      {
        my $id = lc($self->constraint_name($tname, $con_elt));
        $self->msg("  checking foreign key constraint $id\n");

        # check to see if constraint is there
        #	my $addcon = 1;
        #	$self->msg(Dumper($info->{"constraints"}));
        if(exists $info->{"constraints"}->{$id}) {
          $self->msg("  constraint $id exists\n");
        } else {
          $self->msg("  adding foreign key constraint $id\n");
          my $ftable = $con_elt->getAttribute("refTable");
          my @cols;
          my @fcols;
          foreach my $col ($con_elt->findnodes("column")) {
            push @cols, $col->getAttribute("name");
            push @fcols, $col->getAttribute("references");
          }
          croak("no \"column\" elements found " .
                "in foreignKey constraint $id\n")
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
  $self->msg("table $tname done\n");
  return $changed;
}

=item B<config_table_all>

$cfg->config_table_all($table_elt);

=cut
sub config_table_all {
  my $self = shift;
  my ($t) = @_;
  $self->config_table_cols($t);
  $self->config_table_constraints($t);
  $self->config_table_foreign_keys($t);
  $self->config_table_triggers($t);
}

=item B<ensure_table_exists>

$cfg->ensure_table_exists($table_elt);

=cut
sub ensure_table_exists {
  my $self = shift;
  my ($table_elt) = @_;
  unless(ref($table_elt)) {
    $table_elt = $self->parser->parse_string($table_elt)->documentElement;
  }
  my $dbh = $self->dbh;
  my $tname = $table_elt->getAttribute("name");

  return undef if($self->table_exists($tname));

  #    $self->msg("  Creating table " . $table_elt->getAttribute("name") . "\n");

  my $sql = "create table $tname (\n";
  my @both;
  foreach my $col ($table_elt->findnodes("column")) {
    push @both, $col->getAttribute("name") . " " .
	    $self->type_sub($col->getAttribute("type"));
  }
  $sql .= join(",\n",@both);
  $sql .= ");";
  #    $self->msg("  using sql:\n$sql\n");

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
#    $self->msg("There were " . $sth->rows . " oids returned\n");
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
#	$self->msg("  Found constraint $cname ($ctype)\n");
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
  $args = '' unless defined $args;

  # check if language has been loaded
  my $langs = $dbh->selectall_arrayref
    ("select lanname from pg_catalog.pg_language " .
      "where lanname=?",{},$lang);
  unless(@$langs) {
	  # $lang is not installed - try to install it
	  $dbh->do("create language ?",{},$lang);
  }

  my $sql = "create or replace function $name($args)";
  if($ret) {
	   $sql .= " returns $ret";
  }
  $sql .= " as \$$name\$\n";
  open(SCRIPT,$file) ||
    croak "could not open $file to create function $name";
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

sub msg {
  my $self = shift;
  if($self->verbosity) { print @_; }
}

=back

=cut

1;
